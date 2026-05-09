---
title: Dynamic Headroom Calculation（buffer_model = dynamic）
area: acl-qos
verification: hld-only
last_verified: 2026-05-09
sources:
  - repo: sonic-net/SONiC
    path: doc/qos/dynamically-headroom-calculation.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - DEVICE_METADATA
    - LOSSLESS_TRAFFIC_PATTERN
    - LOSSLESS_BUFFER_PARAM
    - BUFFER_POOL
    - BUFFER_PROFILE
    - BUFFER_PG
  cli:
    - config qos reload
    - config interface speed
    - config interface cable-length
    - config interface mtu
  yang: []
---

!!! warning "裏取りステータス: HLD-only"
    `buffermgrd` の dynamic クラス、Lua plugin（vendor 提供）、`buffer_model` フィールド、`asic_table.json` / `peripheral_table.json` 経由の STATE_DB 公開、`SAI_PORT_ATTR_MAXIMUM_HEADROOM_SIZE` の community SAI 取り込みは未確認。

# Dynamic Headroom Calculation（buffer_model = dynamic）

## 概要

PFC headroom（lossless 用 PG の `xon` / `xoff` / `size`）を `pg_profile_lookup.ini` のテーブル lookup ではなく、**式（cell size, MAC/PHY delay, peer response time, IPG, MTU, gearbox delay 等）から動的計算する** 設計[^1]。任意の cable length に対応し、`pg_profile_lookup.ini` 整備の負荷を削減する。

要点:

- `DEVICE_METADATA.localhost.buffer_model` を `traditional` / `dynamic` で切替（default `traditional`）[^1]
- vendor は **Lua plugin** で headroom 計算式と pool 計算アルゴリズムを提供（vendor ごとに buffer model が違うため）
- 静的 `CONFIG_DB.BUFFER_*` から動的 `APPL_DB.BUFFER_*` への変換は `BufferManager` の責務
- speed / cable-length / MTU / admin state 変更で再計算 → APPL_DB → buffer orch → SAI

## 動作仕様

### コンポーネント構成

```mermaid
flowchart LR
    USER[(CONFIG_DB\nDEVICE_METADATA.buffer_model=dynamic\nLOSSLESS_TRAFFIC_PATTERN\nLOSSLESS_BUFFER_PARAM\nBUFFER_*（static）)] --> BMGR[BufferManager\n(dynamic class)]
    JSON[asic_table.json\nperipheral_table.json] --> STATE[(STATE_DB\nASIC_TABLE / PERIPHERAL_TABLE\nPORT_PERIPHERAL_TABLE\nBUFFER_MAX_PARAM)]
    STATE --> BMGR
    BMGR -->|Lua plugin invoke| LUA[(vendor Lua\nheadroom calc / pool calc / legality check)]
    LUA --> BMGR
    BMGR --> APPL[(APPL_DB\nBUFFER_POOL / BUFFER_PROFILE /\nBUFFER_PG / BUFFER_QUEUE /\nBUFFER_PORT_*_PROFILE_LIST)]
    APPL --> BORCH[buffer orchagent]
    BORCH --> SAI[(SAI buffer)]
    BMGR --> STATE2[(STATE_DB\n計算済み数値の公開)]
```

### モード切替条件

| シナリオ | mode |
|----------|------|
| dynamic 対応 vendor の新規 install | `dynamic` |
| 旧 image からの upgrade で buffer 設定がデフォルト値のまま | `dynamic`（自動マイグレーション） |
| 同上で buffer 設定を変えていた | `traditional` を維持 |
| `config load_minigraph` 実行 | `traditional` に戻る |
| `config qos reload` | デフォルトで `dynamic`、`--no-dynamic-mode` で `traditional` |

`buffermgrd` の起動オプションで判別:

- traditional: `-l /usr/share/sonic/hwsku/pg_profile_lookup.ini`
- dynamic: `-a asic_table.json -p peripheral_table.json`[^1]

### ASIC_TABLE / PERIPHERAL_TABLE

vendor が `files/build_templates` に提供する json を初回起動時にレンダリングし、`STATE_DB` にロードする[^1]:

```
ASIC_TABLE|<VENDOR>:
  cell_size, ipg, pipeline_latency, mac_phy_delay, peer_response_time
PERIPHERAL_TABLE|<model>:
  gearbox_delay, ...
PORT_PERIPHERAL_TABLE|<port>:
  peripheral = <model>
BUFFER_MAX_PARAM:
  ...   # SAI から得る max headroom 等
```

### Lua plugin

vendor は 3 つの Lua plugin を提供[^1]:

| Plugin | 役割 |
|--------|------|
| headroom calc | speed / cable / MTU 変更で headroom 再計算 |
| legality check | 計算結果が ASIC 上で実装可能か判定 |
| pool calc | shared pool size 再計算 |

vendor 固有の式（独立 headroom model / shared headroom pool model 等）を抽象化するため Lua を選んでいる。

### Buffer model の差

| 軸 | independent headroom | shared headroom pool |
|----|---------------------|----------------------|
| BUFFER_POOL.xoff | 不要 | shared headroom pool size |
| BUFFER_PROFILE.size | xon + xoff 以上 | xon + xoff 未満可（threshold のみ） |
| ingress pool size | headroom 更新で要再計算 | 再計算不要 |

### SAI 拡張

新 port attribute `SAI_PORT_ATTR_MAXIMUM_HEADROOM_SIZE`（ASIC が許す累積 headroom 上限）を読み出して BufferManager の legality check に使う[^1]。

### 動作の起点

| 入力変化 | 動作 |
|----------|------|
| port `speed` / `cable-length` / `MTU` 変更 | 当該 port の lossless PG を全て再計算 |
| port admin shutdown / startup | shared pool 再計算（admin-down は headroom ゼロ寄与） |
| `LOSSLESS_TRAFFIC_PATTERN` / `LOSSLESS_BUFFER_PARAM` 変更 | 全 port 再計算 |
| `BUFFER_PROFILE` を user が override | dynamic 計算をその profile については停止 |

<!-- evidence:
source: sonic-net/SONiC/doc/qos/dynamically-headroom-calculation.md#L102-L114 (sha: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)
excerpt: |
  - When a port's cable length, speed or MTU is updated, headroom of all lossless priority groups will be updated according to the well-known formula
  - When a port is shut down/started up or its headroom size is updated, the size of shared buffer pool will be adjusted accordingly.
  - All the statically configured data will be stored in `CONFIG_DB` and all dynamically data in `APPL_DB`.
reasoning: 入力 → 再計算 → APPL_DB の流れと、CONFIG_DB / APPL_DB / STATE_DB の責務分担の根拠。
-->

### Headroom override

特定 port の headroom を式から外して固定値にすることが可能。`BUFFER_PROFILE` を直接指定して `BUFFER_PG` に当てる[^1]。

### Shared headroom pool

`BUFFER_POOL.xoff` で shared headroom pool を有効化。over-subscribe ratio または直接 pool size の指定で運用[^1]。

## 設定

### CLI

| Command | 用途 |
|---------|------|
| `config qos reload` | dynamic mode 適用 |
| `config qos reload --no-dynamic-mode` | traditional に戻す |
| `config interface speed` / `cable-length` / `mtu` | 動的再計算の trigger |

### CONFIG_DB

```
DEVICE_METADATA|localhost:
  buffer_model = dynamic | traditional   # default traditional

LOSSLESS_TRAFFIC_PATTERN:
  mtu, small_packet_percentage, default_dynamic_th

LOSSLESS_BUFFER_PARAM:
  default_lossless_pgs   # 例: "3,4"
```

## 制限事項

- vendor が dynamic 対応の Lua plugin と `asic_table.json` / `peripheral_table.json` を提供している platform 限定
- `config load_minigraph` で traditional に戻る点に注意（運用で意図せず traditional 化する事故）
- speed / cable-length 変更が即時的に SAI まで効くため、ライブで弄ると lossless トラフィックに影響あり

## 干渉する機能

- **[Reclaim Reserved Buffer](./reclaim-reserved-buffer.md)**: dynamic mode 配下の admin-down ポートも `zero_profile` で reclaim できる
- **PFC**: lossless PG（default `3, 4`）の構成と headroom 計算が直接連動
- **Gearbox**: PERIPHERAL_TABLE で peripheral delay を加味する

## トラブルシューティング

- speed 変更後 headroom が更新されない → `buffermgrd` ログで Lua plugin invoke を確認、`BUFFER_MAX_PARAM` legality check で reject されていないか確認
- shared pool の sum が合わない → `xoff` の有無、independent vs shared headroom モデルを確認

## 引用元

[^1]: `sonic-net/SONiC` `doc/qos/dynamically-headroom-calculation.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- buffermgrd の dynamic クラスと Lua plugin invoke 経路の現行 master 取り込み確認
- DEVICE_METADATA.buffer_model の YANG 取り込み確認
- ASIC_TABLE / PERIPHERAL_TABLE / PORT_PERIPHERAL_TABLE / BUFFER_MAX_PARAM の STATE_DB 公開実装確認
- LOSSLESS_TRAFFIC_PATTERN / LOSSLESS_BUFFER_PARAM の YANG 取り込み確認
- SAI_PORT_ATTR_MAXIMUM_HEADROOM_SIZE の community SAI 取り込み確認
- vendor (Mellanox/Broadcom) の dynamic Lua plugin と asic_table.json 提供状況確認
-->
