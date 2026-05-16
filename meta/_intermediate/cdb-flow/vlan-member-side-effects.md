# VLAN_MEMBER SET/DEL 副次 DB 書込 分析 (Phase F)

ソース:
- `sonic-swss/cfgmgr/vlanmgr.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

---

## vlanmgrd (cfgmgr/vlanmgr.cpp)

### SET (op == SET_COMMAND)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|-----------------|-----------------|------|
| `m_appVlanMemberTableProducer.set(key, kfvFieldsValues(t))` | APPL_DB / `VLAN_MEMBER_TABLE` | `Vlan<id>|<port>` | addHostVlanMember() 成功後 (vlanmgr.cpp:672) |
| `m_stateVlanMemberTable.set(kfvKey(t), [{state, ok}])` | STATE_DB / `VLAN_MEMBER_TABLE` | `Vlan<id>|<port>` | 同上 (vlanmgr.cpp:677) |

APPL_DB に書き込まれるフィールド: CONFIG_DB の raw フィールド列をそのまま転送 (`kfvFieldsValues(t)`)。
`tagging_mode` が CONFIG_DB に存在しない場合 APPL_DB にも書かれない（orchagent 側で再度 `"untagged"` にフォールバック）。

### DEL (op == DEL_COMMAND)

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|-----------------|------|------|
| `m_appVlanMemberTableProducer.del(key)` | APPL_DB / `VLAN_MEMBER_TABLE` | `Vlan<id>|<port>` | isVlanMemberStateOk() == true (vlanmgr.cpp:697) |
| `m_stateVlanMemberTable.del(kfvKey(t))` | STATE_DB / `VLAN_MEMBER_TABLE` | `Vlan<id>|<port>` | 同上 (vlanmgr.cpp:698) |

---

## PortsOrch::addVlanMember / removeVlanMember (orchagent/portsorch.cpp)

APPL_DB `VLAN_MEMBER_TABLE` を PortsOrch が購読し SAI を呼び出す。

### SET → addVlanMember()

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|-----------------|-----------------|------|
| `sai_vlan_api->create_vlan_member(&vlan_member_id, ...)` | ASIC_DB / `ASIC_STATE:SAI_OBJECT_TYPE_VLAN_MEMBER:<oid>` | `SAI_VLAN_MEMBER_ATTR_VLAN_ID`, `SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID`, `SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE` | 常時 (portsorch.cpp:7553) |
| `setPortPvid(port, vlan_id)` → `SAI_PORT_ATTR_PORT_VLAN_ID` | ASIC_DB (SAI 経由) | ポート OID | `tagging_mode == untagged` かつ非 TUNNEL ポートの場合 (portsorch.cpp:7570) |

SAI tagging_mode マッピング:
- `"untagged"` → `SAI_VLAN_TAGGING_MODE_UNTAGGED`
- `"tagged"` → `SAI_VLAN_TAGGING_MODE_TAGGED`
- `"priority_tagged"` → `SAI_VLAN_TAGGING_MODE_PRIORITY_TAGGED`

### DEL → removeVlanMember()

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|-----------------|------|------|
| `sai_vlan_api->remove_vlan_member(vlan_member_id)` | ASIC_DB / `ASIC_STATE:SAI_OBJECT_TYPE_VLAN_MEMBER:<oid>` 削除 | `<oid>` | 常時 (portsorch.cpp:1618) |

DEL 時の FDB 副作用:
- ポートが VLAN から削除されると `SUBJECT_TYPE_VLAN_MEMBER_CHANGE` 通知が fdborch に送られ、そのポートの FDB エントリが ASIC_DB から自動削除される (fdborch.cpp:655, 1086)。

---

## カーネル操作 (DB 外)

### SET (addHostVlanMember)

```
ip link set <port> master Bridge
bridge vlan del vid 1 dev <port>
bridge vlan add vid <vlan_id> dev <port> [pvid untagged]
```

`pvid untagged` オプション: `tagging_mode == "untagged"` または `"priority_tagged"` の場合に付与 (vlanmgr.cpp:238)。

### DEL (removeHostVlanMember)

```
bridge vlan del vid <vlan_id> dev <port>
# VLAN が残っていなければ:
ip link set <port> nomaster
```

---

## 副作用サマリ

| DB | テーブル | キー形式 | SET | DEL |
|-----|---------|---------|-----|-----|
| APPL_DB | `VLAN_MEMBER_TABLE` | `Vlan<id>|<port>` | 書込 (vlanmgrd) | 削除 (vlanmgrd) |
| STATE_DB | `VLAN_MEMBER_TABLE` | `Vlan<id>|<port>` | `{state: ok}` 書込 (vlanmgrd) | 削除 (vlanmgrd) |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_VLAN_MEMBER:<oid>` | OID | syncd 経由で作成 | syncd 経由で削除 |
| ASIC_DB | `SAI_PORT_ATTR_PORT_VLAN_ID` (ポート属性) | ポート OID | `untagged` 時に PVID 書込 | — |
| ASIC_DB | FDB エントリ | — | — | ポート削除時に自動削除 (fdborch) |
| COUNTERS_DB | — | — | 書込なし | 書込なし |
