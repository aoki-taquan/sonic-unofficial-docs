# switch-trimming failure (Phase D) 調査ログ

## 調査対象

- `sonic-swss/orchagent/switchorch.cpp` L1070–1360
- `sonic-swss/orchagent/switch/trimming/helper.cpp` L62–250
- `sonic-swss/orchagent/switch/trimming/capabilities.cpp` L142–179

## 主要な失敗パス

### パース失敗 (helper.cpp)

- 空文字列フィールド: `"Failed to parse field(%s): empty value is prohibited"` → `parseTrimConfig` が `false` を返しエントリ全体スキップ
- `size` 数値変換失敗 (exception catch): LOG_ERROR + `return false`
- `dscp_value` 範囲外 (0..63 外): `"Failed to parse field(dscp_value): value(%s) is out of range: 0 <= dscp <= 63"` → `return false`
- `tc_value` / `queue_index` 数値変換失敗 (exception catch): LOG_ERROR + `return false`
- 有効フィールド 0 件: `"Validation error: missing valid fields"` → `validateTrimConfig` が `false`

### ASIC capability 失敗 (switchorch.cpp)

- `!trimCap.isSwitchTrimmingSupported()` → WARN + `return true` (no-op、retry なし)
- 各属性の `isAttrSupported=false` → `"capability is not supported"` LOG_ERROR + `return false`

### SAI set 失敗 (switchorch.cpp)

- 各属性の `set_switch_attribute()` 失敗 → `"Failed to set switch trimming <attr> in SAI"` LOG_ERROR + `return false`
- `setSwitchTrimming` が `false` を返すと `"ASIC and CONFIG DB are diverged"` LOG_ERROR

### DEL 非サポート

- DEL 操作は全属性で `"operation is not supported"` → `return false`
- エントリは CONFIG_DB に残存

## retry 挙動

すべての失敗ケースで retry なし (erase)。ASIC capability 未サポートのみ `return true` で no-op となり、エントリが CONFIG_DB に残っても以降も SAI 反映なし。

## STATE_DB / ERROR_TABLE

- ERROR_TABLE への書き込みなし
- `STATE_DB:SWITCH_CAPABILITY|switch` の `SWITCH_TRIMMING_CAPABLE` で反映状態確認可能
