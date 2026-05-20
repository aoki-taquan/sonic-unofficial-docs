---
title: 内部実装
description: "内部実装 — Redis、SwSS、orchagent、counter、P4Orch など実装内部の構造を扱う章。"
area: internals
verification: meta
last_verified: 2026-05-13
---

# 内部実装
[Redis](../reference/glossary.md#term-redis)、SwSS、[orchagent](../reference/glossary.md#term-orchagent)、counter、P4Orch など実装内部の構造を扱う章。

## この章の趣旨

機能 HLD ではなく、[SONiC](../reference/glossary.md#term-sonic) 全体の **内部基盤** を扱う。具体的には:

- **Redis DB スキーマ・分割**: [APPL_DB](../reference/glossary.md#term-appl_db) / [STATE_DB](../reference/glossary.md#term-state_db) / multi-namespace / 複数インスタンス分散
- **SwSS / orchagent コア**: producer/consumer state table、ZMQ、view switching
- **[FlexCounter](../reference/glossary.md#term-flexcounter) / カウンタ集約**: counter init 最適化、[VOQ](../reference/glossary.md#term-voq) aggregate、レート計算
- **P4Orch / 派生 orchestrator**: P4Runtime 連携、[PINS](../reference/glossary.md#term-pins) まわりの実装

機能（[VLAN](../reference/glossary.md#term-vlan) / [VXLAN](../reference/glossary.md#term-vxlan) / [BGP](../reference/glossary.md#term-bgp) 等）の HLD は各機能章を読み、本章は「その機能を支えている共通レイヤがどう書かれているか」を確認するときに参照する。

## この章の読み方
まず全体像や実装単位のページを読み、必要に応じて関連する機能別章またはリファレンス章に移動する。

## 主要ページ

- [swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）](swss-schema.md)
- [ZMQ ProducerStateTable / ConsumerStateTable 設計](zmq-producer-consumer-state-table-design.md)
- [Multi-ASIC 名前空間の Redis（database_global.json と SonicDBConfig）](support-redis-databases-in-multiple-namespaces.md)
- [複数 Redis インスタンスのユーザ定義（database_config.json で DB を分散）](support-multiple-user-defined-redis-database-instances.md)
- [FlexCounter リファクタ（CounterContext テンプレート化）](sonic-flexcounter-refactor.md)
- [flex counter 初期化最適化（pending_sai_objects + バッチ bulk_get_stats）](sonic-counter-initialization-optimization.md)
- [P4Orch（PINS の P4Runtime 用 orchagent / 同期書き込み）](p4-orchagent.md)
- [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](dump-utility-for-easy-debugging.md)
- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show arp）](l3-scaling-and-performance-enhancements.md)
- [バイト/パケットレートとポート使用率（RATES テーブル + EMA）](byte-packet-rates-port-utilization-in-sonic.md)

## 扱わない範囲

- 機能 HLD（VLAN / BGP / [ACL](../reference/glossary.md#term-acl) 等の設計）は各機能章
- [CONFIG_DB](../reference/glossary.md#term-config_db) の **テーブル別リファレンス** は [reference](../reference/index.md) 章
- [YANG](../reference/glossary.md#term-yang) モジュール / CLI コマンドの一覧も [reference](../reference/index.md) 章
- ベンダー実装に依存する [SAI](../reference/glossary.md#term-sai) 拡張は対象外（コミュニティ `master` の sairedis / sai-redis-vs に閉じる）
## 検証状況
- ページ数: 12
- 分布: Code-verified: 10 / Discrepancy-found: 1 / [HLD](../reference/glossary.md#term-hld)-only: 1

## 実装差分があるページ
- [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show arp）](l3-scaling-and-performance-enhancements.md)

## HLD-only のページ
- [swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）](swss-schema.md)

## ページ一覧

| ページ | 検証 |
|---|---|
| [FlexCounter リファクタ（CounterContext テンプレート化）](sonic-flexcounter-refactor.md) | Code-verified |
| [L3 Scaling と Performance 強化（kernel ARP gc / sairedis bulk / fpmsyncd / show arp）](l3-scaling-and-performance-enhancements.md) | Discrepancy-found |
| [Multi-ASIC 名前空間の Redis（database_global.json と SonicDBConfig）](support-redis-databases-in-multiple-namespaces.md) | Code-verified |
| [P4Orch（PINS の P4Runtime 用 orchagent / 同期書き込み）](p4-orchagent.md) | Code-verified |
| [VOQ カウンタ集約（chassis supervisor からの aggregate 表示）](aggregate-voq-counters-in-sonic.md) | Code-verified |
| [ZMQ ProducerStateTable / ConsumerStateTable 設計](zmq-producer-consumer-state-table-design.md) | Code-verified |
| [dump utility（モジュール単位で複数 DB から関連 key を集約する debug CLI）](dump-utility-for-easy-debugging.md) | Code-verified |
| [flex counter 初期化最適化（pending_sai_objects + バッチ bulk_get_stats）](sonic-counter-initialization-optimization.md) | Code-verified |
| [swss-schema（APPL_DB / STATE_DB の中心スキーマ参照）](swss-schema.md) | HLD-only |
| [コンテナ health-check（k8s readiness probe）](why-need-health-check.md) | Code-verified |
| [バイト/パケットレートとポート使用率（RATES テーブル + EMA）](byte-packet-rates-port-utilization-in-sonic.md) | Code-verified |
| [複数 Redis インスタンスのユーザ定義（database_config.json で DB を分散）](support-multiple-user-defined-redis-database-instances.md) | Code-verified |

<!-- glossary-links-injected: 4a5eb5b30e9a -->
