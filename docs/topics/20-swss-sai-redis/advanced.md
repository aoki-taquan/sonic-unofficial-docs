---
title: 発展トピック
description: 発展トピック — 起動、readiness、warm reboot のように「DB と daemon の状態を時間軸で扱う」テーマを集める。機能章で「reload
  直後の動作」「warm reboot 中の差分適用」が前提として出てくるとき、ここに戻る。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - show feature status
  - show system-health
  - show warm_restart
  config_db:
  - FEATURE
  - WARM_RESTART
  yang:
  - sonic-feature
  - sonic-warm-restart
---

# 発展トピック

起動、readiness、warm reboot のように「DB と daemon の状態を時間軸で扱う」テーマを集める。機能章で「reload 直後の動作」「warm reboot 中の差分適用」が前提として出てくるとき、ここに戻る。

## app health と system ready の共通設計

`system ready` は、各 app が「自分はもう UP と見なしてよい」状態に達したことを sysmonitor が集約して全体判定する設計である。container ごとの health-check（k8s readiness probe）と、system ready（per-app の closest UP status を event 集約して全体判定）は層が違う。

- container 単位: [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md)
- システム単位: [System Ready（sysmonitor + per-app closest UP status の event 集約）](../../system/system-ready-hld.md)

機能章で「reload 直後の不整合」を見るときは、この 2 段の readiness のどちらで止まっているかを切り分ける。

## FEATURE.delayed と PortInitDone

config reload や起動直後では、`port` が [ASIC](../../reference/glossary.md#term-asic) 上に存在するまで他 daemon が動いても意味がないことがある。`FEATURE.<container>.delayed` を真にした container は、`PortInitDone` を待ってから起動される。[BGP](../../reference/glossary.md#term-bgp) のように「port 不在で route を流す」と害が大きい機能では、これを使って起動順を制御する。

設計の前提は [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](../../management/config-reload-enhancement.md) を読む。

## warm reboot と ProducerStateTable の view switching

warm reboot では、再起動前の状態と再起動後の意図の差分だけを ASIC に適用したい。[ProducerStateTable](../../reference/glossary.md#term-producerstatetable) の view switching は、新しい view への書き込みを蓄積しておき、最終的に古い view から新しい view への差分（追加・削除・更新）として [APPL_DB](../../reference/glossary.md#term-appl_db) に反映する設計である。これにより、warm reboot 中の transient な「全削除→全追加」を回避する。

機能章で「warm reboot 安全に書ける」と語られている前提は、この仕組みに依存することが多い。設計は [ProducerStateTable の view switching（warm reboot 用の差分適用）](../../switching/view-switching-in-producerstatetable.md) を読む。

## FEATURE 制御と startup の関係

`FEATURE` テーブルの auto-restart、state、has_per_asic_scope、has_global_scope 等は、container の起動と多インスタンス展開を一括制御する。[Multi-ASIC](../../reference/glossary.md#term-multi-asic) では `has_per_asic_scope` が真の container は ASIC 数だけ並走する。startup 順、依存、Multi-ASIC 展開を一緒に変えたいときに見るのはこの 1 表である。詳細は [FEATURE テーブルによるオプショナル機能の有効/無効制御](../../system/sonic-optional-feature-control-enhancement.md) を読む。

## 関連ページ

- [System Ready（sysmonitor + per-app closest UP status の event 集約）](../../system/system-ready-hld.md)
- [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](../../management/config-reload-enhancement.md)
- [FEATURE テーブルによるオプショナル機能の有効/無効制御](../../system/sonic-optional-feature-control-enhancement.md)
- [ProducerStateTable の view switching（warm reboot 用の差分適用）](../../switching/view-switching-in-producerstatetable.md)
- [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md)

## 発展トピック

- **[SAI](../../reference/glossary.md#term-sai) [Redis](../../reference/glossary.md#term-redis) pipe / batch**: SAI Redis (`libsairedis`) は [orchagent](../../reference/glossary.md#term-orchagent) からの SAI call を pipe batch で [syncd](../../reference/glossary.md#term-syncd) に渡す。大量更新時の bulk API が性能を支配する。
- **[ASIC_DB](../../reference/glossary.md#term-asic_db) の sharding**: 単一 Redis インスタンスに全 SAI object が乗ると memory が膨れる。namespace 分割や Redis cluster 化が議題。
- **オフライン構成検証**: `swss-cli` や `sonic-cfggen` で生成した [CONFIG_DB](../../reference/glossary.md#term-config_db) をオフラインで [YANG](../../reference/glossary.md#term-yang) 検証してから流し込むパス。
- **CONFIG_DB と APPL_DB の責務再整理**: SET-then-DEL の transient を避けるため、orch 側で diff-based reconciliation が拡張されつつある。
- **eventd / publish-subscribe**: state 変化 event の structured stream。telemetry / fault management の前提基盤。

## 既知の制約と回避方法

- **`config reload` の重さ**: 大量 schema reload で daemon 全体が再起動レベルの負荷になる。`config reload --no-service` のような部分 reload と PortInitDone を組合せる。
- **warm reboot 中の view switching 失敗**: 一部 orch が view switching に対応していないと、その object だけ全削除→全追加になる。対象 orch の WARM_BOOT capability 一覧を確認する。
- **redis OOM risk**: ASIC_DB / [COUNTERS_DB](../../reference/glossary.md#term-counters_db) の scale が大きいと memory swap が発生。`maxmemory-policy` を `noeviction` にしないと counter が消える。
- **FEATURE state の race**: container 起動と FEATURE state 更新が非同期で、依存先を先に起動してしまう例がある。`delayed` と `auto_restart` を組み合わせる。

## warm reboot の既知パターンと対処

以下は実際に報告されている warm reboot 関連の落とし穴である。

### dummy SAI objects の削除失敗（バージョン跨ぎアップグレード）

古い image（例: 201811）から新 image（例: 202012）へ warm reboot でアップグレードした後、同 image での 2 回目 warm reboot で orchagent がクラッシュするケースがある（issue #1429）。

原因: 最初の warm reboot アップグレードで syncd が作成した「dummy SAI objects」が ASIC_DB に残り、次回 warm reboot の reconcile 時に `SAI_STATUS_INVALID_PARAMETER` で削除できない。

```
syncd: remove of SAI object OID:xxx failed: SAI_STATUS_INVALID_PARAMETER
orchagent: FATAL syncd failed to remove dummy object
```

対処:
1. バージョン跨ぎの warm reboot が必要な場合、中間バージョンを踏んで 2 段階で移行することを検討する。
2. 問題が起きた場合は cold reboot で回復する（ASIC_DB / SAI state が初期化される）。

### SAI_SWITCH_ATTR_RESTART_WARM を reconcile 後に false に戻す必要

warm reboot 実行前に `setRestartWarmOnAllSwitches(true)` が呼ばれ、syncd が warm=true で起動する。しかし reconcile 完了後に `SAI_SWITCH_ATTR_RESTART_WARM = false` を SAI にセットしない実装だと、その後の通常 reboot（cold/fast）でも SAI が warm `remove_switch` を実行してしまうことがある（issue #1361）。

対処: ベンダ SAI の実装によって挙動が異なる。連続 warm reboot が必要な環境では、reconcile 後の `RESTART_WARM = false` セットを SAI / syncd の実装が行っていることを確認する。

### buffer profile が zero の queue に対する reconcile 失敗

warm reboot 実行時、一部の queue に「zero buffer profile」が attach されている場合、temp asic view に余分な buffer profile が 2 件生成されることがある（issue #899）。これら余分な buffer profile は current asic view と VID は一致するが attribute リストが空になるため、`performObjectSetTransition` 内の比較で失敗する：

```
performObjectSetTransition: object OID:xxx attribute list is empty in temp view
```

PR #906 で修正済み（[sonic-sairedis](../../reference/glossary.md#term-sonic-sairedis) master）。古い image でこの症状が出た場合は cold reboot で回復し、image を更新する。

### warm reboot 後の FlexCounter による新 VID の処理失敗

warm reboot の `init view` フェーズ（`apply_view` 前）では、[FlexCounter](../../reference/glossary.md#term-flexcounter) がまだ ASIC state を完全に認識していない。buffer pool など新たに作成された VID を持つ object が FlexCounter の `processFlexCounterEvent` で処理されようとすると、VID→RID マッピングが未確立で counter 取得に失敗する（issue #862、[sonic-swss](../../reference/glossary.md#term-sonic-swss) PR #1987 で修正済）。

現行 master では `apply_view` 完了後に FlexCounter の VID 再登録が行われるため通常は問題ない。古い image でこの症状が出た場合（syslog に `processFlexCounterEvent` のエラーが連続して現れる）は、image を更新する。

### warm reboot 後の ACL counter OID マッピングズレ

warm reboot 後、orchagent が ACL Entry の `SAI_ACL_ENTRY_ATTR_ACTION_COUNTER` に誤った ACL counter RID を SET するケースが報告された（issue #449）。同一 ACL Entry の RID と counter RID の対応が temp view 生成時にずれることが原因で、修正済み（closed as fixed）。症状：

```
syncd: SET on ACL_ENTRY with counter RID that belongs to another entry
```

現行 master では解消しているが、reconcile 後に ACL counter の値が意図しない entry に集計されているように見える場合は、このパターンを疑って image バージョンを確認する。

## 将来計画 / ロードマップ

- `system ready` [HLD](../../reference/glossary.md#term-hld) の最終形に向けて、closest UP status の整理と sysmonitor の集約ロジックが拡張中。
- ProducerStateTable view switching の対応 orch 拡大。
- Redis 7.x / Valkey への移行検討。
- SAI bulk API の利用範囲拡大による update スループット改善。

## 関連 RFC / 仕様書

- SAI / SWSS / Redis 層は IETF / IEEE 標準とは独立し、OCP コミュニティの SAI specification が中心。
- [Redis Protocol](https://redis.io/docs/reference/protocol-spec/) — RESP プロトコル
- [OCP SAI specification](https://github.com/opencomputeproject/SAI)

## upstream 開発の最新動向

- `sonic-swss-common` で `ProducerStateTable` view switching 対応 orch 拡大の PR が継続。
- `sonic-sairedis` で bulk API 拡張と syncd の事前計算最適化 PR が散発。
- `system-health` / `sysmonitor` で closest UP status の event 集約ロジック改善が議題化。
- Redis 6.2 → 7.x への対応検討と、複数 Redis instance での scale 改善議論が続く。

## ハンドオフ

- **概念とアーキテクチャ**は本章の [concept](concept.md) / [internals](internals.md) と、関連 HLD の [System Ready HLD](../../system/system-ready-hld.md), [view switching in ProducerStateTable](../../switching/view-switching-in-producerstatetable.md), [config reload enhancement](../../management/config-reload-enhancement.md) で完結する。`orchagent` の event loop、`syncd` の SAI binding、Redis pub/sub の責務分担は internals で詳述。
- **設定とリファレンス**は [reference/cli](../../reference/cli/index.md) の `swssloglevel`, `saictl`, `redis-cli`、`FEATURE`, `DEVICE_METADATA`, `COUNTERS_DB` 各種 [CONFIG_DB スキーマ](../../reference/config-db/index.md) に集約。
- **本ページ** は ProducerStateTable view switching、SAI bulk API、Redis 7.x 移行、複数 Redis instance、closest UP status などの「実装基盤の進化」発展領域だけを扱う。

## トラブルシュート観点

- orchagent が CPU 100% で hang する場合は、`docker exec swss orchent --dump-state` (debug build) や `swssloglevel -l DEBUG -c orchagent` でログを上げ、`ASIC_DB` の特定テーブル更新でループしているかを点検する。SAI bulk API 失敗時のリトライ無限ループも疑う。
- COUNTERS_DB が肥大化して redis OOM が起きる場合、`redis-cli -n 2 info memory` で used_memory を確認し、`FLEX_COUNTER_TABLE` の polling 間隔と counter group 数を見直す。`maxmemory-policy noeviction` の維持は必須。
- FEATURE 起動順 race による依存先未起動は、`show feature status` と `systemctl list-dependencies sonic.target` で `delayed` / `auto_restart` の設定を確認し、`/etc/sonic/feature_advanced.json` の dependency を補正する。

## 検証パスとラボ要件

- orchagent throughput 検証は CONFIG_DB に 10k〜100k entry (route / [FDB](../../reference/glossary.md#term-fdb) / [ACL](../../reference/glossary.md#term-acl) rule) を一括投入し、ASIC_DB 反映までのレイテンシを計測する。SAI bulk API 利用時の倍率向上 (target 2x〜5x) を確認する。
- view switching 検証は warm reboot を多数回繰り返し、`ProducerStateTable` の view A/B 切替と、orchagent / syncd の状態差分が cleanup される過程を `redis-cli` で観察する。
- closest UP status 検証は意図的に container を 1 つ kill し、`system-health` / `sysmonitor` の event aggregation で上位 status (`Operational`/`Degraded`/`Failed`) が期待通り遷移することを確認する。

## 関連ページ (追補)

- [System Ready HLD](../../system/system-ready-hld.md)
- [SONiC bulk counter design](../../architecture/sonic-bulk-counter-design.md)
- [SONiC optional feature control enhancement](../../system/sonic-optional-feature-control-enhancement.md)
- [view switching in ProducerStateTable](../../switching/view-switching-in-producerstatetable.md)
- [config reload enhancement](../../management/config-reload-enhancement.md)
- [02 BGP: orchagent の route programming throughput](../02-bgp/index.md)
- [09 Telemetry / SNMP: COUNTERS_DB の polling](../09-telemetry-snmp/index.md)
- [11 Reboot: warm reboot と view switching](../11-reboot/index.md)
- [21 Lab / Developer: dev container 内での swss/sai 開発](../21-lab-vs-developer/index.md)

<!-- glossary-links-injected: 9ffe0f19a975 -->
