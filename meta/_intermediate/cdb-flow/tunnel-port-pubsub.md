# VXLAN トンネルポート (Port::TUNNEL) — Phase G: 通信メカニズム (pubsub)

## 調査対象

slug: tunnel-port
phase: pubsub (通信メカニズム)
調査日: 2026-05-18

## ソース

- `orchagent/vxlanorch.cpp` (4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/portsorch.cpp` (同リポジトリ)
- `orchagent/isolationgrouporch.cpp` (同リポジトリ)

## 調査結果

### 1. Port::TUNNEL は CONFIG_DB 非購読 — 動的生成オブジェクト

VXLAN トンネルポートは CONFIG_DB / APPL_DB のテーブルを直接購読しない。
親テーブル (`VXLAN_TUNNEL_MAP` / `VXLAN_EVPN_NVO`) の処理結果として動的生成される。
pubsub の観点では「書き手（PortsOrch）が内部 API 経由で生成し、STATE_DB / COUNTERS_DB を書く」構造。

### 2. addBridgePort() → SUBJECT_TYPE_BRIDGE_PORT_CHANGE 通知

`PortsOrch::addBridgePort()` 末尾 (portsorch.cpp:7280-7281) が `SUBJECT_TYPE_BRIDGE_PORT_CHANGE` を発行する。
`m_observers` を通じた Observer パターンで以下の購読者に通知される:

- `IsolationGroupOrch` (isolationgrouporch.cpp:233): Port::TUNNEL 型を特別扱いしないため実質副作用なし

この通知は Redis Pub/Sub ではなく in-process Observer パターン。
他プロセスや APPL_DB/STATE_DB には伝搬しない。

### 3. updateDbTunnelOperStatus() → STATE_DB

SAI ポートステータス変化イベント → `VxlanTunnelOrch::updateDbTunnelOperStatus()` (vxlanorch.cpp:1893) →
`m_stateVxlanTable.set(tunnel_name, {operstatus})` で STATE_DB:VXLAN_TUNNEL_TABLE を直接更新する。
この書込は `Table` 型 (非 ProducerStateTable) のため Redis `HSET` を直接発行する。
Redis Pub/Sub チャンネルへの通知はない。

### 4. SelectableTimer → COUNTERS_DB

`VxlanTunnelOrch` が 1 秒タイマー (`FLEX_COUNTER_UPD_INTERVAL=1` 秒) で
`doTask(SelectableTimer)` を周期実行し、COUNTERS_DB の `COUNTERS_TUNNEL_NAME_MAP` /
`COUNTERS_TUNNEL_TYPE_MAP` を更新する (vxlanorch.cpp:1322-1335)。
ブリッジポート OID ではなく SAI tunnel OID が対象。

### 5. removeBridgePort() → SUBJECT_TYPE_BRIDGE_PORT_CHANGE 通知 (削除)

`PortsOrch::removeBridgePort()` も削除完了後に `SUBJECT_TYPE_BRIDGE_PORT_CHANGE` を発行する。
購読者への通知方法は addBridgePort と同じ in-process Observer パターン。

## まとめ

Port::TUNNEL の pubsub 経路は 3 つ:
1. in-process Observer (BRIDGE_PORT_CHANGE) — 生成・削除時、即時、プロセス内のみ
2. STATE_DB Table.set — SAI oper-status 変化時、非同期、Redis HSET 直接発行
3. COUNTERS_DB Table.set — 1 秒タイマー、FLEX_COUNTER_UPD_INTERVAL 遅延あり

Redis ProducerStateTable / ConsumerStateTable 型の Pub/Sub は使用していない。
