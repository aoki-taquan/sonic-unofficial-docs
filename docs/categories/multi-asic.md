---
title: Multi-ASIC / VOQ chassis 関連
area: categories
verification: meta
last_verified: 2026-05-10
---

# Multi-ASIC / VOQ chassis 関連

## 概要

Multi-ASIC、VOQ chassis、namespace、fabric / line card / supervisor、chassis DB を横断して追う入口です。

主要キーワード: `Multi-ASIC`, `VOQ`, `chassis`, `namespace`, `fabric`, `line card`, `supervisor`

## 関連ページ

- [VoQ アーキテクチャの分散転送（FSI/SSI と Chassis DB / redis_chassis）](../acl-qos/distributed-forwarding-in-a-virtual-output-queue-voq-architecture.md) (area: `acl-qos`, verification: `code-verified`)
- [VOQ カウンタ集約（chassis supervisor からの aggregate 表示）](../internals/aggregate-voq-counters-in-sonic.md) (area: `internals`, verification: `code-verified`)
- [Multi-ASIC 名前空間の Redis（database_global.json と SonicDBConfig）](../internals/support-redis-databases-in-multiple-namespaces.md) (area: `internals`, verification: `code-verified`)
- [SONiC on Multi-ASIC platforms（namespace / per-asic Redis / sonic-net）](../platform/1-sonic-on-multi-asic-platforms.md) (area: `platform`, verification: `code-verified`)
- [Chassis Line Card 自動プロビジョニング（sonic-provisiond / provision_module）](../platform/automatic-module-provisioning-for-chassis.md) (area: `platform`, verification: `code-verified`)
- [multi-ASIC 用 Golden Config 単一 JSON フォーマット（localhost / asic0 / asic1 ...）](../platform/db-design-for-multi-asic-scenarios.md) (area: `platform`, verification: `code-verified`)
- [VoQ Chassis での Everflow ミラー（recycle port 経由の rewrite）](../platform/everflow-support-on-voq-chassis.md) (area: `platform`, verification: `hld-only`)
- [VOQ シャーシの Fabric ポート（fabric ASIC 管理 / link monitoring）](../platform/fabric-port-support-on-sonic.md) (area: `platform`, verification: `code-verified`)
- [新 Platform API（sonic_platform / Chassis / PSU/Fan/Sfp の Python クラス階層）](../platform/global-platform-specific-psuutil-class-instance.md) (area: `platform`, verification: `code-verified`)
- [Multi-ASIC Single JSON Configuration（Golden Config に namespace layer）](../platform/multi-asic-single-json-configuration-design.md) (area: `platform`, verification: `code-verified`)
- [VOQ シャシでの recirculation port サポート（Inb / Rec ポートロール）](../platform/recirculation-port-support-on-voq-chassis.md) (area: `platform`, verification: `code-verified`)
- [単一 ASIC VoQ 固定システム（chassisdb.conf による is_voq_chassis 分岐）](../platform/single-asic-voq-fixed-system-sonic.md) (area: `platform`, verification: `code-verified`)
- [VoQ SONiC（distributed VoQ chassis / system-port / fabric）](../platform/voq-sonic.md) (area: `platform`, verification: `code-verified`)
- [VoQ シャーシでの BGP 構成（iBGP フルメッシュ + addpath / multipath-relax）](../routing/bgp-setup-for-voq-chassis.md) (area: `routing`, verification: `code-verified`)
- [Reliable TSA（VoQ Chassis 全体での TSA を CHASSIS_APP_DB で同期）](../routing/reliable-tsa.md) (area: `routing`, verification: `code-verified`)
- [分散 VOQ シャシでの LAG（SYSTEM_LAG_TABLE と system_lag_id）](../switching/lag-on-distributed-voq-system.md) (area: `switching`, verification: `hld-only`)
- [Multi-ASIC warm reboot（namespace 横断の協調 shutdown / boot）](../system/multi-asic-warm-reboot.md) (area: `system`, verification: `code-verified`)
- [PMON の Multi-ASIC 対応（global DB と per-ASIC namespace の役割分担）](../system/platform-monitor-design-for-multi-asic-platforms.md) (area: `system`, verification: `code-verified`)
- [シャーシサブシステムにおける Platform Monitor 要件（Mandatory + Future）](../system/platform-monitor-requirement-for-chassis-subsystem.md) (area: `system`, verification: `code-verified`)
- [Entity MIB / Entity Sensor MIB 拡張（chassis 階層化と sensor / fan / PSU 追加）](../system/sonic-entity-mib-and-entity-sensor-mib-extension.md) (area: `system`, verification: `code-verified`)

## 関連カテゴリ

- [Warm-Reboot / Fast-Reboot 関連](reboot.md)
- [BGP / EVPN 関連](bgp-evpn.md)
- [MIB / SNMP 関連](mib-snmp.md)
- [Container / Build system 関連](container-build.md)
