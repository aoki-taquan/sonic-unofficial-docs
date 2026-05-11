---
title: BGP_ALLOWED_PREFIXES テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-allowed-prefix.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BGP_ALLOWED_PREFIXES
    - BGP_GLOBALS
    - BGP_NEIGHBOR
  cli:
    - config bgp
  yang:
    - sonic-bgp-allowed-prefix
---

# BGP_ALLOWED_PREFIXES テーブル

## 概要

`BGP_ALLOWED_PREFIXES` テーブルは、deployment id 単位で許可するプレフィックスリスト (IPv4 / IPv6) を CONFIG_DB に定義し、`bgpcfgd` のテンプレ展開で BGP 入出力の prefix-list / route-map に反映するための入力データ[^1]。`sonic-bgp-allowed-prefix.yang` で次の 4 list を定義する:

- `BGP_ALLOWED_PREFIXES_LIST` (deployment, id)
- `BGP_ALLOWED_PREFIXES_NEIGH_LIST` (deployment, id, neighbor, neighbor_type)
- `BGP_ALLOWED_PREFIXES_COM_LIST` (deployment, id, community)
- `BGP_ALLOWED_PREFIXES_NEIGH_COM_LIST` (deployment, id, neighbor, neighbor_type, community)

## key 構造

```
BGP_ALLOWED_PREFIXES|<deployment>|<id>
BGP_ALLOWED_PREFIXES|<deployment>|<id>|<neighbor>|<neighbor_type>
BGP_ALLOWED_PREFIXES|<deployment>|<id>|<community>
BGP_ALLOWED_PREFIXES|<deployment>|<id>|<neighbor>|<neighbor_type>|<community>
```

| キー | 型 | 説明 |
|------|----|------|
| `deployment` | string `DEPLOYMENT_ID` 固定 | キー識別子 |
| `id` | uint32 | deployment 内の通し ID |
| `neighbor` | string `NEIGHBOR_TYPE` 固定 | 隣接種別キー |
| `neighbor_type` | string | 種別文字列 |
| `community` | string | community 識別子 |

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `default_action` | `routing-policy-action-type` (permit/deny) | デフォルト動作 |
| `prefixes_v4` | leaf-list `bgp-allowed-ipv4-prefix` | IPv4 プレフィックス（`A.B.C.D/n [le|ge n]`） |
| `prefixes_v6` | leaf-list `bgp-allowed-ipv6-prefix` | IPv6 プレフィックス（`X::/n [le|ge n]`） |

`bgp-allowed-ipv4-prefix` / `bgp-allowed-ipv6-prefix` 型は通常の inet:ipv4-prefix / ipv6-prefix の末尾に `le` または `ge` のサフィックスを許可するカスタム文字列型として定義されている。

## 制約

- `prefixes_v4` / `prefixes_v6` は `ordered-by user`（ユーザーが順序を制御可能）
- `default_action` は `sonic-routing-policy-sets:routing-policy-action-type` に従う

## 購読者

- `bgpcfgd` (`docker-fpm-frr`) — テンプレートで `bgpd` の `ip prefix-list` / `route-map` 設定を生成

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `BGP_GLOBALS`、`BGP_NEIGHBOR`、`BGP_PEER_GROUP`、`ROUTE_MAP`、`PREFIX_LIST`
- 関連 YANG: `sonic-bgp-allowed-prefix`、`sonic-routing-policy-sets`
- 関連 CLI: `config bgp`（プレフィックスリスト操作は主に jinja テンプレ経由）

## 引用元

[^1]: YANG 定義: `sonic-bgp-allowed-prefix.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-allowed-prefix.yang>

## 関連ページ
- [CONFIG_DB: BGP_NEIGHBOR](bgp-neighbor.md)
- [CONFIG_DB: BGP_GLOBALS](bgp-globals.md)
