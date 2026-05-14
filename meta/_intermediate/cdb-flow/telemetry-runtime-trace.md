# telemetry — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`TELEMETRY`

## 段階 1: Consumer 登録

- **gnmi-telemetry / sonic-gnmi**: `TELEMETRY` テーブルを `ConfigDBConnector` で購読してグローバル設定を適用。

## 段階 2: CFG → APPL 翻訳

- gnmi-telemetry がサーバポート / TLS 証明書 / 認証設定を読み込みリッスンを開始。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- SAI 経由なし。gNMI サーバが DATA_DB / STATE_DB を購読してデータを提供。

## 段階 4: タイミング + 副作用

- 設定変更は gnmi-telemetry 再起動後に有効 (数秒)。クライアントは再接続が必要。
