---
title: 内部実装
description: "内部実装 — Redis、SwSS、orchagent、counter、P4Orch など実装内部の構造を扱う章。"
verification: stub
---

# 内部実装
Redis、SwSS、orchagent、counter、P4Orch など実装内部の構造を扱う章。
## この章の読み方
まず全体像や実装単位のページを読み、必要に応じて関連する機能別章またはリファレンス章に移動する。
## 検証状況
- ページ数: 12
- 分布: Code-verified: 10 / Discrepancy-found: 1 / HLD-only: 1

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
