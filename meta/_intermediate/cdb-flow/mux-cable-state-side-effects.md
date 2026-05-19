# mux-cable-state — Phase F 副次 DB 書込 調査証跡

## 調査対象ソース

- `sonic-swss/orchagent/muxorch.cpp`
- `sonic-linkmgrd/src/DbInterface.cpp`
- `sonic-linkmgrd/src/DbInterface.h`
- `sonic-swss-common/common/schema.h`

## orchagent (MuxCableOrch) の副次書込み

### APP_DB.HW_MUX_CABLE_TABLE (APP_HW_MUX_CABLE_TABLE_NAME = "HW_MUX_CABLE_TABLE")

`MuxCableOrch::updateMuxState()` は STATE_DB ではなく APP_DB の `HW_MUX_CABLE_TABLE` に `state` を書き込む。
これは MuxStateOrch が APPL_DB 側の同テーブルを購読しているため、orchagent 内部での pub-sub 経路になっている。

```cpp
// muxorch.cpp:2505,2508-2513
mux_table_ = unique_ptr<Table>(new Table(db, APP_HW_MUX_CABLE_TABLE_NAME));

void MuxCableOrch::updateMuxState(string portName, string muxState) {
    vector<FieldValueTuple> tuples;
    FieldValueTuple tuple("state", muxState);
    tuples.push_back(tuple);
    mux_table_->set(portName, tuples);
}
```

### STATE_DB.MUX_METRICS_TABLE (STATE_MUX_METRICS_TABLE_NAME = "MUX_METRICS_TABLE")

`MuxCableOrch::updateMuxMetricState()` は MUX 状態遷移の開始・終了タイムスタンプを STATE_DB の
`MUX_METRICS_TABLE` に書き込む。フィールドは `"orch_switch_<state>_start"` / `"orch_switch_<state>_end"` の形式。

呼び出しタイミング:
- `MuxCable::stateActive()` / `stateStandby()` 開始時: `updateMuxMetricState(port, state, true)` (muxorch.cpp:540)
- `MuxCable::setState()` で状態が確定した時: `updateMuxMetricState(port, state, false)` (muxorch.cpp:556)
- rollback 時: `updateMuxMetricState(port, prev_state_str, true)` (muxorch.cpp:576)
- rollback 完了後: `updateMuxMetricState(port, state_str, false)` (muxorch.cpp:611)

### APP_DB.TUNNEL_ROUTE_TABLE (APP_TUNNEL_ROUTE_TABLE_NAME = "TUNNEL_ROUTE_TABLE")

`MuxCableOrch::addTunnelRoute()` / `removeTunnelRoute()` は standby 側への P2P トンネル経路を
APP_DB の `TUNNEL_ROUTE_TABLE` に書き込む / 削除する。

呼び出しタイミング:
- neighbor が MUX 管理に入った時 (neighbor_mode 切替): `addTunnelRoute(nh)` (muxorch.cpp:1104)
- neighbor が MUX 管理から外れた時: `removeTunnelRoute(nh)` (muxorch.cpp:1108)

---

## linkmgrd (DbInterface) の副次書込み

### STATE_DB.MUX_LINKMGR_TABLE (STATE_MUX_LINKMGR_TABLE_NAME = "MUX_LINKMGR_TABLE")

linkmgrd は自身の内部状態遷移を STATE_DB の `MUX_LINKMGR_TABLE` に書き込む。
`hset(portName, "state", mMuxLinkmgrState[...])` (DbInterface.cpp:471)

### STATE_DB.MUX_METRICS_TABLE (STATE_MUX_METRICS_TABLE_NAME = "MUX_METRICS_TABLE")

linkmgrd も orchagent と同じ `MUX_METRICS_TABLE` にタイムスタンプを書き込む。
`del(portName)` + `hset(portName, msg, time)` で古い値を消してから書き込む (DbInterface.cpp:498-501)。

### STATE_DB.MUX_SWITCH_CAUSE (STATE_MUX_SWITCH_CAUSE_TABLE_NAME = "MUX_SWITCH_CAUSE")

active ↔ standby 切り替えが発生した時、切り替え原因 (`cause`) とタイムスタンプ (`time`) を
STATE_DB の `MUX_SWITCH_CAUSE` テーブルに記録する (DbInterface.cpp:246-247)。

### STATE_DB.LINK_PROBE_STATS (STATE_LINK_PROBE_STATS_TABLE_NAME = "LINK_PROBE_STATS")

リンクプローバの統計情報 (ICMP echo の送受信カウンタ等) を STATE_DB の `LINK_PROBE_STATS` テーブルに書き込む。
`hdel` + `hset` パターンで更新 (DbInterface.cpp:528-531,558)。

### APP_DB.MUX_CABLE_TABLE (APP_MUX_CABLE_TABLE_NAME = "MUX_CABLE_TABLE") via ProducerStateTable

linkmgrd は APPL_DB の `MUX_CABLE_TABLE` に ProducerStateTable 経由で mux 状態変更コマンドを送る。
orchagent がこれを購読して実際の MUX 切替を実行する。

### APP_DB.HW_FORWARDING_STATE_PEER (APP_PEER_HW_FORWARDING_STATE_TABLE_NAME = "HW_FORWARDING_STATE_PEER")

Peer ToR の HW forwarding state を APP_DB に書き込む (DbInterface.cpp:430)。
ycabled / gRPC から受け取ったピア側の状態を伝達するための経路。

### APP_DB.MUX_CABLE_COMMAND_TABLE (APP_MUX_CABLE_COMMAND_TABLE_NAME = "MUX_CABLE_COMMAND_TABLE")

linkmgrd が mux probe コマンドを APP_DB の `MUX_CABLE_COMMAND_TABLE` に送る (DbInterface.cpp:443)。
orchagent がこれを購読して gRPC probe を実行する。

### CONFIG_DB.MUX_CABLE (CFG_MUX_CABLE_TABLE_NAME) — warm restart 限定

warm restart 時のみ、linkmgrd は `handleSetMuxMode()` で CONFIG_DB の `MUX_CABLE.state` を
書き直す (DbInterface.cpp:1047)。通常運用時には発生しない。

---

## まとめ

STATE_DB の `MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` への書込みを起点に、以下の副次 DB 書込みが発生する:

| 副次 DB | テーブル | 書込み元 | トリガ |
|---------|---------|---------|-------|
| APP_DB | HW_MUX_CABLE_TABLE | MuxCableOrch | MUX 状態遷移 |
| APP_DB | TUNNEL_ROUTE_TABLE | MuxCableOrch | neighbor 追加/削除 |
| STATE_DB | MUX_METRICS_TABLE | MuxCableOrch / linkmgrd | 状態遷移開始・終了 |
| STATE_DB | MUX_LINKMGR_TABLE | linkmgrd | linkmgrd 内部状態遷移 |
| STATE_DB | MUX_SWITCH_CAUSE | linkmgrd | active↔standby 切替 |
| STATE_DB | LINK_PROBE_STATS | linkmgrd | リンクプローバ統計 |
| APP_DB | MUX_CABLE_TABLE | linkmgrd (ProducerStateTable) | mux 状態変更コマンド |
| APP_DB | HW_FORWARDING_STATE_PEER | linkmgrd | ピア HW state 通知 |
| APP_DB | MUX_CABLE_COMMAND_TABLE | linkmgrd | probe コマンド |
| CONFIG_DB | MUX_CABLE | linkmgrd | warm restart 限定 |
