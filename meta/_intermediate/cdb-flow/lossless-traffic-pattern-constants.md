# LOSSLESS_TRAFFIC_PATTERN — ハードコード定数スキャンノート (Phase E)

## スキャン対象

- `sonic-swss/cfgmgr/buffer_headroom_mellanox.lua` (全 180 行)
- `sonic-swss/cfgmgr/buffer_headroom_barefoot.lua` (全 141 行)

## 抽出定数

### speed_of_light = 198000000 (m/s)

- mellanox: L119, barefoot: L97
- ケーブル長→伝搬遅延変換: `bytes_on_cable = 2 * cable_length * port_speed * 1e9 / 198000000 / (8 * 1000)`
- 真空中光速 (3×10⁸) の 66% — 光ファイバ実効伝搬速度

### minimal_packet_size = 64 (bytes)

- mellanox: L120, barefoot: L98
- イーサネット最小フレームサイズ
- `worst_case_factor` 計算基準値

### pause_quanta_per_speed テーブル (IEEE 802.3 31B.3.7)

mellanox: L41-51, barefoot: L37-46

| 速度 (Mb/s) | Mellanox quanta | Barefoot quanta |
|---|---|---|
| 800000 | 905 | なし |
| 400000 | 905 | 905 |
| 200000 | 453 | 453 |
| 100000 | 394 | 394 |
| 50000 | 147 | 147 |
| 40000 | 118 | 118 |
| 25000 | 80 | 80 |
| 10000 | 67 | 67 |
| 1000 | 2 | 2 |
| 100 | 1 | 1 |

### アライメント = 1024 bytes

- mellanox: L165, L167, L174; barefoot: L136, L138, L141
- `xoff_value`, `xon_value`, `headroom_size` を 1024B 境界に切り上げ

### pause_quanta → peer_response_time 変換

- `peer_response_time = pause_quanta * 512 / 8`
- 1 quanta = 512 bit time; /8 = byte 変換
- mellanox: L157, barefoot: L124

### Spectrum-4/5 kb_on_tile 係数 (Mellanox のみ)

- `port_speed / 1000 * 120 / 8` bytes
- ASIC キー末尾 '4' or '5' のときのみ有効
- mellanox: L82-87
