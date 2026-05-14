# SWITCH_HASH — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`SwitchOrch` が `SWITCH_HASH` テーブルを読み、SAI の ECMP/LAG hash 属性を設定する。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| SAI `SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_*` | `ecmp_hash_algorithm` フィールド | CRC/XOR/Random 等に対応する SAI enum | `switchorch.cpp` |
| SAI `SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_*` | `lag_hash_algorithm` フィールド | 同上 | `switchorch.cpp` |
| hash field list OID | `ecmp_hash` / `lag_hash` leaf-list | 各 hash-field に対応する SAI hash field オブジェクト | `switchorch.cpp` |

**CONFIG_DB 内フィールド間の自動付与**: `ecmp_hash_algorithm` / `lag_hash_algorithm` が未設定の場合は SAI デフォルトのままとなる（CRC 相当）。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `SwitchOrch` は常時登録 | `SWITCH_HASH` テーブルは無条件購読 | `orchdaemon.cpp` |
| SAI hash capability 未サポート | `sai_query_attribute_capability()` 失敗 → ログのみ | `switchorch.cpp` |
| `SWITCH_HASH|GLOBAL` エントリのみ有効 | シングルトン制約 (key が GLOBAL 以外は無視) | `sonic-hash.yang` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `SwitchOrch` | `ecmp_hash_algorithm` フィールドあり | ECMP hash algorithm を SAI 属性として設定 | `switchorch.cpp` |
| `SwitchOrch` | `lag_hash_algorithm` フィールドあり | LAG hash algorithm を SAI 属性として設定 | `switchorch.cpp` |
| `SwitchOrch` | `ecmp_hash` leaf-list あり | ECMP 用 hash field オブジェクト群を生成して SAI に設定 | `switchorch.cpp` |
| `SwitchOrch` | `lag_hash` leaf-list あり | LAG 用 hash field オブジェクト群を生成して SAI に設定 | `switchorch.cpp` |
| `SwitchOrch` | SAI 設定エラー | ログ出力 + 処理継続 | `switchorch.cpp` |

> **スキャン証跡**: `SWITCH_HASH` はスイッチ全体の ECMP/LAG ハッシュポリシーの単一エントリ。SwitchOrch が SAI hash attribute を直接設定。field 間の自動派生はアルゴリズムデフォルト補完のみ。
