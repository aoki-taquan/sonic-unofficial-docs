---
title: BGP_GLOBALS_AF_NETWORK テーブル
description: "BGP_GLOBALS_AF_NETWORK テーブル — BGP_GLOBALS_AF_AGGREGATE_ADDR が複数の動的ルートを 集約 するのに対し、こちらは管理者が 明示的に広告したいプレフィックス を列挙する用途。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-global.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BGP_GLOBALS_AF_NETWORK
    - BGP_GLOBALS_AF
    - BGP_GLOBALS
  cli:
    - config bgp
  yang:
    - sonic-bgp-global
---

# BGP_GLOBALS_AF_NETWORK テーブル

## 概要

**VRF × アドレスファミリ単位** で BGP に **静的に注入するネットワーク** (`network <prefix>` ステートメント) を定義する CONFIG_DB テーブル[^1]。FRR `bgpd` の `address-family <afi> <safi>` 配下の `network <ip_prefix>` に対応する。`frr-mgmt-framework` 経路 (DEVICE_METADATA `frr_mgmt_framework_config = true`) で使用される。

`BGP_GLOBALS_AF_AGGREGATE_ADDR` が複数の動的ルートを **集約** するのに対し、こちらは管理者が **明示的に広告したいプレフィックス** を列挙する用途。

## key 構造

```
BGP_GLOBALS_AF_NETWORK|<vrf_name>|<afi_safi>|<ip_prefix>
```

- `<vrf_name>`: `BGP_GLOBALS.vrf_name` への leafref
- `<afi_safi>`: `ipv4_unicast`, `ipv6_unicast` 等
- `<ip_prefix>`: 広告対象プレフィックス (`inet:ip-prefix`)

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `vrf_name` (key) | leafref → `BGP_GLOBALS.vrf_name` | 所属 VRF |
| `afi_safi` (key) | string | アドレスファミリ |
| `ip_prefix` (key) | inet:ip-prefix | 広告するネットワーク |
| `policy` | leafref → `ROUTE_MAP_SET.name` | 属性を加工する route-map |
| `backdoor` | boolean | backdoor ルートとして指定 (RFC 1771 / FRR 拡張) |

## 制約

- 3 つのキーで一意。
- 対応する VRF の BGP インスタンスが先に必要 (leafref)。
- `network` で広告するためには、**実際にそのプレフィックスが RIB (ルーティングテーブル) に存在する** ことが BGP の動作上の前提（`BGP_GLOBALS.network_import_check = true` の場合）。
- `backdoor` は IGP と BGP の同一プレフィックスで IGP を優先させたいときに使う。

## 購読者

- `frr-mgmt-framework`: vtysh の `network <prefix> [route-map <name>] [backdoor]` コマンドに変換
- `bgpd` (FRR): network 経由で BGP UPDATE に該当プレフィックスを注入

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `BGP_GLOBALS`, `BGP_GLOBALS_AF`, `BGP_GLOBALS_AF_AGGREGATE_ADDR`, `ROUTE_MAP_SET`, `STATIC_ROUTE`
- 関連 CLI: vtysh の `network <prefix>` (`frr-mgmt-framework` 経路では CONFIG_DB 投入)
- 関連 YANG: `sonic-bgp-global`

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-bgp-global`](../yang/sonic-bgp-global.md)
- CLI: [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-bgp-global.yang` (`BGP_GLOBALS_AF_NETWORK` container). <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-global.yang>

## 関連ページ
- [CONFIG_DB: BGP_GLOBALS_AF](bgp-globals-af.md)
- [CONFIG_DB: BGP_GLOBALS_AF_AGGREGATE_ADDR](bgp-globals-af-aggregate-addr.md)
