# SUPPRESS_ASIC_SDK_HEALTH_EVENT — ハードコード定数 (Phase E)

## 調査対象

- `sonic-net/sonic-swss` : `orchagent/switchorch.cpp`
- `sonic-net/sonic-swss-common` : `common/schema.h`

## テーブル名マクロ (schema.h)

| マクロ | 値 | evidence |
|--------|----|----------|
| `CFG_SUPPRESS_ASIC_SDK_HEALTH_EVENT_NAME` | `"SUPPRESS_ASIC_SDK_HEALTH_EVENT"` | `schema.h:394` |

## severity → SAI 属性マッピング (switchorch.cpp:71-76)

`switch_asic_sdk_health_event_severity_to_switch_attribute_map` で固定:

| CONFIG_DB キー (severity) | SAI 属性 |
|--------------------------|---------|
| `"fatal"` | `SAI_SWITCH_ATTR_REG_FATAL_SWITCH_ASIC_SDK_HEALTH_CATEGORY` |
| `"warning"` | `SAI_SWITCH_ATTR_REG_WARNING_SWITCH_ASIC_SDK_HEALTH_CATEGORY` |
| `"notice"` | `SAI_SWITCH_ATTR_REG_NOTICE_SWITCH_ASIC_SDK_HEALTH_CATEGORY` |

他の文字列は `std::out_of_range` 例外 → `SWSS_LOG_ERROR` + エントリ消費スキップ (`switchorch.cpp:1439`).

## categories フィールド値 → SAI カテゴリ (switchorch.cpp:93-100)

`switch_asic_sdk_health_event_category_map` で固定:

| CONFIG_DB 値 | SAI 定数 |
|-------------|---------|
| `"software"` | `SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_SW` |
| `"firmware"` | `SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_FW` |
| `"cpu_hw"` | `SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_CPU_HW` |
| `"asic_hw"` | `SAI_SWITCH_ASIC_SDK_HEALTH_CATEGORY_ASIC_HW` |

不明文字列は `SWSS_LOG_ERROR("Unknown ASIC/SDK health category %s to suppress", ...)` + `continue` (`switchorch.cpp:1384`).

## categories フィールドのセパレータ

`tokenize(suppressed_category_list, ',')` でカンマ区切り (`switchorch.cpp:1375`). スペース除去なし。

## デフォルト登録セット (categories 未指定時)

`switch_asic_sdk_health_event_category_universal_set` = {SW, FW, CPU_HW, ASIC_HW} の全 4 カテゴリが登録対象 (`switchorch.cpp:1369`). `categories` フィールドが空 / 未指定 → 全カテゴリを監視 (抑制なし).

## SAI notification コールバック登録の定数

| 属性 | 値 | evidence |
|------|----|----------|
| `SAI_SWITCH_ATTR_SWITCH_ASIC_SDK_HEALTH_EVENT_NOTIFY` | (SAI 定数) | `switchorch.cpp:218` — 対応有無クエリに使用 |

コールバック関数ポインタ `on_switch_asic_sdk_health_event` も固定シンボル (`switchorch.cpp:222`).
