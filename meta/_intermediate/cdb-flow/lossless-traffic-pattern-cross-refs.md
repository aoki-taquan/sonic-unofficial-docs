# LOSSLESS_TRAFFIC_PATTERN — cross-refs scan notes (Phase C)

## 調査対象ファイル

- `sonic-swss/cfgmgr/buffer_headroom_mellanox.lua`
- `sonic-swss/cfgmgr/buffer_headroom_barefoot.lua`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-lossless-traffic-pattern.yang`

## YANG leafref 確認

`sonic-lossless-traffic-pattern.yang` には `leafref` なし。テーブルは完全にスタンドアロン。

## Lua スクリプトによる暗黙参照

`buffermgrdyn` は `LOSSLESS_TRAFFIC_PATTERN` を直接購読しない
（`m_bufferTableHandlerMap` に登録されていない）。
代わりにベンダー別 Lua スクリプトが headroom 計算時に CONFIG_DB / STATE_DB を直接参照する。

### 1. STATE_DB.ASIC_TABLE

| スクリプト | 行 | 参照内容 |
|---|---|---|
| `buffer_headroom_mellanox.lua` | L62-80 | `KEYS ASIC_TABLE*` → `HGETALL asic_keys[1]`: cell_size, pipeline_latency, mac_phy_delay, peer_response_time |
| `buffer_headroom_barefoot.lua` | L57-76 | 同上 |

`asic_keys[1]` が nil の場合 → `HGETALL nil` → Lua エラー → headroom 計算失敗。

### 2. CONFIG_DB.DEFAULT_LOSSLESS_BUFFER_PARAMETER

| スクリプト | 行 | 参照内容 |
|---|---|---|
| `buffer_headroom_mellanox.lua` | L105-106 | `KEYS DEFAULT_LOSSLESS_BUFFER_PARAMETER*` → `HGET ... over_subscribe_ratio` |

`default_lossless_param_keys[1]` が nil の場合 → Lua エラー。

### 3. CONFIG_DB.BUFFER_POOL|ingress_lossless_pool

| スクリプト | 行 | 参照内容 |
|---|---|---|
| `buffer_headroom_mellanox.lua` | L109 | `HGET BUFFER_POOL|ingress_lossless_pool xoff` |
| `buffer_headroom_barefoot.lua` | L94 | 同上 |

SHP 未設定の場合 `xoff` が nil → `shp_size = nil` → 計算式依存で 0 扱いまたはエラー。

## 結論

YANG に leafref なし。Lua スクリプト経由の暗黙参照が 3 件: STATE_DB.ASIC_TABLE、
DEFAULT_LOSSLESS_BUFFER_PARAMETER、BUFFER_POOL|ingress_lossless_pool。
