# switch-hash failure behavior (Phase D) — 調査証跡

## 調査対象

- `sonic-swss/orchagent/switchorch.cpp` — `doCfgSwitchHashTableTask()` / `setSwitchHash()` / `setSwitchHashFieldListSai()`
- `sonic-swss/orchagent/switch/switch_helper.cpp` — `parseSwHash()`
- `sonic-swss/orchagent/switch/switch_capabilities.cpp` — `isSwitchEcmpHashSupported()` など

## SET 時の失敗パターン

### 1. 空キー
`doCfgSwitchHashTableTask()` 冒頭でキーが空文字列の場合
`"Failed to parse switch hash key: empty string"` → LOG_ERROR → continue（エントリスキップ）。
再試行なし（Consumer の `m_toSync` エントリは erase される）。

### 2. ASIC capability 機構自体が未サポート (`isSwitchEcmpHashSupported()` = false)
`setSwitchHash()` の capability チェックで `false` を返す。
`SWSS_LOG_WARN("Switch ECMP hash configuration is not supported: skipping ...")` のみ。
SAI SET は発行されず、内部キャッシュ (`swHlpr.setSwHash()`) も更新されない。
エントリは Consumer から erase → 再試行なし。**エラーにならずサイレントに握りつぶされる。**

### 3. SAI capability セットに含まれない hash-field / hash-algorithm
`validateSwitchHashFieldCap()` / `validateSwitchHashAlgorithmCap()` が false を返す。
`LOG_ERROR("Failed to validate switch ECMP/LAG hash: capability is not supported")` → `return false`。
上位 `setSwitchHash()` → `"Failed to set switch hash: ASIC and CONFIG DB are diverged"` LOG_ERROR。
Consumer erase → 再試行なし。

### 4. SAI `set_hash_attribute()` 失敗
`setSwitchHashFieldListSai()` 内で SAI API が `SAI_STATUS_SUCCESS` 以外を返す。
`LOG_ERROR("Failed to set switch ECMP/LAG hash in SAI")` → `return false`。
内部キャッシュは更新されない（`swHlpr.setSwHash()` が呼ばれない）。
Consumer erase → 再試行不可。**CLI / sonic-db-cli での再書き込みが唯一の回復手段。**

### 5. OID キャッシュ未取得での SET
`querySwitchHashDefaults()` が起動時に OID 取得失敗した場合、`m_switchHashDefaults` が無効なまま。
`setSwitchHashFieldListSai()` は無効な OID で SAI を呼ぶため SAI SET 失敗になる（→ パターン 4 に帰着）。
OID 取得失敗自体は `LOG_WARN` のみ。

## DEL 時の失敗パターン

`ecmp_hash` / `lag_hash` / `ecmp_hash_algorithm` / `lag_hash_algorithm` はいずれも DEL 非サポート。
`doCfgSwitchHashTableTask()` の DEL 分岐で
`LOG_ERROR("Failed to remove switch ECMP/LAG hash configuration: operation is not supported")` → `return false`。
Consumer erase → 再試行なし。

ASIC/CONFIG_DB 乖離時の DEL:
`LOG_ERROR("Failed to remove switch hash: operation is not supported: ASIC and CONFIG DB are diverged")`

## STATE_DB への書き込み

`SWITCH_HASH` 処理は STATE_DB (`SWITCH_HASH_TABLE` 等) へステータスを書き込まない。
エラー記録は syslog (`SWSS_LOG_ERROR` / `SWSS_LOG_WARN`) のみ。

## 再試行メカニズム

Consumer レベルの自動再試行なし。失敗時はエントリを `map.erase(it)` で消費するため、
再試行には CLI / `sonic-db-cli` による再書き込みが必要。

## 証跡ソース

- `switchorch.cpp`: `doCfgSwitchHashTableTask()` L947-999、`setSwitchHash()` L789-948、`setSwitchHashFieldListSai()` L750-769、`querySwitchHashDefaults()` L2030-2043
- `switch_helper.cpp`: `parseSwHash()` L150-194
- `switch_capabilities.cpp`: `isSwitchEcmpHashSupported()` / `validateSwitchHashFieldCap()` 等
