# pfc-wd — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`PFC_WD`

## 段階 1: Consumer 登録

- **orchagent / PfcWdOrch** (`sonic-swss/orchagent/pfcwdorch.cpp`): `PFC_WD` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- PfcWdOrch が各ポートの PFC Watchdog ポーリング間隔 (`detection_time`, `restoration_time`) と action (`drop`, `forward`, `alert`) を解析。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- PfcWdOrch が SAI `sai_port_api` / `sai_queue_api` を使用して PFC deadlock 検出と自動回復を設定。
- action=drop: デッドロック検知時に該当キューの PFC フレームを drop。

## 段階 4: タイミング + 副作用

- `detection_time` ms 以内に PFC デッドロードを検知し、`restoration_time` ms 後に自動復旧。
- 副作用: action=drop 時にトラフィックが一時的に DROP。lossless クラスのパケットロスが生じる可能性。
- STATE_DB `PFC_WD_TABLE` でデッドロック検知状態を確認可能。
