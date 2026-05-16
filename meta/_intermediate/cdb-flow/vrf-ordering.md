# VRF テーブル — 書込み順依存調査メモ (Phase B)

調査日: 2026-05-15
調査対象:
- `sonic-swss/cfgmgr/vrfmgr.cpp`
- `sonic-swss/orchagent/vrforch.cpp`
- `sonic-swss/orchagent/vrforch.h`
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-utilities/config/main.py`

---

## 1. 書込み順制約（CREATE 側）

### 1-1. VRF は INTERFACE より先に書く必要がある

`intfmgrd` の `doIntfGeneralTask()` では `vrf_name` フィールドが指定されている場合、
`isIntfStateOk(vrf_name)` を呼んで STATE_DB の `VRF_TABLE|<name>` エントリを確認する。

```cpp
// intfmgr.cpp:839-842
if (!vrf_name.empty() && !isIntfStateOk(vrf_name))
{
    SWSS_LOG_DEBUG("VRF is not ready, skipping %s", vrf_name.c_str());
    return false;
}
```

`isIntfStateOk` は STATE_DB の `STATE_VRF_TABLE|<name>` を参照する。
`vrfmgrd` は VRF SET 後に `ip link add <name> type vrf table <id>` を実行し、
成功したら `m_stateVrfTable.set(vrfName, {{"state","ok"}})` を書く（vrfmgr.cpp:289）。

**順序制約**: `VRF|<name>` を書いてから `STATE_DB.VRF_TABLE` が ok になるまで、
`*_INTERFACE|<port>` の `vrf_name` 指定は Consumer キューに残り続ける。
逆順に書いても最終収束するが、vrfmgrd の Linux VRF 作成完了を待つ必要がある。

### 1-2. orchagent 側の VRF 確認（二段階依存）

`intfsorch.cpp` の `doTask()` でも `m_vrfOrch->isVRFexists(vrf_name)` を確認し、
VRF OID が orchagent 内に存在しなければキューに戻す。

CONFIG_DB → vrfmgrd → APP_DB → VrfOrch → SAI、という経路を経るまでの間、
INTERFACE エントリも待機キューに留まる二段階依存がある。

### 1-3. vni 設定は VRF 作成後かつ VXLAN_TUNNEL_MAP 後

`config vrf add_vrf_vni_map` (config/main.py:7740) は:
1. `VRF` テーブルに対象 VRF が存在するか確認 → なければ `ctx.fail()`
2. `VXLAN_TUNNEL_MAP` テーブルに同 VNI のマップが存在するか確認 → なければ `ctx.fail()`

```python
# main.py:7743-7760
if vrfname not in config_db.get_table('VRF').keys():
    ctx.fail("vrf {} doesn't exist".format(vrfname))
...
if (found == 0):
    ctx.fail("VLAN VNI not mapped. Please create VLAN VNI map entry first")
```

**順序制約**: `VXLAN_TUNNEL` → `VXLAN_TUNNEL_MAP`（VLAN-VNI エントリ）→ `VRF` → `VRF|<name>.vni` の順に書く必要がある。

---

## 2. 書込み順制約（DELETE 側）

### 2-1. VRF 削除前に *_INTERFACE エントリを先に削除する必要がある

`config vrf del` (config/main.py:7702-7733) は内部で `del_interface_bind_to_vrf()` を呼ぶ:

```python
# main.py:568-580
def del_interface_bind_to_vrf(config_db, vrf_name):
    tables = ['INTERFACE', 'PORTCHANNEL_INTERFACE', 'VLAN_INTERFACE',
              'LOOPBACK_INTERFACE', 'VLAN_SUB_INTERFACE']
    for table_name in tables:
        ...
        if 'vrf_name' in interface_dict[interface_name] and vrf_name == interface_dict[interface_name]['vrf_name']:
            config_db.set_entry(table_name, interface_name, None)
```

CLI は自動的に紐付く全インタフェースを削除してから VRF エントリを削除する。
CONFIG_DB を直接操作する場合は手動で同じ順序を実行する必要がある。

**順序制約**: `*_INTERFACE|<port>` (vrf_name 参照ロウ) DEL → `VRF|<name>` DEL。逆順にすると `intfsorch` の ref_count が残存しオブジェクト削除に失敗する。

### 2-2. orchagent ref_count による VRF 削除ブロック

`vrforch.cpp:169` で `vrf_table_[vrf_name].ref_count` が 0 でなければ DEL を返す:

```cpp
if (vrf_table_[vrf_name].ref_count)
    return false;
```

ref_count は以下の箇所でインクリメント/デクリメントされる:
- `intfsorch.cpp:504` — インタフェース VRF bind で `increaseVrfRefCount(vrf_id)`
- `intfsorch.cpp:640` — インタフェース VRF unbind で `decreaseVrfRefCount(vrf_id)`
- `routeorch.cpp:2013` — ルート追加で `increaseVrfRefCount(vrf_id)`
- `routeorch.cpp:2773,2993` — ルート削除で `decreaseVrfRefCount(vrf_id)`
- `mplsrouteorch.cpp:474,957` — MPLS ルートの追加/削除
- `srv6orch.cpp:1639,1683` — SRv6 SID の追加/削除

**順序制約**: VRF を削除する前に、所属するインタフェース・ROUTE・MPLS ルート・SRv6 SID をすべて削除して ref_count を 0 にする必要がある。ref_count が残ると `VRFOrch::delOperation` が `return false` し、STATE_DB の `VRF_OBJECT_TABLE` エントリも削除されないため vrfmgrd も Linux VRF デバイスを削除できない無限待機状態になる。

### 2-3. vrfmgrd の削除待機ロジック（isVrfObjExist ループ）

```cpp
// vrfmgr.cpp:328-346
if (m_stateVrfTable.get(vrfName, temp))
{
    /* VRFOrch add delay so wait */
    if (!isVrfObjExist(vrfName))
    {
        it++;
        continue;  // ← キューに戻して次ループへ
    }
    ...
    m_appVrfTableProducer.del(vrfName);
    m_stateVrfTable.del(vrfName);
}

if (isVrfObjExist(vrfName))
{
    it++;
    continue;  // ← ref_count が残っている間は削除しない
}
```

`isVrfObjExist` は STATE_DB `VRF_OBJECT_TABLE|<name>` の存在を確認する。
VRFOrch が `delOperation` 完了後に `m_stateVrfObjectTable.del(vrf_name)` を書く（vrforch.cpp:193）まで、vrfmgrd は Linux デバイス削除ループを回し続ける。

### 2-4. vni 削除は VRF 削除前に行う（または CLI が自動処理）

`doVrfVxlanTableRemoveTask` は VRF DEL 時に自動呼び出しされるが、
手動で CONFIG_DB を操作する場合は `VRF|<name>.vni=0` を SET してから VRF を DEL する。

**順序制約**: `VRF|<name>` DEL 前に `VRF|<name>.vni` を 0 に SET するか、CLI `del_vrf_vni_map` を使う（main.py:7784: `config_db.mod_entry('VRF', vrfname, {"vni": 0})`）。

---

## 3. SYSLOG_SERVER の参照依存

`config vrf del` は `SYSLOG_SERVER` テーブルを走査し、対象 VRF を参照しているエントリがあれば削除を拒否する（main.py:7712-7717）。

**順序制約**: `SYSLOG_SERVER` が当該 VRF を参照している場合、先に `SYSLOG_SERVER` エントリを削除してから `VRF` を削除する。

---

## 4. mgmt VRF の特例順序

`MGMT_VRF_CONFIG|vrf_global.mgmtVrfEnabled=true` でトリガされる mgmt VRF は、
通常の `VRF` テーブルではなく `MGMT_VRF_CONFIG` テーブルから制御される。

- `vrfmgrd` は `CFG_MGMT_VRF_CONFIG_TABLE_NAME` 購読も持ち、`mgmt` という固定名 VRF を処理する
- mgmt VRF は Linux VRF デバイス `ip link add` をスキップし（hostcfgd が先に初期化）、固定テーブル ID 6000 を使う

**順序制約**: mgmt VRF は hostcfgd の初期化が先行している前提。`MGMT_VRF_CONFIG` を書いた直後に `ip vrf exec mgmt` が使えるわけではなく、hostcfgd → vrfmgrd の処理完了を待つ。

---

## 5. BGP_GLOBALS との順序依存

`BGP_GLOBALS|<vrf_name>` は VRF 名を key として参照するが、YANG 上は leafref による制約ではなく文字列マッチ。ただし、bgpcfgd / frr-mgmt-framework は VRF が実際に Linux カーネルで存在するまで FRR 設定 (`vrf <name>`) が有効にならない。

**順序制約**: `VRF|<name>` が vrfmgrd によって Linux VRF デバイスとして作成された後に `BGP_GLOBALS|<vrf_name>` を書くと FRR 設定が確実に適用される（逆順でも FRR 側で retry されるが、タイムアウト依存になる）。

---

## 6. SAI virtual_router 作成順序（vrforch.cpp 調査）

調査日: 2026-05-16
調査対象: `sonic-swss/orchagent/vrforch.cpp`, `sonic-swss/orchagent/vrforch.h`

### 6-1. SAI VR 作成の内部ステップ

`VRFOrch::addOperation` (vrforch.cpp:27–155) の新規作成パス:

1. `vrf_table_.find(vrf_name) == end` で新規作成判定
2. `sai_virtual_router_api->create_virtual_router(&router_id, gSwitchId, attrs)` — SAI VR 生成 (vrforch.cpp:93-105)
3. `vrf_table_[vrf_name].vrf_id = router_id; ref_count = 0` — orchagent 内部マップ登録 (vrforch.cpp:107-108)
4. `gFlowCounterRouteOrch->onAddVR(router_id)` — フローカウンタ登録 (vrforch.cpp:110)
5. `vni != 0` の場合 `updateVrfVNIMap(vrf_name, vni)` — EVPN VTEP 存在確認、未設定なら `return false` (vrforch.cpp:111-118, 225-230)
6. `m_stateVrfObjectTable.hset(vrf_name, "state", "ok")` — STATE_DB へ完了通知 (vrforch.cpp:120)

### 6-2. SAI VR 削除の内部ステップ

`VRFOrch::delOperation` (vrforch.cpp:157–198):

1. `vrf_table_[vrf_name].ref_count` チェック → 非ゼロなら `return false` (vrforch.cpp:169)
2. `sai_virtual_router_api->remove_virtual_router(router_id)` (vrforch.cpp:173)
3. `gFlowCounterRouteOrch->onRemoveVR(router_id)` (vrforch.cpp:184)
4. `vrf_table_.erase(vrf_name); vrf_id_table_.erase(router_id)` (vrforch.cpp:186-187)
5. `delVrfVNIMap(vrf_name, 0)` — VNI マッピング解除 (vrforch.cpp:188)
6. `m_stateVrfObjectTable.del(vrf_name)` — STATE_DB の VRF_OBJECT_TABLE 消去 (vrforch.cpp:193)

### 6-3. ROUTE / NEIGHBOR ref_count の全網羅

`vrf_table_[name].ref_count` の増減箇所 (vrforch.h:91-119):

| ファイル | 行 | 操作 | トリガ |
|---------|-----|------|-------|
| `intfsorch.cpp` | 504 | increase | インタフェース VRF bind |
| `intfsorch.cpp` | 640 | decrease | インタフェース VRF unbind |
| `intfsorch.cpp` | 848 | increase | VRF 変更時の新 VRF |
| `intfsorch.cpp` | 854 | decrease | VRF 変更時の旧 VRF |
| `intfsorch.cpp` | 855 | increase | VRF 変更時の新 VRF (ロールバック) |
| `intfsorch.cpp` | 1057 | decrease | インタフェース削除 |
| `routeorch.cpp` | 2013 | increase | ROUTE 追加 |
| `routeorch.cpp` | 2773 | decrease | ROUTE 削除 (通常) |
| `routeorch.cpp` | 2993 | decrease | ROUTE 削除 (rollback) |
| `mplsrouteorch.cpp` | 474 | increase | MPLS ROUTE 追加 |
| `mplsrouteorch.cpp` | 957 | decrease | MPLS ROUTE 削除 |
| `srv6orch.cpp` | 1639 | increase | SRv6 SID 追加 |
| `srv6orch.cpp` | 1683 | decrease | SRv6 SID 削除 |
| `fgnhgorch.cpp` | 1326 | increase | FG-NHG 追加 |
| `fgnhgorch.cpp` | 1612 | decrease | FG-NHG 削除 |

**NEIGHBOR（neighorch.cpp）は VRF ref_count を直接操作しない**。NEIGHBOR エントリはインタフェース経由で VRF に属するが、neighorch では `increaseVrfRefCount` / `decreaseVrfRefCount` を呼ばない。インタフェース削除時に intfsorch が ref_count を減らし、それによって NEIGHBOR も自動的に無効化される。

---

## 7. まとめ（書込み順依存一覧）

| 依存カテゴリ | 必須順序 | ソース |
|------------|---------|-------|
| CREATE: VXLAN_TUNNEL → VXLAN_TUNNEL_MAP → VRF → VRF.vni | VNI 設定は VLAN-VNI マップ後かつ VRF 作成後 | `config/main.py:7743-7760` |
| CREATE: VRF → *_INTERFACE | VRF の STATE_DB ready 後に vrf_name 指定 INTERFACE を書く | `intfmgr.cpp:839-842` |
| CREATE: VRF SAI VR → ROUTE | routeorch が VRF OID を `getVRFid()` で参照。未確立ならキューに残す | `vrforch.cpp:107-108` |
| CREATE: VRF → BGP_GLOBALS | Linux VRF デバイス作成後が推奨 | `vrfmgr.cpp:289` |
| DELETE: ROUTE/MPLS/SRv6/FG-NHG DEL → VRF DEL | ルート削除で ref_count を 0 にしてから VRF DEL | `routeorch.cpp:2773,2993`, `vrforch.cpp:169` |
| DELETE: *_INTERFACE DEL → VRF DEL | インタフェース unbind で ref_count を 0 にしてから VRF DEL | `vrforch.cpp:169`, `intfsorch.cpp:640` |
| DELETE: VRF.vni=0 → VRF DEL | VNI マッピングを先に解除 | `vrfmgr.cpp:337` |
| DELETE: SYSLOG_SERVER DEL → VRF DEL | syslog VRF 参照を先に削除 | `config/main.py:7712-7717` |
| DELETE: VRF ref_count=0 待機 | orchagent の全依存オブジェクト削除完了まで Linux デバイス削除が待機 | `vrfmgr.cpp:330-346` |
| DELETE: SAI VR 削除 → STATE_DB VRF_OBJECT_TABLE del | vrforch.cpp:193 が STATE_DB 消去 → vrfmgrd が Linux デバイス削除を実行 | `vrforch.cpp:193`, `vrfmgr.cpp:330-346` |
| NEIGHBOR: ref_count 非依存 | NEIGHBOR は VRF ref_count を操作しない。INTERFACE 削除で間接的に無効化 | `vrforch.h:91-119` |
| mgmt VRF: hostcfgd 先行 | hostcfgd 初期化済み前提でのみ mgmt VRF が機能 | `vrfmgr.cpp:176-183` |
