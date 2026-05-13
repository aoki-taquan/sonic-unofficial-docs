# AUTO_TECHSUPPORT_FEATURE テーブル — consumer 例外条件分析

## Consumer 1: memory_threshold_check (sonic-utilities/scripts/memory_threshold_check.py)

### 処理関数
- `Config.__init__()` (L118)

### 例外条件・特殊挙動

#### 1. feature 不在 → デフォルト (0%) で動作
`feature_table.get(key)` で取れない場合、`parse_value_from_db` は `DEFAULT_MEMORY_AVAILABLE_FEATURE_THRESHOLD = 0` を返す。
0% = コンテナメモリチェックを実質スキップ。

#### 2. available_mem_threshold の型変換失敗 → MemoryCheckerException
`float(value)` が失敗すると `MemoryCheckerException` → `EXIT_FAILURE`。techsupport 起動しない。

#### 3. feature キー名と docker コンテナ名の prefix match
```python
# sonic-utilities/scripts/memory_threshold_check.py:202
if not container.startswith(feature):
    continue
```
multi-ASIC インスタンス (`swss0`, `swss1` 等) に対応するため `startswith` で前方一致。
feature 名が誤っていると対応コンテナが見つからずチェックがスキップされる。

## Consumer 2: sonic_package_manager (sonic-utilities/sonic_package_manager/service_creator/feature.py)

### 例外条件・特殊挙動

#### 4. AUTO_TECHSUPPORT|GLOBAL 不在 → feature エントリを追加しない
```python
# sonic-utilities/sonic_package_manager/service_creator/feature.py:186
log.debug("Skip adding AUTO_TECHSUPPORT_FEATURE table because no AUTO_TECHSUPPORT|GLOBAL entry is found")
```
GLOBAL が存在しない場合、パッケージインストール時に `AUTO_TECHSUPPORT_FEATURE` エントリが自動作成されない。

#### 5. state フィールド未設定 → インストール時のデフォルト
パッケージインストール時、`state` が未設定の場合はデフォルト (`disabled`) で登録される。
