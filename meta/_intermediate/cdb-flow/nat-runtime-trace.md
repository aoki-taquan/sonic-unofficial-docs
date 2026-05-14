# nat — CDB → 実コンテナ動作 ランタイムトレース

## 対象テーブル
`NAT_GLOBAL / STATIC_NAT / STATIC_NAPT / NAT_POOL / NAT_BINDINGS`

## 段階 1: Consumer 登録

- **orchagent / NatOrch** (`sonic-swss/orchagent/natorch.cpp`): `NAT_GLOBAL`, `STATIC_NAT`, `STATIC_NAPT`, `NAT_POOL`, `NAT_BINDINGS` を `SubscriberStateTable` で購読。

## 段階 2: CFG → APPL 翻訳

- NatOrch が `NAT_GLOBAL.admin_mode=enabled` を確認してから各テーブルの処理を開始。
- STATIC_NAT/STATIC_NAPT エントリは APP_DB 経由ではなく orchagent から直接 SAI へ。
- `admin_mode=disabled` の場合はエントリをキューに保持して SAI 操作を行わない。

## 段階 3: APPL → SAI

- NatOrch が `sai_nat_api->create_nat_entry()` を呼び出してハードウェアに NAT エントリを書き込む。
- NAT pool + binding の場合は Dynamic NAT (MASQUERADE 型) として SAI に登録。

## 段階 4: タイミング + 副作用

- `admin_mode` 有効化時にキュー内の全エントリを一括処理 (数十〜数百エントリの場合に数百 ms 要する場合あり)。
- 副作用: conntrack timeout 変更は既存セッションには影響しない (新規セッションから適用)。
- 副作用: NAT pool の枯渇時は新規 NAT セッションが確立できず DROP。STATE_DB でカウンタ確認可能。
