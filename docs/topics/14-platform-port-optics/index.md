---
title: Platform / Port / Optics / PHY
description: Platform / Port / Optics / PHY — この章は、SONiC の「物理層に近い面」を 1 つの読み口に束ねる入口です。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources: []
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
  - show platform
  - show interfaces
  - config interface
  - config platform firmware
  - show interfaces transceiver
  - config acl
  - config interface breakout
  config_db:
  - PORT
  - BREAKOUT_CFG
  - DEVICE_METADATA
  - ACL_TABLE
  - ACL_RULE
  - PORTCHANNEL
  - BUFFER_PG
  yang:
  - sonic-port
  - sonic-cable-length
  - sonic-crm
  - sonic-snmp
  - sonic-xcvrd-log
  - sonic-portchannel
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

| ページ | 行数 | 状態 | verification | 主目的 |
|---|---|---|---|---|
| concept | 173 | ✅ 完成 | meta | 概念・位置付け |
| architecture | 63 | ⚠️ プレースホルダ | code-verified | アーキテクチャ・データフロー |
| setup | 319 | ✅ 完成 | code-verified | セットアップ手順 |
| operations | 260 | ✅ 完成 | meta | 運用・デバッグ |
| internals | 150 | ✅ 完成 | meta | 内部実装 |
| advanced | 103 | ✅ 完成 | meta | 発展トピック |

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
- [FEC FLR 概念（FLR / CER / interleaving / observed vs predicted）](../../platform/fec-flr-support-in-sonic-concepts.md)
- [FEC FLR 制限事項と HLD との乖離（CLI 未取り込み / ハードコード値）](../../platform/fec-flr-support-in-sonic-limitations.md)
- [FEC FLR 設定・運用（counterpoll / show interfaces counters fec-stats / portstat -f）](../../platform/fec-flr-support-in-sonic-operations.md)
- [新 Platform API（sonic_platform / Chassis / PSU/Fan/Sfp の Python クラス階層）](../../platform/global-platform-specific-psuutil-class-instance.md)
- [FEC FLR 内部実装（port_flr.lua / FlexCounterOrch / SAI counter mapping）](../../platform/fec-flr-support-in-sonic-internals.md)
- [ICMP Hardware Offload（DualToR link prober の NPU 化）](../../platform/icmp-hardware-offload.md)

**関連トラブルシュート 5 件**

- [CONFIG_DB の永続化が失敗する](../../reference/runbooks/config-db-persistence-failure.md)
- [minigraph 適用後に reload が完了しない / 起動が固まる](../../reference/runbooks/minigraph-reload-stuck.md)
- [Multi-ASIC で namespace 間通信できない](../../reference/runbooks/multi-asic-namespace.md)
- [counter が更新されない (FLEX_COUNTER)](../../reference/runbooks/flex-counter-stuck.md)
- [PINS gRPC (P4Runtime) が応答しない](../../reference/runbooks/pins-grpc-unresponsive.md)

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
