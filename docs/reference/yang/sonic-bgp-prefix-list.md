---
title: sonic-bgp-prefix-list YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-prefix-list.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [PREFIX_LIST]
  cli: []
  yang: [sonic-types]
---

# sonic-bgp-prefix-list YANG

## 概要

- module: `sonic-bgp-prefix-list`
- namespace: `http://github.com/sonic-net/sonic-bgp-prefix-list`
- revision: `2025-02-17` (`Updated description and leafs for PREFIX_LIST_LIST`)、初版 `2025-02-05`
- import: `sonic-types`
- top container: `sonic-bgp-prefix-list`

BGP ルーティング ポリシー用の prefix list を定義する SONiC モジュール[^1]。`PREFIX_LIST_LIST` の各エントリは prefix 種別と IPv4/IPv6 prefix の組で表現される。

## ツリー

```
module: sonic-bgp-prefix-list
  +--rw sonic-bgp-prefix-list
     +--rw PREFIX_LIST
        +--rw PREFIX_LIST_LIST* [prefix_type ip-prefix]
           +--rw prefix_type    string
           +--rw ip-prefix      union<stypes:sonic-ip4-prefix, stypes:sonic-ip6-prefix>
           +--rw family?        stypes:ip-family
```

## container / list 一覧

| 種別 | パス | key | 説明 |
|------|------|-----|------|
| `container` | `sonic-bgp-prefix-list` |  | top |
| `container` | `sonic-bgp-prefix-list/PREFIX_LIST` |  | BGP で消費される PREFIX_LIST コンテナ |
| `list` | `sonic-bgp-prefix-list/PREFIX_LIST/PREFIX_LIST_LIST` | `prefix_type ip-prefix` | 各エントリは BGP route filtering 用の prefix 種別と IP prefix を定義 |

## leaf 一覧

| leaf | 型 | 必須 | 制約 | 説明 |
|------|----|------|------|------|
| `prefix_type` | `string` | yes |  | Prefix 種別 (アプリ層が解釈) |
| `ip-prefix` | `union<sonic-ip4-prefix, sonic-ip6-prefix>` | yes |  | CIDR 表記の IPv4 / IPv6 prefix |
| `family` | `stypes:ip-family` | no | `must "(contains(../ip-prefix, ':') and current()='IPv6') or (contains(../ip-prefix, '.') and current()='IPv4')"` | 後方互換用の address family フィールド。`ip-prefix` が IPv4 の場合は `IPv4`、IPv6 の場合は `IPv6` でなければならない |

## leafref / 依存

- なし (型は `sonic-types` の typedef を再利用)

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `PREFIX_LIST`
- CLI: BGP 用 prefix list は `vtysh` ベースで設定するのが一般的で、本テーブルは template / cfggen 経由で書き込まれる。

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`PREFIX_LIST`](../config-db/prefix-list.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-bgp-prefix-list.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-prefix-list.yang>
