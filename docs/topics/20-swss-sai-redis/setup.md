---
title: 設定
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 設定

内部実装側にも「設定」がある。機能 CLI ではなく、Redis instance のレイアウト、Multi-ASIC 向け namespace、FEATURE による daemon 起動の有効/無効、起動の遅延制御などが該当する。

## Redis instance のレイアウト

歴史的には全 DB が単一の Redis instance に同居していたが、性能や障害分離のために、DB を複数 Redis instance に分ける設計が入った。割り当ては `database_config.json`（Multi-ASIC では `database_global.json`）で持ち、各 DB は `db_name → instance` のマッピングで決まる。

- DB を別 instance に出すと、巨大な DB（例: COUNTERS_DB）の処理が他 DB の応答性に影響しにくくなる。
- DB 名で参照する API は変わらないため、ユーザ daemon は instance 構成を意識せずに済む。
- 設計と運用上の注意は [複数 Redis インスタンスのユーザ定義（database_config.json で DB を分散）](../../internals/support-multiple-user-defined-redis-database-instances.md) を読む。

## Multi-ASIC と namespace

Multi-ASIC や VOQ chassis では、ASIC ごとに別の Redis 名前空間を持つ。`SonicDBConfig` のロード対象を、`database_config.json` から `database_global.json` 経由の複数 namespace に拡張する設計である。namespace 切り替えにより、同じ DB 名（例: `ASIC_DB`）が ASIC ごとに独立した instance を指す。

- 設計の前提は [Multi-ASIC 名前空間の Redis](../../internals/support-redis-databases-in-multiple-namespaces.md) を読む。
- 機能側の見え方（特に [Multi-ASIC 章への接続]）は今後の章で受ける。

## FEATURE による daemon 制御

`FEATURE` テーブルは、container（=機能 daemon 群）の有効/無効、自動再起動、依存関係を一元管理する。Optional Feature Control は、CLI から `config feature state` で切り替え、 config reload 後の一貫した起動順を保証する設計である。

設定の入口や CLI 規約は [FEATURE テーブルによるオプショナル機能の有効/無効制御](../../system/sonic-optional-feature-control-enhancement.md) を読む。

## config reload と PortInitDone

`config reload` の event-driven 化により、port 初期化完了（`PortInitDone`）など特定イベントを待ってから依存 daemon を起動できる。`FEATURE.<container>.delayed` で遅延 container を識別し、PortInitDone 後にまとめて起動する。これにより BGP 等が「ASIC 上の port がまだ無い」状態で route を流し始める問題を避ける。

詳細は [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](../../management/config-reload-enhancement.md) を読む。

## 健全性 probe

各機能 container は健全性確認のための probe を持つ。k8s に乗せた SONiC では readiness probe としても使うため、container 内で `monit` 系の検査結果を 1 つの判定に集約する設計が必要になる。意義と境界条件は [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md) を読む。

## 関連ページ

- [複数 Redis インスタンスのユーザ定義（database_config.json で DB を分散）](../../internals/support-multiple-user-defined-redis-database-instances.md)
- [Multi-ASIC 名前空間の Redis（database_global.json と SonicDBConfig）](../../internals/support-redis-databases-in-multiple-namespaces.md)
- [FEATURE テーブルによるオプショナル機能の有効/無効制御](../../system/sonic-optional-feature-control-enhancement.md)
- [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](../../management/config-reload-enhancement.md)
- [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md)
