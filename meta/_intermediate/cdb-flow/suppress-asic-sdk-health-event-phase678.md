# SUPPRESS_ASIC_SDK_HEALTH_EVENT — Phase 6/7/8 派生・分岐 証跡

## Phase 6: 自動派生 (assignment scan)

`SwitchOrch` が `SUPPRESS_ASIC_SDK_HEALTH_EVENT` テーブルを読み、SAI の health event 抑制設定を行う。

| 派生先 | 派生元条件 | 派生値 | ソース |
|---|---|---|---|
| SAI health event suppression | `SUPPRESS_ASIC_SDK_HEALTH_EVENT` エントリ存在 | `SwitchOrch` が対応する SAI 属性を設定 | `switchorch.cpp` |
| event category マッピング | `event_category` フィールド値 | SAI `sai_switch_attr_t` の対応 health event 属性へマッピング | `switchorch.cpp` |

**CONFIG_DB 内フィールド間の自動付与なし**: テーブル内フィールドは SAI 属性への直接マッピング。

## Phase 7: 条件付き登録 (add_manager 条件)

| 条件 | 影響 | ソース |
|---|---|---|
| `SwitchOrch` は常時登録 | `SUPPRESS_ASIC_SDK_HEALTH_EVENT` テーブルは無条件購読 | `orchdaemon.cpp` |
| SAI capability: health event suppression 未サポート | SAI 属性設定がエラーになるが、orchagent はログのみで継続 | `switchorch.cpp` |

## Phase 8: Handler メソッド内分岐

| Handler | 分岐条件 | 効果 | evidence |
|---|---|---|---|
| `SwitchOrch` | `event_category` フィールド値 | 対応する SAI health event カテゴリへの suppress 属性設定 | `switchorch.cpp` |
| `SwitchOrch` | エントリ削除 | 対応 SAI suppress 設定を解除 | `switchorch.cpp` |
| `SwitchOrch` | SAI 応答エラー | ログ出力 + 処理継続 (致命的エラーとしない) | `switchorch.cpp` |

> **スキャン証跡**: `SUPPRESS_ASIC_SDK_HEALTH_EVENT` は比較的新しいテーブル。SwitchOrch 経由で SAI の ASIC health event フィルタリングを制御。CONFIG_DB 内フィールド間の自動派生なし。
