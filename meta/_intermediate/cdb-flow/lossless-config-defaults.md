# LOSSLESS_TRAFFIC_PATTERN — Phase A: コード由来の暗黙デフォルト調査

## フィールド一覧

| フィールド | YANG mandatory | YANG default |
|---|---|---|
| `mtu` | `mandatory true` | なし（YANG default 宣言なし） |
| `small_packet_percentage` | `mandatory true` | なし（YANG default 宣言なし） |

YANG 上は両フィールドとも `mandatory true` であるため、エントリを SET する際は必ず両フィールドの指定が必要。ただし **エントリ自体が存在しない** 場合の C++ / Lua 側フォールバックを以下で調査する。

---

## 検出した暗黙デフォルト・fallback・discrepancy

### 1. `mtu` — ビルド時デフォルト: `"1024"` (j2 テンプレート)

**種別**: ハードコード固定値

`buffers_config.j2:342-347` で `dynamic_mode` が定義されている場合のみ出力される:

```jinja
"LOSSLESS_TRAFFIC_PATTERN": {
    "AZURE": {
        "mtu": "1024",
        "small_packet_percentage": "50"
    }
}
```

`"1024"` はハードコード固定値。実際のポート MTU（通常 9216 / 9100）とは無関係に、ロスレストラフィックパターンの最大パケットサイズとして使われる。

### 2. `small_packet_percentage` — ビルド時デフォルト: `"50"` (j2 テンプレート)

**種別**: ハードコード固定値

同じく `buffers_config.j2:345` でハードコード `"50"`。動的バッファモードの全プラットフォームに共通の初期値。

### 3. `mtu` / `small_packet_percentage` — db_migrator デフォルト: `"1024"` / `"100"` (ハードコード)

**種別**: ハードコード固定値 / 経路依存乖離

`db_migrator.py:414` で静的→動的バッファ移行時（Mellanox 系）に両フィールドをハードコードで挿入する:

```python
append_item_method(('LOSSLESS_TRAFFIC_PATTERN', 'AZURE', {'mtu': '1024', 'small_packet_percentage': '100'}))
```

**ビルド時 j2 (`small_packet_percentage=50`) と db_migrator (`small_packet_percentage=100`) で値が異なる**。
移行経路によって `small_packet_percentage` が 50 または 100 になる乖離がある。

### 4. `mtu` — Lua スクリプト: エントリ不在時は `nil` → 算術エラー

**種別**: silent error / 前提条件依存

`buffer_headroom_mellanox.lua:91-101` / `buffer_headroom_barefoot.lua:80-90` では CONFIG_DB から `LOSSLESS_TRAFFIC_PATTERN*` キーを KEYS で取得し、存在するキーの先頭エントリのみ読む:

```lua
local lossless_traffic_keys = redis.call('KEYS', 'LOSSLESS_TRAFFIC_PATTERN*')
local lossless_traffic_table_content = redis.call('HGETALL', lossless_traffic_keys[1])
```

`LOSSLESS_TRAFFIC_PATTERN` エントリが**一切存在しない**場合、`lossless_traffic_keys[1]` が `nil` となり `HGETALL nil` でエラーになる（Lua index エラー）。C++ 側でのフォールバックなし。つまり dynamic buffer モードで `LOSSLESS_TRAFFIC_PATTERN` が未設定の場合、ヘッドルーム計算スクリプトが Lua エラーで失敗し、lossless PG が設定されない。

### 5. `small_packet_percentage` — Lua スクリプト: `nil` の場合は算術エラー

**種別**: silent error / 前提条件依存

`buffer_headroom_mellanox.lua:146` で `small_packet_percentage` が直接乗算式に使われる:

```lua
local small_packet_percentage_by_byte = 100 * minimal_packet_size /
    ((small_packet_percentage * minimal_packet_size + (100 - small_packet_percentage) * lossless_mtu) / 100)
```

エントリに `small_packet_percentage` フィールドが欠落していた場合、変数は `nil` となり Lua 算術エラーで失敗。YANG `mandatory true` があるため通常は欠落しないが、手動 redis-cli で不完全エントリを書いた場合に発生する。

---

## まとめ表

| フィールド | 検出種類 | 暗黙値 / fallback | 証拠 |
|---|---|---|---|
| `mtu` | ハードコード固定値（j2 テンプレート） | `"1024"` | `buffers_config.j2:344` |
| `mtu` | ハードコード固定値（db_migrator 移行） | `"1024"` | `db_migrator.py:414` |
| `mtu` | エントリ不在時 Lua エラー | `nil` → HGETALL エラーで計算不能 | `buffer_headroom_mellanox.lua:91-94` |
| `small_packet_percentage` | ハードコード固定値（j2 テンプレート） | `"50"` | `buffers_config.j2:345` |
| `small_packet_percentage` | ハードコード固定値（db_migrator 移行） | `"100"` | `db_migrator.py:414` |
| `small_packet_percentage` | j2 vs db_migrator 値乖離 | j2=50, migrator=100 — 同一フィールドで経路依存 discrepancy | `buffers_config.j2:345` / `db_migrator.py:414` |
| `small_packet_percentage` | フィールド欠落時 Lua 算術エラー | `nil` → 計算スクリプト失敗 | `buffer_headroom_mellanox.lua:146` |
