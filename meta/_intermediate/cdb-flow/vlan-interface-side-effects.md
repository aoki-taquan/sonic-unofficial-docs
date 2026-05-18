# VLAN_INTERFACE — side-effects 調査ノート

調査対象: `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/orchagent/intfsorch.cpp`
調査日: 2026-05-18

## SET — 属性ロウ (`VLAN_INTERFACE|Vlan<N>`)

### intfmgrd 側

- `ProducerStateTable m_appIntfTableProducer` で **APPL_DB `INTF_TABLE|Vlan<N>`** に書込み
  - フィールド: `vrf_name`, `mac_addr`, `admin_status`, `proxy_arp`, `grat_arp`, `mpls` (非空時)
  - タイミング: `doIntfGeneralTask()` の SET 末尾 (`intfmgr.cpp:1053`)
- `Table m_stateIntfTable` で **STATE_DB `STATE_INTERFACE_TABLE|Vlan<N>`** に書込み
  - フィールド: `vrf` (vrf_name 値)
  - タイミング: 同上 (`intfmgr.cpp:1054`)

### orchagent IntfsOrch 側

- `sai_router_intfs_api->create_router_interface(...)` — **ASIC_DB** 経由で SAI RIF OID 生成 (`intfsorch.cpp:1296`)
- **COUNTERS_DB**
  - `COUNTERS_RIF_NAME_MAP` に `{alias: rif_oid}` 追加 (タイマー; `addRifToFlexCounter()`)
  - `COUNTERS_RIF_TYPE_MAP` に `{rif_oid: "SAI_ROUTER_INTERFACE_TYPE_VLAN"}` 追加 (同)
- **FLEX_COUNTER_DB** `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP:<rif_oid>` エントリ登録 (`startFlexCounterPolling()`)
- VOQ chassis 環境のみ: `voqSyncAddIntf(alias)` で **CHASSIS_APP_DB `SYSTEM_INTERFACE_TABLE`** に `oper_status` を SET (`intfsorch.cpp:1314-1317`)

## SET — IP プレフィクスロウ (`VLAN_INTERFACE|Vlan<N>|<ip_prefix>`)

### intfmgrd 側

- **APPL_DB `INTF_TABLE|Vlan<N>|<ip_prefix>`** に書込み
  - フィールド: `scope="global"` (固定), `family="IPv4"/"IPv6"` (自動判定)
  - IPv4 link-local アドレスは APPL_DB に送信しない (`intfmgr.cpp:1131`)
  - タイミング: `doIntfAddrTask()` の SET 末尾 (`intfmgr.cpp:1137`)
- **STATE_DB `STATE_INTERFACE_TABLE|Vlan<N>|<ip_prefix>`** に書込み
  - フィールド: `state="ok"`
  - タイミング: 同上 (`intfmgr.cpp:1138`)

### orchagent IntfsOrch 側

- `addIp2MeRoute()` — **ASIC_DB** に IP2me ルート (CPU trap) 追加 (`sai_route_api->create_route_entry(...)`)
- VLAN IF に IPv4 prefix が付与される場合: `addDirectedBroadcast()` — **ASIC_DB** に Directed Broadcast ネイバーエントリ追加 (`sai_neighbor_api->create_neighbor_entry(...)`) (`intfsorch.cpp:595-597`)
- **CRM カウンタ** increment (COUNTERS_DB)
- VOQ chassis + inband port の場合: `gNeighOrch->addInbandNeighbor()` で他 ASIC にネイバーを伝播 (`intfsorch.cpp:586-592`)

## DEL — 属性ロウ (`VLAN_INTERFACE|Vlan<N>`)

### intfmgrd 側

- IP プレフィクスロウが残存する場合は `return false`（retry）。DEL は保留。
- **APPL_DB `INTF_TABLE|Vlan<N>`** DEL (`intfmgr.cpp:1088`)
- **STATE_DB `STATE_INTERFACE_TABLE|Vlan<N>`** DEL (`intfmgr.cpp:1089`)

### orchagent IntfsOrch 側

- `sai_router_intfs_api->remove_router_interface(...)` — SAI RIF OID 削除
- **COUNTERS_DB** `COUNTERS_RIF_NAME_MAP` / `COUNTERS_RIF_TYPE_MAP` エントリ削除 (`removeRifFromFlexCounter()`)
- **FLEX_COUNTER_DB** エントリ削除 (`stopFlexCounterPolling()`) (`intfsorch.cpp:1346`)
- VOQ chassis 環境のみ: `voqSyncDelIntf(alias)` で **CHASSIS_APP_DB `SYSTEM_INTERFACE_TABLE`** から DEL (`intfsorch.cpp:1367-1370`)

## DEL — IP プレフィクスロウ (`VLAN_INTERFACE|Vlan<N>|<ip_prefix>`)

### intfmgrd 側

- **APPL_DB `INTF_TABLE|Vlan<N>|<ip_prefix>`** DEL (IPv4 link-local を除く) (`intfmgr.cpp:1163`)
- **STATE_DB `STATE_INTERFACE_TABLE|Vlan<N>|<ip_prefix>`** DEL (`intfmgr.cpp:1162`)

### orchagent IntfsOrch 側

- `removeIp2MeRoute()` — ASIC_DB から IP2me ルート削除
- VLAN IF の場合: `removeDirectedBroadcast()` — Directed Broadcast ネイバーエントリ削除 (`intfsorch.cpp:626-628`)
- **CRM カウンタ** decrement

## 参照コード

- `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
- `sonic-swss/orchagent/intfsorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/intfsorch.cpp>
