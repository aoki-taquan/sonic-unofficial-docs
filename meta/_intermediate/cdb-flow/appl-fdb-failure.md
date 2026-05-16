# APPL_DB FDB_TABLE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-appl-fdb)

ソース: `sonic-net/sonic-swss` `orchagent/fdborch.cpp` (master)

## 1. SET 失敗パス / retry マトリクス

`FdbOrch::doTask(Consumer&)` / `addFdbEntry()` を全行精読し、書込失敗・retry・silent-ignore 経路を抽出した。

| # | トリガー | 検出箇所 | 結果 | retry / 救済 |
|---|---------|---------|------|------|
| 1 | `allPortsReady()` が false (PortsOrch 初期化未完了) | `fdborch.cpp:711-714` | `doTask()` 冒頭 `return` で全 FDB イベント処理停止。`m_toSync` 滞留 | あり (Orch スケジューラ次回呼出で再評価。無限ポーリング) |
| 2 | key の `<VlanName>` に対応する VLAN 未作成 (`getPort(keys[0], vlan)` 失敗) | `fdborch.cpp:738-761` | SET は `it++` で次周回再試行。DEL は `deleteFdbEntryFromSavedFDB()` だけ実行して `m_toSync.erase` | SET: あり (自動ポーリング)。DEL: 冪等成功 |
| 3 | `port` フィールドのポートが未作成 / `bridge_port_id == SAI_NULL_OBJECT_ID` | `addFdbEntry()` `fdborch.cpp:1297-1304` | `saved_fdb_entries[port_name]` に push して **呼出側へ `return true`**（`m_toSync` から消える） | あり (PortsOrch observer 経由 `updateVlanMember(add=true)` で **自動 replay**) |
| 4 | `port` が VLAN メンバーでない (`isVlanMember()` 失敗) | `addFdbEntry()` `fdborch.cpp:1312-1319` | 同上 `saved_fdb_entries` に保留 → `return true` | あり (`updateVlanMember()` 通知で自動 replay) |
| 5 | VXLAN_FDB_TABLE 経路で `remote_ip` 空 | `doTask()` `fdborch.cpp:838-841` | `m_toSync.erase` で **破棄**。保留せず | なし。再投入が必要 |
| 6 | VXLAN_FDB_TABLE 経路で VTEP / tunnel 未作成 (`getEVPNVtep() == NULL`) | `doTask()` `fdborch.cpp:847-855` | 同上 `m_toSync.erase` で破棄 | なし。tunnel 先行作成必須 |
| 7 | 不正な `type` 値 (`"dynamic"` / `"dynamic_local"` / `"static"` 以外) | `doTask()` `fdborch.cpp:830` `assert()` | **orchagent プロセスクラッシュ** (NDEBUG 無効ビルドのみ。リリースビルドでは未定義動作) | なし (fail-fast) |
| 8 | 不正な VNI (`stoi` 例外) | `doTask()` `fdborch.cpp:818-823` | `SWSS_LOG_INFO("Invalid VNI in remote MAC ...")` → `vni=0; break` で当該 fv ループ脱出。後続処理は継続 | なし (vni=0 でそのまま投入) |
| 9 | 不正な remote IP (parse 例外) | `doTask()` `fdborch.cpp:802-807` | `SWSS_LOG_NOTICE("Invalid IP address in remote MAC ...")` → `break` で当該 fv ループ脱出 | なし (`remote_ip` 空のまま VXLAN 経路 → #5 に合流) |
| 10 | SAI `create_fdb_entry()` 失敗 (新規作成) | `addFdbEntry()` 末尾 (L1519 周辺) | `SWSS_LOG_ERROR("Failed to create FDB ...")` → `handleSaiCreateStatus(SAI_API_FDB, status)` 経由で `task_need_retry` / `task_failed` / `parseHandleSaiStatusFailure()` | あり (一時エラーは Orch 共通 retry 機構)。恒久エラーは process exit (`parseHandleSaiStatusFailure`) |
| 11 | SAI `set_fdb_entry_attribute()` 失敗 (MAC update) | `addFdbEntry()` `fdborch.cpp:1505-1517` | 同上 `handleSaiSetStatus()` | あり (同上) |
| 12 | SAI `remove_fdb_entry()` 失敗 | `removeFdbEntry()` `fdborch.cpp:1701-1710` | `SWSS_LOG_ERROR` → `handleSaiRemoveStatus()` | 状況依存 (コメント `FIXME: it should be based on status. Some could be retried` あり) |
| 13 | DEL で `fdbData.origin != origin` (投入元と異なる origin から DEL) | `removeFdbEntry()` `fdborch.cpp:1666-1690` | `deleteFdbEntryFromSavedFDB()` のみ呼んで `return true`（**silently ignored**）。例外: MCLAG ピアポート oper-down 時のみ LEARN として削除続行 | なし (設計上の silent ignore) |
| 14 | DEL で `m_entries` に存在しない MAC | `removeFdbEntry()` `fdborch.cpp:1646-1654` | `SWSS_LOG_INFO` のみ。`saved_fdb_entries` クリーンアップして `return true` (冪等) | n/a (成功扱い) |
| 15 | DEL で `getPortByBridgePortId()` 失敗 | `removeFdbEntry()` `fdborch.cpp:1659-1663` | `SWSS_LOG_NOTICE` → `return false` | あり (`m_toSync` に残り次周回再試行) |
| 16 | DEL で `getPort(bv_id, vlan)` 失敗 | `removeFdbEntry()` `fdborch.cpp:1640-1644` | `SWSS_LOG_NOTICE` → `return false` | あり (次周回再試行) |
| 17 | 不明 op_type (SET/DEL 以外) | `doTask()` `fdborch.cpp:917-918` | `SWSS_LOG_ERROR("Unknown operation type %s")` → `m_toSync.erase` で破棄 | なし |

## 2. retry / 自動調停の構造

### 2.1 doTask 周回再試行 (VLAN 未解決時)

```cpp
// fdborch.cpp:739-758  (SET 経路)
if (!m_portsOrch->getPort(keys[0], vlan)) {
    if (op == DEL_COMMAND) {
        deleteFdbEntryFromSavedFDB(...);
        it = consumer.m_toSync.erase(it);
    } else {
        it++;          // <-- SET は erase せず次周回再評価
    }
    continue;
}
```

VLAN が後から作成されると `Orch::doTask()` の次回スケジュールで `getPort()` が成功して
書込が完了する。**明示的な backoff / sleep は無く**、orchagent の select-loop 駆動。

### 2.2 saved_fdb_entries による保留

```cpp
// fdborch.cpp:1297-1320  (addFdbEntry 経路)
if (!m_portsOrch->getPort(port_name, port) || (port.m_bridge_port_id == SAI_NULL_OBJECT_ID)) {
    saved_fdb_entries[port_name].push_back({entry.mac, vlan.m_vlan_info.vlan_id, fdbData});
    return true;       // <-- 呼出側からは成功扱い → m_toSync から消える
}
if (!m_portsOrch->isVlanMember(vlan, port, end_point_ip)) {
    saved_fdb_entries[port_name].push_back({...});
    return true;
}
```

`m_portsOrch->attach(this)` (`fdborch.cpp:39`) で observer 登録されており、
`updateVlanMember(add=true)` のタイミングで `saved_fdb_entries[port_name]` を走査して
`addFdbEntry()` を再実行する (`fdborch.cpp:1240-1275`)。

### 2.3 VXLAN 経路は救済なし

```cpp
// fdborch.cpp:838-855
if(origin == FDB_ORIGIN_VXLAN_ADVERTIZED) {
    if (tunnel_orch->isDipTunnelsSupported()) {
        if(!remote_ip.length()) {
            it = consumer.m_toSync.erase(it);  // <-- 破棄
            continue;
        }
        ...
    } else {
        VxlanTunnel* sip_tunnel = evpn_nvo_orch->getEVPNVtep();
        if (sip_tunnel == NULL) {
            it = consumer.m_toSync.erase(it);  // <-- 破棄
            continue;
        }
        ...
    }
}
```

VTEP / tunnel の事後作成では replay されない。BGP/EVPN による再 advertise 待ち。

## 3. silent ignore パターン

`fdborch.cpp` には **エラーログを出さず無視** する経路が複数存在する:

| 経路 | 箇所 | 理由 |
|---|---|---|
| DEL with `m_entries` に未登録 MAC | L1646 | 二重 DEL / 学習前 DEL の冪等性確保 |
| DEL with `fdbData.origin != origin` | L1666 | クロス origin 削除を抑止 (例: BGP が remote → local 移行した MAC を削除してもローカル MAC を維持) |
| `assert()` パスのうちリリースビルド | L830 | `NDEBUG` 有効ビルドでは assert が消えるため不正 type は素通り（その後の SAI mapping で `dynamic_local` 以外は `STATIC` に倒れる） |

`assert(type == ...)` は **設計上クラッシュさせる入力検証** であり、Producer 側
(`vlanmgr`, `swssconfig`, `fdbsyncd`) で値の妥当性を保証する前提。

## 4. SAI 失敗時の共通 handler

`handleSaiCreateStatus` / `handleSaiSetStatus` / `handleSaiRemoveStatus` は
`Orch` 基底クラスで定義され、SAI status code 別に下記を返す:

- `task_success` — 成功または無視可能
- `task_need_retry` — `m_toSync` 残置で再試行
- `task_failed` — 当該イベントを破棄
- それ以外 → `parseHandleSaiStatusFailure()` で **`abort()` 相当のプロセス終了**

`FdbOrch::addFdbEntry()` (L1505-1517, L1535-1544) と
`removeFdbEntry()` (L1700-1710) は全て上記 handler 経由でステータスを処理し、
**FdbOrch 固有の retry queue は持たない**（Orch 共通の `m_toSync` 滞留に委譲）。

## 5. type 不一致 silent ignore (補足)

CONFIG_DB / APPL_DB 経由で `type=static` のエントリを投入後、
別 origin（例: `VXLAN_FDB_TABLE` から）で同じ MAC を DEL しても
`removeFdbEntry()` L1666-1690 で `origin` 不一致と判定され、
**ログ `SWSS_LOG_INFO` のみで成功扱い** となり実エントリは残存する。

このため運用上は「投入と同じ origin から DEL する」必要があり、
APPL_DB を直接 DEL するクライアントは origin を区別できない点に注意。

## 6. 観測手段

```bash
# 失敗ログ抽出
docker logs swss 2>&1 | grep -iE 'fdborch|fdb.*fail|Failed to (create|remove) FDB|Saving a fdb entry'

# m_toSync 滞留の間接観測 (CounterDB の Orch task カウンタ)
redis-cli -n 2 KEYS 'COUNTERS_FDB_TABLE*'

# saved_fdb の MAC 数 (orchagent 再起動時の warm restart ログ)
docker logs swss 2>&1 | grep -i 'saved.*fdb\|Add warm input FDB State'
```

## 7. STATE_DB への失敗反映

`FdbOrch` は STATE_DB の `ERROR_*` 系には書込まない。失敗時の参照点は syslog のみ。
ローカル MAC の `port` / `type` のみ STATE_DB `FDB_TABLE` (`m_fdbStateTable`) に
書込み、失敗時は当然 STATE_DB エントリも作成されない (`fdborch.cpp:1569-1582`)。
