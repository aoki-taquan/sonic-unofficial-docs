# system-defaults — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`SYSTEM_DEFAULTS`

## 段階 1: Consumer 登録

- **各種 mgrd / orchagent**: `SYSTEM_DEFAULTS` テーブルを起動時に `ConfigDBConnector` で読み込む。
- 主に `switch_type` (L2, L3, VOQ 等) の判定に使用される。

## 段階 2: CFG → APPL 翻訳

- orchagent 起動時に `SYSTEM_DEFAULTS` を読み込んでスイッチモードを決定。動的変更は基本的に非サポート。

## 段階 3: APPL → SAI

- SAI 初期化時に `sai_switch_api->create_switch()` のパラメータとして switch_type 等が渡される。

## 段階 4: タイミング + 副作用

- SYSTEM_DEFAULTS は主に起動時設定。変更時はサービス再起動が必要。
- 副作用: switch_type の変更は swss/syncd の完全再起動が必要でサービス断が生じる。
