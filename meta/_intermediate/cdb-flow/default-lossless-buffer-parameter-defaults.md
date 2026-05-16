# DEFAULT_LOSSLESS_BUFFER_PARAMETER — Phase A: コード由来の暗黙デフォルト調査

## フィールド一覧

| フィールド | YANG mandatory | YANG default |
|---|---|---|
| `default_dynamic_th` | `mandatory true` | なし（YANG default 宣言なし） |
| `over_subscribe_ratio` | 任意 | なし（YANG default 宣言なし） |

---

## 検出した暗黙デフォルト・fallback・discrepancy

### 1. `default_dynamic_th` — 起動時 fallback: `""` (空文字列)

**種別**: 書き込み時 vs 実行時乖離 / 前提条件依存

`buffermgrdyn` の C++ メンバー `m_defaultThreshold` は `std::string` で宣言され、**初期値なし（空文字列）**。

起動時に CONFIG_DB の `DEFAULT_LOSSLESS_BUFFER_PARAMETER` エントリを読んで初期化を試みる（`buffermgrdyn.cpp:150-154`）：

```cpp
m_cfgDefaultLosslessBufferParam.getKeys(keys);
if (!keys.empty())
{
    m_cfgDefaultLosslessBufferParam.hget(keys[0], "default_dynamic_th", m_defaultThreshold);
}
```

**条件依存**: テーブルが空（エントリなし）または `default_dynamic_th` フィールドが未設定の場合、`m_defaultThreshold` は空文字列のまま。この状態では `buffermgrdyn.cpp:1460-1464` で lossless PG の再計算がスキップされる：

```cpp
if (!m_bufferPoolReady || m_defaultThreshold.empty())
{
    SWSS_LOG_INFO("Nothing to be done since either the buffer pool or default threshold is not ready");
    m_bufferObjectsPending = true;
    return task_process_status::task_success;
}
```

すなわち **`default_dynamic_th` 未設定 → lossless PG 全体のバッファ計算が保留状態** になる（dead lock ではなく pending; 後からエントリが届けば解消）。

### 2. `default_dynamic_th` — ビルド時デフォルト: `"0"` (ハードコード固定値)

**種別**: ハードコード固定値 / プラットフォーム依存

`buffers_config.j2:334` で `dynamic_mode` 変数が定義されている場合（dynamic buffer model）のみ出力される：

```jinja
{% if dynamic_mode is defined %}
    "DEFAULT_LOSSLESS_BUFFER_PARAMETER": {
        "AZURE": {
            "default_dynamic_th": "0"
            ...
        }
    },
```

`"0"` はハードコードであり、`buffers_defaults_*.j2` 側の `defs` から導出されない。プラットフォーム・トポロジーによらず固定 `"0"` (alpha=1)。

### 3. `default_dynamic_th` — db_migrator デフォルト: `"0"` (ハードコード)

**種別**: ハードコード固定値 / 経路依存乖離

`db_migrator.py:1087` で静的→動的バッファ移行時に `default_dynamic_th='0'` をハードコードで渡す（Mellanox 系のみ）：

```python
self.migrate_config_db_buffer_tables_for_dynamic_calculation(
    speed_list, cable_len_list, '0', abandon_method, append_method)
```

`db_migrator.py:413` で実際に書き込む：

```python
append_item_method(('DEFAULT_LOSSLESS_BUFFER_PARAMETER', 'AZURE', {'default_dynamic_th': default_dynamic_th}))
```

この経路では `over_subscribe_ratio` は **一切書き込まれない**（SHP 無効状態）。

### 4. `over_subscribe_ratio` — 未設定時 fallback: SHP 無効

**種別**: 暗黙 reset + fallback / silent drop

YANG で `optional`、C++ メンバー `m_overSubscribeRatio` は空文字列で初期化。

`handleDefaultLossLessBufferParam` (L1981): `newRatio = ""` がデフォルト。SET コマンド時に `over_subscribe_ratio` フィールドが存在しない場合、`newRatio` は `""` のまま `isNonZero("")` → `false` → SHP 無効扱い。

DEL コマンド時 (L2005-2008): `newRatio = ""` に強制リセット → SHP 無効化 + `refreshSharedHeadroomPool` トリガー。

**暗黙 reset+restore**: DEL が来ると `over_subscribe_ratio` は自動的に `""` へ戻され SHP が再計算される。エントリ削除 ≠ フィールド維持であり、silent drop して SHP 無効方向に fallback。

### 5. `over_subscribe_ratio` — ビルド時: `shp` 変数が未定義なら省略

**種別**: プラットフォーム依存 / 条件付き生成

`buffers_config.j2:335-339`:

```jinja
{%- if shp is defined -%}
,
"max_headroom_size" : "0",
"over_subscribe_ratio" : "1"
{%- endif -%}
```

`shp` が Jinja コンテキストで定義されていない場合（通常は `buffers_defaults_*.j2` を呼び出す際にプラットフォームが指定しない）、`over_subscribe_ratio` は CONFIG_DB に**一切書き込まれない** = SHP デフォルト無効。`shp` が定義されている場合は固定値 `"1"` が書き込まれる。

### 6. `default_dynamic_th` — プロファイル名エンコーディングとの乖離

**種別**: YANG-実装 discrepancy / 書き込み順依存

`buffermgrdyn.cpp:494-496` で動的プロファイル名は `m_defaultThreshold` と比較して生成される：

```cpp
if (threshold != m_defaultThreshold)
{
    buffer_profile_key = buffer_profile_key + "_th" + threshold;
}
```

`m_defaultThreshold` が CONFIG_DB から正常に読み込まれる前にポートイベントが来た場合（起動直後のレース）、`threshold != m_defaultThreshold` の比較が空文字列との比較になり、すべての threshold が `_th<value>` サフィックス付きプロファイル名で作られる。その後 `m_defaultThreshold` が更新されると命名規則が変わり、既存プロファイルと新規プロファイルが別名になる可能性がある（**書き込み順依存**）。

---

## まとめ表

| フィールド | 検出種類 | 暗黙値 / fallback | 証拠 |
|---|---|---|---|
| `default_dynamic_th` | ハードコード固定値（j2） | `"0"` | `buffers_config.j2:334` |
| `default_dynamic_th` | ハードコード固定値（migrator） | `"0"` | `db_migrator.py:1087,413` |
| `default_dynamic_th` | 前提条件依存（起動時空） | `""` → lossless PG 計算保留 | `buffermgrdyn.cpp:150-154, 1460-1464` |
| `default_dynamic_th` | 書き込み順依存（プロファイル名） | 空文字列との比較でプロファイル名乖離 | `buffermgrdyn.cpp:494-496` |
| `over_subscribe_ratio` | silent drop+fallback（未設定） | `""` → SHP 無効 | `buffermgrdyn.cpp:1981-2003` |
| `over_subscribe_ratio` | 暗黙 reset（DEL） | `""` → SHP 無効化+再計算 | `buffermgrdyn.cpp:2005-2008` |
| `over_subscribe_ratio` | プラットフォーム依存（j2） | `shp` 未定義 → 省略; 定義時 `"1"` | `buffers_config.j2:335-339` |
| `over_subscribe_ratio` | YANG default 外 fallback | YANG default なし、実装は `""` | `sonic-default-lossless-buffer-parameter.yang:47-50` |
