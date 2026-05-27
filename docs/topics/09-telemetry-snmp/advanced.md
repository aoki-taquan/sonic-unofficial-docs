---
title: 発展トピック
description: 発展トピック — このページは、基本の observability 経路（CLI / counter / SNMP / gNMI / techsupport）から外れる、専門観測機能と最近の
  telemetry 拡張をまとめます。設計判断に直結する局面以外は深追い不要です。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/system/dataplane-telemetry-in-sonic.md
- docs/system/dataplane-telemetry-test-plan.md
- docs/architecture/sflow-high-level-design.md
- docs/architecture/sflow-test-plan.md
- docs/system/sonic-entity-mib-and-entity-sensor-mib-extension.md
- docs/system/snmp-transceiver-monitoring-testbed-test-plan.md
- docs/system/process-and-docker-stats-availability-via-telemetry-agent.md
- docs/system/memory-statistics-feature-in-sonic.md
- docs/system/reboot-cause-information-via-telemetry-agent.md
related:
  cli:
  - config snmp
  config_db:
  - SNMP
  - SNMP_AGENT_ADDRESS_CONFIG
  - SNMP_COMMUNITY
  - SNMP_USER
  - SNMP_TRAP_CONFIG
  - MGMT_VRF_CONFIG
  yang:
  - sonic-snmp
---

# 発展トピック

このページは、基本の observability 経路（CLI / counter / [SNMP](../../reference/glossary.md#term-snmp) / [gNMI](../../reference/glossary.md#term-gnmi) / techsupport）から外れる、専門観測機能と最近の telemetry 拡張をまとめます。設計判断に直結する局面以外は深追い不要です。

## Dataplane Telemetry (DTel)

DTel は In-band Network Telemetry を [SONiC](../../reference/glossary.md#term-sonic) スイッチがエクスポートする機能です。[ASIC](../../reference/glossary.md#term-asic) が flow ごとにスイッチ内部情報（latency、queue 状態、drop reason 等）を packet header に書き込み、[INT](../../reference/glossary.md#term-int) report として外部 collector に送出します。SONiC は collector / report session / watchlist を [CONFIG_DB](../../reference/glossary.md#term-config_db) と APP_DB に持ち、`dtelorch` が [SAI](../../reference/glossary.md#term-sai) DTEL object に変換します。

DTel は ASIC capability への依存が大きく、すべての platform で同じ event type / report mode が出るわけではありません。test plan ページは、SAI DTEL object と SONiC table の対応、report format の検証観点を整理しています。

## sFlow

sFlow は古典的なサンプリング + counter polling 型 telemetry です。hsflowd が `psample` 経由で kernel から packet sample を取り、`SFLOW_COLLECTOR` 宛に sFlow datagram を送ります。Counter polling も hsflowd が担当し、`SFLOW|global` テーブルの `polling_interval` フィールドで interval を制御します。

sFlow と DTel の住み分けは、sFlow が「サンプリングされた粗い flow telemetry」、DTel が「flow ごとの精密 in-band telemetry」と覚えると整理できます。test plan ページは collector / agent / sampling rate の確認観点をまとめます。

## Entity MIB と Sensor MIB

SONiC SNMP は標準で IF-MIB / IF-X 系を提供しますが、Entity MIB / Entity Sensor MIB 拡張により、シャーシ / module / sensor / fan / PSU の階層と sensor 値（temp、voltage、current）を SNMP で読めます。`entPhysicalTable` と `entitySensor` の OID 群が [Redis](../../reference/glossary.md#term-redis) の platform daemon 出力（`STATE_DB` の `TEMPERATURE_INFO` / `FAN_INFO` / `PSU_INFO`）から組み立てられます。

SNMP polling を中心とした既存運用に、新しい platform sensor を載せたいときの入口です。

## SNMP Transceiver Monitoring

Optics の DOM (Digital Optical Monitoring) を SNMP でも読みたいニーズに対し、`xcvrd` が `STATE_DB` の `TRANSCEIVER_DOM_SENSOR` などに書く値を、SNMP subagent から OID にマップします。Test plan ページは、対応 OID と DOM 値の取得観点、warning / alarm threshold の確認方法を扱います。

## Telemetry Agent の拡張

gNMI telemetry agent には、Redis に元から無い情報を取り込んで publish する拡張があります。

- **Process / docker stats**: psutil で取得した CPU / memory / FD などを gNMI path で publish。
- **Memory statistics**: `/proc/meminfo` 系の memory 内訳を集計し、gNMI で公開。
- **Reboot cause**: 直近の reboot reason、time、cause（warm / fast / cold / unknown）を gNMI で取得可能にする。

いずれも従来は CLI を ssh 越しに叩いていた情報を streaming で扱えるようにする変更で、外部 SDN controller との連携を容易にします。

## SNMP yml 互換性の注意

SNMP の設定は CONFIG_DB に集約されつつありますが、過去資産の `snmp.yml` をそのまま入れたいケースもあります。Migration [HLD](../../reference/glossary.md#term-hld) では `config load_minigraph` 時の生成挙動と、手動で `snmp.yml` を編集する運用が共存できるかが整理されています。将来の deprecate を見据え、CONFIG_DB 側で管理することが推奨です。

## 関連ページ

- [Dataplane Telemetry](../../system/dataplane-telemetry-in-sonic.md)
- [DTel test plan](../../system/dataplane-telemetry-test-plan.md)
- [sFlow HLD](../../architecture/sflow-high-level-design.md)
- [sFlow test plan](../../architecture/sflow-test-plan.md)
- [Entity MIB と Entity Sensor MIB 拡張](../../system/sonic-entity-mib-and-entity-sensor-mib-extension.md)
- [SNMP transceiver monitoring](../../system/snmp-transceiver-monitoring-testbed-test-plan.md)
- [Process / docker stats を telemetry に](../../system/process-and-docker-stats-availability-via-telemetry-agent.md)
- [Memory statistics 機能](../../system/memory-statistics-feature-in-sonic.md)
- [Reboot cause を telemetry に](../../system/reboot-cause-information-via-telemetry-agent.md)
- [02 BGP: BMP との連携](../02-bgp/index.md)
- [10 gNMI / OpenConfig: 変換層と subscribe path](../10-gnmi-openconfig/index.md)
- [20 SWSS / SAI / Redis: COUNTERS_DB の polling 設計](../20-swss-sai-redis/index.md)

## 追加の発展トピック

- **IPFIX / sFlow v5 統合**: 既存 sFlow に加え、IPFIX (RFC 7011) 出力を望むユースケースが増えており、export pipeline を統一する提案がある。
- **DTel report の sampling**: 全 flow を export すると collector が飽和するため、watchlist と sampling rate の組合せで scale を制御する。queue / latency event のみ extract する mode も検討対象。
- **OTel (OpenTelemetry) との橋渡し**: SONiC counter / log を OTel collector へ流す community 提案がある。observability stack の統合が進めば、SNMP polling の比重が下がる。
- **[YANG](../../reference/glossary.md#term-yang)-modeled SNMP**: legacy `snmp.yml` を YANG モデル経由で生成し、SNMP 設定も gNMI Set で扱える流れ。`sonic-snmp.yang` の拡充が前提。
- **High-frequency counter streaming**: per-port / per-queue counters を 100ms 級で stream する用途。`telemetry` docker の CPU 影響と subscription 上限が論点。

## 既知の制約と回避方法

- **DTel platform 依存**: 全 ASIC が同じ event type を出すわけではなく、INT report header の format も platform 別。Production 投入前に対応 SAI attribute を確認する。
- **sFlow sampling rate の現実値**: 設定値どおりにサンプリングされない ASIC があり、`SAI_SAMPLEPACKET_TYPE` の制約で 1/N が丸められることがある。実測 sampling rate を `show sflow` と collector 側で照合する。
- **SNMP polling と gNMI streaming の重複コスト**: 同じ counter を SNMP polling と gNMI subscribe で両取りすると、Redis 負荷と control CPU が二重になる。一方に寄せる方針を決める。
- **Entity MIB の sensor 命名揺れ**: platform daemon が `STATE_DB` に出す sensor 名が SKU 別で異なり、SNMP polling の dashboard で名前不一致になる事例。命名規約を SKU 横断で揃える運用ガイドが必要。

## 将来計画 / ロードマップ

- DTel の report format 標準化 ([IFA](../../reference/glossary.md#term-ifa) / INT-MD) と SONiC 対応の追従。
- Telemetry agent からの structured logging export と OTel 連携。
- SNMP からの段階的退役は community 課題で、レガシー監視ツールとの併走期間設計が論点。

## 関連 RFC / 仕様書

- [RFC 7011](https://datatracker.ietf.org/doc/html/rfc7011) — IPFIX
- [RFC 7012](https://datatracker.ietf.org/doc/html/rfc7012) — IPFIX Information Model
- [RFC 3176](https://datatracker.ietf.org/doc/html/rfc3176) — sFlow v5
- [RFC 4133](https://datatracker.ietf.org/doc/html/rfc4133) — Entity MIB v3
- [RFC 3433](https://datatracker.ietf.org/doc/html/rfc3433) — Entity Sensor MIB
- [In-band Network Telemetry (INT) spec](https://github.com/p4lang/p4-applications/blob/master/docs/INT_latest.pdf)

## upstream 開発の最新動向

- `sonic-buildimage` の telemetry agent 拡張 PR が頻繁に入る（reboot cause、memory stats、process stats など）。
- `sonic-snmpagent` で transceiver / entity / sensor 対応の拡張、SNMP v3 関連修正が継続。
- DTel / sFlow の test plan が更新され、ASIC capability matrix が PR で明確化される傾向。

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [internals](internals.md) と、area HLD の [system/](../../system/index.md) 配下 telemetry / SNMP ページ群、および [sFlow HLD](../../architecture/sflow-high-level-design.md) で完結する。`telemetry` docker、`snmpd` agent、sFlow / DTel agent の責務分担は internals で詳細化。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `show snmp` / `show sflow` / `config sflow` 系、`SFLOW`, `SFLOW_COLLECTOR`, `TELEMETRY`, `SNMP` の [CONFIG_DB スキーマ](../../reference/config-db/index.md)、および `sonic-sflow`, `sonic-snmp` YANG モジュールが該当。
- **本ページ** は OTel との連携、DTel/INT、IPFIX、SNMPv3 USM/SMI などの「Streaming/Push 系への移行と従来 SNMP のレガシー併走」発展領域だけを扱う。

## トラブルシュート観点

- gNMI subscribe が応答しないときは、`docker exec telemetry telemetryctl status` で agent up、`/var/log/syslog` で TLS / cert エラーを確認する。`TELEMETRY|certs` の `ca_crt` パス、`gnmi.server.crt`/`key` の存在も併せて点検。
- SNMP walk が timeout する場合、`snmpd` の view [ACL](../../reference/glossary.md#term-acl) 設定 (`/etc/sonic/snmp.yml`)、`SNMP_AGENT_ADDRESS_CONFIG` のリスン IP、`snmpd` プロセス内の MIB initialization 遅延 (起動後 30 秒程度) を疑う。
- sFlow sample が collector に届かないときは `show sflow interface` で sample rate、`config sflow polling-interval` の有効性、`SFLOW_COLLECTOR` の宛先到達性 (UDP 6343) を点検。

## 検証パスとラボ要件

- gNMI subscribe の性能検証は `gnmi_cli -subscribe` で 1k〜10k path を sample 並列受信し、telemetry agent の CPU/メモリと、`COUNTERS_DB` の polling 間隔への影響を計測する。
- SNMP scale 検証は `snmpwalk -t 30 -r 3` で entity MIB / transceiver MIB を large port count (256 ports〜) で取得する。target は 60 秒以内の完走。
- DTel / sFlow の sampling 精度検証は、`pktgen` で既知レートのトラフィックを流し、collector 側で sample 数 × sampling rate ≒ 実トラフィックになることを確認する。

<!-- glossary-links-injected: fad4d220bc71 -->
