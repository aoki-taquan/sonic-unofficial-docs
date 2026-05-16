# VLAN SET/DEL 副次 DB 書込 分析 (Phase F)

ソース:
- `sonic-swss/cfgmgr/vlanmgr.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-utilities/dump/plugins/vlan.py`
- `sonic-utilities/dump/match_helper.py`

---

## vlanmgrd (cfgmgr/vlanmgr.cpp)

### SET (op == SET_COMMAND)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|-----------------|-----------------|------|
| `m_appVlanTableProducer.set(key, fvVector)` | APPL_DB / `VLAN_TABLE` | `Vlan<id>` | 常時 (vlanmgr.cpp:437) |
| `m_stateVlanTable.set(key, [{state, ok}])` | STATE_DB / `VLAN_TABLE` | `Vlan<id>` field=`state` | 常時 (vlanmgr.cpp:443) |

`fvVector` に含まれるフィールド (APPL_DB 書込み内容):
- `admin_status` — 明示指定がない場合は `"up"` を自動補完
- `mtu` — 省略時は `DEFAULT_MTU_STR`（`9100`）を代入
- `mac` — 省略時は `gMacAddress` (スイッチ MAC) を代入
- `host_ifname` — ホスト IF 名 (通常は空文字)

カーネル操作 (DB 書込ではない):
- `ip link add Vlan<id> type bridge vlan_filtering 1` — Linux カーネルブリッジ作成
- `ip link set Vlan<id> up/down` — `admin_status` に応じた状態セット

### DEL (op == DEL_COMMAND)

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|-----------------|------|------|
| `m_appVlanTableProducer.del(key)` | APPL_DB / `VLAN_TABLE` | `Vlan<id>` | `m_vlans` に存在する場合 (vlanmgr.cpp:462) |
| `m_stateVlanTable.del(key)` | STATE_DB / `VLAN_TABLE` | `Vlan<id>` | `m_vlans` に存在する場合 (vlanmgr.cpp:463) |

カーネル操作:
- `ip link set Vlan<id> down; ip link del Vlan<id>` — ブリッジ削除

---

## PortsOrch / addVlan() (orchagent/portsorch.cpp)

APPL_DB `VLAN_TABLE` を VlanOrch / PortsOrch が購読し SAI を呼び出す。

### SET → addVlan()

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|-----------------|-----------------|------|
| `sai_vlan_api->create_vlan(&vlan_oid, ...)` | ASIC_DB / `ASIC_STATE:SAI_OBJECT_TYPE_VLAN:<oid>` | `SAI_VLAN_ATTR_VLAN_ID=<id>` | 常時 (portsorch.cpp:7392) |

SAI 呼び出し後、orchagent はメモリ内 `m_portList` / `saiOidToAlias` を更新するのみで追加の DB 書込みは行わない。ASIC_DB エントリは syncd が SAI 応答を基に書き込む。

### DEL → removeVlan()

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|-----------------|------|------|
| `sai_vlan_api->remove_vlan(vlan_oid)` | ASIC_DB / `ASIC_STATE:SAI_OBJECT_TYPE_VLAN:<oid>` 削除 | `<oid>` | 常時 (portsorch.cpp:7469) |

DEL ガード条件 (portsorch.cpp:7427-7454):
- `m_fdb_count > 0` — FDB エントリが残っている場合は false を返し retry
- `m_port_ref_count > 0` — 参照カウントが残っている場合は error
- `m_members.size() > 0` — メンバーポートが残っている場合は error
- `m_vnid != VNID_NONE` — VXLAN VNI マッピングが残っている場合は error

---

## COUNTERS_DB への書込み

VLAN SET/DEL 単体では COUNTERS_DB への直接書込みはなし。

- VLAN MEMBER の追加 (addVlanMember) 時も COUNTERS_DB / CRM カウンタ操作は不発生。
- `COUNTERS_DB` へのマッピング (`COUNTERS_PORT_NAME_MAP` 等) は PORT/LAG 登録時に書かれるものであり、VLAN 自体のカウンタマップは存在しない。
- ただし、VLAN に `VLAN_INTERFACE` (RIF) を付与した場合、`IntfsOrch::addRouterIntfs()` が `COUNTERS_RIF_NAME_MAP` / `COUNTERS_RIF_TYPE_MAP` を書き込む (これは INTERFACE テーブルの副作用であり VLAN テーブル直接の副作用ではない)。

---

## STATE_DB への読み取り (warm-restart guard)

- `m_stateVlanTable.get(key, temp)` — SET 処理冒頭で warm-restart 判定に使用 (vlanmgr.cpp:371)
- `m_statePortTable`, `m_stateLagTable` — VLAN_MEMBER 処理時にポート/LAG の state を確認

---

## 副作用サマリ

| DB | テーブル | キー形式 | SET | DEL |
|-----|---------|---------|-----|-----|
| APPL_DB | `VLAN_TABLE` | `Vlan<id>` | 書込 (vlanmgrd) | 削除 (vlanmgrd) |
| STATE_DB | `VLAN_TABLE` | `Vlan<id>` | `{state: ok}` 書込 (vlanmgrd) | 削除 (vlanmgrd) |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_VLAN:<oid>` | OID | syncd 経由で作成 | syncd 経由で削除 |
| COUNTERS_DB | — | — | 書込なし | 書込なし |
