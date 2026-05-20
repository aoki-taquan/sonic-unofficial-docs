---
title: SmartSwitch 関連
description: SmartSwitch 関連 — このカテゴリでは、SmartSwitch を横断するページを NPU 側設計（CONFIG_DB / APPL_DB
  の DPU overlay と HA actor）・DPU 管理（IP 割当・gNMI フィードバック・独立アップグレード・graceful shutdown）・EN…
area: categories
verification: meta
last_verified: 2026-05-10
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# SmartSwitch 関連

## 概要

**[SmartSwitch](../reference/glossary.md#term-smartswitch)** は、従来の単一 [NPU](../reference/glossary.md#term-npu) 型 [SONiC](../reference/glossary.md#term-sonic) スイッチに **複数の [DPU](../reference/glossary.md#term-dpu)**（[SmartNIC](../reference/glossary.md#term-smartnic) / IPU）を内蔵し、L2/L3 スイッチング機能を NPU 側、ステートフルな [NAT](../reference/glossary.md#term-nat) / [ACL](../reference/glossary.md#term-acl) / フロー処理を DPU 側に分担させるアーキテクチャです。Microsoft が提案した [DASH](../reference/glossary.md#term-dash) の上位プラットフォームとして整備され、`HAMgrD` を中心とした HA、DPU ごとの [gNOI](../reference/glossary.md#term-gnoi) 経路、`midplane` ブリッジによる DPU IP 管理など、独自のサブシステムが多数あります。

このカテゴリでは、SmartSwitch を横断するページを **NPU 側設計**（[CONFIG_DB](../reference/glossary.md#term-config_db) / [APPL_DB](../reference/glossary.md#term-appl_db) の DPU overlay と HA actor）・**DPU 管理**（IP 割当・[gNMI](../reference/glossary.md#term-gnmi) フィードバック・独立アップグレード・graceful shutdown）・**[ENI](../reference/glossary.md#term-eni) Forwarding**（DASH ベースの DPU 振り分け）・**reboot 順序**（NPU と DPU の協調 reboot）に分類しています。[HLD](../reference/glossary.md#term-hld) は数多くあるものの、DPU 側ソフトウェアは別リポ管理が多く、SmartSwitch ページだけで完結する設計ではありません。

SmartSwitch を学ぶ際は、まず NPU と DPU の境界（どこが [Redis](../reference/glossary.md#term-redis) ベース DB で、どこが DBUS / gNMI / gNOI 経由なのか）を押さえると全体が見えやすくなります。HA は DPU-Scope-DPU-Driven 構成が現行マスターブランチの主流で、`HAMgrD` の actor 分割が中心です。

主要キーワード: `SmartSwitch`, `DPU`, `NPU`, `HA`, `gNMI`, `gNOI`, `HAMgrD`, `midplane`

## 関連ページ

### architecture（NPU 側設計 / HA）

- [Smart Switch のデータベース構成（NPU 上の DPU overlay DB）](../architecture/smart-switch-database-design.md) (area: `architecture`, verification: `code-verified`) — DPU APPL_DB / [STATE_DB](../reference/glossary.md#term-state_db) の overlay 構造
- [SmartSwitch HA - DPU-Scope-DPU-Driven 構成](../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md) (area: `architecture`, verification: `code-verified`) — 現行マスターの HA 主流
- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) (area: `architecture`, verification: `discrepancy-found`)

### overlay（ENI ベース転送）

- [SmartSwitch ENI Based Forwarding（DashEniFwdOrch / ENI_REDIRECT ACL）](../overlay/smartswitch-eni-based-forwarding.md) (area: `overlay`, verification: `code-verified`) — DPU 振り分け ACL

### management（gNMI 経路）

- [SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id）](../management/smart-switch-gnmi-feedback-design-omit-in-toc.md) (area: `management`, verification: `discrepancy-found`)

### platform（PMON / graceful shutdown）

- [SmartSwitch PMON（NPU 側 pmon と DPU 連携の境界）](../platform/smartswitch-pmon-high-level-design.md) (area: `platform`, verification: `code-verified`)
- [Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT）](../platform/smartswitch-dpu-graceful-shutdown.md) (area: `platform`, verification: `discrepancy-found`)

### system（DPU IP / upgrade / reboot）

- [Smart Switch DPU IP アドレス割当（midplane bridge / DHCP server）](../system/smart-switch-ip-address-assignment.md) (area: `system`, verification: `code-verified`)
- [Smart Switch: DPU 独立アップグレード（gNOI 経路）](../system/independent-dpu-upgrade.md) (area: `system`, verification: `code-verified`)
- [SmartSwitch reboot 順序（NPU → 各 DPU の gNOI HALT → PCI detach → 個別 reboot）](../system/smart-switch-reboot-high-level-design.md) (area: `system`, verification: `code-verified`)

## 典型的な読み進め方

1. **NPU と DPU の境界** → `smart-switch-database-design.md` で DB 構造と APPL_DB overlay を把握
2. **DPU 接続** → `smart-switch-ip-address-assignment.md` で midplane bridge と DHCP の流れ
3. **ENI ベース転送** → `smartswitch-eni-based-forwarding.md` で DPU 振り分けの ACL 構造
4. **HA** → `smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md` → `smartswitch-high-availability-manager-daemon-hamgrd-design.md`
5. **運用**（reboot / upgrade / shutdown） → `smart-switch-reboot-high-level-design.md` → `independent-dpu-upgrade.md` → `smartswitch-dpu-graceful-shutdown.md`
6. **PMON** → `smartswitch-pmon-high-level-design.md`

## 関連 Topics 章

- [Topics 13: DASH / SmartSwitch](../topics/13-dash-smartswitch/index.md) — SmartSwitch を段階的に学ぶ章
- [Topics 10: gNMI / OpenConfig](../topics/10-gnmi-openconfig/index.md) — DPU 制御に使う gNOI の前提
- [Topics 11: Reboot / Upgrade](../topics/11-reboot/index.md) — SmartSwitch reboot 順序の前提

## verification ステータス注意点

- **discrepancy-found**: `smart-switch-gnmi-feedback-design-omit-in-toc.md`, `smartswitch-high-availability-manager-daemon-hamgrd-design.md`, `smartswitch-dpu-graceful-shutdown.md` — 実コードと HLD で記述差異あり。各ページの末尾参照

## 関連カテゴリ

- [DASH 関連](dash.md)
- [gNMI / gNOI / OpenConfig 関連](gnmi-openconfig.md)
- [Warm-Reboot / Fast-Reboot 関連](reboot.md)
- [Container / Build system 関連](container-build.md)

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: DASH と SmartSwitch](../topics/13-dash-smartswitch/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 8ba32e5aa69d -->
