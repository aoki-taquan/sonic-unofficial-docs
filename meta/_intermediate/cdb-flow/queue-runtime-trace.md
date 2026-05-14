# queue — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`QUEUE`

## 段階 1: Consumer 登録

- **orchagent / QosOrch** (`sonic-swss/orchagent/qosorch.cpp`): `QUEUE` テーブルを `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- QosOrch がキューのスケジューラマップ (`scheduler`) と WRED プロファイル (`wred_profile`) を解析。
- APP_DB への書き込みなし。

## 段階 3: APPL → SAI

- QosOrch が `sai_scheduler_api` / `sai_wred_api` を呼び出し、キュー OID に対してスケジューラと WRED を適用。

## 段階 4: タイミング + 副作用

- 参照するスケジューラ/WRED が未作成の場合は `task_need_retry`。
- 副作用: キューの WRED 変更は既存フロー中のパケットからリアルタイムに適用される。
