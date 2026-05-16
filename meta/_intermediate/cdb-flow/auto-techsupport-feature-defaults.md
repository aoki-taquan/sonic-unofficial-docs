# Phase A — AUTO_TECHSUPPORT_FEATURE 暗黙デフォルト調査

調査日: 2026-05-14  
対象ページ: `docs/reference/config-db/auto-techsupport-feature.md`

## フィールド一覧と YANG default

YANG モデル (`sonic-auto_techsupport.yang`) での明示的 default:

| フィールド | YANG default |
|-----------|-------------|
| `state` | なし (default 宣言なし) |
| `available_mem_threshold` | `10.0` (YANG `default 10.0;`) |
| `rate_limit_interval` | なし (default 宣言なし) |

## コード由来の暗黙デフォルト

### `state`

**ソース**: `sonic-utilities/sonic_package_manager/service_creator/feature.py:22-26`

```python
DEFAULT_AUTO_TS_FEATURE_CONFIG = {
    'state': 'disabled',
    'rate_limit_interval': '600',
    'available_mem_threshold': '10.0'
}
```

- パッケージインストール時に `FeatureRegistry.register_auto_ts()` が呼ばれ、`DEFAULT_AUTO_TS_FEATURE_CONFIG` をベースに DB エントリを書き込む。
- `state` の実際値は `infer_auto_ts_capability()` が `AUTO_TECHSUPPORT|GLOBAL.state` を参照して上書き: GLOBAL が `enabled` なら `enabled`、`GLOBAL` エントリ自体が不在なら `disabled` で固定。
- **実質デフォルト**: `"disabled"`（GLOBAL が未設定の場合）または GLOBAL の `state` 値を引き継ぐ。

`coredump_gen_handler.py:55` では `.get()` の戻りを `!= "enabled"` で比較するため、フィールド未設定 = `None` → `disabled` 扱い（スキップ）となる。

### `available_mem_threshold`

**ソース 1 (init 時)**: `feature.py:26` → `'available_mem_threshold': '10.0'`  
**ソース 2 (init_cfg.json.j2)**: `"available_mem_threshold": "10.0"` (ビルド時テンプレート)  
**ソース 3 (memory_threshold_check.py:28)**:

```python
DEFAULT_MEMORY_AVAILABLE_FEATURE_THRESHOLD = 0
```

`Config.__init__` (memory_threshold_check.py:140-144) では、feature エントリが存在してもフィールドが欠落している場合:

```python
self.feature_config[key] = self.parse_value_from_db(
    config,
    "available_mem_threshold",
    float,
    DEFAULT_MEMORY_AVAILABLE_FEATURE_THRESHOLD,  # = 0
)
```

→ **フィールドが DB に存在しない場合の実行時 fallback = `0.0`**（メモリチェックをスキップ）。

**二段階デフォルト**:
1. DB エントリ自体を書く段階（`feature.py` / `init_cfg.j2`）: `10.0`
2. DB エントリが存在するが `available_mem_threshold` キーが欠落している場合の実行時 fallback (`memory_threshold_check.py`): `0.0`

フィールド値が float 変換不可だと `MemoryCheckerException` が raise される（`parse_value_from_db` L155-156）。

### `rate_limit_interval`

**ソース 1 (init 時)**: `feature.py:25` → `'rate_limit_interval': '600'`  
**ソース 2 (init_cfg.json.j2)**: `"rate_limit_interval": "600"`  
**ソース 3 (auto_techsupport_helper.py:328-331)**:

```python
try:
    container_cooloff = float(container_cooloff)
except ValueError:
    container_cooloff = 0.0
```

`db.get(CFG_DB, FEATURE.format(container), COOLOFF)` が `None` を返した場合 (`float(None)` → `TypeError` ではなく `ValueError` ではないため注意):

実際は `float(None)` は `TypeError` なので `except ValueError` には引っかからない。ただし `db.get()` が `None` を返したとき、`float(None)` は `TypeError` → **キャッチされない**。

ただし SonicV2Connector の `get()` は key 不存在時に空文字列 `""` を返すことが多い。`float("")` は `ValueError` → `container_cooloff = 0.0`。

→ **フィールド未設定の実行時 fallback = `0.0`**（rate-limit 無効 = 連続実行を許可）。

これは DB エントリ書き込み時のデフォルト (`600`) と**乖離**しており、フィールドが存在しないエントリに対してはレートリミット無効で動作する。

## まとめ表

| フィールド | YANG default | 書き込み時 default (feature.py / init_cfg.j2) | 実行時 fallback (コード) | fallback 根拠 |
|-----------|-------------|----------------------------------------------|------------------------|--------------|
| `state` | なし | `disabled` (GLOBAL 不在時) / GLOBAL の state 値 | `None` → `"enabled"` との != 比較でスキップ扱い | `coredump_gen_handler.py:55` |
| `available_mem_threshold` | `10.0` (YANG) | `10.0` | `0.0` (フィールド欠落時) | `memory_threshold_check.py:28,144` |
| `rate_limit_interval` | なし | `600` | `0.0` (空文字・欠落時) | `auto_techsupport_helper.py:328-331` |

## evidence ファイル

- `sonic-utilities/sonic_package_manager/service_creator/feature.py` L22-26 (DEFAULT_AUTO_TS_FEATURE_CONFIG)
- `sonic-utilities/sonic_package_manager/service_creator/feature.py` L159-174 (infer_auto_ts_capability)
- `sonic-utilities/sonic_package_manager/service_creator/feature.py` L176-197 (register_auto_ts)
- `sonic-utilities/scripts/memory_threshold_check.py` L24-28 (DEFAULT_* 定数)
- `sonic-utilities/scripts/memory_threshold_check.py` L116-156 (Config.__init__, parse_value_from_db)
- `sonic-utilities/utilities_common/auto_techsupport_helper.py` L313-337 (invoke_ts_command_rate_limited)
- `sonic-utilities/scripts/coredump_gen_handler.py` L47-60 (handle_core_dump_creation_event)
- `sonic-buildimage/files/build_templates/init_cfg.json.j2` (AUTO_TECHSUPPORT_FEATURE ブロック)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-auto_techsupport.yang` L111-115 (available_mem_threshold default)
