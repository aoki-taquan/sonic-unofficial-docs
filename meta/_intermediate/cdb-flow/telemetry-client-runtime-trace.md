# telemetry-client — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`TELEMETRY_CLIENT`

## 段階 1: Consumer 登録

- **gnmi-telemetry** または **sonic-gnmi**: `TELEMETRY_CLIENT` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- gnmi-telemetry がテレメトリクライアント設定 (サブスクリプション対象, エンドポイント, 認証) を読み込みセッションを確立。

## 段階 3: APPL → SAI

- SAI 経由なし。gNMI Dial-Out でリモートコレクタへ購読データを Push。

## 段階 4: タイミング + 副作用

- 設定変更後 gnmi-telemetry が再起動されるまで数秒。サブスクリプション確立に数秒かかる場合あり。
