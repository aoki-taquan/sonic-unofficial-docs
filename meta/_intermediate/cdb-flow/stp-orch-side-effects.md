# stp-orch — Phase F 副作用 (side-effects) エビデンス

対象ページ: `docs/reference/config-db/stp-orch.md`

## ソース

- `orchagent/stporch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `orchagent/stporch.h` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `cfgmgr/stpmgr.cpp` @ sonic-net/sonic-swss master
- `cfgmgr/stpmgr.h` @ sonic-net/sonic-swss master
- `common/schema.h` @ sonic-net/sonic-swss-common master

## 副作用一覧

### STP_VLAN_INSTANCE_TABLE SET

1. `create_stp` — SAI STP インスタンス生成 (stporch.cpp:115-163)
2. `set_vlan_attribute(SAI_VLAN_ATTR_STP_INSTANCE)` — VLAN の STP インスタンス割当変更
3. `m_stpInstToOid` マップへの OID 追加
4. `m_vlanAliasToStpInstanceMap` 更新 → STP_INST_PORT_FLUSH_TABLE の前提

### STP_VLAN_INSTANCE_TABLE DEL

5. `set_vlan_attribute(SAI_VLAN_ATTR_STP_INSTANCE)` で `m_defaultStpId` に復元
6. VLAN ゼロになった場合 `remove_stp` で SAI STP インスタンス削除

### STP_PORT_STATE_TABLE SET

7. `gPortsOrch->addBridgePort(port)` — bridge port 未作成時に自動生成
8. `create_stp_port` — SAI STP ポートオブジェクト生成 (初期状態 `SAI_STP_PORT_STATE_BLOCKING`)
9. `set_stp_port_attribute(SAI_STP_PORT_ATTR_STATE)` — ASIC ポート状態更新

### STP_PORT_STATE_TABLE DEL

10. `remove_stp_port` — SAI STP ポートオブジェクト削除

### STP_FASTAGEING_FLUSH_TABLE SET

11. `gFdbOrch->flushFdbByVlan(vlan_alias)` — 対象 VLAN の全 FDB エントリ削除 (PVST 向け)

### STP_INST_PORT_FLUSH_TABLE SET

12. `gFdbOrch->flushFdbByVlan()` を複数 VLAN に対して実行 — MST インスタンス配下の全 VLAN FDB フラッシュ

### コンストラクタ (起動時)

13. `m_stpTable->set("GLOBAL", ...)` — `STATE_DB:STP_TABLE|GLOBAL.max_stp_inst` = `SAI_SWITCH_ATTR_MAX_STP_INSTANCE - 1` 書き込み (stporch.cpp:603-616)
    - `stpmgrd::getStpMaxInstances()` がこの値を読み取り `max_delay=60` でポーリング (stpmgr.cpp:1380-1413)
    - 値が 0 のままタイムアウトした場合 `STP_DEFAULT_MAX_INSTANCES = 255` にフォールバック (stpmgr.h:38)
    - この値は `stpd` への `STP_BRIDGE_CONFIG_MSG.max_stp_instances` に使われる

## STATE_DB テーブル名

`STATE_STP_TABLE_NAME = "STP_TABLE"` (common/schema.h:445)
