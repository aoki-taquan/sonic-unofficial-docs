# LOSSLESS_TRAFFIC_PATTERN — ordering scan notes (Phase B)

## 調査対象ファイル

- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/cfgmgr/buffer_headroom_mellanox.lua`
- `sonic-swss/cfgmgr/buffer_headroom_barefoot.lua`

## 依存関係の概要

`LOSSLESS_TRAFFIC_PATTERN` は `buffermgrdyn` が呼び出すベンダー別 Lua プラグイン
(`buffer_headroom_<vendor>.lua`) 内で CONFIG_DB から直接 `KEYS LOSSLESS_TRAFFIC_PATTERN*`
+ `HGETALL` により読み込まれる。

### 先行必須テーブル

1. **BUFFER_POOL (`m_bufferPoolReady` フラグ)**
   - `buffermgrdyn.cpp:892-896`: `!m_bufferPoolReady` の場合、ヘッドルーム計算全体がデファーされる
   - Lua スクリプトは `m_bufferPoolReady == true` 後に初めて呼び出される

2. **DEFAULT_LOSSLESS_BUFFER_PARAMETER (`m_defaultThreshold`)**
   - `buffermgrdyn.cpp:1460`: `m_defaultThreshold.empty()` の場合もデファー
   - Lua スクリプト内でも `DEFAULT_LOSSLESS_BUFFER_PARAMETER` を読む
     (`buffer_headroom_mellanox.lua:105-106`)

3. **STATE_DB.ASIC_TABLE (Mellanox のみ)**
   - `buffer_headroom_mellanox.lua:61-80`: ASIC テーブルを STATE_DB から読む
   - `asic_keys[1]` が nil の場合、cell_size / pipeline_latency 等が未定義になり計算失敗

### LOSSLESS_TRAFFIC_PATTERN 自身の先行制約

- `buffer_headroom_mellanox.lua:91-94`: `KEYS LOSSLESS_TRAFFIC_PATTERN*` → `HGETALL lossless_traffic_keys[1]`
  - エントリが 0 件の場合 `lossless_traffic_keys[1]` が nil → `HGETALL nil` → Lua エラー
  - ヘッドルーム計算全体が失敗し、BUFFER_PROFILE が APPL_DB に転送されない

### 違反時の挙動

| 欠如テーブル | 挙動 | コード証拠 |
|---|---|---|
| `BUFFER_POOL` 未到着 | `m_bufferPoolReady == false` → PG/Profile の APPL_DB 書き込みをデファー | `buffermgrdyn.cpp:892-896` |
| `DEFAULT_LOSSLESS_BUFFER_PARAMETER` 未到着 | `m_defaultThreshold.empty()` → デファー | `buffermgrdyn.cpp:1460` |
| `LOSSLESS_TRAFFIC_PATTERN` エントリなし | Lua の `lossless_traffic_keys[1]` が nil → `HGETALL` エラー → headroom 計算失敗 | `buffer_headroom_mellanox.lua:91-94` |
| `STATE_DB.ASIC_TABLE` 未到着 (Mellanox) | `asic_keys[1]` が nil → cell_size 等未定義 → 計算式エラー | `buffer_headroom_mellanox.lua:62-65` |

## 結論

`LOSSLESS_TRAFFIC_PATTERN` 自身は他テーブルへの依存を持たないが、
`BUFFER_POOL` と `DEFAULT_LOSSLESS_BUFFER_PARAMETER` が確立した後にのみ
ヘッドルーム計算 (= 実効的な消費) が行われる。
エントリが CONFIG_DB に存在しない場合は Lua エラーで headroom 計算が失敗する。
