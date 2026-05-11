---
title: 発展トピック
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
---

# 発展トピック

このページは、基本の observability 経路（CLI / counter / SNMP / gNMI / techsupport）から外れる、専門観測機能と最近の telemetry 拡張をまとめます。設計判断に直結する局面以外は深追い不要です。

## Dataplane Telemetry (DTel)

DTel は In-band Network Telemetry を SONiC スイッチがエクスポートする機能です。ASIC が flow ごとにスイッチ内部情報（latency、queue 状態、drop reason 等）を packet header に書き込み、INT report として外部 collector に送出します。SONiC は collector / report session / watchlist を CONFIG_DB と APP_DB に持ち、`dtelorch` が SAI DTEL object に変換します。

DTel は ASIC capability への依存が大きく、すべての platform で同じ event type / report mode が出るわけではありません。test plan ページは、SAI DTEL object と SONiC table の対応、report format の検証観点を整理しています。

## sFlow

sFlow は古典的なサンプリング + counter polling 型 telemetry です。hsflowd が `psample` 経由で kernel から packet sample を取り、`SFLOW_COLLECTOR` 宛に sFlow datagram を送ります。Counter polling も hsflowd が担当し、`SFLOW.global.polling_interval` で interval を制御します。

sFlow と DTel の住み分けは、sFlow が「サンプリングされた粗い flow telemetry」、DTel が「flow ごとの精密 in-band telemetry」と覚えると整理できます。test plan ページは collector / agent / sampling rate の確認観点をまとめます。

## Entity MIB と Sensor MIB

SONiC SNMP は標準で IF-MIB / IF-X 系を提供しますが、Entity MIB / Entity Sensor MIB 拡張により、シャーシ / module / sensor / fan / PSU の階層と sensor 値（temp、voltage、current）を SNMP で読めます。`entPhysicalTable` と `entitySensor` の OID 群が Redis の platform daemon 出力（`STATE_DB` の `TEMPERATURE_INFO` / `FAN_INFO` / `PSU_INFO`）から組み立てられます。

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

SNMP の設定は CONFIG_DB に集約されつつありますが、過去資産の `snmp.yml` をそのまま入れたいケースもあります。Migration HLD では `config load_minigraph` 時の生成挙動と、手動で `snmp.yml` を編集する運用が共存できるかが整理されています。将来の deprecate を見据え、CONFIG_DB 側で管理することが推奨です。

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
