---
title: STATIC_ROUTE テーブル
description: "STATIC_ROUTE テーブル — STATIC_ROUTE は静的経路を CONFIG_DB に保持するテーブル。YANG では template 形式 (STATIC_ROUTE|) と VRF-aware 形式 (STATIC_ROUTE||) の 2 つの list が定義されている。"
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-static-route.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-swss-common
    path: common/schema.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
related:
  config_db:
    - STATIC_ROUTE
  cli:
    - config route
  yang:
    - sonic-static-route
---

# STATIC_ROUTE テーブル

## 概要

`STATIC_ROUTE` は静的経路を CONFIG_DB に保持するテーブル。YANG では template 形式 (`STATIC_ROUTE|<prefix>`) と VRF-aware 形式 (`STATIC_ROUTE|<vrf_name>|<prefix>`) の 2 つの list が定義されている[^1]。nexthop、出力 interface、BGP への advertise、BFD、administrative distance、nexthop VRF、blackhole 指定を扱う。テーブル名の実装側定数は `schema.h` も参照する[^2]。

## key 構造

```text
STATIC_ROUTE|<prefix>
STATIC_ROUTE|<vrf_name>|<prefix>
```

`<prefix>` は IPv4 / IPv6 prefix。`<vrf_name>` は `default`、`mgmt`、または `Vrf...` 形式。

## 主要フィールド

| フィールド | 型 | 既定値 | 説明 |
|-----------|----|--------|------|
| `nexthop` | string | - | nexthop IP。interface route では `0.0.0.0` を指定する想定 |
| `ifname` | string | - | 出力 interface |
| `advertise` | comma-separated boolean string | `false` | BGP へ広告するか。nexthop ごとに指定可能 |
| `bfd` | comma-separated boolean string | `false` | nexthop ごとの BFD 監視有効化。template 形式のみ |
| `distance` | comma-separated uint8 string | `0` | administrative distance。VRF-aware 形式のみ |
| `nexthop-vrf` | comma-separated VRF string | - | VRF leaking 用 nexthop VRF。VRF-aware 形式のみ |
| `blackhole` | comma-separated boolean string | `false` | 一致パケットを破棄する blackhole route。VRF-aware 形式のみ |

## 制約

- `advertise`、`bfd`、`blackhole` は `true` / `false` のカンマ区切り文字列。
- `distance` は 0..255 のカンマ区切り文字列。
- `nexthop-vrf` は `default`、`mgmt`、`Vrf...` のカンマ区切り文字列。
- YANG の VRF-aware key は `vrf_name prefix`。template 形式には `vrf_name` が無い。

## 購読者

- `staticd` / `zebra` (FRR): SONiC の設定生成パスを通じて static route を FRR に反映する。
- `bgpcfgd` / routing config パス: `advertise` が有効な static route を BGP 広告対象として扱う。
- `orchagent` / route orch: kernel / FRR から APPL_DB 経由で転送経路を SAI route へ反映する。

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `VRF`、`INTERFACE`、`PORTCHANNEL_INTERFACE`、`VLAN_INTERFACE`、`LOOPBACK_INTERFACE`
- 関連 CLI: `config route`
- 関連 YANG: `sonic-static-route`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-static-route`](../yang/sonic-static-route.md)
- CLI: [`config route`](../cli/config-route.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-static-route.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-static-route.yang>
[^2]: テーブル名定数参照: `schema.h`. <https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/schema.h>
