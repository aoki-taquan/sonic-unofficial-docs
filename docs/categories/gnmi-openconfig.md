---
title: gNMI / gNOI / OpenConfig 関連
description: gNMI / gNOI / OpenConfig 関連 — SONiC の管理プレーンは Management Framework（REST
  / gNMI / Translib / Transformer）と sonic-gnmi（gNMI Server）を中心に、CONFIG_DB と SONiC
  YANG / O…
area: categories
verification: meta
last_verified: 2026-05-10
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# gNMI / gNOI / OpenConfig 関連

## 概要

[SONiC](../reference/glossary.md#term-sonic) の管理プレーンは **Management Framework**（REST / [gNMI](../reference/glossary.md#term-gnmi) / Translib / Transformer）と **sonic-gnmi**（gNMI Server）を中心に、[CONFIG_DB](../reference/glossary.md#term-config_db) と SONiC [YANG](../reference/glossary.md#term-yang) / OpenConfig YANG の双方を扱う構造になっています。`telemetryd` が gNMI Subscribe を提供し、`gnmi-native` モード（SONiC YANG）と `gnmi-translib` モード（OpenConfig 経由）が共存します。設定経路では **Generic Config Updater ([GCU](../reference/glossary.md#term-gcu))** が JSON Patch を YANG 制約に従って段階的に apply する仕組みを担当します。

[gNOI](../reference/glossary.md#term-gnoi) は gRPC ベースの **運用 API**（OS install / System reboot / File / FactoryReset / Healthz / Wake-on-LAN など）で、DBUS 経由でホスト側サービスを叩く構造になっています。SONiC 内では `system / OS / file / factory_reset / healthz / wol` などのサービス実装が `sonic-gnmi` 配下にあり、[SmartSwitch](../reference/glossary.md#term-smartswitch) では [DPU](../reference/glossary.md#term-dpu) 単位の gNOI を持ちます。

このカテゴリは gNMI / gNOI / OpenConfig / YANG・Management Framework に関わるページを area 横断でまとめます。本ドキュメントで最も関連ページが多い（57 件）カテゴリで、YANG リファレンスが大半を占めるのは設計通りです。

主要キーワード: `gNMI`, `gNOI`, `OpenConfig`, `YANG`, `REST`, `Management Framework`, `telemetry`, `GCU`, `Translib`

## 関連ページ

### management（HLD 本体・最重要）

- [SONiC Management Framework（REST / gNMI / Translib / Transformer）](../management/sonic-management-framework.md) (area: `management`, verification: `code-verified`) — まずこれ
- [SONiC NOS の設定手段一覧（CLI / sonic-cfggen / config_db.json / RESTCONF / gNMI / ZTP / vtysh / redis / apply-patch）](../management/sonic-nos-configuration-methods.md) (area: `management`, verification: `code-verified`)
- [SONiC gNMI Server インタフェース設計（CONFIG_DB / SONiC YANG / Generic Config Updater 連携）](../management/sonic-gnmi-server-interface-design.md) (area: `management`, verification: `code-verified`)
- [gNMI クライアントツールの使い方（gnmi_get / gnmi_set / gnmi_cli）](../management/gnmi-usage.md) (area: `management`, verification: `code-verified`)
- [gNMI Master Arbitration（election ID と SetRequest 拡張）](../management/gnmi-master-arbitration-hld.md) (area: `management`, verification: `discrepancy-found`)
- [gNMI Save-On-Set（Set ごとの ConfigDB 永続化）](../management/save-on-set-hld.md) (area: `management`, verification: `code-verified`)
- [SmartSwitch gNMI フィードバック（DPU APPL_STATE_DB と version_id）](../management/smart-switch-gnmi-feedback-design-omit-in-toc.md) (area: `management`, verification: `discrepancy-found`)
- [YANG モデルによる ConfigDB 更新検証（GCU + ConfigDBConnector デコレータ）](../management/sonic-config-update-validation-via-yang.md) (area: `management`, verification: `code-verified`)
- [JSON Patch ordering（YANG 制約に従う apply-patch のステップ分割）](../management/json-patch-ordering-using-yang-models.md) (area: `management`, verification: `code-verified`)
- [SONiC CLI 自動生成ツール（YANG → click plugin 自動生成）](../management/sonic-cli-auto-generation-tool.md) (area: `management`, verification: `code-verified`)
- [SONiC YANG モデル記述ガイドライン（ABNF.json → sonic-*.yang）](../management/sonic-yang-model-guidelines.md) (area: `management`, verification: `discrepancy-found`)
- [OpenConfig Interfaces YANG（Ethernet 設定の REST/gNMI 対応と sonic-mgmt-common transformer）](../management/openconfig-support-for-ethernet-interfaces.md) (area: `management`, verification: `code-verified`)

### management（gNOI 系）

- [gNOI System Reboot / RebootStatus / CancelReboot（reboot method と sanity check）](../management/gnoi-hld-for-system-apis.md) (area: `management`, verification: `code-verified`)
- [gNOI OS API（Install / Activate / Verify と sonic-installer 連携）](../management/gnoi-hld-for-os-apis.md) (area: `management`, verification: `code-verified`)
- [gNOI Healthz API（Get / Acknowledge / Artifact + DBUS host service）](../management/gnoi-hld-for-healthz-api.md) (area: `management`, verification: `code-verified`)
- [gNOI File.Remove と FactoryReset.Start（gNMI/UMF + DBUS host service）](../management/gnoi-hld-for-file-and-factory-reset-apis.md) (area: `management`, verification: `code-verified`)

### platform / system（gNMI / gNOI 経路）

- [液冷漏洩検出（LiquidCoolingBase + thermalctld + system-health gNMI イベント）](../platform/liquid-cooling-leakage-detection-in-sonic.md) (area: `platform`, verification: `discrepancy-found`)
- [Smart Switch DPU Graceful Shutdown（gnoi_reboot_daemon HALT）](../platform/smartswitch-dpu-graceful-shutdown.md) (area: `platform`, verification: `discrepancy-found`)
- [Management Framework 経由の show techsupport（REST/gNMI/IETF since 形式）](../system/show-techsupport.md) (area: `system`, verification: `code-verified`)
- [telemetry dial-out モード（gNMIDialOut.Publish / TELEMETRY_CLIENT）](../system/sonic-telemetry-in-dial-out-mode-2.md) (area: `system`, verification: `code-verified`)
- [gNMI dial-out モード（dialout_client_cli + gNMIDialOut.Publish）](../system/sonic-telemetry-in-dial-out-mode.md) (area: `system`, verification: `code-verified`)
- [Smart Switch: DPU 独立アップグレード（gNOI 経路）](../system/independent-dpu-upgrade.md) (area: `system`, verification: `code-verified`)
- [SmartSwitch reboot 順序（NPU → 各 DPU の gNOI HALT → PCI detach → 個別 reboot）](../system/smart-switch-reboot-high-level-design.md) (area: `system`, verification: `code-verified`)

### routing / switching（OpenConfig 対応）

- [gNMI Subscription for YANG Data（ON_CHANGE / SAMPLE / TARGET_DEFINED）](../routing/gnmi-subscription-for-yang-data.md) (area: `routing`, verification: `code-verified`)
- [FRR-BGP Unified Mgmt Framework（frrcfgd / OpenConfig BGP）](../routing/sonic-frr-bgp-extended-unified-configuration-management-framework.md) (area: `routing`, verification: `code-verified`)
- [VLAN インタフェースの OpenConfig YANG 対応（REST / gNMI）](../switching/add-support-for-vlan-interface-using-openconfig-yang.md) (area: `switching`, verification: `code-verified`)
- [PortChannel (LAG) の OpenConfig YANG サポート（REST / gNMI）](../switching/openconfig-support-for-portchannel-aggregate-interface.md) (area: `switching`, verification: `code-verified`)
- [Wake-on-LAN（wol CLI と SonicWolService gNOI）](../switching/wake-on-lan-in-sonic.md) (area: `switching`, verification: `discrepancy-found`)

### reference - YANG モジュール

- [sonic-bgp-global YANG](../reference/yang/sonic-bgp-global.md)
- [sonic-bgp-neighbor YANG](../reference/yang/sonic-bgp-neighbor.md)
- [sonic-bgp-peergroup YANG](../reference/yang/sonic-bgp-peergroup.md)
- [sonic-buffer-pg YANG](../reference/yang/sonic-buffer-pg.md)
- [sonic-buffer-pool YANG](../reference/yang/sonic-buffer-pool.md)
- [sonic-buffer-profile YANG](../reference/yang/sonic-buffer-profile.md)
- [sonic-buffer-queue YANG](../reference/yang/sonic-buffer-queue.md)
- [sonic-copp YANG](../reference/yang/sonic-copp.md)
- [sonic-device_metadata YANG](../reference/yang/sonic-device_metadata.md)
- [sonic-dscp-tc-map YANG](../reference/yang/sonic-dscp-tc-map.md)
- [sonic-feature YANG](../reference/yang/sonic-feature.md)
- [sonic-interface YANG](../reference/yang/sonic-interface.md)
- [sonic-loopback-interface YANG](../reference/yang/sonic-loopback-interface.md)
- [sonic-mclag YANG](../reference/yang/sonic-mclag.md)
- [sonic-mirror-session YANG](../reference/yang/sonic-mirror-session.md)
- [sonic-ntp YANG](../reference/yang/sonic-ntp.md)
- [sonic-pfcwd YANG](../reference/yang/sonic-pfcwd.md)
- [sonic-port YANG](../reference/yang/sonic-port.md)
- [sonic-portchannel YANG](../reference/yang/sonic-portchannel.md)
- [sonic-queue YANG](../reference/yang/sonic-queue.md)
- [sonic-route-common YANG](../reference/yang/sonic-route-common.md)
- [sonic-route-map YANG](../reference/yang/sonic-route-map.md)
- [sonic-scheduler YANG](../reference/yang/sonic-scheduler.md)
- [sonic-syslog YANG](../reference/yang/sonic-syslog.md)
- [sonic-system-aaa YANG](../reference/yang/sonic-system-aaa.md)
- [sonic-tc-queue-map YANG](../reference/yang/sonic-tc-queue-map.md)
- [sonic-vlan YANG](../reference/yang/sonic-vlan.md)
- [sonic-vrf YANG](../reference/yang/sonic-vrf.md)
- [sonic-vxlan YANG](../reference/yang/sonic-vxlan.md)

YANG リファレンスは全件 `code-verified`。詳細は [reference/yang インデックス](../reference/yang/index.md) を参照。

## 典型的な読み進め方

1. **管理プレーン全体像** → `sonic-management-framework.md` → `sonic-nos-configuration-methods.md` で REST / gNMI / Translib / [vtysh](../reference/glossary.md#term-vtysh) / apply-patch の選択肢を俯瞰
2. **gNMI Server** → `sonic-gnmi-server-interface-design.md` → `gnmi-usage.md` で実機操作
3. **設定検証** → `sonic-config-update-validation-via-yang.md` → `json-patch-ordering-using-yang-models.md` で GCU / apply-patch
4. **YANG モデル** → `sonic-yang-model-guidelines.md` → `openconfig-support-for-ethernet-interfaces.md` で SONiC YANG と OpenConfig 双方
5. **gNOI** → `gnoi-hld-for-system-apis.md` → `gnoi-hld-for-os-apis.md` → `gnoi-hld-for-healthz-api.md` → `gnoi-hld-for-file-and-factory-reset-apis.md`
6. **Telemetry** → `gnmi-subscription-for-yang-data.md` → `sonic-telemetry-in-dial-out-mode.md`
7. **個別機能の OpenConfig 対応** → `add-support-for-vlan-interface-using-openconfig-yang.md` → `openconfig-support-for-portchannel-aggregate-interface.md`
8. **YANG リファレンス** → 個別モジュールページ

## 関連 Topics 章

- [Topics 10: gNMI / OpenConfig](../topics/10-gnmi-openconfig/index.md) — gNMI / gNOI / gNSI / OpenConfig / YANG を段階的に学ぶ章（`yang-reference` 章もあり）
- [Topics 09: Telemetry / SNMP](../topics/09-telemetry-snmp/index.md) — telemetry 経路の前提
- [Topics 22: Reference Index](../topics/22-reference-index/index.md) — YANG リファレンスのインデックス

## verification ステータス注意点

- **discrepancy-found**: `gnmi-master-arbitration-hld.md`, `sonic-yang-model-guidelines.md`, `smart-switch-gnmi-feedback-design-omit-in-toc.md`, `liquid-cooling-leakage-detection-in-sonic.md`, `smartswitch-dpu-graceful-shutdown.md`, `wake-on-lan-in-sonic.md` — [HLD](../reference/glossary.md#term-hld) と実装に差異あり
- 上記以外はすべて `code-verified`。本ドキュメント全体で `hld-only` のページは 0 件（裏取り完了済み）

## 関連カテゴリ

- [SmartSwitch 関連](smartswitch.md)
- [BGP / EVPN 関連](bgp-evpn.md)
- [MIB / SNMP 関連](mib-snmp.md)
- [Container / Build system 関連](container-build.md)

<!-- glossary-links-injected: 7ac8e66e1af3 -->
