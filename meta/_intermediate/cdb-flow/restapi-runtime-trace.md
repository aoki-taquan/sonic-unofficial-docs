# restapi — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`RESTAPI`

## 段階 1: Consumer 登録

- **hostcfgd**: `RESTAPI` テーブルを `ConfigDBConnector` で購読。

## 段階 2: CFG → APPL 翻訳

- hostcfgd が REST API サービス (sonic-restapi / sonic-gnmi) の有効・無効設定を `/etc/sonic/` に書き込む。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- SAI 経由なし。REST API は管理プレーン機能。

## 段階 4: タイミング + 副作用

- hostcfgd が設定を反映後、対象サービスが再起動されるまで数秒。
- 副作用: REST API 無効化中に自動化スクリプトが接続しようとするとタイムアウトが発生。
