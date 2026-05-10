---
title: Overlay 発展トピック
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/routing/evpn-vxlan-multihoming.md
  - docs/overlay/smartswitch-eni-based-forwarding.md
  - docs/overlay/nvgre-tunnel-in-sonic.md
  - docs/platform/subnet-decapsulation-with-sonic.md
  - docs/overlay/vnet-local-endpoint-forwarding.md
---

# Overlay 発展トピック

ここでは、基本の VXLAN / VNET / EVPN の延長に見えるが、別の前提や別の orch を持つ機能を整理します。設計検討では同じ overlay として並びますが、運用手順や実装成熟度は同一ではありません。

## EVPN multihoming

EVPN multihoming は、host を複数 leaf に接続し、BGP-EVPN の Type-1 / Type-4、ESI、DF election、split-horizon で重複転送とループを避ける機能です。通常の EVPN VXLAN が Type-2 / Type-5 で MAC/IP/prefix を配るのに対し、multihoming は Ethernet Segment の制御を追加します。

既存ページでは、`EVPN_ETHERNET_SEGMENT` や EVPN-MH 用 CLI / YANG が現行 master で確認できない可能性も示されています。利用判断では FRR、SAI、ASIC、SONiC schema の対応状況を個別に確認してください。

## DASH / SmartSwitch 連携

SmartSwitch ENI based forwarding は、ENI と DPU の対応を NPU 側に理解させ、ACL の `REDIRECT` で local nexthop または tunnel nexthop へ送る設計です。VXLAN tunnel nexthop 表記を ACL action が解釈するため、VNET/VXLAN の tunnel nexthop 管理と接点があります。

VNET local endpoint forwarding は、DPU が local にいる場合に tunnel route ではなく通常 ECMP route を使う最適化です。failover 中の transient state では、tunnel decap 後のパケットを local nexthop へ redirect する高優先 ACL が使われます。

## NVGRE

NVGRE は VXLAN と同じく overlay encapsulation ですが、GRE と VSID を使います。SONiC の NVGRE HLD は decap 側を中心にしており、`NVGRE_TUNNEL` / `NVGRE_TUNNEL_MAP` と `nvgreorch` は VXLAN 系 orch とは別です。

VXLAN/VNET の章で一緒に読む価値があるのは、tenant ID を tunnel map で inner L2 domain に戻す考え方、ASIC tunnel resource、inner packet hashing の課題が似ているためです。EVPN control plane と一体に扱うべき機能ではありません。

## Subnet decap

Subnet decap は VXLAN overlay ではなく、VLAN subnet 宛の IPinIP decap を自動生成して Netscan probe を処理する platform 機能です。`TUNNEL_DECAP_TABLE` や tunnel term という部品は共通ですが、tenant overlay を作るものではありません。

この機能を VXLAN のトラブルシュートに混ぜると判断を誤ります。見るべきポイントは `SUBNET_DECAP`、自動生成される `IPINIP_SUBNET` / `IPINIP_V6_SUBNET`、warm reboot 後の APPL_DB 再投入です。

## 関連ページ

- [EVPN VXLAN Multihoming](../../routing/evpn-vxlan-multihoming.md)
- [SmartSwitch ENI Based Forwarding](../../overlay/smartswitch-eni-based-forwarding.md)
- [VNET の Local Endpoint Forwarding](../../overlay/vnet-local-endpoint-forwarding.md)
- [NVGRE トンネル](../../overlay/nvgre-tunnel-in-sonic.md)
- [VLAN Subnet Decap](../../platform/subnet-decapsulation-with-sonic.md)
