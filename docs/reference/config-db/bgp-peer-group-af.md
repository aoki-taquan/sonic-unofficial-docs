---
title: BGP_PEER_GROUP_AF テーブル
description: "BGP_PEER_GROUP_AF テーブル — BGP_PEER_GROUP の アドレスファミリ別 設定を保持するテーブル。frr-mgmt-framework が DEVICE_METADATA.frr_mgmt_framework_config = true のときに使用する generic 形式。"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-peergroup.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-common.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - BGP_PEER_GROUP_AF
    - BGP_PEER_GROUP
    - BGP_NEIGHBOR_AF
  cli:
    - config bgp
  yang:
    - sonic-bgp-peergroup
    - sonic-bgp-common
---

# BGP_PEER_GROUP_AF テーブル

## 概要

`BGP_PEER_GROUP` の **アドレスファミリ別** 設定を保持するテーブル[^1]。`frr-mgmt-framework` が `DEVICE_METADATA.frr_mgmt_framework_config = true` のときに使用する generic 形式。`sonic-bgp-common.yang` の `sonic-bgp-cmn-af` grouping を `uses` し、route-map / prefix-list / community / max-prefix 等の AF スコープ設定を表現する。

## key 構造

```
BGP_PEER_GROUP_AF|<vrf_name>|<peer_group_name>|<afi_safi>
```

- `<vrf_name>`: `BGP_GLOBALS_LIST.vrf_name` への leafref
- `<peer_group_name>`: `BGP_PEER_GROUP_LIST.peer_group_name` への leafref（同一 vrf 限定）
- `<afi_safi>`: `ipv4_unicast` / `ipv6_unicast` / `l2vpn_evpn` 等

## フィールド (`sonic-bgp-cmn-af` より継承)

| フィールド | 型 | 説明 |
|-----------|----|------|
| `afi_safi` | enum | address-family 識別子（key 部） |
| `admin_status` | boolean / string | activate / no-activate |
| `send_default_route` | boolean | default-originate |
| `default_rmap` | string | default-originate route-map |
| `max_prefix_limit` | uint32 | maximum-prefix |
| `max_prefix_warning_only` | boolean | warning-only |
| `max_prefix_warning_threshold` | uint8 | warning threshold (%) |
| `max_prefix_restart_interval` | uint16 | restart 間隔 |
| `route_map_in` / `route_map_out` | leaf-list string | inbound / outbound route-map |
| `soft_reconfiguration_in` | boolean | soft-reconfiguration inbound |
| `unsuppress_map_name` | string | unsuppress-map |
| `rrclient` | boolean | route-reflector-client |
| `weight` | uint16 | weight |
| `as_override` | boolean | as-override |
| `send_community` | enum | send-community 種別 |
| `tx_add_paths` | enum | addpath 送出 |
| `unchanged_as_path` / `unchanged_med` / `unchanged_nexthop` | boolean | attribute-unchanged |
| `filter_list_in` / `filter_list_out` | string | as-path filter-list |
| `nhself` / `nexthop_self_force` | boolean | next-hop-self / force |
| `prefix_list_in` / `prefix_list_out` | string | prefix-list 参照 |
| `remove_private_as_enabled` / `replace_private_as` / `remove_private_as_all` | boolean | remove-private-AS の各オプション |
| `allow_as_in` / `allow_as_count` / `allow_as_origin` | boolean / uint8 | allowas-in |
| `cap_orf` | enum | capability orf |
| `route_server_client` | boolean | route-server-client |

合計 30 以上の AF レベル leaf を持つ。完全な一覧は `sonic-bgp-common.yang` の `grouping sonic-bgp-cmn-af` を参照。

## 制約

- `vrf_name` / `peer_group_name` はそれぞれ leafref。存在しない peer-group 名はバリデーション失敗
- key の `peer_group_name` leafref は `[vrf_name=current()/../vrf_name]` のスコープ式で同一 VRF に縛られる

## 購読者

- `frr-mgmt-framework`: FRR (bgpd) の `address-family ... / neighbor PG ...` 配下コマンドへ変換
- `bgpcfgd` テンプレ系: 主に neighbor 単位処理が中心で、AF 別設定はテンプレ展開で間接反映

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: [`BGP_PEER_GROUP`](./bgp-peer-group.md)、[`BGP_NEIGHBOR_AF`](./bgp-neighbor-af.md)、`PREFIX_LIST`、`ROUTE_MAP`
- 関連 YANG: `sonic-bgp-peergroup`、`sonic-bgp-common`
- 関連 CLI: [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: [`sonic-bgp-peergroup`](../yang/sonic-bgp-peergroup.md) / `sonic-bgp-common`
- CLI: [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: YANG 定義: `sonic-bgp-peergroup.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-peergroup.yang>; AF 共通 leaf は `sonic-bgp-common.yang` の `grouping sonic-bgp-cmn-af`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-bgp-common.yang>

<!-- ops-hint -->
## 運用ヒント

### 典型値

- key 形式: `BGP_PEER_GROUP_AF|<vrf>|<peer_group>|<afi_safi>` (例 `BGP_PEER_GROUP_AF|default|UPSTREAM|ipv4_unicast`)。
- `admin_status=true` で activate、`route_map_in`/`route_map_out` でフィルタ。

### よくある誤設定

- peer-group を作成した直後に AF 設定を行わず、neighbor が activate されない (アドレスファミリ未投入)。
- `max_prefix_limit` を運用ピーク以下に設定して BGP セッションが reset する。

### 確認コマンド

```bash
sonic-db-cli CONFIG_DB keys 'BGP_PEER_GROUP_AF|*'
vtysh -c "show ip bgp summary"
vtysh -c "show running-config bgpd"
```
<!-- /ops-hint -->
