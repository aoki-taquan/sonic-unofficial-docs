# SYSTEM_DEFAULTS — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`db_migrator` と各サービスが `SYSTEM_DEFAULTS` テーブルを参照してシステム全体のデフォルト挙動を決定する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| 各サービスのデフォルト動作 | `SYSTEM_DEFAULTS.synchronous_mode` | `enable` のとき orchagent が SAI call を synchronous モードで実行 | `orchagent/main.cpp` |
| `frr_mgmt_framework_config` | `SYSTEM_DEFAULTS.frr_mgmt_framework_config` | `true` のとき sonic-mgmt-framework が FRR 設定を管理 | 複数サービス |
| `interface_naming_mode` | `SYSTEM_DEFAULTS.interface_naming_mode` | `alias` のとき IF エイリアス名を使用 | `portsyncd` / `intfmgrd` |

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `db_migrator` 実行時 | `SYSTEM_DEFAULTS` テーブルの初期化・マイグレーション | `db_migrator.py` |
| `orchagent` 起動時 | `synchronous_mode` を読み取って起動モードを決定 | `orchagent/main.cpp` |
| `SYSTEM_DEFAULTS|GLOBAL` エントリのみ有効 | シングルトン制約 | `sonic-device_metadata.yang` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `orchagent` 起動 | `synchronous_mode==enable` | SAI API を synchronous モードで呼び出し | `orchagent/main.cpp` |
| `orchagent` 起動 | `synchronous_mode==disable` または未設定 | SAI API を asynchronous モードで呼び出し | `orchagent/main.cpp` |
| 各サービス | `frr_mgmt_framework_config==true` | sonic-mgmt-framework による FRR 設定管理を有効化 | 複数サービス |
| `portsyncd` / `intfmgrd` | `interface_naming_mode==alias` | インターフェース alias 名を使用 | `portsyncd` |
| `portsyncd` / `intfmgrd` | `interface_naming_mode==default` | 標準 IF 名を使用 | `portsyncd` |

> **スキャン証跡**: `SYSTEM_DEFAULTS` は複数のシステム全体設定を束ねるシングルトンテーブル。`synchronous_mode` の分岐が orchagent 起動時の動作に直結する主要な Phase 8 分岐。
