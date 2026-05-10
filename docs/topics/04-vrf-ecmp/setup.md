---
title: VRF と Static Route の設定
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
---

# VRF と Static Route の設定

設定を読む入口は 3 つあります。作業者が打つのは CLI、永続設定として残るのは CONFIG_DB、外部管理システムが検証する型は YANG です。このページでは VRF 付き L3 設定の最小単位をその順で整理します。

## 最小構成の流れ

1. VRF を作る。
2. L3 interface を VRF に bind する。
3. interface に IP address を付ける。
4. static route を VRF 付きで追加する。
5. 必要なら nexthop VRF、blackhole、FG ECMP を加える。

CLI の詳細な引数は [config vrf](../../reference/cli/config-vrf.md) と [config route](../../reference/cli/config-route.md) を参照してください。

## CLI 例

```console
sudo config vrf add Vrf_blue
sudo config interface vrf bind Ethernet0 Vrf_blue
sudo config interface ip add Ethernet0 192.0.2.1/31
sudo config route add prefix vrf Vrf_blue 198.51.100.0/24 nexthop 192.0.2.0 dev Ethernet0
```

この例では、`Vrf_blue` を作り、`Ethernet0` をその VRF の L3 interface にし、VRF 内の static route を追加します。実際の構文と制約は SONiC バージョンや interface 種別で変わり得るため、CLI reference 側を正にしてください。

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

Loopback を使う場合は `LOOPBACK_INTERFACE` を読みます。BGP の router-id や per-VRF loopback を扱うときは [LOOPBACK_INTERFACE テーブル](../../reference/config-db/loopback-interface.md) が入口です。

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

