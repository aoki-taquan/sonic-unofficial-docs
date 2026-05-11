---
title: 運用
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/internals/aggregate-voq-counters-in-sonic.md
  - docs/system/platform-monitor-design-for-multi-asic-platforms.md
  - docs/system/platform-monitor-requirement-for-chassis-subsystem.md
  - docs/system/sonic-entity-mib-and-entity-sensor-mib-extension.md
---

# 運用

Multi-ASIC / VOQ chassis の運用調査は、pizza-box と比べて「どこから見るか」が増えます。supervisor から見るか、line card から見るか、ASIC namespace から見るか。ここでは典型的な確認順を整理します。

## どこから見るかの判定

| 観点 | 入口 |
|------|------|
| 物理 inventory（line card / fabric / PSU / fan） | supervisor の PMON / Entity MIB |
| line card 個別の port up/down、route、neighbor | line card host の `show` に `--namespace asic0` など |
| ASIC 内部 counter（queue、buffer、PG） | line card の ASIC namespace |
| VOQ counter（ingress 側 per-system-port queue） | line card の COUNTERS_DB を aggregate |
| chassis 全体の system port、line card 状態 | supervisor の Chassis DB |

CLI 上は `show platform inventory` / `show chassis modules` などが supervisor で chassis 全体を見せ、line card 内では従来の `show interfaces` 系が namespace を集約して見せます。

## Aggregate VOQ Counter

`aggregate-voq-counters-in-sonic` HLD は、VOQ counter が ASIC namespace ごとに分散している問題を解決します。VOQ は ingress 側で egress system port ごとに存在するため、「ある egress system port の輻輳」を知りたいときに、全 ingress line card の COUNTERS_DB を横断する必要があります。

集約は以下の流れで行います。

1. 各 line card の COUNTERS_DB が persys-port VOQ counter を持つ。
2. supervisor 側の aggregator が全 line card の COUNTERS_DB を購読する。
3. egress system port 単位での合計値を Chassis DB 側に書き込む。
4. CLI `show queue` 系が、aggregator 出力を整形して提示する。

運用者が押さえるのは「単一 line card の counter だけ見ても egress 系の輻輳は見えない」「supervisor 側の aggregate 値が遅延を持つ可能性がある」の 2 点です。

## PMON for Multi-ASIC / Chassis

`platform-monitor-design-for-multi-asic-platforms` および `platform-monitor-requirement-for-chassis-subsystem` は、PMON が複数 ASIC / 複数 line card 環境でどう動くかを定義します。

- Multi-ASIC pizza-box では PMON は 1 つの host で動き、ASIC それぞれの transceiver / DOM / thermal を集約します。
- VOQ chassis では PMON は supervisor と各 line card に独立して存在し、supervisor PMON が fabric / chassis 共通の sensor を、line card PMON が自分の transceiver / 内部 sensor を担当します。
- chassis subsystem 要件として、line card 抜き差し、PSU、fan tray、fabric card の hotswap 検出が PMON 経由で `STATE_DB` および Chassis DB に反映されます。

## Entity MIB / Entity Sensor MIB

`sonic-entity-mib-and-entity-sensor-mib-extension` は、chassis を含む物理コンポーネントツリーを SNMP で公開するための entityPhysical / entitySensor 拡張を定義します。

- chassis -> linecard -> ASIC -> port のような階層を `entPhysicalTable` で表現します。
- thermal / voltage / current / fan speed を `entSensorTable` 系で提供します。

運用上、NMS から chassis 全体を 1 つの SNMP target として見たいときに必要な仕組みで、line card 個別の SNMP target を増やさずに済みます。

## 典型的な調査フロー

問題タイプ別の入口の例:

1. **特定の egress port で drop が見える**: line card 側 `show interfaces counters` で drop 種別を確認し、ingress 側全 line card の VOQ counter を aggregate で確認、fabric port の link monitoring を見る。
2. **route が片方向しか上がっていない**: line card ごとの BGP namespace で neighbor 状態確認、Chassis DB の system port presence、`show ip route --namespace` で各 ASIC namespace を順に見る。
3. **新しい line card が立ち上がらない**: supervisor PMON で module 検出ログ、Chassis DB の line card 登録、line card 起動ログ（sub_role / hwsku 取得失敗を検索）。
4. **fabric link error**: supervisor PMON で fabric card 状態、`show fabric` 系コマンド、line card 側 fabric port counter。

## 関連ページ

- [Aggregate VOQ Counters](../../internals/aggregate-voq-counters-in-sonic.md)
- [PMON for Multi-ASIC Platforms](../../system/platform-monitor-design-for-multi-asic-platforms.md)
- [PMON for Chassis Subsystem](../../system/platform-monitor-requirement-for-chassis-subsystem.md)
- [Entity MIB / Entity Sensor MIB 拡張](../../system/sonic-entity-mib-and-entity-sensor-mib-extension.md)
