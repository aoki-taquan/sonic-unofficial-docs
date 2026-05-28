---
title: アーキテクチャ
description: アーキテクチャ — 仮想 SONiC には用途別に複数の系統があります。「どれが本物の SONiC か」ではなく、「どこを再現したいか」で選びます。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - show platform
  - config vnet
  - show techsupport
  - show version
  - show acl
  - config acl
  config_db: []
  yang: []
  _no_related_config_db: true
  _no_related_yang: true
---

# アーキテクチャ

仮想 [SONiC](../../reference/glossary.md#term-sonic) には用途別に複数の系統があります。「どれが本物の SONiC か」ではなく、「どこを再現したいか」で選びます。

## 仮想環境の比較

| 環境 | 何を再現するか | 主な用途 | 入口 |
| --- | --- | --- | --- |
| SONiC-[VS](../../reference/glossary.md#term-vs) (libvirt / KVM) | 単体 SONiC NOS（[SAI](../../reference/glossary.md#term-sai) VS + 全 docker） | [HLD](../../reference/glossary.md#term-hld) 検証、PR 自動テスト、CLI / [CONFIG_DB](../../reference/glossary.md#term-config_db) 動作確認 | [SONiC-VS のビルドと libvirt 起動手順](../../architecture/steps-to-bring-up-sonic-vs.md) |
| GNS3 + sonic-vs.img | SONiC-VS を GNS3 トポロジ内で配線 | 評価者・初学者の手元学習、ネットワーク図と組み合わせた構成検証 | [GNS3 VM 上での SONiC 動作](../../architecture/sonic-on-gns3-vm.md) |
| ALViS / KNE (Alpine 仮想 SONiC) | Kubernetes ネイティブな軽量 SONiC | CI で多数ノードを並べる、KNE トポロジ統合 | [Alpine 仮想 SONiC](../../architecture/alpine-high-level-design.md) |
| [DASH](../../reference/glossary.md#term-dash) SONiC KVM | [DPU](../../reference/glossary.md#term-dpu) / DASH appliance を BMv2 で代替 | DASH HLD・[ENI](../../reference/glossary.md#term-eni) ルール検証 | [DASH SONiC KVM](../../overlay/dash-sonic-kvm.md) |

それぞれ前提が異なります。SONiC-VS と GNS3 は同じ `sonic-vs.img` を使う関係で、SONiC-VS で動くものは GNS3 でも動きます。ALViS / KNE は Alpine ベースで軽量化されており、機能セットが SONiC-VS と完全には一致しないため、対応する HLD で対象範囲を確認します。

## SONiC-VS の構造

SONiC-VS は実機イメージから [ASIC](../../reference/glossary.md#term-asic)・platform 部品を VS 化したもので、内部は実機と同じ docker 群（swss、[syncd](../../reference/glossary.md#term-syncd)、bgp、[teamd](../../reference/glossary.md#term-teamd-teamsyncd-teammgrd)、snmp、telemetry など）が動きます。違いは syncd の SAI backend が SAI VS で、SAI 操作が Linux netdev / bridge に変換される点です。

bring-up 手順、libvirt 定義、image の作成方法は [SONiC-VS のビルドと libvirt 起動手順](../../architecture/steps-to-bring-up-sonic-vs.md) を読みます。CONFIG_DB の投入、minigraph、CLI 操作は実機と同じ流れになります。

## GNS3 / KNE / KVM の位置付け

- GNS3 は SONiC-VS を「GNS3 のトポロジ」に並べて触るための wrapper です。Qemu テンプレートの作り方が中心の議題で、SONiC 自体の挙動は SONiC-VS と同じです。
- ALViS / KNE は Kubernetes 上で多数ノードを並べる前提の設計です。KNE 連携・Alpine 化・Pod ごとの SONiC 構成は HLD を読むのが早いです。
- DASH SONiC KVM は DASH の DPU 検証用で、データプレーンを BMv2 が担います。DASH の HLD と組で読みます。

## 物理 lab の機材側

物理 lab を組むと、SONiC 本体以外に console / terminal server / udev のような周辺要素が出てきます。

- [udev rules design for terminal server](../../architecture/1-udev-rules-design-for-terminal-server.md): 物理 console を `/dev/ttyXXX` に固定するための udev 設計。
- [SONiC console switch](../../management/sonic-console-switch.md): SONiC スイッチ自体を console concentrator にする設計。
- [Portable console device design](../../management/portable-console-device-design.md): 携帯型 console 機材としての位置付け。

これらは仮想 lab では出てこないため、実機投入や DC への持ち込みフェーズでだけ読み返します。

<!-- glossary-links-injected: 9fb3fca99a59 -->
