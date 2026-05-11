---
title: 設定
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/routing/static-configuration-of-srv6-in-sonic-hld.md
  - docs/routing/segment-routing-over-ipv6-srv6-hld.md
  - docs/routing/mpls-for-sonic-high-level-design-document.md
  - docs/routing/mpls-tc-to-tc-map.md
  - docs/routing/path-tracing-midpoint.md
  - docs/reference/yang/sonic-route-common.md
---

# 設定

SRv6 / MPLS / Path Tracing の設定は、いずれも CONFIG_DB のテーブルに置けば最小構成が組めます。CLI ラッパは限定的で、`config interface mpls` や `config interface pt-interface-id` のような per-feature コマンドが中心です。ここでは「最小限の有効化」と「reference のどこに正規定義があるか」を並べます。

## SRv6 Static SID / Locator

FRR の SRv6 制御プレーンは master 時点で限定的なため、Static SID / Locator を CONFIG_DB に直接書く構成が現実的です。`SRV6_MY_LOCATORS` と `SRV6_MY_SIDS` は `sonic-srv6` YANG に定義され、`bgpcfgd` の `SRv6Mgr` が `vtysh -c "segment-routing" -c "srv6" -c "static-sids" -c "sid ... locator ... behavior ... vrf ..."` の形で FRR に流し込みます。

```
SRV6_MY_LOCATORS|<locator_name>:
  prefix = <ipv6_prefix>
  block_len = 40
  node_len  = 24
  func_len  = 16
  arg_len   = 0

SRV6_MY_SIDS|<sid>:
  locator  = <locator_name>
  behavior = end.dt46
  vrf      = Vrf01
```

`SRv6Mgr` は locator 不在のまま SID が来た場合に `SRV6_MY_LOCATORS` を subscribe して deferred 解決する経路を持つため、locator と SID の投入順序を厳密にそろえる必要はありません。

## SRv6 base スキーマ

base HLD では Static SID とは別に、`srv6orch` が直接消費する次のテーブルが定義されています。

```
SRV6_SID_LIST|<segment_name>:
  path = [<sid>, <sid>, ...]

SRV6_MY_SID_TABLE|<ipv6_addr>:
  block_len  = 40
  node_len   = 24
  func_len   = 16
  arg_len    = 0
  action     = end.dt46
  vrf        = Vrf01
  adj        = <ipv6_nh>     ; uA / End.X 系で必須

SRV6_POLICY|<policy_name>:
  segment    = <segment_name>
  ...

SRV6_STEER|<key>:
  policy     = <policy_name>
  ...
```

`adj` は L3 隣接が必要な behavior（`uA` / `End.X` / `uDX4` / `uDX6` / `End.DX4` / `End.DX6`）のみで意味を持ちます。投入時に Neighbor 未解決でも srv6orch の pending queue が後から flush するため、運用上の neighbor タイミングをそろえる必要はありません（[アーキテクチャ](architecture.md) を参照）。

## MPLS の有効化

MPLS は **per-RIF で明示的に enable** が前提です。`INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` の `mpls` フィールドを `enable` に設定します。

```
INTERFACE|Ethernet0:
  mpls = enable

VLAN_INTERFACE|Vlan100:
  mpls = enable
```

CLI ラッパとしては `config interface mpls enable <intf>` / `config interface mpls disable <intf>` が用意され、状態確認は `show mpls` 系コマンドです。静的 LSP は FRR 側で設定し、`fpmsyncd` が `AF_MPLS` netlink から `LABEL_ROUTE_TABLE` 経由で APP_DB に流します。

### MPLS と QoS

MPLS パケットの TC を SONiC 内部 TC にマップするには、`MPLS_TC_TO_TC_MAP` を定義し、`PORT_QOS_MAP` の `mpls_tc_to_tc_map` フィールドで参照します。

```
MPLS_TC_TO_TC_MAP|AZURE:
  0 = 0
  1 = 1
  ...

PORT_QOS_MAP|Ethernet0:
  mpls_tc_to_tc_map = AZURE
```

DSCP/TC マップと同じ MAP セットに対して、MPLS だけのフィールド名が追加されている形です。詳細は [MPLS TC → TC map](../../routing/mpls-tc-to-tc-map.md) を参照してください。

## Path Tracing Midpoint

Path Tracing は per-port 設定です。`PORT|<port>` に 2 つのフィールドを足します。

```
PORT|Ethernet0:
  pt_interface_id        = 1234
  pt_timestamp_template  = template_3
```

`pt_interface_id` は MCD に刻まれる interface 識別、`pt_timestamp_template` は timestamp のビット切り出し方（例: `12_19` 系テンプレート）を決めます。SAI 側で対応する属性は `SAI_PORT_ATTR_PATH_TRACING_INTF` と `SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE` です。

PT Source / Sink / Regional Collector は SONiC 外側で構築するため、SONiC 単体としては Midpoint 設定だけで完結します。

## reference の不足を把握する

SRv6 / MPLS / Path Tracing は CLI / CONFIG_DB / YANG の reference が他の章ほど揃っていません。設定する前に以下を確認しておくと、ドキュメントとコードの乖離に悩まされにくくなります。

- **CLI** — `config interface mpls`、`show mpls`、`config interface pt-interface-id`、`config interface pt-timestamp-template`、`show interface path-tracing` は確認済みですが、SRv6 系は `vtysh` 経由が中心で SONiC 独自 CLI は限定的です。
- **CONFIG_DB** — `SRV6_MY_LOCATORS` / `SRV6_MY_SIDS` は `sonic-srv6` YANG に、`INTERFACE.mpls` 等は `sonic-interface` / `sonic-vlan` / `sonic-portchannel`、`MPLS_TC_TO_TC_MAP` は `sonic-port-qos-map` 系に定義があります。SRv6 base スキーマ（`SRV6_MY_SID_TABLE` 等）は YANG モデル化が進行中で、CONFIG_DB 直接投入が前提です。
- **YANG** — 共通の `sonic-route-common` は MPLS / SRv6 のラベル / SID 表現で参照されます。

## 関連ページ

- [SRv6 Static SID / Locator 設定](../../routing/static-configuration-of-srv6-in-sonic-hld.md)
- [MPLS HLD](../../routing/mpls-for-sonic-high-level-design-document.md)
- [MPLS TC → TC map](../../routing/mpls-tc-to-tc-map.md)
- [Path Tracing Midpoint](../../routing/path-tracing-midpoint.md)
- [sonic-route-common YANG](../../reference/yang/sonic-route-common.md)
