---
title: VRF と Static Route の設定
description: VRF と Static Route の設定 — 設定を読む入口は 3 つあります。作業者が打つのは CLI、永続設定として残るのは CONFIG_DB、外部管理システムが検証する型は
  YANG です。このページでは VRF 付き L3 設定の最小単位をその順で整理します。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/reference/cli/config-vrf.md
- docs/reference/cli/config-route.md
- docs/reference/config-db/vrf.md
- docs/reference/config-db/interface.md
- docs/reference/config-db/loopback-interface.md
- docs/reference/config-db/static-route.md
- docs/reference/config-db/fg-nhg.md
- docs/reference/yang/sonic-vrf.md
- docs/reference/yang/sonic-interface.md
- docs/reference/yang/sonic-static-route.md
- docs/reference/yang/sonic-route-common.md
related:
  cli:
  - config route
  - config vrf
  - config interface
  - show ip
  - show interfaces
  - config portchannel
  - show route map
  config_db:
  - VRF
  - VLAN
  - LOOPBACK_INTERFACE
  - FG_NHG
  - STATIC_ROUTE
  - ROUTE_MAP
  - BGP_PEER_GROUP_AF
  yang:
  - sonic-static-route
  - sonic-vrf
  - sonic-interface
  - sonic-route-common
  - sonic-route-map
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
---

# VRF と Static Route の設定

設定を読む入口は 3 つあります。作業者が打つのは CLI、永続設定として残るのは [CONFIG_DB](../../reference/glossary.md#term-config_db)、外部管理システムが検証する型は [YANG](../../reference/glossary.md#term-yang) です。このページでは [VRF](../../reference/glossary.md#term-vrf) 付き L3 設定の最小単位をその順で整理します。

## 最小構成の流れ

1. VRF を作る。
2. L3 interface を VRF に bind する。
3. interface に IP address を付ける。
4. static route を VRF 付きで追加する。
5. 必要なら nexthop VRF、blackhole、FG [ECMP](../../reference/glossary.md#term-ecmp) を加える。

CLI の詳細な引数は [config vrf](../../reference/cli/config-vrf.md) と [config route](../../reference/cli/config-route.md) を参照してください。

## 典型シナリオ 1: tenant VRF を新規作成して L3 サブインタフェースに割り当てる

「multi-tenant の青 VRF を作って、`Ethernet0` をその VRF の uplink にして、上位 router 向け static default を入れたい」というケース。

### CLI で打つ場合

```bash
# 1. VRF を作成
sudo config vrf add Vrf_blue

# 2. interface を VRF に bind (この瞬間に IP が剥がれるので注意)
sudo config interface vrf bind Ethernet0 Vrf_blue

# 3. IP を付け直す
sudo config interface ip add Ethernet0 192.0.2.1/31

# 4. VRF 内の default route
sudo config route add prefix vrf Vrf_blue 0.0.0.0/0 nexthop 192.0.2.0
```

`bind` の瞬間に kernel netlink で interface が VRF table に紐づき直されるため、既存の IP は一度落ちます。順序を逆にすると `Interface ... has IP address ...` のような warning が出るバージョンもあるので、空にしてから bind するのが安全です。

### CONFIG_DB で投入する場合

```json
{
  "VRF": {
    "Vrf_blue": {
      "NULL": "NULL"
    }
  },
  "INTERFACE": {
    "Ethernet0": {
      "vrf_name": "Vrf_blue"
    },
    "Ethernet0|192.0.2.1/31": {
      "NULL": "NULL"
    }
  },
  "STATIC_ROUTE": {
    "Vrf_blue|0.0.0.0/0": {
      "nexthop": "192.0.2.0",
      "ifname": "Ethernet0",
      "distance": "0",
      "blackhole": "false"
    }
  }
}
```

`VRF|<name>` 行は属性なしの marker、`INTERFACE|<name>` 行は VRF binding を持ち、`INTERFACE|<name>|<ip/prefix>` 行は IP 割り当てです。3 行は別々の key であり、削除時もこの順序を逆に外します。

`sonic-cfggen` で部分適用:

```bash
sonic-cfggen -a "$(cat vrf_patch.json)" --write-to-db
config save -y
```

### show コマンドで確認

```bash
show vrf
show ip route vrf Vrf_blue
show ip interfaces
show interfaces vrf
```

`show vrf` の典型出力:

```text
VRF        Interfaces
---------  ------------
Vrf_blue   Ethernet0
```

`show ip route vrf Vrf_blue`:

```text
VRF Vrf_blue:
S>* 0.0.0.0/0 [1/0] via 192.0.2.0, Ethernet0, weight 1, 00:00:12
C>* 192.0.2.0/31 is directly connected, Ethernet0, 00:00:30
```

`S>*` が static、`C>*` が connected。`>` が無いと FIB に入っていない (RIB のみ) ことを示します。

## 典型シナリオ 2: ECMP static route を 2 nexthop で組む

WAN 側に 2 本の uplink がある場合の冗長化。

```bash
sudo config route add prefix vrf Vrf_blue 203.0.113.0/24 \
  nexthop 192.0.2.0 nexthop 192.0.2.2
```

CONFIG_DB 表現 (カンマ区切り、index で揃える):

```json
{
  "STATIC_ROUTE": {
    "Vrf_blue|203.0.113.0/24": {
      "nexthop": "192.0.2.0,192.0.2.2",
      "ifname": "Ethernet0,Ethernet4",
      "distance": "0,0",
      "blackhole": "false,false"
    }
  }
}
```

確認:

```bash
show ip route vrf Vrf_blue 203.0.113.0/24
```

```text
Routing entry for 203.0.113.0/24
  Known via "static", distance 1, metric 0
  Last update 00:00:05 ago
  * 192.0.2.0, via Ethernet0, weight 1
  * 192.0.2.2, via Ethernet4, weight 1
```

両 nexthop に `*` が出れば両方 active。片方だけなら [ARP](../../reference/glossary.md#term-arp) / next-hop reachability を疑います。

## 典型シナリオ 3: VRF leaking と blackhole

「青 VRF から赤 VRF の loopback (10.99.0.1/32) を見えるようにする」。

```bash
sudo config route add prefix vrf Vrf_blue 10.99.0.1/32 \
  nexthop vrf Vrf_red 10.99.0.1
```

```json
{
  "STATIC_ROUTE": {
    "Vrf_blue|10.99.0.1/32": {
      "nexthop": "10.99.0.1",
      "nexthop-vrf": "Vrf_red",
      "distance": "0",
      "blackhole": "false"
    }
  }
}
```

blackhole route (流入 packet を破棄):

```json
{
  "STATIC_ROUTE": {
    "Vrf_blue|192.168.100.0/24": {
      "nexthop": "",
      "blackhole": "true",
      "distance": "0"
    }
  }
}
```

`blackhole=true` の場合 `nexthop` は空でよい ([orchagent](../../reference/glossary.md#term-orchagent) が null route を install する)。

## CONFIG_DB で見る形

VRF は `VRF|<name>`、物理 L3 interface は `INTERFACE|<name>`、static route は `STATIC_ROUTE|<vrf>|<prefix>` を見ます。

```text
VRF|Vrf_blue
    NULL = NULL

INTERFACE|Ethernet0
    vrf_name = Vrf_blue

INTERFACE|Ethernet0|192.0.2.1/31

STATIC_ROUTE|Vrf_blue|198.51.100.0/24
    nexthop = 192.0.2.0
    ifname = Ethernet0
    distance = 0
```

Loopback を使う場合は `LOOPBACK_INTERFACE` を読みます。[BGP](../../reference/glossary.md#term-bgp) の router-id や per-VRF loopback を扱うときは [LOOPBACK_INTERFACE テーブル](../../reference/config-db/loopback-interface.md) が入口です。

## ECMP static route の表現

複数 next hop はカンマ区切りの同じ index で揃えます。

```text
STATIC_ROUTE|Vrf_blue|203.0.113.0/24
    nexthop = 192.0.2.0,192.0.2.2
    ifname = Ethernet0,Ethernet4
    distance = 0,0
    blackhole = false,false
```

`nexthop-vrf` を使うと VRF leaking を表現できます。blackhole route は `blackhole=true` で一致パケットを破棄する経路として扱います。詳細な key とフィールドは [STATIC_ROUTE テーブル](../../reference/config-db/static-route.md) と [sonic-static-route YANG](../../reference/yang/sonic-static-route.md) を確認してください。

## FG_NHG は通常 route 設定とは別に読む

Fine Grained ECMP は static route のカンマ区切り ECMP とは別に、`FG_NHG`、`FG_NHG_PREFIX`、`FG_NHG_MEMBER` で bucket と member を定義します。route の next-hop set を単に増やす機能ではなく、flow stickiness と bucket 配置を制御する機能です。

設定テーブルの詳細は [FG_NHG テーブル](../../reference/config-db/fg-nhg.md)、動作の背景は [ECMP family](ecmp.md) を参照してください。

## YANG を見る場面

YANG は、外部 API や config validation の入力制約を確認するときに見ます。

| YANG | 使う場面 |
|------|----------|
| [sonic-vrf](../../reference/yang/sonic-vrf.md) | VRF 名、fallback、VNI の型と制約。 |
| [sonic-interface](../../reference/yang/sonic-interface.md) | `vrf_name` leafref、IP prefix、link-local-only、loopback action。 |
| [sonic-static-route](../../reference/yang/sonic-static-route.md) | VRF-aware static route、`nexthop-vrf`、blackhole。 |
| [sonic-route-common](../../reference/yang/sonic-route-common.md) | route redistribute の VRF / protocol / route-map の型。 |

## よくある設定エラーと対処

`sonic-utilities/config/main.py` の `ctx.fail()` から抜粋:

| エラーメッセージ | 原因 | 対処 |
|---|---|---|
| `VRF <name> does not exist!` | route で参照した VRF 未作成 | 先に `config vrf add <name>` |
| `Nexthop VRF <vrf> does not exist!` | `nexthop-vrf` 指定先が未作成 | leaking 先の VRF を先に作成 |
| `interface <name> does not exist.` | route の `ifname` 未作成 | 先に物理 / [VLAN](../../reference/glossary.md#term-vlan) / [PortChannel](../../reference/glossary.md#term-portchannel) interface を確認 |
| `portchannel does not exist.` | [LAG](../../reference/glossary.md#term-lag) ifname を指定したが LAG 未作成 | `config portchannel add` |
| `vlan interface does not exist.` | VLAN ifname を指定したが VLAN_INTERFACE 未作成 | `config interface ip add Vlan<id>` |
| `argument is not in pattern prefix [vrf ...] <A.B.C.D/M> nexthop [vrf ...] ...` | `config route add` の引数順誤り | reference の構文に厳密に従う |

bind 系の暗黙挙動:

- `config interface vrf bind` は対象 interface の IP を kernel 側で一度落とします。bind 後に `ip add` し直す
- VRF 削除は配下 interface を全て unbind してから。残っていると `VRF still has interfaces bound` 系の警告

## 関連ページ

- [CLI: config vrf](../../reference/cli/config-vrf.md)
- [CLI: config route](../../reference/cli/config-route.md)
- [CONFIG_DB: VRF](../../reference/config-db/vrf.md)
- [CONFIG_DB: INTERFACE](../../reference/config-db/interface.md)
- [CONFIG_DB: LOOPBACK_INTERFACE](../../reference/config-db/loopback-interface.md)
- [CONFIG_DB: STATIC_ROUTE](../../reference/config-db/static-route.md)
- [CONFIG_DB: FG_NHG](../../reference/config-db/fg-nhg.md)
- [YANG: sonic-vrf](../../reference/yang/sonic-vrf.md)
- [YANG: sonic-interface](../../reference/yang/sonic-interface.md)
- [YANG: sonic-static-route](../../reference/yang/sonic-static-route.md)
- [YANG: sonic-route-common](../../reference/yang/sonic-route-common.md)

<!-- glossary-links-injected: 3643cd287eaf -->
