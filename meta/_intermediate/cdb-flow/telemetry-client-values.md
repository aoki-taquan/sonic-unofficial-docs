# TELEMETRY_CLIENT — 値依存挙動調査メモ

## ソース

- `sonic-telemetry_client.yang` (sonic-buildimage@9ea932ec)
- `sonic-gnmi/dialout/dialout_client/dialout_client.go`

## enum 値

### `encoding` (encoding typedef)

- `JSON_IETF`: RFC 7951 準拠 JSON エンコーディング（最も広く使用）
- `ASCII`: テキスト ASCII エンコーディング
- `BYTES`: バイナリエンコーディング
- `PROTO`: Protobuf エンコーディング

### `report_type` (report-type typedef)

- `periodic`: `report_interval` 間隔で定期報告
- `stream`: イベント駆動型リアルタイムストリーム
- `once`: 1 回だけ送信してサブスクリプション終了

### `path_target` (path_target typedef)

- `APPL_DB` / `CONFIG_DB` / `COUNTERS_DB` / `STATE_DB`: 対応する Redis DB を購読
- `OTHERS`: 上記以外のデータソース

### `prefix` (Subscription / DestinationGroup)

- `Subscription`: サブスクリプションエントリ
- `DestinationGroup`: 宛先グループエントリ

## 値依存挙動

| フィールド | 値 | 挙動 |
|-----------|-----|-----|
| `report_type` | `periodic` | `report_interval` [ms] ごとに定期送信。デフォルト 5000ms |
| `report_type` | `stream` | ON_CHANGE — データ変化時に即送信 |
| `report_type` | `once` | 1 回取得して切断。`report_interval` 無視 |
| `unidirectional` | `true` (default) | dial-out は一方向ストリーム |
| `unidirectional` | `false` | 双方向 RPC (コレクタからの応答あり) |
| `dst_addr` | IPv6 アドレス | `ipv4-port` typedef の pattern で YANG 拒否 |
| `dst_group` (Subscription) | 存在しない DestinationGroup 名 | `must` 制約違反で YANG バリデーション失敗 |
| `TELEMETRY_CLIENT|Global` | DEL 操作 | 拒否 (`"Invalid delete operation"`) |
