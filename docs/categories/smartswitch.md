---
title: SmartSwitch 関連
area: categories
verification: meta
last_verified: 2026-05-10
---

# SmartSwitch 関連

## 概要

SmartSwitch の NPU / DPU 分担、HA、DPU 管理、gNMI / gNOI 経路、PMON、reboot / upgrade を横断して追う入口です。

主要キーワード: `SmartSwitch`, `DPU`, `NPU`, `HA`, `gNMI`, `gNOI`

## 関連ページ

- [Smart Switch のデータベース構成（NPU 上の DPU overlay DB）](../architecture/smart-switch-database-design.md) (area: `architecture`, verification: `code-verified`)
- [SmartSwitch HA - DPU-Scope-DPU-Driven 構成](../architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup.md) (area: `architecture`, verification: `code-verified`)
- [SmartSwitch HA: HAMgrD（NPU 側 actor 分割と DPU 連携）](../architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md) (area: `architecture`, verification: `discrepancy-found`)
- [SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id）](../management/smart-switch-gnmi-feedback-design-omit-in-toc.md) (area: `management`, verification: `hld-only`)
- [SmartSwitch ENI Based Forwarding（DashEniFwdOrch / ENI_REDIRECT ACL）](../overlay/smartswitch-eni-based-forwarding.md) (area: `overlay`, verification: `code-verified`)
- [Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT）](../platform/smartswitch-dpu-graceful-shutdown.md) (area: `platform`, verification: `discrepancy-found`)
- [SmartSwitch PMON（NPU 側 pmon と DPU 連携の境界）](../platform/smartswitch-pmon-high-level-design.md) (area: `platform`, verification: `code-verified`)
- [Smart Switch: DPU 独立アップグレード（gNOI 経路）](../system/independent-dpu-upgrade.md) (area: `system`, verification: `code-verified`)
- [Smart Switch DPU IP アドレス割当（midplane bridge / DHCP server）](../system/smart-switch-ip-address-assignment.md) (area: `system`, verification: `code-verified`)
- [SmartSwitch reboot 順序（NPU → 各 DPU の gNOI HALT → PCI detach → 個別 reboot）](../system/smart-switch-reboot-high-level-design.md) (area: `system`, verification: `code-verified`)

## 関連カテゴリ

- [DASH 関連](dash.md)
- [gNMI / gNOI / OpenConfig 関連](gnmi-openconfig.md)
- [Warm-Reboot / Fast-Reboot 関連](reboot.md)
- [Container / Build system 関連](container-build.md)
