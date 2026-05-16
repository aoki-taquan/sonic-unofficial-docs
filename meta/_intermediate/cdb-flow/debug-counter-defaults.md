# Phase A: DEBUG_COUNTER field defaults — コード由来暗黙デフォルト調査

対象ページ: `docs/reference/config-db/debug-counter.md`  
調査日: 2026-05-14

---

## 1. フィールド列挙

`DEBUG_COUNTER_LIST` の全フィールド（YANG `sonic-debug-counter.yang` より）:

| フィールド | YANG 型 | YANG default |
|---|---|---|
| `name` | string | なし (key) |
| `alias` | string | なし |
| `desc` | string | なし |
| `group` | string | なし |
| `drop_monitor_status` | stypes:admin_mode | `"disabled"` |
| `window` | uint64 (sec) | `900` |
| `incident_count_threshold` | uint64 | `3` |
| `drop_count_threshold` | uint64 | `100` |
| `type` | stypes:debug_counter_type | なし (mandatory true) |

---

## 2. コード由来デフォルト / 暗黙挙動

### 2.1 `alias` / `desc` / `group` — dead fields (silent drop)

- `debug_counter.h` の `supported_debug_counter_attributes` に列挙されているが、
  `getDebugCounterType()` は `type` フィールドのみ読む。
  `alias`, `desc`, `group` は SAI にも FlexCounter にも一切伝播しない。
- **分類**: dead field / silent drop
- **evidence**: `debugcounterorch.cpp:726-758` — `for (auto attr : values)` ループ内で
  `attr_name == "type"` のみ処理し、他フィールドは `SWSS_LOG_ERROR("Unknown ... attribute")` すら出さず continue。

### 2.2 `drop_monitor_status` — YANG default `"disabled"` + コード初期値 `false`

- YANG default: `"disabled"`
- orchagent 側の実行時初期値: `debugcounterorch.h:102` に
  `bool debug_monitor_enabled = false;` とハードコード。
- Lua スクリプト (`drop_monitor.lua:31-38`) が CONFIG_DB から直接 `drop_monitor_status`
  を読み、`if status == 'enabled'` でポーリング有効化。
  YANG default と実装初期値が一致しており乖離なし。
- **分類**: YANG default = コードデフォルト（整合）

### 2.3 `window` — YANG default `900`、コードは parse_number fallback `0`

- YANG default: `900` (秒)
- Lua の `parse_number(redis.call('HGET', ..., 'window'))` は
  Redis KEY が存在しない場合 `tonumber(nil) or 0` で **0** を返す。
- つまり CONFIG_DB に `window` が書かれていない場合、Lua は `0` をウィンドウ長として
  インシデント判定する（全タイムスタンプが「期限切れ」とみなされ即クリア）。
- **分類**: YANG default 外 fallback (実行時 `0`、YANG `900` との乖離)
- **evidence**: `drop_monitor.lua:34`

### 2.4 `incident_count_threshold` — YANG default `3`、コードは parse_number fallback `0`

- Lua の `parse_number(redis.call('HGET', ..., 'incident_count_threshold'))` → 欠損時 `0`。
- `if incident_count > incident_count_threshold` (L80) が `> 0` になるため、
  1 インシデントでアラート発火（YANG default `3` より厳しい）。
- **分類**: YANG default 外 fallback
- **evidence**: `drop_monitor.lua:33, 80`

### 2.5 `drop_count_threshold` — YANG default `100`、コードは parse_number fallback `0`

- Lua の `parse_number(redis.call('HGET', ..., 'drop_count_threshold'))` → 欠損時 `0`。
- `if delta_drop_count > drop_count_threshold` (L59) が `> 0` になるため、
  1 パケットドロップでインシデント登録（YANG default `100` より厳しい）。
- **分類**: YANG default 外 fallback
- **evidence**: `drop_monitor.lua:32, 59`

### 2.6 `type` — mandatory, 欠損時は empty string → SAI lookup miss → task_failed

- YANG: `mandatory true`
- `getDebugCounterType()` は `type` が values に存在しない場合 `counter_type` が
  空文字列のまま返る（例外なし）。
- `installDebugCounter()` L387: `supported_counter_types.find("")` → end → `task_failed`。
- **分類**: mandatory + silent empty-string fallback → task_failed
- **evidence**: `debugcounterorch.cpp:385-391`

### 2.7 `drop_monitor_status`（DEBUG_DROP_MONITOR テーブル側）— enabled/disabled 以外 silent drop

- `doTask()` L256-259: `config_value` が `"enabled"` でも `"disabled"` でもない場合
  `SWSS_LOG_ERROR` → `task_failed`（silent drop ではなく明示エラー）。
- **分類**: 大文字小文字制約（`"Enabled"` 等も拒否）
- **evidence**: `debugcounterorch.cpp:257`

### 2.8 SAI 非サポートカウンタ種別 → supported_counter_types 空 → task_failed

- `publishDropCounterCapabilities()` が SAI から取得できない場合（デバイス非対応）、
  `supported_counter_types` が空になる。
  全カウンタ作成リクエストが `task_failed`。
- **分類**: プラットフォーム依存
- **evidence**: `drop_counter.cpp:380-384`

### 2.9 drop_reason なしでの counter 作成 → free_drop_counters に保留

- drop_reason が 1 つも来ない間は SAI に counter が作成されない
  （`reconcileFreeDropCounters` が条件を満たさない）。
- counter 作成自体は `task_success` を返すが SAI オブジェクトは存在しない状態。
- **分類**: 暗黙 pending / partial failure
- **evidence**: `debugcounterorch.cpp:393-394, 586-594`

### 2.10 FlexCounter ポーリング interval — ハードコード `60000` ms

- `DEBUG_DROP_MONITOR_FLEX_COUNTER_POLLING_INTERVAL_MS "60000"` は
  CONFIG_DB フィールドではなく C++ ヘッダのハードコード定数。
- `window` の時間精度はこの poll interval に依存する。
- **分類**: ハードコード固定値
- **evidence**: `debugcounterorch.h:21`

### 2.11 PORT_DEBUG カウンタ — PHY ポートのみ対象（非 PHY は silent skip）

- `installDebugFlexCounters()` L639: `if (curr.second.m_type != Port::Type::PHY) { continue; }`
- LAG / VLAN / CPU ポートは無言でスキップ。
- **分類**: silent drop (非 PHY ポート)
- **evidence**: `debugcounterorch.cpp:639-641`

---

## 3. 結論サマリ

| フィールド | YANG default | 実行時 fallback | 乖離 |
|---|---|---|---|
| `alias` | - | 無視 (dead) | dead field |
| `desc` | - | 無視 (dead) | dead field |
| `group` | - | 無視 (dead) | dead field |
| `drop_monitor_status` | `disabled` | `false` (コード) | 整合 |
| `window` | `900` | `0` (Lua fallback) | 乖離あり |
| `incident_count_threshold` | `3` | `0` (Lua fallback) | 乖離あり |
| `drop_count_threshold` | `100` | `0` (Lua fallback) | 乖離あり |
| `type` | mandatory | 空文字 → task_failed | mandatory 違反は task_failed |
