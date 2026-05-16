# MUX_CABLE 副次 DB 書込 (Phase F)

対象: `sonic-swss/orchagent/muxorch.cpp`
調査日: 2026-05-16

## 副次書込一覧

### 1. STATE_DB `MUX_CABLE_TABLE`（`state_mux_cable_table_`）

- **書込者**: `MuxOrch::handleMuxCfg()` (muxorch.cpp:2285)
- **キー**: `MUX_CABLE_TABLE|<ifname>`
- **フィールド**: `neighbor_mode` = `"host-route"` or `"prefix-route"`
- **トリガー**: CONFIG_DB `MUX_CABLE` に SET 操作が来て MuxCable オブジェクトが新規作成されたとき（既存エントリ更新では走らない）
- **ライブラリ**: `swss::Table::hset()`
- **schema.h 定数**: `STATE_MUX_CABLE_TABLE_NAME = "MUX_CABLE_TABLE"` (schema.h:457)

### 2. STATE_DB `MUX_CABLE_TABLE`（`mux_state_table_`）

- **書込者**: `MuxStateOrch::updateMuxState()` (muxorch.cpp:2640)
- **キー**: `MUX_CABLE_TABLE|<ifname>`
- **フィールド**: `state` = HW 状態と mux 論理状態を照合した結果（`active` / `standby` / `unknown` / `error`）
- **トリガー**: APPL_DB `HW_MUX_CABLE_TABLE` に HW 状態通知が届いたとき (`MuxStateOrch::addOperation()`)
- **ライブラリ**: `swss::Table::hset()`

### 3. APPL_DB `HW_MUX_CABLE_TABLE`（`mux_table_`）

- **書込者**: `MuxCableOrch::updateMuxState()` (muxorch.cpp:2513)
- **キー**: `HW_MUX_CABLE_TABLE|<ifname>`
- **フィールド**: `state` = `active` or `standby`（mux 状態遷移完了後）
- **トリガー**: active/standby 遷移ハンドラ (`stateActive()` / `stateStandby()`) から `mux_cb_orch->updateMuxState()` 呼び出し経由
- **ライブラリ**: `swss::Table::set()`
- **schema.h 定数**: `APP_HW_MUX_CABLE_TABLE_NAME = "HW_MUX_CABLE_TABLE"` (schema.h:141)

### 4. STATE_DB `MUX_METRICS_TABLE`（`mux_metric_table_`）

- **書込者**: `MuxCableOrch::updateMuxMetricState()` (muxorch.cpp:2544)
- **キー**: `MUX_METRICS_TABLE|<ifname>`
- **フィールド**: `orch_switch_<active|standby>_start` / `orch_switch_<active|standby>_end` = タイムスタンプ文字列（例: `"2026-May-16 12:34:56.123456"`）
- **トリガー**: active/standby 切替開始・完了時。`stateActive()`/`stateStandby()` から `mux_cb_orch->updateMuxMetricState()` を呼ぶ
- **ライブラリ**: `swss::Table::hset()`
- **schema.h 定数**: `STATE_MUX_METRICS_TABLE_NAME = "MUX_METRICS_TABLE"` (schema.h:460)

### 5. APPL_DB `TUNNEL_ROUTE_TABLE`（`app_tunnel_route_table_`）

- **書込者**: `MuxCableOrch::addTunnelRoute()` / `delTunnelRoute()` (muxorch.cpp:2547, 2570)
- **キー**: `TUNNEL_ROUTE_TABLE|<server-ip-prefix>`
- **フィールド**: `alias` = ポート名（tunnel nexthop エイリアス）
- **トリガー**: standby 遷移時（neighbor を tunnel NH に切替するとき）は `addTunnelRoute()`, active 遷移時は `delTunnelRoute()`
- **ライブラリ**: `swss::ProducerStateTable::set()` / `del()`
- **schema.h 定数**: `APP_TUNNEL_ROUTE_TABLE_NAME = "TUNNEL_ROUTE_TABLE"` (schema.h:51)

## 備考

- `state_mux_cable_table_` と `mux_state_table_` は同じ STATE_DB テーブル名 `MUX_CABLE_TABLE` を指すが、
  用途が異なる（前者: `neighbor_mode` フィールド, 後者: `state` フィールド）。
- `mux_table_` (APPL_DB `HW_MUX_CABLE_TABLE`) への書込は HW 状態の最終確定を通知し、
  `MuxStateOrch` がこれを購読して STATE_DB の `state` を更新する二段構成になっている。
