# SUPPRESS_ASIC_SDK_HEALTH_EVENT 例外条件抽出 (cdb-batch-7)

## ソース
- `sonic-swss/orchagent/switchorch.cpp`

## 抽出した例外条件

1. **key が空文字列**: key が空の場合 `SWSS_LOG_ERROR("Failed to parse switch hash key: empty string")` → エントリ破棄。
   - 証拠: switchorch.cpp l.1427-1430

2. **severity が未知の値**: key に設定された severity が `switch_asic_sdk_health_event_severity_to_switch_attribute_map` に存在しない場合 `SWSS_LOG_ERROR("Unknown severity %s in SUPPRESS_ASIC_SDK_HEALTH_EVENT table")` → エントリ破棄。有効な severity は `fatal` / `warning` / `notice` 等の SAI 定義値のみ。
   - 証拠: l.1436-1441

3. **SAI 非対応 severity**: `m_supportedAsicSdkHealthEventAttributes.find(saiSeverity) == end()` の場合、`SWSS_LOG_NOTICE("Unsupport to register categories on severity %d")` → エントリ破棄 (スキップ)。SAI 実装がその severity をサポートしないプラットフォームでは設定が無視される。
   - 証拠: l.1455-1462

4. **categories フィールド未指定の場合はデフォルト全カテゴリ登録**: `categories` フィールドが存在しない場合は `registerAsicSdkHealthEventCategories(saiSeverity, key)` が引数なしで呼ばれ、全カテゴリが抑制対象として登録される。

5. **DEL 操作でカテゴリ抑制解除**: DEL_COMMAND 受信時は `registerAsicSdkHealthEventCategories(saiSeverity, key)` を引数なしで呼び出し、全カテゴリの抑制を解除 (登録をリセット) する。

6. **未知の operation**: `SET_COMMAND` / `DEL_COMMAND` 以外の op が来た場合 `SWSS_LOG_ERROR("Unknown operation(%s)")` を出力してスキップ。
   - 証拠: l.1485-1488
