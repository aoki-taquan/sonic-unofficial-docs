# INTERFACE SET/DEL 副次 DB 書込 分析 (Phase F)

ソース: `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/orchagent/intfsorch.cpp`

## intfmgrd (cfgmgr/intfmgr.cpp)

### SET — 属性ロウ (INTERFACE|<name>)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_appIntfTableProducer.set(alias, data)` | APPL_DB / `INTF_TABLE` | `<name>` | 常時 |
| `m_stateIntfTable.hset(alias, "vrf", vrf_name)` | STATE_DB / `INTERFACE_TABLE` | `<name>` field=`vrf` | 常時 |
| `m_statePortTable.set(alias, {state:ok})` | STATE_DB / `PORT_TABLE` | `<name>` | サブインターフェース かつ EthernetX 系 |
| `m_stateLagTable.set(alias, {state:ok})` | STATE_DB / `LAG_TABLE` | `<name>` | サブインターフェース かつ Po 系 |
| `m_appIntfTableProducer.set(intf, {mtu})` | APPL_DB / `INTF_TABLE` | 親インターフェースのサブインターフェース | サブ IF の MTU を引き継ぐとき |
| `m_appIntfTableProducer.set(intf, {admin_status})` | APPL_DB / `INTF_TABLE` | 親インターフェースのサブインターフェース | 親の admin_status 変化に連動 |

カーネル変更 (副次 DB 書込ではなくカーネル sysctl / ip コマンド):
- `ip link set <alias> master <vrf>` — VRF バインド
- `ip link set <alias> nomaster` — VRF アンバインド
- `ip link set <alias> address <mac>` — MAC 設定
- `sysctl net.mpls.conf.<alias>.input=1/0` — MPLS on/off
- `/proc/sys/net/ipv4/conf/<alias>/arp_accept` — GARP
- `/proc/sys/net/ipv4/conf/<alias>/proxy_arp[_pvlan]` — Proxy ARP

### SET — IP プレフィクスロウ (INTERFACE|<name>|<ip_prefix>)

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_appIntfTableProducer.set(appKey, [{scope,family}])` | APPL_DB / `INTF_TABLE` | `<name>:<ip_prefix>` | IPv4 link-local 以外 |
| `m_stateIntfTable.hset("<name>|<ip_prefix>", "state", "ok")` | STATE_DB / `INTERFACE_TABLE` | `<name>|<ip_prefix>` field=`state` | IPv4 link-local 以外 |

カーネル変更: `ip address add <ip_prefix> dev <alias>` (v4/v6)

### DEL — 属性ロウ (INTERFACE|<name>)

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|------------------|------|------|
| `m_appIntfTableProducer.del(alias)` | APPL_DB / `INTF_TABLE` | `<name>` | 常時 |
| `m_stateIntfTable.del(alias)` | STATE_DB / `INTERFACE_TABLE` | `<name>` | 常時 |
| `m_statePortTable.del(alias)` | STATE_DB / `PORT_TABLE` | `<name>` | サブ IF かつ EthernetX 系 |
| `m_stateLagTable.del(alias)` | STATE_DB / `LAG_TABLE` | `<name>` | サブ IF かつ Po 系 |

カーネル変更: `ip link set <alias> nomaster` (VRF 除去)、サブ IF は `ip link del <alias>`

### DEL — IP プレフィクスロウ

| 操作 | 対象 DB / テーブル | キー | 条件 |
|------|------------------|------|------|
| `m_appIntfTableProducer.del(appKey)` | APPL_DB / `INTF_TABLE` | `<name>:<ip_prefix>` | IPv4 link-local 以外 |
| `m_stateIntfTable.del("<name>|<ip_prefix>")` | STATE_DB / `INTERFACE_TABLE` | `<name>|<ip_prefix>` | IPv4 link-local 以外 |

カーネル変更: `ip address del <ip_prefix> dev <alias>`

---

## IntfsOrch (orchagent/intfsorch.cpp)

APPL_DB の `INTF_TABLE` を購読し、SAI 呼び出しと DB 書込みを行う。

### SET — 属性ロウ → addRouterIntfs()

| 操作 | 対象 DB / テーブル | キー / フィールド | 条件 |
|------|------------------|-----------------|------|
| `m_rifNameTable->set("", [{name,oid}])` | COUNTERS_DB / `COUNTERS_RIF_NAME_MAP` | `""` field=`<alias>` | RIF 作成時 (タイマー経由) |
| `m_rifTypeTable->set("", [{oid,type}])` | COUNTERS_DB / `COUNTERS_RIF_TYPE_MAP` | `""` field=`<oid>` | RIF 作成時 (タイマー経由) |
| `startFlexCounterPolling(...)` → FLEX_COUNTER_DB エントリ | FLEX_COUNTER_DB / `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP:<oid>` | `<oid>` | RIF 作成時 |
| `m_tableVoqSystemInterfaceTable->set(alias, {oper_status})` | CHASSIS_APP_DB / `SYSTEM_INTERFACE_TABLE` | `<system_port_alias>` | VoQ システムかつ Local インターフェース |

SAI 呼び出し (ASIC_DB へ反映):
- `sai_router_intfs_api->create_router_interface(...)` → ASIC_DB に RIF OID エントリ
- `sai_router_intfs_api->set_router_interface_attribute(SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID)` — nat_zone
- `sai_router_intfs_api->set_router_interface_attribute(SAI_ROUTER_INTERFACE_ATTR_ADMIN_MPLS_STATE)` — mpls
- `sai_router_intfs_api->set_router_interface_attribute(SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS)` — mac_addr
- `sai_router_intfs_api->set_router_interface_attribute(SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION)` — loopback_action

### SET — IP プレフィクスロウ → addIp2MeRoute()

| 操作 | 対象 DB / テーブル | 条件 |
|------|------------------|------|
| `gCrmOrch->incCrmResUsedCounter(CRM_IPV4_ROUTE / CRM_IPV6_ROUTE)` | COUNTERS_DB / `CRM` カウンタ | 常時 |
| `gFlowCounterRouteOrch->onAddMiscRouteEntry(...)` | (FlexCounter 管理) | 常時 |

SAI 呼び出し:
- `sai_route_api->create_route_entry(...)` — IP2me ルート (CPU へ trap)
- VLAN ポートの場合: `sai_neighbor_api->create_neighbor_entry(...)` — Directed Broadcast エントリ
- VoQ Inband の場合: `gNeighOrch->addInbandNeighbor(...)` — Inband ネイバー登録

### DEL — 属性ロウ → removeRouterIntfs()

| 操作 | 対象 DB / テーブル | 条件 |
|------|------------------|------|
| `m_rifNameTable->hdel("", name)` | COUNTERS_DB / `COUNTERS_RIF_NAME_MAP` | 常時 |
| `m_rifTypeTable->hdel("", id)` | COUNTERS_DB / `COUNTERS_RIF_TYPE_MAP` | 常時 |
| `stopFlexCounterPolling(...)` → FLEX_COUNTER_DB エントリ削除 | FLEX_COUNTER_DB | 常時 |
| `m_tableVoqSystemInterfaceTable->del(alias)` | CHASSIS_APP_DB / `SYSTEM_INTERFACE_TABLE` | VoQ システムかつ Local IF |

SAI 呼び出し:
- `sai_router_intfs_api->remove_router_interface(...)` — RIF 削除

### DEL — IP プレフィクスロウ → removeIp2MeRoute()

| 操作 | 対象 DB / 対象 | 条件 |
|------|---------------|------|
| `gCrmOrch->decCrmResUsedCounter(...)` | COUNTERS_DB / CRM カウンタ | 常時 |
| `gFlowCounterRouteOrch->onRemoveMiscRouteEntry(...)` | FlexCounter | 常時 |

SAI 呼び出し:
- `sai_route_api->remove_route_entry(...)` — IP2me ルート削除
- VLAN: `sai_neighbor_api->remove_neighbor_entry(...)` — Directed Broadcast 削除
- VoQ Inband: `gNeighOrch->delInbandNeighbor(...)` — Inband ネイバー削除
