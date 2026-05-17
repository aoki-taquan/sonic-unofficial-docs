# VXLAN トンネルポート (Port::TUNNEL) — Phase F 副次 DB 書込スキャンノート

対象: `Port::TUNNEL` ランタイムオブジェクト (tunnel-port)
Consumer: `VxlanTunnelOrch` / `PortsOrch` (`orchagent/vxlanorch.cpp`, `orchagent/portsorch.cpp`)
スキャン範囲: `addTunnel()`, `addBridgePort()`, `removeBridgePort()`, `removeTunnel()`,
              `updateDbTunnelOperStatus()`, `addRemoveStateTableEntry()`,
              `addTunnelToFlexCounter()`, `removeTunnelFromFlexCounter()`, `doTask(SelectableTimer&)` 全行精読

---

## 副次 DB 書込の検出結果

### 1. STATE_DB — `VXLAN_TUNNEL_TABLE` への oper status 書込

- `VxlanTunnelOrch::updateDbTunnelOperStatus()` (vxlanorch.cpp:1893–1910):
  `m_stateVxlanTable.set(tunnel_name, [{"operstatus", "up"|"down"}])` を呼ぶ。
- トンネルポート生成直後は STATE_DB への直接書込なし (`addTunnel()` / `addBridgePort()` 自体は STATE_DB を触らない)。
- oper status の STATE_DB 書込は SAI ポートステータス変更イベント受信後に
  `VxlanTunnelOrch::updateDbTunnelOperStatus()` 経由でトリガされる。
- `addRemoveStateTableEntry()` (vxlanorch.cpp:1917–1953) は VXLAN_TUNNEL (トンネルオブジェクト) の
  追加/削除時に STATE_DB に `src_ip` / `dst_ip` / `tnl_src` / `operstatus` を書く。
  これはトンネルポート (Port::TUNNEL) 生成時ではなく、VXLAN_TUNNEL エントリ追加時に呼ばれる。
- STATE_DB キー: `VXLAN_TUNNEL_TABLE|<tunnel_name>` (例: `VXLAN_TUNNEL_TABLE|EVPN_<remote_vtep_ip>`)
- evidence: vxlanorch.cpp:1893–1910, 1917–1953

### 2. COUNTERS_DB — `COUNTERS_TUNNEL_NAME_MAP` / `COUNTERS_TUNNEL_TYPE_MAP`

- `VxlanTunnelOrch::doTask(SelectableTimer&)` (vxlanorch.cpp:1309–1341) が
  m_pendingAddToFlexCntr に溜まった pending OID を走査し:
  - `m_tunnelNameTable->set("", [{tunnel_name, sai_oid}])` → `COUNTERS_DB::COUNTERS_TUNNEL_NAME_MAP`
  - `m_tunnelTypeTable->set("", [{sai_oid, "SAI_TUNNEL_TYPE_VXLAN"}])` → `COUNTERS_DB::COUNTERS_TUNNEL_TYPE_MAP`
  - `tunnel_stat_manager->setCounterIdList(oid, CounterType::TUNNEL, stats)` → FlexCounter 登録
- `addTunnelToFlexCounter()` (vxlanorch.cpp:1342) は `m_pendingAddToFlexCntr[oid] = name` に追加するのみで
  即時 COUNTERS_DB 書込ではない。実際の書込は次の SelectableTimer 発火時 (1秒間隔)。
- これは **VxlanTunnel (SAI トンネルオブジェクト)** に対する FlexCounter 登録であり、
  **Port::TUNNEL ブリッジポート** に対するカウンタではない。tunnel_id (SAI tunnel OID) が対象。
- evidence: vxlanorch.cpp:1278–1341, common/schema.h:247–248

### 3. ASIC_DB (SAI 経由) — ブリッジポート作成

- `PortsOrch::addBridgePort()` (portsorch.cpp:7258):
  `sai_bridge_api->create_bridge_port(&port.m_bridge_port_id, ...)` を呼ぶ。
  SAI が ASIC_DB に `ASIC_STATE:SAI_OBJECT_TYPE_BRIDGE_PORT:<oid>` エントリを書く。
- 属性: TYPE=TUNNEL, TUNNEL_ID=<sai_tunnel_id>, BRIDGE_ID=<default_1q_bridge>, ADMIN_STATE=true,
        FDB_LEARNING_MODE=DISABLE
- evidence: portsorch.cpp:7228–7281

### 4. インメモリ副次更新 — `m_portList` / `saiOidToAlias`

- `PortsOrch::addTunnel()` (portsorch.cpp:8373–8374):
  `m_portList[tunnel_alias] = tunnel` および `saiOidToAlias[tunnel_id] = tunnel_alias` を更新。
  DB への直接書込ではなく orchagent 内のランタイムマップへの登録。
- `addBridgePort()` 終端 (portsorch.cpp:7277):
  `saiOidToAlias[port.m_bridge_port_id] = port.m_alias` でブリッジポート OID もマッピング。
- evidence: portsorch.cpp:8373–8374, 7277

### 5. Observer 通知 — `SUBJECT_TYPE_BRIDGE_PORT_CHANGE`

- `PortsOrch::addBridgePort()` 終端 (portsorch.cpp:7280–7281):
  `PortUpdate update = { port, true }; notify(SUBJECT_TYPE_BRIDGE_PORT_CHANGE, ...)` を呼ぶ。
- 現状の subscriber: `IsolationGroupOrch` (isolationgrouporch.cpp:233) が
  `SUBJECT_TYPE_BRIDGE_PORT_CHANGE` を購読する唯一のコンポーネント。
- `IsolationGroupOrch` は Port::TUNNEL 型ポートについて特別な処理を持たないため、
  通知は届くが実質的な副作用はない (`isolationgrouporch.cpp:233` でタイプチェックして処理をスキップ)。
- evidence: portsorch.cpp:7280–7281, isolationgrouporch.cpp:233

### 6. DB 書込なし (確認済み)

- APPL_DB: `VxlanTunnelOrch` / `PortsOrch` の `addTunnel()` / `addBridgePort()` に
  APPL_DB への書込呼出は存在しない。vxlanorch.cpp 全体を `ProducerStateTable`/`Table.set(`で grep → 0件 (APPL_DB 向け)。
- FLEX_COUNTER_DB: `tunnel_stat_manager->setCounterIdList()` 経由で書込まれるが、
  これは FLEX_COUNTER_DB であり COUNTERS_DB と同一 Redis インスタンス内の別テーブル。
  対象はブリッジポートではなくトンネル SAI OID。
- LOGLEVEL_DB / CONFIG_DB: 書込なし。

---

## 副次 DB 書込サマリ

| DB | テーブル / キー | トリガ | タイミング |
|----|--------------|--------|----------|
| STATE_DB | `VXLAN_TUNNEL_TABLE\|<tunnel_name>` (`operstatus`) | SAI ポートステータスイベント → `updateDbTunnelOperStatus()` | トンネルポート生成後、アンダーレイ経路確立時 |
| COUNTERS_DB | `COUNTERS_TUNNEL_NAME_MAP`, `COUNTERS_TUNNEL_TYPE_MAP` | `doTask(SelectableTimer)` | トンネルポート生成後、最大 1 秒遅延 |
| ASIC_DB (SAI) | `SAI_OBJECT_TYPE_BRIDGE_PORT:<oid>` | `sai_bridge_api->create_bridge_port()` via `addBridgePort()` | `addBridgePort()` 呼出時に同期 |
| APPL_DB | なし | — | — |
| CONFIG_DB | なし | — | — |
