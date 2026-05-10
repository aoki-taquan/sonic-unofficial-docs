---
title: L3 基盤と VRF
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/routing/sonic-vrf-support-design-spec-draft.md
  - docs/routing/static-ip-route-configuration.md
  - docs/routing/ipv6-link-local-enhancements.md
  - docs/routing/sonic-management-vrf-design-document-201911-release.md
---

# L3 基盤と VRF

SONiC の L3 を読むときは、最初に route ではなく **VRF と interface** を押さえると後続が追いやすくなります。route は必ずどこかの VRF に属し、next hop は到達可能な interface と neighbor 解決に依存し、最終的な ASIC object も VRF と RIF を基準に作られるためです。

## 最初に押さえる順番

| 順番 | 見るもの | 何を決めるか |
|------|----------|--------------|
| 1 | VRF | 経路表を分ける単位。default VRF、データ VRF、management VRF を区別する。 |
| 2 | L3 interface | Ethernet / VLAN / PortChannel / Loopback をどの VRF に所属させるか。 |
| 3 | IP address / link-local | RIF と connected route、BGP unnumbered や RFC 5549 の next-hop 解決に関係する。 |
| 4 | static / dynamic route | FRR が RIB を持ち、SONiC 側へ FPM で流す。 |
| 5 | next hop / NHG | 単一 next hop、ECMP、WCMP、FG ECMP などの差がここで出る。 |

VRF の設計詳細は [VRF サポート](../../routing/sonic-vrf-support-design-spec-draft.md) が入口です。static route の CONFIG_DB から FRR への経路は [Static IP Route 設定](../../routing/static-ip-route-configuration.md) を参照してください。

## VRF は Linux と ASIC の両方に現れる

SONiC の VRF は、Linux 上では VRF master device として、ASIC 側では SAI Virtual Router として扱われます。`vrfmgrd` は `CONFIG_DB.VRF` から Linux VRF を作り、`VRFOrch` は `APP_DB.VRF_TABLE` 側を受けて SAI Virtual Router を作ります。interface は `intfmgrd` / `IntfsOrch` を通って Linux と ASIC の両方に反映されます。

重要なのは、VRF は単なる CLI 上の名前ではなく、FRR、kernel、orchagent、SAI の共通キーになることです。non-default VRF の経路を調べるときは、常に「その route はどの VRF の route か」「next hop は同じ VRF か、`nexthop-vrf` で別 VRF を参照しているか」を確認します。

## Management VRF はデータ VRF と用途が違う

management VRF は front panel port の転送ではなく、`eth0` を使う管理面トラフィックを分離するための VRF です。`config vrf add mgmt` は通常のデータ VRF と違い、`MGMT_VRF_CONFIG` や management interface 側の処理に関係します。

古い management VRF HLD には cgroup を使う起動ラッパー方式が出てきますが、現行ページでは iproute2 の VRF master device 方式へ寄っている点が注記されています。詳細は [Management VRF 設計](../../routing/sonic-management-vrf-design-document-201911-release.md) を確認してください。

## IPv6 link-local は next hop のキーに interface を含める

IPv6 link-local の next hop はアドレスだけでは一意になりません。同じ `fe80::...` が複数 interface 上に存在し得るため、SONiC の next hop key は link-local 利用時に interface alias を含めて扱います。BGP unnumbered や RFC 5549 を読むときは、next hop IP と出力 interface をセットで見ます。

IPv6 link-local-only の設定条件、`fe80::/10` の route-to-CPU、IP2ME の扱いは [IPv6 Link-Local アドレス管理](../../routing/ipv6-link-local-enhancements.md) にまとまっています。

## Static route は CONFIG_DB から FRR へ入る

`config route` は `STATIC_ROUTE` テーブルを書き、FRR の staticd / zebra 側に反映されます。ASIC へ直接 route を書くわけではありません。FRR が RIB を計算し、FPM 経由で `fpmsyncd` が `APPL_DB.ROUTE_TABLE` へ書き、そこから RouteOrch が SAI route object を作ります。

VRF 付き static route では key が `STATIC_ROUTE|<vrf>|<prefix>` になります。ECMP は nexthop / ifname / distance などのカンマ区切りリストで表現され、同じ index の値が 1 つの next hop を構成します。

## 関連ページ

- [VRF サポート](../../routing/sonic-vrf-support-design-spec-draft.md)
- [Static IP Route 設定](../../routing/static-ip-route-configuration.md)
- [IPv6 Link-Local アドレス管理](../../routing/ipv6-link-local-enhancements.md)
- [Management VRF 設計](../../routing/sonic-management-vrf-design-document-201911-release.md)

