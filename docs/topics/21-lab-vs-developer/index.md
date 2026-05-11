---
title: Lab / Virtual SONiC / Developer Entry
description: "Lab / Virtual SONiC / Developer Entry — この章は、SONiC を「実機を触らずに、あるいは小さな lab で」評価・開発・検証するための入口を整理する章です。"
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/guides/beginner.md
  - docs/guides/developer.md
  - docs/guides/evaluator.md
  - docs/guides/operator.md
  - docs/architecture/steps-to-bring-up-sonic-vs.md
  - docs/architecture/sonic-on-gns3-vm.md
  - docs/architecture/alpine-high-level-design.md
  - docs/overlay/dash-sonic-kvm.md
  - docs/architecture/1-udev-rules-design-for-terminal-server.md
  - docs/management/sonic-console-switch.md
  - docs/management/portable-console-device-design.md
  - docs/routing/vrf-vs-test-plan.md
  - docs/routing/vrf-feature-ansible-test-plan-omit-in-toc.md
  - docs/acl-qos/acl-ingress-egress-test-plan.md
  - docs/acl-qos/everflow-test-plan.md
  - docs/system/dataplane-telemetry-test-plan.md
  - docs/platform/thermal-control-test-plan.md
  - docs/architecture/dip-sip-ptf-validation-high-level-design.md
keywords:
  - Lab
  - Virtual SONiC
  - VS
  - developer
  - sonic-mgmt
  - vlab
  - testbed
  - 開発環境
  - GNS3
---

# Lab / Virtual SONiC / Developer Entry

この章は、SONiC を「実機を触らずに、あるいは小さな lab で」評価・開発・検証するための入口を整理する章です。SONiC-VS、GNS3 VM、ALViS / KNE、DASH SONiC KVM、PTF ベースのテスト計画は、それぞれ別の HLD として書かれているため、ここでは目的別にどれを使うかを並べ直します。

仮想環境は実機の代替ではなく、設計と CI を回すための再現可能な箱です。ASIC・optics・PHY・thermal・PSU といった物理依存は仮想化されないため、virtual lab で何が確認でき、何が確認できないのかをはじめに区別しておきます。

## この章で答える質問

- SONiC-VS、GNS3、ALViS / KNE はどの目的で使い分けるか。
- evaluator / beginner / developer / operator guide は読み物章にどう接続するか。
- DIP=SIP PTF、VRF VS test、test plan 系ページはどこから参照するか。
- virtual lab で再現しづらい platform / optics / ASIC 依存はどう明示するか。
- 物理 lab に必要な console / terminal server / udev はどこで読むか。

## 読み進め方

1. [概念](concept.md): persona guide、virtual / physical lab の境界、何が再現できて何ができないか。
2. [アーキテクチャ](architecture.md): SONiC-VS、GNS3 VM、ALViS / KNE、DASH SONiC KVM の比較。
3. [設定](setup.md): lab bring-up の前提、console / terminal server / udev の位置付け。
4. [運用](operations.md): VS / PTF / Ansible test plan をどう読むか。
5. [内部実装](internals.md): DIP=SIP PTF などテストフレームワークの設計ポイント。
6. [発展トピック](advanced.md): DASH KVM、ALViS / KNE、CI 連携と、virtual で再現しづらい依存。

## 関連ページ

- [初学者向けガイド](../../guides/beginner.md)
- [開発者向けガイド](../../guides/developer.md)
- [評価者向けガイド](../../guides/evaluator.md)
- [運用者向けガイド](../../guides/operator.md)

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)

**派生で読むべき章**

- [Build / Packaging / Application Extension](../19-build-packaging/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)

**補完的に読む章**

- [P4 / PINS / Programmable Pipeline](../18-p4-pins/index.md)
- [リファレンス横断索引](../22-reference-index/index.md)

