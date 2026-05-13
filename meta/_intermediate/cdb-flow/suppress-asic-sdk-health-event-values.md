# SUPPRESS_ASIC_SDK_HEALTH_EVENT — 値依存挙動分析

## Phase 1: YANG フィールド全列挙

- `severity` (key): 文字列（`fatal` / `warning` / `notice`）
- `max_events`: uint32
- `categories`: leaf-list of enum（`software` / `firmware` / `cpu_hw` / `asic_hw`）

## Phase 2: per-value 挙動

### `severity` (key) 値別挙動
| 値 | SAI 変換 | 挙動 |
|----|----------|------|
| `fatal` | `SAI_SWITCH_ATTR_REG_FATAL_SWITCH_ASIC_SDK_HEALTH_CATEGORY` | fatal 重大度の health event カテゴリを登録。 |
| `warning` | `SAI_SWITCH_ATTR_REG_WARNING_SWITCH_ASIC_SDK_HEALTH_CATEGORY` | warning 重大度のカテゴリを登録。 |
| `notice` | `SAI_SWITCH_ATTR_REG_NOTICE_SWITCH_ASIC_SDK_HEALTH_CATEGORY` | notice 重大度のカテゴリを登録。 |
| 空文字 | なし | `SWSS_LOG_ERROR("Failed to parse switch hash key: empty string")` → 破棄。 |
| その他 | なし | `SWSS_LOG_ERROR("Unknown severity %s")` → 破棄。SAI severity map にない値は全て拒否。 |
| プラットフォーム非対応 severity | なし | `SWSS_LOG_NOTICE("Unsupport to register categories on severity %d")` → スキップ。 |

### `categories` 値別挙動
| 値 | SAI 変換 | 挙動 |
|----|----------|------|
| `software` | `SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_SW` | ソフトウェア起因イベントを抑制。 |
| `firmware` | `SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_FW` | ファームウェア起因イベントを抑制。 |
| `cpu_hw` | `SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_CPU_HW` | CPU ハードウェア起因イベントを抑制。 |
| `asic_hw` | `SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_ASIC_HW` | ASIC ハードウェア起因イベントを抑制。 |
| 省略（未指定） | なし | 全カテゴリが抑制対象として登録される（`registerAsicSdkHealthEventCategories` 引数なし呼び出し）。 |

### DEL 操作時の挙動
| 操作 | 挙動 |
|------|------|
| DEL_COMMAND | 全カテゴリの抑制を解除（`registerAsicSdkHealthEventCategories` 引数なし）。 |

## Phase 3: ソース確認

- `sonic-swss/orchagent/switchorch.cpp:73-90`: severity → SAI attr map、category → SAI category map の両方が定義。
- `switchorch.cpp:1369-1380`: `interested_categories_set` を universal set で初期化し、suppressed リストを erase してから SAI に登録。
- `switchorch.cpp:261-270`: 初期化時に `cfgSuppressASHETable.hget(severity, "categories")` で既存設定を読み込み。

## enum 有無

- `severity` (key): enum なし（文字列。有効値 `fatal` / `warning` / `notice`）
- `categories`: YANG leaf-list enum（`software` / `firmware` / `cpu_hw` / `asic_hw`）
