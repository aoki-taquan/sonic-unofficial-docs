---
title: 内部実装
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 内部実装

仮想 lab とテストフレームワークの内部構造で、章本文を読むときに前提として知っておくと便利な点を集めます。SAI VS や PTF の中身を全部書き下すのではなく、HLD ページへの導線を整理する位置付けです。

## SAI VS が何を代替するか

SONiC-VS の中核は SAI VS で、syncd の SAI backend を Linux netdev / bridge へ写すレイヤです。

- L2 forwarding は Linux bridge
- L3 forwarding は Linux route table
- VLAN は Linux VLAN device
- ACL / counter は SAI 側で限定的にサポート

このため「CONFIG_DB と orchagent の整合性」「sairedis の object 生成」までは VS で完全に検証できますが、ASIC capability に依存する path は VS の境界を越えます。具体的なソースとビルド手順は [SONiC-VS のビルドと libvirt 起動手順](../../architecture/steps-to-bring-up-sonic-vs.md) を参照します。

## DIP=SIP PTF validation

PTF（Packet Test Framework）は、SONiC 機能の data plane 挙動を「スイッチを物理 PTF host で囲んで検証する」ためのフレームワークです。その派生として、特定パケットパターン（DIP=SIP のような martian / loopback 様パケット）が punt / drop されるかを検証する設計があります。

設計の枠組みは [DIP=SIP PTF validation HLD](../../architecture/dip-sip-ptf-validation-high-level-design.md) にあります。読みどころは「PTF host と SONiC の topology」「期待 packet action と CoPP / ACL 経路の関連」「結果判定の自動化」です。ACL / CoPP の章本文（[ACL / CoPP / Mirror / Packet Action](../07-acl-copp-mirror/index.md)）と組で読むと文脈が掴めます。

## VS test と Ansible test の役割分担

VRF を例にすると test plan は 2 系統あります。

- [VRF VS test plan](../../routing/vrf-vs-test-plan.md): SONiC-VS の中で完結する unit / scenario test。CONFIG_DB 投入、FRR の挙動、kernel route の最終形まで。
- [VRF Ansible test plan](../../routing/vrf-feature-ansible-test-plan-omit-in-toc.md): Ansible で複数ノードを駆動する system test。実機・PTF を含む構成での検証を想定。

VS test は「実機なしで何が確認できるか」の上限を、Ansible test は「実機で必要な確認の集合」を示します。機能 HLD を読むときに、両方の test plan を見ると検証境界が分かります。

## Alpine / KNE の内部差分

ALViS / KNE は容量・依存・起動時間の都合で、Debian ベースの SONiC とは構成が異なります。Pod に同居する docker、init 順序、SAI VS の組み込み方の差は [Alpine 仮想 SONiC](../../architecture/alpine-high-level-design.md) で読みます。CI で多数ノードを並べる動機（topology テスト、KNE 連携、リソース効率）も同 HLD に整理されています。
