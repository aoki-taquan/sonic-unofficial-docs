---
title: sonic-bgp-allowed-prefix YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-allowed-prefix.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [BGP_ALLOWED_PREFIXES]
  cli: []
  yang: [sonic-routing-policy-sets]
---

# sonic-bgp-allowed-prefix YANG

## 概要

- module: `sonic-bgp-allowed-prefix`
- namespace: `http://github.com/sonic-net/sonic-bgp-allowed-prefix`
- revision: `2022-02-26`
- import: `ietf-inet-types`、`sonic-routing-policy-sets`
- top container: `sonic-bgp-allowed-prefix`

deployment-id 単位で BGP セッションに対する **allowed prefix list** (permit/deny ベース) を定義する SONiC 拡張モジュール。neighbor / community / その組み合わせで複数 list を分けて持てる[^1]。

## ツリー

```
module: sonic-bgp-allowed-prefix
  +--rw sonic-bgp-allowed-prefix
     +--rw BGP_ALLOWED_PREFIXES
        +--rw BGP_ALLOWED_PREFIXES_LIST*            [deployment id]
        +--rw BGP_ALLOWED_PREFIXES_NEIGH_LIST*      [deployment id neighbor neighbor_type]
        +--rw BGP_ALLOWED_PREFIXES_COM_LIST*        [deployment id community]
        +--rw BGP_ALLOWED_PREFIXES_NEIGH_COM_LIST*  [deployment id neighbor neighbor_type community]
```

各 list は次の共通 leaf を持つ。

| leaf | 型 | 説明 |
|------|----|------|
| `deployment` | string (pattern `DEPLOYMENT_ID`) | 固定文字列 `DEPLOYMENT_ID` (key 構造のラベル) |
| `id` | uint32 | デプロイメント ID |
| `default_action` | `rpolsets:routing-policy-action-type` | permit / deny の既定アクション |
| `prefixes_v4` | `leaf-list bgp-allowed-ipv4-prefix` (`ordered-by user`) | 許可/拒否対象の IPv4 prefix 群 |
| `prefixes_v6` | `leaf-list bgp-allowed-ipv6-prefix` (`ordered-by user`) | 許可/拒否対象の IPv6 prefix 群 |

`bgp-allowed-ipv4-prefix` / `bgp-allowed-ipv6-prefix` は本モジュール内で定義された typedef で、`<prefix>` に **任意で `le N` / `ge N` を suffix** できる文字列形式 (例: `10.0.0.0/8 ge 16`)。

## list 別の追加 key

| list | 追加 key | 用途 |
|------|---------|------|
| `BGP_ALLOWED_PREFIXES_LIST` | (なし) | deployment-id ベースの基本セット |
| `BGP_ALLOWED_PREFIXES_NEIGH_LIST` | `neighbor` (固定文字列 `NEIGHBOR_TYPE`)、`neighbor_type` (string) | neighbor 種別ごとに上書き |
| `BGP_ALLOWED_PREFIXES_COM_LIST` | `community` (string) | 受信 community ベースで上書き |
| `BGP_ALLOWED_PREFIXES_NEIGH_COM_LIST` | `neighbor`、`neighbor_type`、`community` | neighbor + community 複合 |

## leafref / 依存

- `default_action` は `sonic-routing-policy-sets` の `routing-policy-action-type` を参照する。

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `BGP_ALLOWED_PREFIXES`
- CLI: 直接の CLI はなく、minigraph 生成系 (`sonic-cfggen` / `templates/`) で書き込まれる。

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`BGP_ALLOWED_PREFIXES`](../config-db/bgp-allowed-prefixes.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-bgp-allowed-prefix.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-allowed-prefix.yang>
