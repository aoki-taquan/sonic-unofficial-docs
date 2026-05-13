# AUTO_TECHSUPPORT テーブル — consumer 例外条件分析

## Consumer: memory_threshold_check (sonic-utilities/scripts/memory_threshold_check.py)

### 処理関数
- `Config.__init__()` (L118)
- `Config.parse_value_from_db()` (static, L153)

### 例外条件・特殊挙動

#### 1. GLOBAL エントリ不在 → デフォルト値で動作
`cfg_db.get_table(AUTO_TECHSUPPORT).get("GLOBAL")` が None の場合、`parse_value_from_db` はデフォルト値を使用する。
クラッシュしない。

```python
# sonic-utilities/scripts/memory_threshold_check.py:153
@staticmethod
def parse_value_from_db(config, key, converter, default):
    value = config.get(key)
    if not value:
        return default
```

デフォルト値:
- `available_mem_threshold`: 10 (%)
- `min_available_mem`: 200 (MB) → 204800 KB

#### 2. available_mem_threshold = 0 → メモリチェックスキップ
`memory_available_threshold` が 0 の場合、システムメモリチェック全体をスキップし、feature 単位のチェックのみ実行。

```python
# sonic-utilities/scripts/memory_threshold_check.py:178
if self.config.memory_available_threshold:
    ...  # 0 のときスキップ
```

#### 3. 型変換失敗 → MemoryCheckerException
`float(value)` で ValueError が発生した場合、`MemoryCheckerException` を raise し、`main()` は `EXIT_FAILURE` を返す。techsupport は起動しない。

```python
# sonic-utilities/scripts/memory_threshold_check.py:153
try:
    return converter(value)
except ValueError as err:
    logger.log_error(f'Failed to parse {key} value "{value}": {err}')
    raise MemoryCheckerException(err)
```

#### 4. rate_limit_interval / max_techsupport_limit
これらのフィールドは memory_threshold_check では読まれない (coredump 監視デーモンが別途使用)。
memory_threshold_check は `available_mem_threshold` と `min_available_mem` のみ参照する。

#### 5. state フィールドの評価
`state` フィールド (enabled/disabled) は `memory_threshold_check.py` では直接読まれない。
呼び出し元のラッパースクリプトが state を確認してから本スクリプトを起動するアーキテクチャ。
