---
title: 内部実装
description: "内部実装 — Redis、SwSS、orchagent、counter、P4Orch など実装内部の構造を扱う章。"
verification: stub
---

# 内部実装
[Redis](../reference/glossary.md#term-redis)、SwSS、[orchagent](../reference/glossary.md#term-orchagent)、counter、P4Orch など実装内部の構造を扱う章。

## この章の趣旨
本章は機能ページから一段降りた「SONiC の中で何が起きているか」を扱う。具体的には Redis 多重 DB / namespace、SwSS の Producer/Consumer State Table、orchagent の bulk オペレーション、FlexCounter による統計収集、P4Orch / PINS 系の同期書き込み、debug / dump utility の内部、health-check の境界条件などを、当該の HLD と実コード (`sonic-swss-common`, `sonic-swss`, `sonic-sairedis`) を突き合わせて整理している。機能設計者が「この機能はどの SwSS 層に入るべきか」を決めるための足場としても使える。

## 主要ページ
- DB / スキーマ基礎: [swss-schema](swss-schema.md) / [複数 Redis インスタンスのユーザ定義](support-multiple-user-defined-redis-database-instances.md) / [Multi-ASIC 名前空間の Redis](support-redis-databases-in-multiple-namespaces.md)
- SwSS の同期パイプライン: [ZMQ ProducerStateTable / ConsumerStateTable 設計](zmq-producer-consumer-state-table-design.md)
- カウンタ / 統計基盤: [FlexCounter リファクタ](sonic-flexcounter-refactor.md) / [flex counter 初期化最適化](sonic-counter-initialization-optimization.md) / [VOQ カウンタ集約](aggregate-voq-counters-in-sonic.md) / [バイト/パケットレートとポート使用率](byte-packet-rates-port-utilization-in-sonic.md)
- 制御プレーン拡張: [P4Orch](p4-orchagent.md)
- 運用支援: [dump utility](dump-utility-for-easy-debugging.md) / [コンテナ health-check](why-need-health-check.md) / [L3 Scaling と Performance 強化](l3-scaling-and-performance-enhancements.md)

## 扱わない範囲
- ConfigDB / STATE_DB テーブル定義のリファレンス (列挙) は「[リファレンス](../reference/index.md)」章
- 機能単位の orchagent 仕様 (PortsOrch / RouteOrch など) は対応する機能章 (スイッチング / ルーティング / プラットフォーム)
- platform_api / sonic_platform 配下の Python クラス階層は「[プラットフォーム](../platform/index.md)」章
- ビルドシステム / docker レイヤ構成は「[アーキテクチャ](../architecture/index.md)」章

## この章の読み方
まず全体像や実装単位のページを読み、必要に応じて関連する機能別章またはリファレンス章に移動する。
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

<!-- glossary-links-injected: 90f82b1c14c0 -->
