# MUX_CABLE_TABLE / HW_MUX_CABLE_TABLE (STATE_DB) — 副次 DB 書込 (Phase F) 解析メモ

対象: STATE_DB `MUX_CABLE_TABLE|<ifname>` / `HW_MUX_CABLE_TABLE|<ifname>`

ソース確認:
- `sonic-swss/orchagent/muxorch.cpp`
- `sonic-linkmgrd/src/DbInterface.cpp`
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py`
- `sonic-swss-common/common/schema.h`

## 1. STATE_DB テーブルへの書込は「副次書込の終点」

`MUX_CABLE_TABLE` / `HW_MUX_CABLE_TABLE` は STATE_DB テーブルであり、
CONFIG_DB からのデータフローの最終段に位置する。

ただし、これらのテーブルへの書込が**さらに他のコンポーネントの副次処理を引き起こす**ことがある。

## 2. STATE_DB MUX_CABLE_TABLE の書込と副次処理チェーン

### orchagent (MuxStateOrch) → STATE_DB MUX_CABLE_TABLE

`MuxStateOrch::updateMuxState()` (`muxorch.cpp:2637`) が
`mux_state_table_.hset(portName, "state", muxState)` で書込む。

- **直後の副次処理**: なし（STATE_DB への素の HSET のみ）
- **受信側の副次処理**: linkmgrd が `STATE_DB MUX_CABLE_TABLE` を `SubscriberStateTable` で購読しており、書込を検知する

### orchagent (MuxOrch::handleMuxCfg) → STATE_DB MUX_CABLE_TABLE.neighbor_mode

`MuxOrch::handleMuxCfg()` (`muxorch.cpp:2285`) が新規ポート追加時のみ
`state_mux_cable_table_->hset(port_name, "neighbor_mode", neighbor_mode_str)` を書込む。

- **直後の副次処理**: なし
- **受信側の副次処理**: linkmgrd は `neighbor_mode` フィールドを購読検知後に読み取る可能性あり

### orchagent (MuxCableOrch::updateMuxState) → APPL_DB HW_MUX_CABLE_TABLE

`MuxCableOrch::updateMuxState()` (`muxorch.cpp:2509`) が
`mux_table_->set(portName, tuples)` で APPL_DB `HW_MUX_CABLE_TABLE` に書込む。

- **直後の副次処理**: この APPL_DB `HW_MUX_CABLE_TABLE` を `MuxStateOrch` が購読しており、
  hw_state と mux_state を比較して STATE_DB `MUX_CABLE_TABLE.state` を更新する連鎖が発生する

### orchagent (MuxCableOrch::updateMuxMetricState) → STATE_DB MUX_METRICS_TABLE

`updateMuxMetricState()` (`muxorch.cpp:2517-2547`) が
`mux_metric_table_.hset(portName, msg, time)` で STATE_DB `MUX_METRICS_TABLE` にタイムスタンプを書込む。

- **直後の副次処理**: なし（計測用の書込のみ）

## 3. STATE_DB MUX_CABLE_TABLE → linkmgrd ステートマシン更新

linkmgrd の `DbInterface` は STATE_DB `MUX_CABLE_TABLE` を
`SubscriberStateTable(stateDbPtr, STATE_MUX_CABLE_TABLE_NAME)` で購読している (`DbInterface.cpp:1833`)。

`handleMuxStateNotifiction()` (`DbInterface.cpp:1513`) → `processMuxStateNotifiction()` (`DbInterface.cpp:1481`)
→ `mMuxManagerPtr->addOrUpdateMuxPortMuxState(port, v)` でステートマシンを更新する。

ステートマシン更新の結果として linkmgrd は APPL_DB や他の STATE_DB テーブルへの
副次書込を行う場合がある（MUX_CABLE_TABLE (APPL_DB)、MUX_LINKMGR_TABLE、MUX_SWITCH_CAUSE など）。

## 4. ycabled → STATE_DB HW_MUX_CABLE_TABLE

ycabled は gRPC 応答から `HW_MUX_CABLE_TABLE`、`HW_MUX_CABLE_TABLE_PEER`、`MUX_CABLE_INFO` を
直接書込む (swss::Table API)。これらの書込には Redis PUBLISH は行われないが、
`MuxStateOrch` が APPL_DB の `HW_MUX_CABLE_TABLE` を購読しており、
STATE_DB への書込とは別に APPL_DB 経由の連鎖が発生する。

## 5. 副次書込まとめ

| 書込トリガー | 書込先 DB / テーブル | 書込者 | 条件 |
|---|---|---|---|
| STATE_DB `MUX_CABLE_TABLE.state` 更新 | `MuxManager` 内部ステートマシン (メモリ) | linkmgrd `processMuxStateNotifiction` | 常時 |
| linkmgrd ステートマシン更新 | APPL_DB `MUX_CABLE_TABLE` (active/standby 切替コマンド) | linkmgrd | ステートマシン遷移時 |
| linkmgrd ステートマシン更新 | STATE_DB `MUX_LINKMGR_TABLE` | linkmgrd | 内部状態変化時 |
| linkmgrd ステートマシン更新 | STATE_DB `MUX_SWITCH_CAUSE` | linkmgrd | 切替理由変化時 |
| APPL_DB `HW_MUX_CABLE_TABLE` 書込 | STATE_DB `MUX_CABLE_TABLE.state` (via MuxStateOrch) | orchagent `MuxStateOrch` | hw/mux state 比較後 |
| STATE_DB `MUX_METRICS_TABLE` | — | orchagent `MuxCableOrch` | 切替開始/完了時（計測用） |
