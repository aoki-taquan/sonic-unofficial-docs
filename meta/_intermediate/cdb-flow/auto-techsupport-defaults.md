# Phase A — AUTO_TECHSUPPORT コード由来の暗黙デフォルト

## 調査対象ファイル

- `sonic-utilities/utilities_common/auto_techsupport_helper.py`
- `sonic-utilities/scripts/memory_threshold_check.py`
- `sonic-utilities/scripts/coredump_gen_handler.py`
- `sonic-utilities/scripts/techsupport_cleanup.py`
- `sonic-utilities/sonic_package_manager/service_creator/feature.py`
- `sonic-buildimage/files/build_templates/init_cfg.json.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-auto_techsupport.yang`

---

## AUTO_TECHSUPPORT|GLOBAL フィールド別デフォルト

### `state`

- YANG: `default` 宣言なし
- init_cfg.json.j2: ビルド変数 `enable_auto_tech_support` が `"y"` なら `"enabled"`、それ以外 `"disabled"`
- コード fallback: なし。`coredump_gen_handler.py:17` / `techsupport_cleanup.py:27` は `!= "enabled"` を条件として判定し、未設定は `disabled` と同等に扱う（スキップ）。
- **実質デフォルト: ビルド時設定依存。未設定 = disabled 扱い**

### `rate_limit_interval`

- YANG: `default` 宣言なし
- init_cfg.json.j2: `"180"` (秒)
- コード fallback (`auto_techsupport_helper.py:invoke_ts_command_rate_limited`):
  ```python
  global_cooloff = db.get(CFG_DB, AUTO_TS, COOLOFF)
  try:
      global_cooloff = float(global_cooloff)
  except ValueError:
      global_cooloff = 0.0
  ```
  → 未設定または非数値 → `0.0`（rate-limit 無効）
- **実質デフォルト: init_cfg 経由では 180 秒。DB に値がなければ 0.0（無効）**

### `max_techsupport_limit`

- YANG: `default` 宣言なし
- init_cfg.json.j2: `"10.0"` (%)
- コード fallback (`techsupport_cleanup.py:32-39`):
  ```python
  max_ts = db.get(CFG_DB, AUTO_TS, CFG_MAX_TS)
  try:
      max_ts = float(max_ts)
  except ValueError:
      max_ts = 0.0
  if not max_ts:
      # No cleanup performed
      return
  ```
  → 未設定または 0.0 → クリーンアップなし
- **実質デフォルト: init_cfg 経由では 10.0%。DB に値がなければ 0.0（クリーンアップ無効）**

### `max_core_limit`

- YANG: `default` 宣言なし
- init_cfg.json.j2: `"5.0"` (%)
- コード fallback (`coredump_gen_handler.py:22-30`):
  ```python
  core_usage = db.get(CFG_DB, AUTO_TS, CFG_CORE_USAGE)
  try:
      core_usage = float(core_usage)
  except ValueError:
      core_usage = 0.0
  if not core_usage:
      # No cleanup performed
      return
  ```
  → 未設定または 0.0 → クリーンアップなし
- **実質デフォルト: init_cfg 経由では 5.0%。DB に値がなければ 0.0（クリーンアップ無効）**

### `available_mem_threshold`

- YANG: `default 10.0` (明示)
- init_cfg.json.j2: `"10.0"`
- コード fallback (`memory_threshold_check.py:122-127`):
  ```python
  DEFAULT_MEMORY_AVAILABLE_THRESHOLD = 10  # (%)
  self.memory_available_threshold = self.parse_value_from_db(
      config, "available_mem_threshold", float, DEFAULT_MEMORY_AVAILABLE_THRESHOLD
  )
  ```
  `parse_value_from_db` は `config.get(key)` が falsy なら `default` を返す。
- **実質デフォルト: YANG default / コード定数ともに `10.0 (%)`。3層一致**

### `min_available_mem`

- YANG: `default 200` (明示、MB 単位)
- init_cfg.json.j2: `"200"`
- コード fallback (`memory_threshold_check.py:128-134`):
  ```python
  DEFAULT_MEMORY_AVAILABLE_MIN_THRESHOLD = 200  # (MB)
  self.memory_available_min_threshold = self.parse_value_from_db(
      config, "min_available_mem", float, DEFAULT_MEMORY_AVAILABLE_MIN_THRESHOLD
  ) * MB_TO_KB_MULTIPLIER  # → 200 * 1024 = 204800 KB
  ```
  → 未設定なら 200 MB (= 204800 KB) を閾値として使用
- **実質デフォルト: 200 MB (= 204800 KB)。YANG / コード / init_cfg 3層一致**

### `since`

- YANG: `default` 宣言なし
- init_cfg.json.j2: `"2 days ago"`
- コード fallback (`auto_techsupport_helper.py:212-220`):
  ```python
  SINCE_DEFAULT = "2 days ago"
  def get_since_arg(db):
      since_cfg = db.get(CFG_DB, AUTO_TS, CFG_SINCE)
      if not since_cfg:
          return SINCE_DEFAULT
      rc, _, stderr = subprocess_exec(["date", "--date={}".format(since_cfg)])
      if rc == 0:
          return since_cfg
      return SINCE_DEFAULT  # 不正な日付文字列のときも fallback
  ```
  → 未設定 または `date` コマンド検証失敗 → `"2 days ago"`
- **実質デフォルト: `"2 days ago"`。二重 fallback（未設定・不正値ともに同じ値）**

---

## AUTO_TECHSUPPORT_FEATURE フィールド別デフォルト

### `state` (FEATURE エントリ)

- YANG: `default` 宣言なし
- feature.py:23 (`DEFAULT_AUTO_TS_FEATURE_CONFIG`):
  ```python
  DEFAULT_AUTO_TS_FEATURE_CONFIG = {
      'state': 'disabled',
      'rate_limit_interval': '600',
      'available_mem_threshold': '10.0'
  }
  ```
  ただし `register_auto_ts` が `infer_auto_ts_capability` を呼び、GLOBAL エントリの `state` を継承する。GLOBAL が未設定なら `"disabled"` 固定。
- **実質デフォルト: GLOBAL state 継承。GLOBAL 未設定なら `disabled`**

### `available_mem_threshold` (FEATURE エントリ)

- YANG: `default 10.0`
- feature.py: `DEFAULT_AUTO_TS_FEATURE_CONFIG['available_mem_threshold'] = '10.0'`
- init_cfg.json.j2: `"10.0"`
- コード fallback (`memory_threshold_check.py:139-145`):
  ```python
  DEFAULT_MEMORY_AVAILABLE_FEATURE_THRESHOLD = 0  # (%)
  self.feature_config[key] = self.parse_value_from_db(
      config, "available_mem_threshold", float, DEFAULT_MEMORY_AVAILABLE_FEATURE_THRESHOLD
  )
  ```
  **注意**: `memory_threshold_check.py` のコード定数は `0` だが、YANG / feature.py / init_cfg はいずれも `10.0`。コードが直接読み取る際に DB 上に値があれば `10.0` が優先される。DB 値が欠落した場合のみコード定数 `0` が適用される（= feature メモリチェック無効化）。
- **実質デフォルト: 通常運用 `10.0`。DB 欠落時コードレベル `0`（チェック無効）**

### `rate_limit_interval` (FEATURE エントリ)

- YANG: `default` 宣言なし
- feature.py: `DEFAULT_AUTO_TS_FEATURE_CONFIG['rate_limit_interval'] = '600'` (秒)
- init_cfg.json.j2: `"600"`
- コード fallback (`auto_techsupport_helper.py:316-330`):
  ```python
  container_cooloff = db.get(CFG_DB, FEATURE.format(container), COOLOFF)
  try:
      container_cooloff = float(container_cooloff)
  except ValueError:
      container_cooloff = 0.0
  ```
  → 未設定または非数値 → `0.0`（feature 単位 rate-limit 無効）
- **実質デフォルト: init_cfg 経由では 600 秒。DB 値なければ 0.0（無効）**

---

## 差異サマリ

| フィールド | YANG default | init_cfg.j2 | コード fallback |
|---|---|---|---|
| GLOBAL.state | なし | ビルド変数依存 | 未設定→disabled 扱い |
| GLOBAL.rate_limit_interval | なし | 180 秒 | 0.0 (無効) |
| GLOBAL.max_techsupport_limit | なし | 10.0% | 0.0 (無効) |
| GLOBAL.max_core_limit | なし | 5.0% | 0.0 (無効) |
| GLOBAL.available_mem_threshold | **10.0** | 10.0% | 10 (%) — 3層一致 |
| GLOBAL.min_available_mem | **200** | 200 MB | 200 MB — 3層一致 |
| GLOBAL.since | なし | "2 days ago" | "2 days ago" (不正値も) |
| FEATURE.state | なし | GLOBAL 継承 | disabled (GLOBAL 未設定時) |
| FEATURE.available_mem_threshold | **10.0** | 10.0% | 0 (DB 欠落時のみ) |
| FEATURE.rate_limit_interval | なし | 600 秒 | 0.0 (無効) |
