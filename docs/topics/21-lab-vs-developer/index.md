---
title: Lab / Virtual SONiC / Developer Entry
description: Lab / Virtual SONiC / Developer Entry — この章は、SONiC を「実機を触らずに、あるいは小さな lab で」評価・開発・検証するための入口を整理する章です。
area: topics
verification: meta
page_kind: chapter-index
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
related:
  cli:
  - config acl
  - config bgp
  - config vlan
  - config vrf
  - config vxlan
  - show acl
  - show bgp
  config_db:
  - VRF
  - ACL_RULE
  - ACL_TABLE
  - BGP_NEIGHBOR
  - PFC_WD
  - VXLAN_TUNNEL
  - BGP_GLOBALS
  yang:
  - sonic-bgp-global
  - sonic-vrf
  - sonic-bgp-neighbor
  - sonic-pfc-priority-priority-group-map
  - sonic-pfc-priority-queue-map
  - sonic-vxlan
  - sonic-buffer-pool
---

# Lab / Virtual SONiC / Developer Entry

この章は、[SONiC](../../reference/glossary.md#term-sonic) を「実機を触らずに、あるいは小さな lab で」評価・開発・検証するための入口を整理する章です。SONiC-[VS](../../reference/glossary.md#term-vs)、GNS3 VM、ALViS / KNE、[DASH](../../reference/glossary.md#term-dash) SONiC KVM、PTF ベースのテスト計画は、それぞれ別の [HLD](../../reference/glossary.md#term-hld) として書かれているため、ここでは目的別にどれを使うかを並べ直します。

仮想環境は実機の代替ではなく、設計と CI を回すための再現可能な箱です。[ASIC](../../reference/glossary.md#term-asic)・optics・PHY・thermal・PSU といった物理依存は仮想化されないため、virtual lab で何が確認でき、何が確認できないのかをはじめに区別しておきます。

## この章で答える質問

- SONiC-VS、GNS3、ALViS / KNE はどの目的で使い分けるか。
- evaluator / beginner / developer / operator guide は読み物章にどう接続するか。
- DIP=SIP PTF、[VRF](../../reference/glossary.md#term-vrf) VS test、test plan 系ページはどこから参照するか。
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

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| advanced | 115 | ✅ 完成 | meta | 発展トピック |
| architecture | 39 | ⚠️ プレースホルダ | meta | アーキテクチャ・データフロー |
| concept | 141 | ✅ 完成 | meta | 概念・位置付け |
| internals | 130 | ✅ 完成 | meta | 内部実装 |
| operations | 209 | ✅ 完成 | meta | 運用・デバッグ |
| setup | 277 | ✅ 完成 | meta | セットアップ手順 |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要: 概念](concept.md)
- [アーキテクチャ](architecture.md)
- [設定](setup.md)
- [運用](operations.md)
- [内部実装](internals.md)
- [発展トピック](advanced.md)

**関連する HLD 7 件**

- [Bulk Counter（sai_bulk_object_get_stats / chunk size）](../../architecture/sonic-bulk-counter-design.md)
- [SWSS docker warm restart（state restore / consistency / sync up）](../../system/sonic-swss-docker-warm-restart.md)
- [Dataplane Telemetry（DTel / INT / Postcard / Drop / Queue Report）](../../system/dataplane-telemetry-in-sonic.md)
- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../../system/sonic-libsairedis-api-idempotence-support.md)
- [FRR 用 sysctl チューニングのデフォルト](../../system/useful-sysctl-settings.md)
- [Error Handling Framework（ERROR_DB / SAI 失敗の app への伝搬）](../../architecture/error-handling-framework-in-sonic.md)
- [SONiC BMC Platform Management & Monitoring（pmon ↔ BMC 連携）](../../system/sonic-bmc-platform-management-monitoring.md)

**関連トラブルシュート 5 件**

- [APPL_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [PFC で帯域が出ない / Buffer overflow](../../reference/runbooks/pfc-bandwidth.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [Warm Reboot が失敗 / 通信断が長引く](../../reference/runbooks/warm-reboot-failure.md)

<!-- /next-reads -->

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

<!-- glossary-links-injected: 9fb3fca99a59 -->
