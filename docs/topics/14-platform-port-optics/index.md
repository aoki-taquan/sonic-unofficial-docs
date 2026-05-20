---
title: Platform / Port / Optics / PHY
description: Platform / Port / Optics / PHY — この章は、SONiC の「物理層に近い面」を 1 つの読み口に束ねる入口です。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources:
- docs/platform/global-platform-specific-psuutil-class-instance.md
- docs/architecture/sonic-port-configuration-refactor-design.md
- docs/architecture/port-profile-init-hld.md
- docs/system/sonic-dynamic-port-breakout-feature-high-level-design.md
- docs/architecture/sonic-port-auto-negotiation-design.md
- docs/architecture/sonic-port-link-training-design.md
- docs/architecture/sonic-port-auto-fec-design.md
- docs/platform/sonic-port-fec-ber.md
- docs/platform/fec-flr-support-in-sonic.md
- docs/platform/sonic-fast-link-up.md
- docs/platform/sonic-sfp-refactoring.md
- docs/management/enhancement-of-cmis-module-management.md
- docs/platform/cmis-and-c-cmis-support-for-zr.md
- docs/platform/custom-si-settings-for-cmis-modules.md
- docs/system/transceiver-and-sensor-monitoring-hld.md
- docs/platform/sonic-thermal-control-design.md
- docs/platform/thermal-control-test-plan.md
- docs/platform/liquid-cooling-leakage-detection-in-sonic.md
- docs/platform/sonic-psu-daemon-design.md
- docs/architecture/ssdhealth-design.md
- docs/system/sonic-storage-monitoring-daemon-design.md
- docs/platform/pcieinfo-design.md
- docs/system/sonic-pcie-monitoring-services-hld.md
- docs/platform/media-based-port-settings-in-sonic.md
- docs/platform/sonic-dynamic-gearbox-tuning-design-plan.md
- docs/platform/sonic-npu-mdio-access-support-and-gbsyncd-docker-enhancement-hld.md
- docs/platform/enhanced-lpo-debug-registers-hld.md
- docs/platform/s3ip-sysfs-specification.md
- docs/architecture/s3ip-sysfs-specification-and-s3ip-sysfs-framework-hld.md
- docs/platform/support-bmc-flows-in-sonic.md
- docs/system/sonic-bmc-platform-management-monitoring.md
- docs/platform/1-6t-support-in-sonic.md
- docs/platform/sonic-port-naming-convention-change.md
- docs/acl-qos/enhancements-to-add-or-del-ports-dynamically.md
- docs/platform/sonic-fw-utility.md
- docs/platform/platform-capability-file-enhancement.md
- docs/reference/cli/config-interface.md
- docs/reference/cli/config-platform-firmware.md
- docs/reference/cli/show-platform.md
- docs/reference/config-db/port.md
- docs/reference/yang/sonic-port.md
keywords:
- Platform
- Port
- Optics
- PHY
- transceiver
- xcvrd
- pmon
- port breakout
- SFP
- QSFP
related:
  cli:
  - config qos
  - show acl
  - show platform
  - config acl
  - config snmp
  - show interfaces
  - config interface
  config_db:
  - PORT
  - ACL_RULE
  - ACL_TABLE
  - SNMP
  - SNMP_AGENT_ADDRESS_CONFIG
  - BREAKOUT_CFG
  - DEVICE_METADATA
  yang:
  - sonic-snmp
  - sonic-port
  - sonic-lldp
  - sonic-portchannel
  - sonic-vlan
  - sonic-vlan-sub-interface
  - sonic-cable-length
---

# Platform / Port / Optics / PHY

この章は、[SONiC](../../reference/glossary.md#term-sonic) の「物理層に近い面」を 1 つの読み口に束ねる入口です。port、optics、FEC、auto-neg、Gearbox、MDIO、thermal、PSU、BMC、PCIe、SSD は別 [HLD](../../reference/glossary.md#term-hld) に分かれていますが、運用者から見ると「ポートが上がる／光モジュールが認識される／装置全体が健全である」という 1 本のシナリオに連なります。

既存ページは platform / architecture / system / management の各 area に散らばっています。ここでは HLD の境界ではなく、port lifecycle と platform health monitoring の 2 軸に並べ直し、詳細は元ページへ誘導します。

## この章で答える質問

- `PORT` テーブル、`port_config.ini`、dynamic breakout、auto-neg、FEC はどう関係するのか。
- CMIS / C-CMIS / SFP EEPROM / Gearbox / MDIO はそれぞれどの層の話か。
- thermal、PSU、BMC、PCIe、storage health は platform 章でどう束ねるのか。
- port add / delete、breakout、speed 変更は buffer / [QoS](../../reference/glossary.md#term-qos) / [ACL](../../reference/glossary.md#term-acl) 章とどこで噛み合うのか。
- 装置メトリクスは pmon / S3IP / Redfish / [SNMP](../../reference/glossary.md#term-snmp) のどの経路で出るのか。

## 読み進め方

1. [概要](concept.md): platform abstraction と port lifecycle の境界。
2. [アーキテクチャ](architecture.md): port bring-up、breakout、auto-neg、link training、FEC の流れ。
3. [設定](setup.md): interface / platform firmware / capability ファイル。
4. [運用](operations.md): optics、CMIS、SFP EEPROM、thermal、PSU、SSD、PCIe の確認順序。
5. [内部実装](internals.md): Gearbox、MDIO、media settings、S3IP sysfs、BMC / Redfish。
6. [発展トピック](advanced.md): 1.6T、port naming、dynamic add / delete。

## 関連章

- 設定の反映先は [L2 / VLAN / LAG](../06-l2-vlan-lag/index.md) の前提になります。QoS / Buffer 章は別途参照してください。
- ACL / mirror の bind 先としても port が前提なので、[ACL / CoPP / Mirror](../07-acl-copp-mirror/index.md) と相互参照してください。

## 関連ページ

- [PORT テーブル](../../reference/config-db/port.md)
- [sonic-port YANG](../../reference/yang/sonic-port.md)
- [show platform](../../reference/cli/show-platform.md)
- [config interface](../../reference/cli/config-interface.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 状態 | verification |
|---|---|---|
| concept | ✅ 完成 (170 行) | meta |
| setup | ✅ 完成 (211 行) | meta |
| operations | ✅ 完成 (260 行) | meta |
| internals | ✅ 完成 (144 行) | meta |
| advanced | ✅ 完成 (103 行) | meta |

<!-- /chapter-progress -->

<!-- next-reads -->
## 次に読むべき記事

**この章を読み進める順**

- [概要](concept.md)
- [アーキテクチャ](architecture.md)
- [設定](setup.md)
- [運用](operations.md)
- [内部実装](internals.md)
- [発展トピック](advanced.md)

**関連する HLD 7 件**

- [sfputil read-eeprom / write-eeprom（ページ + オフセット指定で SFP/QSFP EEPROM 操作）](../../platform/sfputil-add-the-ability-to-read-write-any-byte-from-eerpom-both-by-page-and-offset.md)
- [SONiC ポート命名規則の変更案（et[sX]pY[abcd]）](../../platform/sonic-port-naming-convention-change.md)
- [VOQ シャーシの Fabric ポート（fabric ASIC 管理 / link monitoring）](../../platform/fabric-port-support-on-sonic.md)
- [FEC FLR 設定・運用（counterpoll / show interfaces counters fec-stats / portstat -f）](../../platform/fec-flr-support-in-sonic-operations.md)
- [新 Platform API（sonic_platform / Chassis / PSU/Fan/Sfp の Python クラス階層）](../../platform/global-platform-specific-psuutil-class-instance.md)
- [sfputil read-eeprom / write-eeprom（page+offset 単位の生 EEPROM 読み書き）](../../platform/sfputil-add-the-ability-to-read-write-any-byte-from-eerpom-both-by-page-and-offs.md)
- [FEC FLR 概念（FLR / CER / interleaving / observed vs predicted）](../../platform/fec-flr-support-in-sonic-concepts.md)

**関連トラブルシュート 5 件**

- [CONFIG_DB の永続化が失敗する](../../reference/runbooks/config-db-persistence-failure.md)
- [PINS gRPC (P4Runtime) が応答しない](../../reference/runbooks/pins-grpc-unresponsive.md)
- [minigraph 適用後に reload が完了しない / 起動が固まる](../../reference/runbooks/minigraph-reload-stuck.md)
- [Multi-ASIC で namespace 間通信できない](../../reference/runbooks/multi-asic-namespace.md)
- [counter が更新されない (FLEX_COUNTER)](../../reference/runbooks/flex-counter-stuck.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)

**派生で読むべき章**

- [L2 / VLAN / LAG / MC-LAG](../06-l2-vlan-lag/index.md)
- [QoS / Buffer / PFC / Watermark](../08-qos-buffer/index.md)

**補完的に読む章**

- [Telemetry / SNMP / Observability](../09-telemetry-snmp/index.md)
- [Reboot / Upgrade / Lifecycle](../11-reboot/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
