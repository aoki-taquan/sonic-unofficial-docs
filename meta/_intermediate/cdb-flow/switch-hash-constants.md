# switch-hash constants (Phase E)

## 調査対象

- `sonic-swss/orchagent/switch/switch_schema.h`
- `sonic-swss/orchagent/switch/switch_capabilities.cpp`
- `sonic-swss/orchagent/switch/switch_container.h`

## コード由来のハードコード定数

### 1. `switch_schema.h` — フィールド名・アルゴリズム名文字列定数

`SWITCH_HASH_ECMP_HASH` / `SWITCH_HASH_LAG_HASH` / `SWITCH_HASH_ECMP_HASH_ALGORITHM` / `SWITCH_HASH_LAG_HASH_ALGORITHM` がフィールド名文字列として定義される。
hash-field enum 文字列 (`SWITCH_HASH_FIELD_*`) および hash-algorithm enum 文字列 (`SWITCH_HASH_ALGORITHM_*`) も同ファイルに定義。

### 2. `switch_capabilities.cpp` — 内部マッピング・STATE_DB キー

`SWITCH_CAPABILITY_KEY = "switch"` — STATE_DB への capability 書き込み時のキー。
`SWITCH_STATE_DB_NAME = "STATE_DB"`, `SWITCH_STATE_DB_TIMEOUT = 0` — capability 書き込み先 DB 名とタイムアウト(即時)。
`SWITCH_CAPABILITY_HASH_NATIVE_HASH_FIELD_LIST_FIELD = "HASH|NATIVE_HASH_FIELD_LIST"` — capability エントリのフィールド名。
`SWITCH_CAPABILITY_ECMP_HASH_CAPABLE_FIELD = "ECMP_HASH_CAPABLE"` / `SWITCH_CAPABILITY_LAG_HASH_CAPABLE_FIELD = "LAG_HASH_CAPABLE"` — ECMP/LAG hash サポート可否フィールド名。
`SWITCH_CAPABILITY_ECMP_HASH_ALGORITHM_FIELD = "ECMP_HASH_ALGORITHM"` / `*_CAPABLE_FIELD = "ECMP_HASH_ALGORITHM_CAPABLE"` — アルゴリズム capability フィールド名。

### 3. `switch_container.h` — `is_set` フラグのデフォルト値

`SwitchHash` 構造体の `ecmp_hash.is_set`, `lag_hash.is_set`, `ecmp_hash_algorithm.is_set`, `lag_hash_algorithm.is_set` は全て `false` で初期化。CONFIG_DB に該当フィールドが存在しない場合は SAI への書き込みを行わない。
