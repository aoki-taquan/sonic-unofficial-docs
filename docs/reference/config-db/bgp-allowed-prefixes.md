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
    - BGP_NEIGHBOR
    - BGP_PEER_GROUP
  cli: []
  yang:
    - sonic-bgp-allowed-prefix
---

# BGP_ALLOWED_PREFIXES テーブル

## 概要

`BGP_ALLOWED_PREFIXES` は **deployment ID 単位の prefix 許可リスト** を CONFIG_DB に格納するテーブル[^1]。bgpcfgd の Jinja テンプレが読み込み、ToR / leaf スイッチで広告する prefix-list / route-map を生成する。Microsoft 由来の deployment 駆動構成 (T0/T1/T2 ロール) で利用される。

YANG モジュール 1 つで 4 つの list（key の組合せが異なる）を持つ:

1. `BGP_ALLOWED_PREFIXES_LIST` (deployment, id)
2. `BGP_ALLOWED_PREFIXES_NEIGH_LIST` (deployment, id, neighbor, neighbor_type)
3. `BGP_ALLOWED_PREFIXES_COM_LIST` (deployment, id, community)
4. `BGP_ALLOWED_PREFIXES_NEIGH_COM_LIST` (deployment, id, neighbor, neighbor_type, community)

## key 構造

```
BGP_ALLOWED_PREFIXES|<deployment>|<id>[|<neighbor>|<neighbor_type>][|<community>]
```

- `<deployment>` は固定文字列 `DEPLOYMENT_ID` (YANG `pattern "DEPLOYMENT_ID"`)
- `<id>` は uint32 の deployment id
- `<neighbor>` は固定文字列 `NEIGHBOR_TYPE` (`pattern "NEIGHBOR_TYPE"`)
- `<neighbor_type>` は任意の neighbor タイプ名
- `<community>` は community 文字列

> パターンが固定文字列に見えるが、これは bgpcfgd テンプレ側で `DEPLOYMENT_ID` / `NEIGHBOR_TYPE` という文字列キーをそのまま使う構造になっているため。`<id>` などの可変部分で deployment を区別する。

## フィールド（共通）

各 list は次の共通フィールドを持つ:

| フィールド | 型 | 説明 |
|-----------|----|------|
| `default_action` | `rpolsets:routing-policy-action-type` | permit / deny |
| `prefixes_v4` | leaf-list of `bgp-allowed-ipv4-prefix` (ordered-by user) | 許可する IPv4 prefix リスト |
| `prefixes_v6` | leaf-list of `bgp-allowed-ipv6-prefix` (ordered-by user) | 許可する IPv6 prefix リスト |

`bgp-allowed-ipv4-prefix` / `bgp-allowed-ipv6-prefix` は **`<prefix> [le|ge <len>]`** という FRR-like の構文を許す独自 typedef。例: `10.0.0.0/8 le 32`。

## 制約

- `<deployment>` キーは固定パターン `DEPLOYMENT_ID` / `NEIGHBOR_TYPE` に縛られるため、CONFIG_DB に書き込む際は必ずこのリテラルを使う。
- prefix の `le` / `ge` 修飾子は IPv4 では 0..32、IPv6 では 0..128 の範囲のみ許可。
- 4 種類の list は同じ container 配下にあるが、key の組合せが異なるので区別される。

## 購読者

- `bgpcfgd` (`docker-fpm-frr`): deployment id ごとに `BGP_ALLOWED_PREFIXES_*` を読み、Jinja テンプレで `ip prefix-list` / `route-map` 文を vtysh に流す
- `bgpd` (FRR): 生成された prefix-list / route-map を BGP neighbor / peer-group に適用

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `BGP_NEIGHBOR`, `BGP_PEER_GROUP`, `ROUTE_MAP_SET`, `DEVICE_METADATA` (`deployment_id`)
- 関連 CLI: 専用 CLI なし。`sonic-cfggen` / minigraph 経由で投入されるのが通常
- 関連 YANG: `sonic-bgp-allowed-prefix`, `sonic-routing-policy-sets`

## 引用元

[^1]: YANG 定義: `sonic-bgp-allowed-prefix.yang` (revision 2022-02-26). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-allowed-prefix.yang>
