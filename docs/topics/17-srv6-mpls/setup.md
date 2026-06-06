---
title: 設定
description: 設定 — SRv6 / MPLS / Path Tracing の設定は、いずれも CONFIG_DB のテーブルに置けば最小構成が組めます。
area: topics
verification: meta
last_verified: 2026-06-06
sources:
- repo: sonic-net/sonic-buildimage
  path: src/sonic-yang-models/yang-models/sonic-srv6.yang
  lines: "1-146"
- repo: sonic-net/sonic-buildimage
  path: src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py
  lines: "1-150"
- repo: sonic-net/sonic-swss
  path: orchagent/srv6orch.cpp
  lines: "40-70,2204-2228"
related:
  cli:
  - config interface
  - show platform
  - config vrf
  config_db:
  - PORT_QOS_MAP
  - VRF
  - INTERFACE
  - VLAN_INTERFACE
  - PORTCHANNEL_INTERFACE
  - PORT
  - CRM
  yang:
  - sonic-route-common
  - sonic-srv6
  - sonic-interface
  - sonic-port-qos-map
  - sonic-vlan
  - sonic-portchannel
  - sonic-vrf
---

# 設定

[SRv6](../../reference/glossary.md#term-srv6) / [MPLS](../../reference/glossary.md#term-mpls) / Path Tracing の設定は、いずれも [CONFIG_DB](../../reference/glossary.md#term-config_db) のテーブルに置けば最小構成が組めます。CLI ラッパは限定的で、`config interface mpls` や `config interface pt-interface-id` のような per-feature コマンドが中心です。ここでは「最小限の有効化」と「reference のどこに正規定義があるか」を並べます。

## SRv6 Static SID / Locator

[FRR](../../reference/glossary.md#term-frr) の SRv6 制御プレーンは master 時点で限定的なため、Static SID / Locator を CONFIG_DB に直接書く構成が現実的です。`SRV6_MY_LOCATORS` と `SRV6_MY_SIDS` は `sonic-srv6` [YANG](../../reference/glossary.md#term-yang) に定義され、`bgpcfgd` の `SRv6Mgr` が `vtysh -c "segment-routing" -c "srv6" -c "static-sids" -c "sid ... locator ... behavior ... vrf ..."` の形で FRR に流し込みます。

```text
SRV6_MY_LOCATORS|<locator_name>:
  prefix    = <ipv6_address>     ; YANG 型は ipv6-address (例: fcbb:bbbb::)
  block_len = 40                 ; default 32
  node_len  = 24                 ; default 16
  func_len  = 16                 ; default 16
  arg_len   = 0                  ; default 0
  vrf       = default            ; optional, default "default"

SRV6_MY_SIDS|<locator_name>|<ip_prefix>:
  action          = uDT46        ; enum: uN | uDT46
  decap_vrf       = Vrf01        ; optional, default "default"
  decap_dscp_mode = pipe         ; optional enum: uniform | pipe
```

<!-- evidence: .cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-srv6.yang L95-143 SRV6_MY_SIDS leaves action(uN|uDT46) / decap_vrf / decap_dscp_mode -->
<!-- evidence: .cache/sonic-sources/sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py L78-91, L149-150 data['action'] / data['decap_vrf'], FRR command "sid ... locator ... behavior <action> [vrf <decap_vrf>]" -->

CONFIG_DB のフィールド名は `action` / `decap_vrf` ですが、`bgpcfgd` 内の `SRv6Mgr` がこれを FRR の `segment-routing srv6 static-sids sid ... locator ... behavior <action> [vrf <decap_vrf>]` に変換して `vtysh` に流し込むため、FRR 側のキーワードは `behavior` / `vrf` になります。投入時のフィールド名を取り違えないでください。`SRv6Mgr` は locator 不在のまま SID が来た場合に `SRV6_MY_LOCATORS` を subscribe して deferred 解決する経路を持つため、locator と SID の投入順序を厳密にそろえる必要はありません。

## SRv6 base スキーマ

base [HLD](../../reference/glossary.md#term-hld) では Static SID とは別に、`srv6orch` が直接消費する次のテーブルが定義されています。

```text
SRV6_SID_LIST|<segment_name>:
  path = [<sid>, <sid>, ...]

SRV6_MY_SID_TABLE|<block_len>:<node_len>:<func_len>:<arg_len>:<sid_ipv6>:
  action = end.dt46          ; srv6orch 側の lowercase 命名 (end.x / end.dt4 / end.dt46 / udx4 / udx6 ...)
  vrf    = Vrf01             ; decap 用 VRF
  adj    = <ipv6_nh>         ; end.x / end.dx4 / end.dx6 等で必須

SRV6_POLICY|<policy_name>:
  segment    = <segment_name>
  ...

SRV6_STEER|<key>:
  policy     = <policy_name>
  ...
```

<!-- evidence: .cache/sonic-sources/sonic-swss/orchagent/srv6orch.cpp L44-67 endpoint behavior table ("end.x"/"end.dt46" 等), L2204-2228 doTaskMySidTable が action/vrf/adj を読む, L2210 "Key for mySid : block_len:node_len:function_len:args_len:sid-ip" -->

`srv6orch` が直接消費する `SRV6_MY_SID_TABLE` のキーは `<block_len>:<node_len>:<func_len>:<arg_len>:<sid>` 形式で、フィールドは `action` / `vrf` / `adj` の 3 つだけです。前節の `SRV6_MY_SIDS`（`sonic-srv6` YANG 経由で FRR に流す）とはテーブル名・キー構造・action 命名（`uN` / `uDT46` vs `end.dt46`）が異なる点に注意してください。`adj` は L3 隣接が必要な behavior（`end.x` / `end.dx4` / `end.dx6` / `uA` 系）でのみ意味を持ちます。投入時に Neighbor 未解決でも srv6orch の pending queue が後から flush するため、運用上の neighbor タイミングをそろえる必要はありません（[アーキテクチャ](architecture.md) を参照）。

## MPLS の有効化

MPLS は **per-[RIF](../../reference/glossary.md#term-rif) で明示的に enable** が前提です。`INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` の `mpls` フィールドを `enable` に設定します。

```text
INTERFACE|Ethernet0:
  mpls = enable

VLAN_INTERFACE|Vlan100:
  mpls = enable
```

CLI ラッパとしては `config interface mpls enable <intf>` / `config interface mpls disable <intf>` が用意され、状態確認は `show mpls` 系コマンドです。静的 LSP は FRR 側で設定し、`fpmsyncd` が `AF_MPLS` netlink から `LABEL_ROUTE_TABLE` 経由で APP_DB に流します。

### MPLS と QoS

MPLS パケットの TC を [SONiC](../../reference/glossary.md#term-sonic) 内部 TC にマップするには、`MPLS_TC_TO_TC_MAP` を定義し、`PORT_QOS_MAP` の `mpls_tc_to_tc_map` フィールドで参照します。

```text
MPLS_TC_TO_TC_MAP|AZURE:
  0 = 0
  1 = 1
  ...

PORT_QOS_MAP|Ethernet0:
  mpls_tc_to_tc_map = AZURE
```

[DSCP](../../reference/glossary.md#term-dscp)/TC マップと同じ MAP セットに対して、MPLS だけのフィールド名が追加されている形です。詳細は [MPLS TC → TC map](../../routing/mpls-tc-to-tc-map.md) を参照してください。

## Path Tracing Midpoint

Path Tracing は per-port 設定です。`PORT|<port>` に 2 つのフィールドを足します。

```text
PORT|Ethernet0:
  pt_interface_id        = 1234
  pt_timestamp_template  = template3
```

`pt_interface_id` は MCD に刻まれる interface 識別、`pt_timestamp_template` は timestamp のビット切り出し方（例: `12_19` 系テンプレート）を決めます。[SAI](../../reference/glossary.md#term-sai) 側で対応する属性は `SAI_PORT_ATTR_PATH_TRACING_INTF` と `SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE` です。

PT Source / Sink / Regional Collector は SONiC 外側で構築するため、SONiC 単体としては Midpoint 設定だけで完結します。

## 設定シナリオ 1: VRF "Vrf01" 向け SRv6 uDT46 SID の最小投入

locator `loc1` の prefix を `fcbb:bbbb::` （`block_len=40` / `node_len=24` / `func_len=16` / `arg_len=0` で合計 80 bit）として、`fcbb:bbbb:1::/64` を `Vrf01` 向けの `uDT46` SID として宣言します。`sonic-cfggen` 経由か `redis-cli` 直叩きで CONFIG_DB に書きます。

```bash
sudo sonic-cfggen -a '{
  "SRV6_MY_LOCATORS": {
    "loc1": {"prefix":"fcbb:bbbb::","block_len":"40","node_len":"24","func_len":"16","arg_len":"0"}
  },
  "SRV6_MY_SIDS": {
    "loc1|fcbb:bbbb:1::/64": {"action":"uDT46","decap_vrf":"Vrf01"}
  }
}' -w
```

`SRV6_MY_SIDS` のキーは `<locator_name>|<ip_prefix>` 形式で、フィールドは YANG スキーマどおり `action`（`uN` または `uDT46`）と `decap_vrf` を使います。`prefix` は YANG 型が `ipv6-address` のため、サフィックスを付けずに IPv6 アドレスのみを指定します。

確認:

```bash
# CONFIG_DB
sonic-db-cli CONFIG_DB KEYS 'SRV6_MY_*'
sonic-db-cli CONFIG_DB HGETALL 'SRV6_MY_SIDS|loc1|fcbb:bbbb:1::/64'

# FRR への流し込み（SRv6Mgr が behavior/vrf キーワードに変換）
vtysh -c "show segment-routing srv6 locator"
vtysh -c "show segment-routing srv6 sid"

# データプレーン
show ipv6 route fcbb:bbbb:1::/64
```

`vtysh` 期待出力:

```text
Locator:
Name                 ID      Prefix                   Status
-------------------- ------- ------------------------ --------
loc1                 1       fcbb:bbbb::/48           Up
```

## 設定シナリオ 2: per-RIF で MPLS を有効化し、ラベル付き経路を受ける

```bash
sudo config interface mpls enable Ethernet0
sudo config interface mpls enable PortChannel10
show mpls interface
```

CONFIG_DB:

```json
{
    "INTERFACE": {"Ethernet0": {"mpls": "enable"}},
    "PORTCHANNEL_INTERFACE": {"PortChannel10": {"mpls": "enable"}}
}
```

`show mpls interface` の典型出力:

```text
Interface       MPLS State
--------------  ------------
Ethernet0       enable
PortChannel10   enable
```

FRR 側で静的 LSP を引いて確認します。

```text
configure terminal
mpls label local-pool min-label 1000 max-label 1999
mpls lsp 1001 10.0.0.2 Ethernet0 nexthop-label 2001
end
```

データプレーン確認:

```bash
ip -f mpls route show
show mpls ldp neighbor   # LDP を使う場合
```

## 設定シナリオ 3: Path Tracing Midpoint の最小投入

`Ethernet0` を Midpoint として動作させ、ID `1234` を MCD に刻み、`template3` でタイムスタンプを切り出します。

```bash
sudo config interface pt-interface-id Ethernet0 1234
sudo config interface pt-timestamp-template Ethernet0 template3
show interface path-tracing
```

CONFIG_DB:

```json
{
    "PORT": {
        "Ethernet0": {"pt_interface_id": "1234", "pt_timestamp_template": "template3"}
    }
}
```

`show interface path-tracing` 期待出力:

```text
Interface     PT Interface ID    Timestamp Template
------------  ----------------  --------------------
Ethernet0     1234              template3
```

## 設定エラーと対処

| 症状 | 原因 | 対処 |
|---|---|---|
| `SRV6_MY_SIDS` を入れても FRR に降りない | `bgpcfgd` 側で SRv6Mgr が無効 / FRR バージョンが古い | `docker logs bgp` で `SRv6Mgr` のログを確認、FRR 9.x 以上が必要 |
| `uDT46` SID で traffic が drop される | `decap_vrf` の typo、または [VRF](../../reference/glossary.md#term-vrf) が未作成 | `show vrf`、`sonic-db-cli CONFIG_DB HGETALL VRF\|Vrf01` を確認 |
| `config interface mpls enable` が `Not supported on platform` | SAI capability に MPLS なし | `show platform syseeprom` / `sai_redis_record` で `SAI_OBJECT_TYPE_ROUTER_INTERFACE_ATTR_ADMIN_MPLS_STATE` をチェック |
| MPLS_TC_TO_TC_MAP 設定後も DSCP マップ動作のまま | `PORT_QOS_MAP|<port>` で `mpls_tc_to_tc_map` を未参照 | 当該 port の `PORT_QOS_MAP` 行を確認 |
| Path Tracing で MCD が刻まれない | [ASIC](../../reference/glossary.md#term-asic) が Path Tracing 未対応、または FEC / speed 不一致 | capability、`sairedis.rec` のエラーを確認 |
| FRR で `segment-routing srv6 sid` 投入後も `Down` のまま | locator と SID の重複 / encap-source-address 未設定 | `vtysh -c "show ipv6 route fcbb:bbbb::/48"`、`segment-routing srv6 encapsulation source-address ...` を投入 |

## reference の不足を把握する

SRv6 / MPLS / Path Tracing は CLI / CONFIG_DB / YANG の reference が他の章ほど揃っていません。設定する前に以下を確認しておくと、ドキュメントとコードの乖離に悩まされにくくなります。

- **CLI** — `config interface mpls`、`show mpls`、`config interface pt-interface-id`、`config interface pt-timestamp-template`、`show interface path-tracing` は確認済みですが、SRv6 系は `vtysh` 経由が中心で SONiC 独自 CLI は限定的です。
- **CONFIG_DB** — `SRV6_MY_LOCATORS` / `SRV6_MY_SIDS` は `sonic-srv6` YANG に、`INTERFACE.mpls` 等は `sonic-interface` / `sonic-vlan` / `sonic-portchannel`、`MPLS_TC_TO_TC_MAP` は `sonic-port-qos-map` 系に定義があります。SRv6 base スキーマ（`SRV6_MY_SID_TABLE` 等）は YANG モデル化が進行中で、CONFIG_DB 直接投入が前提です。
- **YANG** — 共通の `sonic-route-common` は MPLS / SRv6 のラベル / SID 表現で参照されます。

## 関連リファレンス

- CLI: `config interface mpls`、`show mpls interface`、`config interface pt-interface-id`、`config interface pt-timestamp-template`、`show interface path-tracing`、`vtysh -c "show segment-routing srv6 ..."`
- CONFIG_DB: `SRV6_MY_LOCATORS`、`SRV6_MY_SIDS`、`SRV6_SID_LIST`、`SRV6_MY_SID_TABLE`、`SRV6_POLICY`、`SRV6_STEER`、`INTERFACE.mpls`、`VLAN_INTERFACE.mpls`、`PORTCHANNEL_INTERFACE.mpls`、`MPLS_TC_TO_TC_MAP`、`PORT_QOS_MAP`、`PORT`（PT 用フィールド）
- [APPL_DB](../../reference/glossary.md#term-appl_db) / [ASIC_DB](../../reference/glossary.md#term-asic_db): `LABEL_ROUTE_TABLE`、`SRV6_*` 系、`SAI_OBJECT_TYPE_INSEG_ENTRY`、`SAI_OBJECT_TYPE_MY_SID_ENTRY`、`SAI_PORT_ATTR_PATH_TRACING_*`
- YANG: [`sonic-route-common`](../../reference/yang/sonic-route-common.md)、`sonic-srv6`、`sonic-interface`、`sonic-port-qos-map`
- HLD: [SRv6 静的設定 HLD](../../routing/static-configuration-of-srv6-in-sonic-hld.md)、[SRv6 over IPv6 HLD](../../routing/segment-routing-over-ipv6-srv6-hld.md)、[MPLS HLD](../../routing/mpls-for-sonic-high-level-design-document.md)、[MPLS TC → TC map](../../routing/mpls-tc-to-tc-map.md)、[Path Tracing Midpoint](../../routing/path-tracing-midpoint.md)

## 関連ページ

- [SRv6 Static SID / Locator 設定](../../routing/static-configuration-of-srv6-in-sonic-hld.md)
- [MPLS HLD](../../routing/mpls-for-sonic-high-level-design-document.md)
- [MPLS TC → TC map](../../routing/mpls-tc-to-tc-map.md)
- [Path Tracing Midpoint](../../routing/path-tracing-midpoint.md)
- [sonic-route-common YANG](../../reference/yang/sonic-route-common.md)

<!-- glossary-links-injected: ec18b66e3507 -->
