---
title: DASH と SmartSwitch
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/categories/dash.md
  - docs/categories/smartswitch.md
  - docs/overlay/sonic-dash-hld.md
  - docs/overlay/dash-sonic-kvm.md
  - docs/overlay/smartswitch-eni-based-forwarding.md
  - docs/architecture/smart-switch-database-design.md
  - docs/architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md
  - docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md
  - docs/acl-qos/dash-acl-tags.md
  - docs/system/smart-switch-ip-address-assignment.md
  - docs/management/smart-switch-gnmi-feedback-design-omit-in-toc.md
  - docs/platform/smartswitch-pmon-high-level-design.md
  - docs/system/smart-switch-reboot-high-level-design.md
  - docs/platform/smartswitch-dpu-graceful-shutdown.md
  - docs/system/independent-dpu-upgrade.md
  - docs/management/gnoi-hld-for-system-apis.md
  - docs/management/gnoi-hld-for-os-apis.md
---

# DASH と SmartSwitch

この章は、SONiC で「NPU スイッチに DPU をぶら下げ、その上で DASH オーバーレイを処理する」SmartSwitch 構成を読み解くための入口です。

DASH 系と SmartSwitch 系の既存 HLD は、NPU 側 / DPU 側 / HA / 管理経路にまたがって分散しています。ここでは「NPU と DPU はどう役割を分けているのか」「コントローラから入れた設定はどの DB を通って DPU に届くのか」「HA フェイルオーバーや DPU の reboot / upgrade はどの daemon が動かすのか」という運用者・設計者の質問順に並べ直します。

## この章で答える質問

- DASH、DPU、SmartSwitch、ENI Based Forwarding はそれぞれ何を指しているのか。
- NPU 側 Redis と DPU 側 overlay Redis はどう分かれ、どう同期するのか。
- ENI ベース転送と DASH ACL タグはどの ACL レイヤに入るのか。
- SmartSwitch HA（HAMgrD）と DPU の reboot / upgrade / graceful shutdown はどの順序で動くのか。
- gNMI フィードバックと gNOI 系 API は SmartSwitch でどこに位置付けられるのか。

## 読み進め方

1. [概念](concept.md): DASH / DPU / SmartSwitch / ENI / HA の用語と位置付け。
2. [内部構造](internals.md): NPU-DPU DB アーキテクチャ、ENI ベース転送、DASH ACL タグ。
3. [設定](setup.md): DPU IP 割当、gNMI フィードバック、DASH KVM での検証。
4. [運用](operations.md): HA フェイルオーバー、PMON、reboot / shutdown / upgrade。
5. [発展トピック](advanced.md): gNOI 系との関係、Multi-ASIC / VOQ との境界、管理章への橋渡し。

## 関連ページ

- [DASH 関連](../../categories/dash.md)
- [SmartSwitch 関連](../../categories/smartswitch.md)
- [SONiC-DASH アーキテクチャ概観](../../overlay/sonic-dash-hld.md)
- [Smart Switch のデータベース構成](../../architecture/smart-switch-database-design.md)
