# APPL_DB BUFFER_* — プラットフォーム差調査

Task F Phase H: `BufferOrch` (`sonic-swss/orchagent/bufferorch.cpp` @ ref `4305596156d70e9797e8a881b3d19b46de0bce0d`) のプラットフォーム / ASIC / chassis 構成差を精読した結果。

## 結論

**プラットフォーム差あり**。bufferorch は単一バイナリで動作するが、(a) `gMySwitchType == "voq"` による chassis VOQ 経路、(b) SAI capability に応じた `SAI_STATUS_NOT_IMPLEMENTED` / `SAI_STATUS_NOT_SUPPORTED` の動的判定、(c) ベンダ buffer pool Lua plugin (Mellanox/Barefoot)、の 3 点で挙動が分岐する。Broadcom/Mellanox の PG/queue マップ自体は bufferorch ではなく SAI ベンダ実装に閉じる。

## 1. VOQ chassis (Cisco 8000 系) 分岐

`gMySwitchType == "voq"` を 5 か所で評価。

| 行 | 経路 | non-VOQ との差 |
|---|---|---|
| L116 / L132 | `initBufferReadyList()` 内で `BUFFER_QUEUE_TABLE` を `initVoqBufferReadyList()` に振り替え | VOQ では system port (`<host>\|<asic>\|<port>`) ベースの ready list を別管理 |
| L916 | `processQueue()` の key tokens 数判定 (`== 4` を強制) | non-VOQ は 2 トークン (`<port>\|<range>`)。VOQ は 4 トークン (`<host>\|<asic>\|<port>\|<range>`) |
| L1049 | queue id 取得を `gPortsOrch->getPortVoQIds(port)` に切替 | non-VOQ は `port.m_queue_ids[ind]` |
| L1066-1070 (lock retry) | VOQ 経路では queue lock 判定をスキップ | non-VOQ のみ `m_queue_lock[ind]` チェック → `task_need_retry` |
| L1136 | flex counter の Queue Counter 追加を **non-VOQ のみ** 実施 | VOQ では `flexcounterorch` が全 egress/VOQ queue を一括登録するため bufferorch 側で重複作成しない |
| L1168 | port ref counter 更新を non-VOQ のみ実施 | VOQ では system port が動的生成/削除されないため不要 |
| L2079 | `doTask()` 起動ガードを `gPortsOrch->isInitDone()` に変更 | non-VOQ は `isConfigDone()` |

→ VOQ chassis では (i) BUFFER_QUEUE のキー形式・(ii) queue id 解決・(iii) flex counter 自動登録範囲・(iv) port ref counter 不要、の 4 点で振る舞いが変わる。BUFFER_PG_TABLE 側には VOQ 分岐がないため PG キーは常に 2 トークン (`<port>\|<range>`)。

## 2. SAI capability 動的判定 (ASIC ベンダ依存)

bufferorch は静的にベンダ名 (`broadcom` / `mellanox` 等) を判定しない。代わりに **SAI 戻り値で実行時に capability を検出する**:

### 2-A. buffer pool watermark clear (L310-322 + surrounding)

```cpp
sai_status_t status = sai_buffer_api->clear_buffer_pool_stats(...);
if (status == SAI_STATUS_NOT_SUPPORTED || status == SAI_STATUS_NOT_IMPLEMENTED)
{
    SWSS_LOG_NOTICE("Clear watermark failed on %s, rv: %s", ...);
    noWmClrCapability |= bitMask;
}
```

pool ごとに 32 bit のビットマスク `noWmClrCapability` に capability を記録。**Broadcom DNX 系 / Cisco-8000 系で ingress watermark clear 未サポートのプールが存在する** ことを前提にした実装。bufferorch は 32 プールまでしか想定していない (コメント L313)。

### 2-B. buffer pool 属性 SET (L506-512)

```cpp
sai_status = sai_buffer_api->set_buffer_pool_attribute(sai_object, &attribute);
if (SAI_STATUS_ATTR_NOT_IMPLEMENTED_0 == sai_status)
{
    SWSS_LOG_NOTICE("Buffer pool SET ... not implemented. Ignoring it");
    return task_process_status::task_ignore;
}
```

属性未実装は `task_ignore` で握り潰し → ASIC 差分を吸収。例えば一部 ASIC で `SAI_BUFFER_POOL_ATTR_XOFF_SIZE` の動的変更が未実装でも、APPL_DB 反映自体は成功扱いになる。

### 2-C. buffer profile 属性 SET (L773-777)

```cpp
if (SAI_STATUS_ATTR_NOT_IMPLEMENTED_0 == sai_status)
{
    return task_process_status::task_ignore;
}
```

→ **`xon_offset` (`SAI_BUFFER_PROFILE_ATTR_XON_OFFSET_TH`) を非対応な ASIC では `task_ignore` でスキップされる**。CONFIG_DB / APPL_DB に値が残っていてもハードウェアには反映されない（silent skip）。bufferorch はベンダ名を知らないため、ユーザは SAI vendor 仕様を参照する必要がある。

### 2-D. profile SET 即時 retry (L778-797)

profile 属性のみ「同じ attr で 1 回だけ再試行」する経路を持つ (defaults / failure block 参照)。pool 側にはこの即時 retry はない。これは Mellanox SAI / Broadcom SAI で transient な busy 状態が発生する実装差を吸収するもの。

### 2-E. packet_discard_action=trim (L730-744)

```cpp
else if (value == BUFFER_PROFILE_PACKET_DISCARD_ACTION_TRIM)
{
    attr.value.s32 = SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP_AND_TRIM;
}
```

`trim` 指定時の SAI 属性は `SAI_BUFFER_PROFILE_PACKET_ADMISSION_FAIL_ACTION_DROP_AND_TRIM`。SAI で packet trimming feature を実装していないベンダ (= ほぼ全プラットフォームを除く Broadcom XGS の一部) では `SAI_STATUS_ATTR_NOT_IMPLEMENTED_0` が返り `task_ignore` 経由でスキップされる。さらに **trimming-eligible profile を PG / profile-list に貼ろうとすると `task_failed`** になる (L1382-1388 / L1728 / L1918, defaults block 参照)。

## 3. buffermgrdyn の Lua plugin (ベンダ別ファイル)

`buffermgrdyn.cpp` は dynamic buffer model 時に **`buffer_pool_<platform>.lua` を SAI で実行** してプールサイズを計算する。プラットフォーム特定は SONiC build 時に `device/<vendor>/<platform>/<HWSKU>/buffers_dynamic.json.j2` から差し込まれる。

- Mellanox SN シリーズ: `buffer_pool_mlnx.lua` (例: `device/mellanox/x86_64-mlnx_msn*/`)
- Barefoot Tofino: `buffer_pool_bfn.lua`
- Broadcom: ほとんどの platform で **dynamic buffer model 未採用** → static buffer model (= `buffermgr` 経由) で配布される pre-computed JSON が使われる

→ ユーザは `buffermgrdyn` がいるか `buffermgr` がいるかで挙動が変わる。`BUFFER_POOL_TABLE.size` が空のとき:

- Mellanox/Barefoot (dynamic): Lua plugin が後から書き戻す
- Broadcom (static): `buffermgr` が CONFIG_DB の値をそのまま pass-through (空のままなら APPL_DB にも空)

## 4. PG/queue マップ自体は bufferorch の関心外

PG (priority group) と queue の物理 → SAI object id マッピングは:

- `portsorch` (`PortsOrch::initPort()`) が `sai_get_port_attribute` で `SAI_PORT_ATTR_INGRESS_PRIORITY_GROUP_LIST` / `SAI_PORT_ATTR_QOS_QUEUE_LIST` を取得して `port.m_priority_group_ids` / `port.m_queue_ids` に格納
- bufferorch は L1049 / `port.m_priority_group_ids[ind]` 経由で **既に解決済みの SAI oid を index で引くだけ**

→ Broadcom (例: 8 PG × 8 queue per port) と Mellanox (例: 同 8/8 だが内部 buffer 構造が異なる) の差は SAI ベンダ実装の中にあり、bufferorch には現れない。**PG/queue 数の上限チェック** だけ bufferorch にある (L1058-1061 `m_queue_ids.size() <= ind` / processPriorityGroup の同等 check)。範囲外は `task_invalid_entry`。

## 5. multi-asic / namespace 差

`gMySwitchType == "voq"` 以外に `gMyHostName` / `gMyAsicName` を参照 (L1062-1064):

```cpp
boost::algorithm::to_lower(tmp_token_1);
boost::algorithm::to_lower(tmp_gMyAsicName);
if ((tokens[0] == gMyHostName) && (tmp_token_1 == tmp_gMyAsicName))
{
   local_port = true;
}
```

VOQ chassis の他 line card 宛 BUFFER_QUEUE エントリでも自 ASIC 経由で受信するが、`local_port = false` の system port は SAI bind を行わず ready list 管理のみ。multi-asic non-VOQ (例: T2 chassis BGP-only) では BUFFER_* テーブルは各 asicX namespace の独立した bufferorch インスタンスで処理され、host 横断の干渉はない。

## まとめ表

| 差分点 | 影響テーブル | ベンダ依存？ | 検出方法 |
|---|---|---|---|
| BUFFER_QUEUE key 形式 (2 vs 4 token) | BUFFER_QUEUE_TABLE | switch type (chassis) | `gMySwitchType == "voq"` |
| queue id 解決経路 | BUFFER_QUEUE_TABLE | switch type | 同上 |
| flex counter 自動登録 | BUFFER_QUEUE_TABLE | switch type | 同上 |
| port ref counter | BUFFER_QUEUE_TABLE / BUFFER_PG_TABLE | switch type | 同上 |
| watermark clear capability | BUFFER_POOL_TABLE | ASIC vendor | SAI status (実行時) |
| `xon_offset` 反映 | BUFFER_PROFILE_TABLE | ASIC vendor | SAI status (実行時) |
| `packet_discard_action=trim` | BUFFER_PROFILE_TABLE | ASIC vendor | SAI status (実行時) |
| Lua plugin による size 自動計算 | BUFFER_POOL_TABLE | vendor build asset | `buffer_pool_<vendor>.lua` 配布有無 |
| dynamic vs static buffer model | BUFFER_* 全体 | vendor build choice | `buffermgrdyn` vs `buffermgr` |

## 証跡

- `sonic-swss/orchagent/bufferorch.cpp` L116/L132/L310-322/L506-512/L671-674/L730-744/L773-797/L916/L1049-1064/L1066-1070/L1134-1136/L1166-1168/L1382-1388/L1728/L1918/L2079 全行読了
- VOQ 分岐 grep `gMySwitchType` 5 hit 全件確認
- `SAI_STATUS_NOT_IMPLEMENTED` / `SAI_STATUS_NOT_SUPPORTED` 全 hit 確認 (3 か所)
- buffermgrdyn の Lua plugin 呼び出しは `buffermgrdyn.cpp` 経由 (defaults block 既出)
