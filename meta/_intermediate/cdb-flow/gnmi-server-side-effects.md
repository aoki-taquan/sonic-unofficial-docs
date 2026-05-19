# gnmi-server 副次 DB 書込調査メモ (Phase F)

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/gnmi-server.md`
フェーズ: Phase F (副次 DB 書込 / side-effects)

## 調査対象ファイル

| ファイル | リポジトリ | SHA | 役割 |
|---------|-----------|-----|------|
| `gnmi_server/connection_manager.go` | sonic-net/sonic-gnmi | eb635b76 | STATE_DB TELEMETRY_CONNECTIONS 書き込みロジック |
| `gnmi_server/gnsi_certz.go` | sonic-net/sonic-gnmi | eb635b76 | STATE_DB CREDENTIALS テーブル書き込み |
| `gnmi_server/gnoi_system.go` | sonic-net/sonic-gnmi | eb635b76 | STATE_DB Reboot_Request_Channel 通知 |
| `gnmi_server/server.go` | sonic-net/sonic-gnmi | eb635b76 | save_on_set 時のファイルシステム書込 |
| `common_utils/notification_producer.go` | sonic-net/sonic-gnmi | eb635b76 | STATE_DB PUBLISH 経路 |
| `common_utils/context.go` | sonic-net/sonic-gnmi | eb635b76 | SysV IPC 共有メモリ (CounterType) |

## STATE_DB 書込 — TELEMETRY_CONNECTIONS

Subscribe RPC 接続/切断ごとに STATE_DB の TELEMETRY_CONNECTIONS Hash を更新。

- key: `TELEMETRY_CONNECTIONS` (単一 Hash)
- field: `<peer_ip:port>|<target>|...|<RFC3339_timestamp>` (connection_manager.go:94-108)
- value: `"active"` (ハードコード固定)
- HSet: 接続開始 (Add: L116), HDel: 接続終了 (Remove: L127)
- 起動時 PrepareRedis() で HGetAll → 全エントリ HDel (L52-60)

## STATE_DB 書込 — CREDENTIALS

gNSI Certz (証明書管理 RPC) が証明書メタデータを STATE_DB に書き込む。

- key: `CREDENTIALS|<tbl>[|<key>]`
- field/value: 証明書メタデータ各フィールド
- gnsi_certz.go:1046-1051: `sc.HSet(context.Background(), path, fld, val)`

## STATE_DB PUBLISH — Reboot_Request_Channel

gNOI System Reboot RPC が STATE_DB チャネル "Reboot_Request_Channel" に通知を PUBLISH。
gnoi_system.go:27, 117: common_utils.NewNotificationProducer("Reboot_Request_Channel")

## ファイルシステム書込 — save_on_set

GNMI|gnmi.save_on_set=true の場合、Set RPC 実行後に /etc/sonic/config_db.json を上書きする。
server.go:1051-1063: SaveOnSetEnabled() → sc.ConfigSave("/etc/sonic/config_db.json")

## SysV IPC 共有メモリ — カウンタ

NewServer() が InitCounters() (common_utils) でSysV共有メモリ (memKey=7749) を初期化。
COUNTERS_DB / FLEX_COUNTER_DB への書込なし。gnmi_dump ツールが読み取る。

## DB 書込なし確認

| DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | ProducerStateTable / NotificationProducer の書込なし |
| COUNTERS_DB | なし | カウンタは SysV 共有メモリのみ |
| ASIC_DB | なし | SAI 非経由 |
| FLEX_COUNTER_DB | なし | 参照なし |
