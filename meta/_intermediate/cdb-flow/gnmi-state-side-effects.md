# gnmi-state — Side Effects (Phase F)

## 調査概要

- 対象テーブル: `TELEMETRY_CONNECTIONS` (STATE_DB)
- 調査日: 2026-05-19
- 調査者: Claude (batch #6)
- ソースリポジトリ: `sonic-net/sonic-gnmi` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)

## 結論

`TELEMETRY_CONNECTIONS` への HSet / HDel は他の DB テーブルへの書込を連鎖トリガしない。
このテーブルは可視化専用のランタイム状態であり、制御パスには含まれない。

## 調査ファイル

- `gnmi_server/connection_manager.go`: HSet / HDel ロジック
- `gnmi_server/server.go`: NewServer() → InitCounters() (SysV IPC、TELEMETRY_CONNECTIONS と独立)
- `common_utils/shareMem.go`: gNMI 操作カウンタ (Redis COUNTERS_DB への書込なし)
- `gnmi_server/server_test.go:5176,5182`: HGetAll による読み取りテスト

## 副次書込なしの根拠

- `connection_manager.go` には `swsscommon.ProducerStateTable` / `NotificationProducer` の参照なし
- `APPL_DB` / `ASIC_DB` / `COUNTERS_DB` / `FLEX_COUNTER_DB` への書込コードなし
- `show gnmi` (sonic-utilities) は HGetAll で読み取るのみ
