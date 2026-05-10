---
title: gNMI / gNOI / OpenConfig 関連
area: categories
verification: meta
last_verified: 2026-05-10
---

# gNMI / gNOI / OpenConfig 関連

## 概要

gNMI、gNOI、OpenConfig、YANG、Management Framework、設定更新 / 検証経路を横断して追う入口です。

主要キーワード: `gNMI`, `gNOI`, `OpenConfig`, `YANG`, `REST`, `Management Framework`

## 関連ページ

- [gNMI Master Arbitration（election ID と SetRequest 拡張）](../management/gnmi-master-arbitration-hld.md) (area: `management`, verification: `discrepancy-found`)
- [gNMI クライアントツールの使い方（gnmi_get / gnmi_set / gnmi_cli）](../management/gnmi-usage.md) (area: `management`, verification: `code-verified`)
- [gNOI File.Remove と FactoryReset.Start（gNMI/UMF + DBUS host service）](../management/gnoi-hld-for-file-and-factory-reset-apis.md) (area: `management`, verification: `code-verified`)
- [gNOI Healthz API（Get / Acknowledge / Artifact + DBUS host service）](../management/gnoi-hld-for-healthz-api.md) (area: `management`, verification: `code-verified`)
- [gNOI OS API（Install / Activate / Verify と sonic-installer 連携）](../management/gnoi-hld-for-os-apis.md) (area: `management`, verification: `code-verified`)
- [gNOI System Reboot / RebootStatus / CancelReboot（reboot method と sanity check）](../management/gnoi-hld-for-system-apis.md) (area: `management`, verification: `code-verified`)
- [JSON Patch ordering（YANG 制約に従う apply-patch のステップ分割）](../management/json-patch-ordering-using-yang-models.md) (area: `management`, verification: `code-verified`)
- [OpenConfig Interfaces YANG（Ethernet 設定の REST/gNMI 対応と sonic-mgmt-common transformer）](../management/openconfig-support-for-ethernet-interfaces.md) (area: `management`, verification: `code-verified`)
- [gNMI Save-On-Set（Set ごとの ConfigDB 永続化）](../management/save-on-set-hld.md) (area: `management`, verification: `hld-only`)
- [SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id）](../management/smart-switch-gnmi-feedback-design-omit-in-toc.md) (area: `management`, verification: `hld-only`)
- [SONiC CLI 自動生成ツール（YANG → click plugin 自動生成）](../management/sonic-cli-auto-generation-tool.md) (area: `management`, verification: `code-verified`)
- [YANG モデルによる ConfigDB 更新検証（GCU + ConfigDBConnector デコレータ）](../management/sonic-config-update-validation-via-yang.md) (area: `management`, verification: `code-verified`)
- [SONiC gNMI Server インタフェース設計（CONFIG_DB / SONiC YANG / Generic Config Updater 連携）](../management/sonic-gnmi-server-interface-design.md) (area: `management`, verification: `code-verified`)
- [SONiC Management Framework（REST / gNMI / Translib / Transformer）](../management/sonic-management-framework.md) (area: `management`, verification: `code-verified`)
- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP / vtysh / redis / apply-patch）](../management/sonic-nos-configuration-methods.md) (area: `management`, verification: `code-verified`)
- [SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang）](../management/sonic-yang-model-guidelines.md) (area: `management`, verification: `discrepancy-found`)
- [液冷漏洩検出（LiquidCoolingBase + thermalctld + system-health gNMI イベント）](../platform/liquid-cooling-leakage-detection-in-sonic.md) (area: `platform`, verification: `discrepancy-found`)
- [Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT）](../platform/smartswitch-dpu-graceful-shutdown.md) (area: `platform`, verification: `discrepancy-found`)
- [sonic-bgp-global YANG](../reference/yang/sonic-bgp-global.md) (area: `reference`, verification: `code-verified`)
- [sonic-bgp-neighbor YANG](../reference/yang/sonic-bgp-neighbor.md) (area: `reference`, verification: `code-verified`)
- [sonic-bgp-peergroup YANG](../reference/yang/sonic-bgp-peergroup.md) (area: `reference`, verification: `code-verified`)
- [sonic-buffer-pg YANG](../reference/yang/sonic-buffer-pg.md) (area: `reference`, verification: `code-verified`)
- [sonic-buffer-pool YANG](../reference/yang/sonic-buffer-pool.md) (area: `reference`, verification: `code-verified`)
- [sonic-buffer-profile YANG](../reference/yang/sonic-buffer-profile.md) (area: `reference`, verification: `code-verified`)
- [sonic-buffer-queue YANG](../reference/yang/sonic-buffer-queue.md) (area: `reference`, verification: `code-verified`)
- [sonic-copp YANG](../reference/yang/sonic-copp.md) (area: `reference`, verification: `code-verified`)
- [sonic-device_metadata YANG](../reference/yang/sonic-device_metadata.md) (area: `reference`, verification: `code-verified`)
- [sonic-dscp-tc-map YANG](../reference/yang/sonic-dscp-tc-map.md) (area: `reference`, verification: `code-verified`)
- [sonic-feature YANG](../reference/yang/sonic-feature.md) (area: `reference`, verification: `code-verified`)
- [sonic-interface YANG](../reference/yang/sonic-interface.md) (area: `reference`, verification: `code-verified`)
- [sonic-loopback-interface YANG](../reference/yang/sonic-loopback-interface.md) (area: `reference`, verification: `code-verified`)
- [sonic-mclag YANG](../reference/yang/sonic-mclag.md) (area: `reference`, verification: `code-verified`)
- [sonic-mirror-session YANG](../reference/yang/sonic-mirror-session.md) (area: `reference`, verification: `code-verified`)
- [sonic-ntp YANG](../reference/yang/sonic-ntp.md) (area: `reference`, verification: `code-verified`)
- [sonic-pfcwd YANG](../reference/yang/sonic-pfcwd.md) (area: `reference`, verification: `code-verified`)
- [sonic-port YANG](../reference/yang/sonic-port.md) (area: `reference`, verification: `code-verified`)
- [sonic-portchannel YANG](../reference/yang/sonic-portchannel.md) (area: `reference`, verification: `code-verified`)
- [sonic-queue YANG](../reference/yang/sonic-queue.md) (area: `reference`, verification: `code-verified`)
- [sonic-route-common YANG](../reference/yang/sonic-route-common.md) (area: `reference`, verification: `code-verified`)
- [sonic-route-map YANG](../reference/yang/sonic-route-map.md) (area: `reference`, verification: `code-verified`)
- [sonic-scheduler YANG](../reference/yang/sonic-scheduler.md) (area: `reference`, verification: `code-verified`)
- [sonic-syslog YANG](../reference/yang/sonic-syslog.md) (area: `reference`, verification: `code-verified`)
- [sonic-system-aaa YANG](../reference/yang/sonic-system-aaa.md) (area: `reference`, verification: `code-verified`)
- [sonic-tc-queue-map YANG](../reference/yang/sonic-tc-queue-map.md) (area: `reference`, verification: `code-verified`)
- [sonic-vlan YANG](../reference/yang/sonic-vlan.md) (area: `reference`, verification: `code-verified`)
- [sonic-vrf YANG](../reference/yang/sonic-vrf.md) (area: `reference`, verification: `code-verified`)
- [sonic-vxlan YANG](../reference/yang/sonic-vxlan.md) (area: `reference`, verification: `code-verified`)
- [gNMI Subscription for YANG Data（ON_CHANGE / SAMPLE / TARGET_DEFINED）](../routing/gnmi-subscription-for-yang-data.md) (area: `routing`, verification: `code-verified`)
- [FRR-BGP Unified Mgmt Framework（frrcfgd / OpenConfig BGP）](../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) (area: `routing`, verification: `code-verified`)
- [VLAN インタフェースの OpenConfig YANG 対応（REST / gNMI）](../switching/add-support-for-vlan-interface-using-openconfig-yang.md) (area: `switching`, verification: `code-verified`)
- [PortChannel (LAG) の OpenConfig YANG サポート（REST / gNMI）](../switching/openconfig-support-for-portchannel-aggregate-interface.md) (area: `switching`, verification: `code-verified`)
- [Wake-on-LAN（wol CLI と SonicWolService gNOI）](../switching/wake-on-lan-in-sonic.md) (area: `switching`, verification: `discrepancy-found`)
- [Smart Switch: DPU 独立アップグレード（gNOI 経路）](../system/independent-dpu-upgrade.md) (area: `system`, verification: `code-verified`)
- [Management Framework 経由の show techsupport（REST/gNMI/IETF since 形式）](../system/show-techsupport.md) (area: `system`, verification: `code-verified`)
- [SmartSwitch reboot 順序（NPU → 各 DPU の gNOI HALT → PCI detach → 個別 reboot）](../system/smart-switch-reboot-high-level-design.md) (area: `system`, verification: `code-verified`)
- [telemetry dial-out モード（gNMIDialOut.Publish / TELEMETRY_CLIENT）](../system/sonic-telemetry-in-dial-out-mode-2.md) (area: `system`, verification: `code-verified`)
- [gNMI dial-out モード（dialout_client_cli + gNMIDialOut.Publish）](../system/sonic-telemetry-in-dial-out-mode.md) (area: `system`, verification: `code-verified`)

## 関連カテゴリ

- [SmartSwitch 関連](smartswitch.md)
- [BGP / EVPN 関連](bgp-evpn.md)
- [MIB / SNMP 関連](mib-snmp.md)
- [Container / Build system 関連](container-build.md)
