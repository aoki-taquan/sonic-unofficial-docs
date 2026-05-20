---
title: Telemetry / SNMP / Observability
description: Telemetry / SNMP / Observability — この章は、SONiC で「いまスイッチが何をしているか」「壊れたとき何が起きたか」を読むための機能群をまとめます。
area: topics
verification: meta
page_kind: chapter-index
last_verified: 2026-05-10
sources:
- docs/system/sonic-logging-system-dumps-arch-spec.md
- docs/system/show-techsupport.md
- docs/internals/dump-utility-for-easy-debugging.md
- docs/system/system-ready-hld.md
- docs/internals/sonic-flexcounter-refactor.md
- docs/internals/sonic-counter-initialization-optimization.md
- docs/system/critical-resource-monitoring.md
- docs/system/critical-resource-monitoring-in-sonic.md
- docs/system/generic-sai-extension-critical-resource-monitoring-crm.md
- docs/reference/config-db/crm.md
- docs/reference/config-db/flex-counter-table.md
- docs/reference/cli/config-snmp.md
- docs/reference/cli/config-sflow.md
- docs/reference/cli/config-syslog.md
- docs/reference/config-db/sflow.md
- docs/reference/config-db/syslog-server.md
- docs/reference/config-db/telemetry.md
- docs/reference/config-db/auto-techsupport.md
- docs/reference/yang/sonic-syslog.md
- docs/reference/cli/show-system-health.md
- docs/reference/cli/show-techsupport.md
- docs/reference/cli/show-platform.md
- docs/system/event-driven-techsupport-invocation-coredump-mgmt.md
- docs/system/dump-sfp-eeprom-page-data-in-show-techsupport-command.md
- docs/system/kdump.md
- docs/system/kdump-remote-ssh.md
- docs/system/dataplane-telemetry-in-sonic.md
- docs/system/dataplane-telemetry-test-plan.md
- docs/architecture/sflow-high-level-design.md
- docs/architecture/sflow-test-plan.md
- docs/system/sonic-entity-mib-and-entity-sensor-mib-extension.md
- docs/system/snmp-migration-from-snmp-yml-to-configdb.md
- docs/system/snmp-transceiver-monitoring-testbed-test-plan.md
- docs/system/process-and-docker-stats-availability-via-telemetry-agent.md
- docs/system/memory-statistics-feature-in-sonic.md
- docs/system/reboot-cause-information-via-telemetry-agent.md
- docs/internals/byte-packet-rates-port-utilization-in-sonic.md
keywords:
- Telemetry
- SNMP
- Observability
- gNMI streaming
- syslog
- counters
- snmpd
- telemetry container
- 監視
related:
  cli:
  - config snmp
  - show techsupport
  - show interfaces
  - show acl
  - show lldp
  - config acl
  - config kdump
  config_db:
  - SNMP
  - SNMP_AGENT_ADDRESS_CONFIG
  - SYSLOG_SERVER
  - CRM
  - LLDP
  - SNMP_COMMUNITY
  - SNMP_USER
  yang:
  - sonic-snmp
  - sonic-crm
  - sonic-lldp
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-copp
  - sonic-syslog
---

# Telemetry / SNMP / Observability

この章は、[SONiC](../../reference/glossary.md#term-sonic) で「いまスイッチが何をしているか」「壊れたとき何が起きたか」を読むための機能群をまとめます。counters、[CRM](../../reference/glossary.md#term-crm)、[SNMP](../../reference/glossary.md#term-snmp)、[gNMI](../../reference/glossary.md#term-gnmi) telemetry、sFlow、DTel、syslog、techsupport、kdump など複数の経路があり、[HLD](../../reference/glossary.md#term-hld) は別ページに散らばっています。ここでは運用者と設計者の質問順に並べ直し、既存ページへの入口にします。

観測手段は「現在値を polling で読む」「変化点を push で受ける」「障害時に dump を取る」の 3 系統に整理できます。SNMP は古典的な polling、gNMI telemetry は push 型 streaming、syslog / event / techsupport は障害発生時の証跡です。この区分けが分かると、どこを設定し、どこを見れば良いかが定まります。

## この章で答える質問

- 状態を見るとき、counter、telemetry、SNMP、techsupport のどれを使い分けるか。
- [FlexCounter](../../reference/glossary.md#term-flexcounter)、CRM、DTel、sFlow、watermark は何が違い、どの粒度で出るか。
- system health、logging、kdump、dump utility は障害調査でどう連携するか。
- SNMP MIB と gNMI telemetry は同じ情報を別経路で出しているのか。
- auto-techsupport と event-driven techsupport は何が変わったのか。

## 読み進め方

1. [概念](concept.md): 観測経路の分類と、各手段が答える質問の違い。
2. [アーキテクチャ](architecture.md): FlexCounter / CRM / telemetry / SNMP のデータ収集経路。
3. [設定](setup.md): SNMP、sFlow、syslog、telemetry、auto-techsupport の最小設定。
4. [運用](operations.md): `show techsupport`、`show system-health`、counter、kdump の調査順。
5. [内部実装](internals.md): [syncd](../../reference/glossary.md#term-syncd) / flex counter group、telemetry agent、SNMP subagent。
6. [発展トピック](advanced.md): DTel、sFlow、Entity MIB、process / memory stats、reboot cause。

## 関連ページ

- [Logging と system dump 仕様](../../system/sonic-logging-system-dumps-arch-spec.md)
- [show techsupport](../../system/show-techsupport.md)
- [Dump utility](../../internals/dump-utility-for-easy-debugging.md)
- [System ready](../../system/system-ready-hld.md)

<!-- chapter-progress -->
## 章構成と進捗

| ページ | 状態 | verification |
|---|---|---|
| concept | ✅ 完成 (140 行) | meta |
| setup | ✅ 完成 (248 行) | meta |
| operations | ✅ 完成 (187 行) | meta |
| internals | ✅ 完成 (129 行) | meta |
| advanced | ✅ 完成 (118 行) | meta |

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

- [SNMP 設定の snmp.yml → CONFIG_DB 移行](../../system/snmp-migration-from-snmp-yml-to-configdb.md)
- [libsairedis API idempotence（warm restart 用 OID キャッシュと duplicate 抑止）](../../system/sonic-libsairedis-api-idempotence-support.md)
- [SNMP TABLE スキーマ提案（SNMP / SNMP_COMMUNITY / SNMP_USER）](../../system/sonic-snmp-table-schema-proposal.md)
- [telemetry dial-out モード（gNMIDialOut.Publish / TELEMETRY_CLIENT）](../../system/sonic-telemetry-in-dial-out-mode-2.md)
- [ASIC 内部温度センサのポーリング（ASIC_SENSORS / ASIC_TEMPERATURE_INFO）](../../system/asic-thermal-monitoring-high-level-design.md)
- [gNMI Master Arbitration（election ID と SetRequest 拡張）](../../management/gnmi-master-arbitration-hld.md)
- [gNSI 設定と運用（gNMI フラグ / YANG / 運用イメージ）](../../management/gnsi-hld-operations.md)

**関連トラブルシュート 5 件**

- [APP_DB → ASIC_DB の反映が遅延・停止する](../../reference/runbooks/appdb-asicdb-sync-lag.md)
- [orchagent が CPU 100% で詰まる](../../reference/runbooks/swss-orchagent-busy-loop.md)
- [show interfaces counters が突然リセットされる](../../reference/runbooks/interface-counters-reset.md)
- [経路は RIB にあるが FIB / ASIC に降りない](../../reference/runbooks/route-not-installed-in-fib.md)
- [SNMP polling が timeout する](../../reference/runbooks/snmp-polling-timeout.md)

<!-- /next-reads -->

<!-- xref-related-chapters -->
## 関連する章

**前提として読むべき章**

- [SONiC 全体像と設定基盤](../01-overview/index.md)
- [SWSS / SAI / Redis 内部実装](../20-swss-sai-redis/index.md)

**派生で読むべき章**

- [gNMI / gNOI / OpenConfig / YANG](../10-gnmi-openconfig/index.md)

**補完的に読む章**

- [Reboot / Upgrade / Lifecycle](../11-reboot/index.md)
- [Platform / Port / Optics / PHY](../14-platform-port-optics/index.md)
- [Security / AAA / FIPS / Hardening](../15-security-aaa/index.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
