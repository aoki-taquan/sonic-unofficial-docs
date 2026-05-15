---
title: VNET_ROUTE / VNET_ROUTE_TUNNEL テーブル
description: "VNET_ROUTE / VNET_ROUTE_TUNNEL テーブル — VXLAN overlay 上の仮想ネットワーク内静的経路を CONFIG_DB に定義するテーブル群。"
area: reference
hard: 0
verification: code-verified
last_verified: 2026-05-15
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-vnet.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss
    path: orchagent/vnetorch.cpp
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss
    path: orchagent/vnetorch.h
    ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - VNET
    - VNET_ROUTE
    - VNET_ROUTE_TUNNEL
    - VXLAN_TUNNEL
  cli:
    - show vnet routes
    - config vxlan
  yang:
    - sonic-vnet
---

# VNET_ROUTE / VNET_ROUTE_TUNNEL テーブル

## 概要

`VNET_ROUTE` と `VNET_ROUTE_TUNNEL` は [VXLAN](../../reference/glossary.md#term-vxlan) overlay 上の仮想ネットワーク ([VNET](../../reference/glossary.md#term-vnet)) 内で静的経路を定義する [CONFIG_DB](../../reference/glossary.md#term-config_db) テーブル群[^yang]。`VNET_ROUTE` は underlay インタフェース経由の通常経路を、`VNET_ROUTE_TUNNEL` は [VXLAN](../../reference/glossary.md#term-vxlan) トンネル encapsulation を伴う overlay 経路を表す。テーブル名定数は `schema.h` で `CFG_VNET_RT_TABLE_NAME = "VNET_ROUTE"` および `CFG_VNET_RT_TUNNEL_TABLE_NAME = "VNET_ROUTE_TUNNEL"` として定義されている[^schema]。

CONFIG_DB エントリは `VNetCfgRouteOrch` によって APPL_DB (`VNET_ROUTE_TABLE` / `VNET_ROUTE_TUNNEL_TABLE`) にそのまま passthrough され、APPL_DB の消費者である `VNetRouteOrch` が実際のフィールド解釈と [SAI](../../reference/glossary.md#term-sai) への変換を担う[^vnetorch]。

<!-- cdb-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CDB[("CONFIG_DB<br/>VNET_ROUTE / VNET_ROUTE_TUNNEL")]
  CFGORCH["VNetCfgRouteOrch<br/>(passthrough)"]
  CDB --> CFGORCH
  APPDB[("APP_DB<br/>VNET_ROUTE_TABLE / VNET_ROUTE_TUNNEL_TABLE")]
  CFGORCH --> APPDB
  ROUTEORCH["VNetRouteOrch<br/>(handleRoutes / handleTunnel)"]
  APPDB --> ROUTEORCH
  SAI["SAI<br/>sai_route_api / sai_next_hop_api"]
  ROUTEORCH --> SAI
```

!!! note "凡例"
    CONFIG_DB から SAI までの典型経路。`VNetCfgRouteOrch` はフィールドを解釈せず passthrough するため、フィールドのデフォルト適用は APPL_DB 購読側の `VNetRouteOrch` で行われる。
<!-- /cdb-mermaid -->

## key 構造

```text
VNET_ROUTE|<vnet_name>|<prefix>
VNET_ROUTE_TUNNEL|<vnet_name>|<prefix>
```

| key 要素 | 説明 |
|---------|------|
| `<vnet_name>` | `VNET` テーブルへの leafref。対象 VNET 名 |
| `<prefix>` | IPv4 prefix（CIDR 形式、例 `192.168.1.0/24`） |

## 主要フィールド

### VNET_ROUTE

VNET スコープの underlay（非トンネル）静的経路。

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `nexthop` | `ipv4-address-list` | yes | nexthop IP アドレス（カンマ区切りで ECMP 指定可） |
| `ifname` | string | yes | nexthop に対応するインタフェース名 |

### VNET_ROUTE_TUNNEL

VNET スコープの VXLAN トンネル encapsulation 経路。

| フィールド | 型 | 必須 | 説明 |
|-----------|----|------|------|
| `endpoint` | `ipv4-address-list` | yes | VXLAN tunnel endpoint IP（カンマ区切りで複数 ECMP 指定可） |
| `mac_address` | `mac-address-list` | no | encapsulated パケットの inner destination MAC（endpoint と 1:1 対応） |
| `vni` | `vnid-list` | no | encapsulated パケットに使う VNI（省略時は VNET 本体 VNI） |
| `consistent_hashing_buckets` | uint16 | no | consistent hashing のバケット数（orchagent 未読取 / dead field） |
| `metric` | uint8 | no | 経路分類用 metric。経路動作に影響しない（YANG コメント） |

## 制約

- `<vnet_name>` は既存 `VNET` エントリへの leafref（YANG 強制）。
- `nexthop`（VNET_ROUTE）および `endpoint`（VNET_ROUTE_TUNNEL）は mandatory。
- `mac_address` と `endpoint` はエントリ数が一致する必要がある（orchagent が不一致を検出してエラー）。
- `vni` リストが 2 件以上の場合は `endpoint` と同数でなければならない。
- `endpoint_monitor` を設定する場合は `endpoint` と同数でなければならない（APPL_DB 拡張フィールド）。

## 購読者・処理経路

1. **`VNetCfgRouteOrch`** (`vnetorch.cpp:3577`): CONFIG_DB の `VNET_ROUTE` / `VNET_ROUTE_TUNNEL` を購読。フィールドを解釈せず全フィールドを APPL_DB にそのまま転送する。
2. **`VNetRouteOrch::handleRoutes()`** (`vnetorch.cpp:1811`): APPL_DB `VNET_ROUTE_TABLE` を消費。`nexthop` / `ifname` を解析して underlay 経路を VRF に追加する。
3. **`VNetRouteOrch::handleTunnel()`** (`vnetorch.cpp:3195`): APPL_DB `VNET_ROUTE_TUNNEL_TABLE` を消費。`endpoint` / `mac_address` / `vni` 等を解析して tunnel nexthop グループを構築し、`sai_route_api` / `sai_next_hop_group_api` でハードウェアに反映する。

## 例外条件・特殊挙動 <!-- cdb-exceptions -->

<!-- evidence: sonic-swss/orchagent/vnetorch.cpp; sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vnet.yang -->

- **`mac_address` / `endpoint` 件数不一致**: orchagent が `"MAC address size of %zu does not match endpoint size of %zu"` エラーを記録して `false` を返す（vnetorch.cpp:3280-3284）。
- **`vni` 件数不一致（2 件以上）**: `"VNI size of %zu does not match endpoint size of %zu"` エラーを記録（vnetorch.cpp:3274-3278）。
- **`endpoint_monitor` なし + `primary` あり**: `"Primary/backup behaviour cannot function without endpoint monitoring."` エラーで処理中断（vnetorch.cpp:3291-3294）。
- **VNET 未存在**: `vnet_orch_->getTypeMap()` で VNET エントリが見つからない場合、メッセージを保留してリトライ。
- **VNI 0 の encapsulation**: `vni=0` で tunnel nexthop 作成時、VXLAN orch はベース tunnel の VNI にフォールバックする。

[^yang]: YANG 定義: `sonic-vnet.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-vnet.yang>
[^schema]: テーブル名定数: `schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h>
[^vnetorch]: 実装: `vnetorch.cpp`. <https://github.com/sonic-net/sonic-swss/blob/4305596156d70e9797e8a881b3d19b46de0bce0d/orchagent/vnetorch.cpp>

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`VNET`](./vnet.md)
- YANG: [`sonic-vnet`](../yang/sonic-vnet.md)
- CLI: [`show vnet routes`](../cli/show-vnet.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-vnet.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-vnet.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- `VNET_ROUTE` key 例: `VNET_ROUTE|Vnet_1000|10.1.1.0/24`
- `VNET_ROUTE_TUNNEL` key 例: `VNET_ROUTE_TUNNEL|Vnet_1000|192.168.100.0/24`
- `endpoint` に複数 IP（カンマ区切り）を指定すると ECMP になる。

### よくある誤設定

- `mac_address` の件数が `endpoint` と一致しないと orchagent がエラーで処理を中断する。
- `vni` を省略すると VNET 本体 VNI で encapsulation されるため、意図的な per-prefix VNI が必要な場合は明示指定が必要。
- `consistent_hashing_buckets` と `metric` は orchagent が読まないため設定しても動作に影響しない。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'VNET_ROUTE|Vnet_1000|10.1.1.0/24'
sonic-db-cli CONFIG_DB hgetall 'VNET_ROUTE_TUNNEL|Vnet_1000|192.168.100.0/24'
show vnet routes all
show vnet routes tunnel
```
<!-- /ops-hint -->

<!-- runtime-trace -->
## CDB → 実コンテナ動作トレース

### 段階 1: Consumer 登録

- **`VNetCfgRouteOrch`** (`vnetorch.cpp:3577`): `VNET_ROUTE` / `VNET_ROUTE_TUNNEL` テーブルを `SubscriberStateTable` で購読。

### 段階 2: CFG → APPL passthrough

- `doVnetRouteTask()` が CONFIG_DB キー区切り文字（`|`）を APPL_DB 区切り文字（`:`）に変換し、
  全フィールドを `VNET_ROUTE_TABLE` に set する（vnetorch.cpp:3638-3661）。
- `doVnetTunnelRouteTask()` が同様に `VNET_ROUTE_TUNNEL_TABLE` に set する（vnetorch.cpp:3613-3636）。

### 段階 3: APPL → SAI

- `VNetRouteOrch::handleRoutes()`: underlay 経路を `sai_route_api->create_route_entry()` でハードウェアに追加。
- `VNetRouteOrch::handleTunnel()`: tunnel endpoint ごとに `NextHopKey` を構築し、
  nexthop group を `sai_next_hop_group_api` で作成後、`sai_route_api->create_route_entry()` で経路追加。

### 段階 4: タイミング + 副作用

- 対応する `VNET` エントリが先に処理されている必要あり。
- 副作用: endpoint モニタリング有効時は BFD セッションが自動生成される（`createBfdSession()`）。
- VNET 削除時は関連経路・nexthop が全て自動削除される。

<!-- /runtime-trace -->

<!-- entry-points -->
## 書き込み入り口 (Direction A)

### CLI

- 専用 CLI なし — `config load` による JSON 投入またはプログラマティックな `sonic-db-cli` 書き込みが主経路。

### minigraph / sonic-cfggen

minigraph.py に VNET_ROUTE 生成なし。

### REST / gNMI

REST/gNMI 書き込み経路なし（手動 JSON 投入が主経路）。

### db_migrator

`db_migrator.py` での VNET_ROUTE マイグレーションなし。

### ビルド時デフォルト (build-time default)

なし。

### ハードコードデフォルト / ランタイム注入

なし。

<!-- /entry-points -->

<!-- defaults -->
## コード由来の暗黙デフォルト

### VNET_ROUTE

| フィールド | YANG default | コード実装デフォルト | 出典 |
|-----------|-------------|---------------------|------|
| `nexthop` | なし (mandatory) | 省略不可 | sonic-vnet.yang:133 |
| `ifname` | なし (mandatory) | 省略不可。コード初期値 `""` | vnetorch.cpp:1816 |

### VNET_ROUTE_TUNNEL

| フィールド | YANG default | コード実装デフォルト | 出典 |
|-----------|-------------|---------------------|------|
| `endpoint` | なし (mandatory) | 省略不可 | sonic-vnet.yang:169 |
| `mac_address` | なし | `00:00:00:00:00:00`（ゼロ MAC）per endpoint | vnetorch.cpp:3200, 3361-3375 |
| `vni` | なし | `0` — [VNET](../../reference/glossary.md#term-vnet) 本体の VNI で encapsulation | vnetorch.cpp:3201, 3362 |
| `consistent_hashing_buckets` | なし | [orchagent](../../reference/glossary.md#term-orchagent) 未使用（dead field） | vnetorch.h（登録なし） |
| `metric` | なし | [orchagent](../../reference/glossary.md#term-orchagent) 未使用（dead field）。経路選択に影響しない | vnetorch.cpp:3214-3272 |

### 注記

- **`consistent_hashing_buckets` の dead field 性**: `vnet_route_description` への登録がないため `handleTunnel()` が読み取らない。[CONFIG_DB](../../reference/glossary.md#term-config_db) に保存されるが APPL_DB に転送後も無視される。
- **`metric` の dead field 性**: `vnetorch.h:327` で `REQ_T_UINT` として登録はされるが、`handleTunnel()` 内に読み取り・使用コードが存在しない。[YANG](../../reference/glossary.md#term-yang) コメント通り経路選択に影響しない。
- **`mac_address` = ゼロ MAC**: 省略時は各 endpoint の inner dst-mac が `00:00:00:00:00:00` になる。remote VTEP が MAC 学習する構成では問題ないが、固定 MAC が必要な場合は明示指定が必要。
- **`vni` = 0 のフォールバック**: [VXLAN](../../reference/glossary.md#term-vxlan) orch に `vni=0` を渡すとベース tunnel の VNI が encapsulation に使われる（`createNextHopTunnel()` 呼び出し経路）。
<!-- /defaults -->
