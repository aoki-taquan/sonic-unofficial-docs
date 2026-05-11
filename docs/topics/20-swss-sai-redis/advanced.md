---
title: 発展トピック
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
---

# 発展トピック

起動、readiness、warm reboot のように「DB と daemon の状態を時間軸で扱う」テーマを集める。機能章で「reload 直後の動作」「warm reboot 中の差分適用」が前提として出てくるとき、ここに戻る。

## app health と system ready の共通設計

`system ready` は、各 app が「自分はもう UP と見なしてよい」状態に達したことを sysmonitor が集約して全体判定する設計である。container ごとの health-check（k8s readiness probe）と、system ready（per-app の closest UP status を event 集約して全体判定）は層が違う。

- container 単位: [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md)
- システム単位: [System Ready（sysmonitor + per-app closest UP status の event 集約）](../../system/system-ready-hld.md)

機能章で「reload 直後の不整合」を見るときは、この 2 段の readiness のどちらで止まっているかを切り分ける。

## FEATURE.delayed と PortInitDone

config reload や起動直後では、`port` が ASIC 上に存在するまで他 daemon が動いても意味がないことがある。`FEATURE.<container>.delayed` を真にした container は、`PortInitDone` を待ってから起動される。BGP のように「port 不在で route を流す」と害が大きい機能では、これを使って起動順を制御する。

設計の前提は [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](../../management/config-reload-enhancement.md) を読む。

## warm reboot と ProducerStateTable の view switching

warm reboot では、再起動前の状態と再起動後の意図の差分だけを ASIC に適用したい。ProducerStateTable の view switching は、新しい view への書き込みを蓄積しておき、最終的に古い view から新しい view への差分（追加・削除・更新）として APPL_DB に反映する設計である。これにより、warm reboot 中の transient な「全削除→全追加」を回避する。

機能章で「warm reboot 安全に書ける」と語られている前提は、この仕組みに依存することが多い。設計は [ProducerStateTable の view switching（warm reboot 用の差分適用）](../../switching/view-switching-in-producerstatetable.md) を読む。

## FEATURE 制御と startup の関係

`FEATURE` テーブルの auto-restart、state、has_per_asic_scope、has_global_scope 等は、container の起動と多インスタンス展開を一括制御する。Multi-ASIC では `has_per_asic_scope` が真の container は ASIC 数だけ並走する。startup 順、依存、Multi-ASIC 展開を一緒に変えたいときに見るのはこの 1 表である。詳細は [FEATURE テーブルによるオプショナル機能の有効/無効制御](../../system/sonic-optional-feature-control-enhancement.md) を読む。

## 関連ページ

- [System Ready（sysmonitor + per-app closest UP status の event 集約）](../../system/system-ready-hld.md)
- [config reload の event-driven 化（FEATURE.delayed + PortInitDone）](../../management/config-reload-enhancement.md)
- [FEATURE テーブルによるオプショナル機能の有効/無効制御](../../system/sonic-optional-feature-control-enhancement.md)
- [ProducerStateTable の view switching（warm reboot 用の差分適用）](../../switching/view-switching-in-producerstatetable.md)
- [コンテナ health-check（k8s readiness probe）](../../internals/why-need-health-check.md)

## 発展トピック

- **SAI Redis pipe / batch**: SAI Redis (`libsairedis`) は orchagent からの SAI call を pipe batch で syncd に渡す。大量更新時の bulk API が性能を支配する。
- **ASIC_DB の sharding**: 単一 Redis インスタンスに全 SAI object が乗ると memory が膨れる。namespace 分割や Redis cluster 化が議題。
- **オフライン構成検証**: `swss-cli` や `sonic-cfggen` で生成した CONFIG_DB をオフラインで YANG 検証してから流し込むパス。
- **CONFIG_DB と APPL_DB の責務再整理**: SET-then-DEL の transient を避けるため、orch 側で diff-based reconciliation が拡張されつつある。
- **eventd / publish-subscribe**: state 変化 event の structured stream。telemetry / fault management の前提基盤。

## 既知の制約と回避方法

- **`config reload` の重さ**: 大量 schema reload で daemon 全体が再起動レベルの負荷になる。`config reload --no-service` のような部分 reload と PortInitDone を組合せる。
- **warm reboot 中の view switching 失敗**: 一部 orch が view switching に対応していないと、その object だけ全削除→全追加になる。対象 orch の WARM_BOOT capability 一覧を確認する。
- **redis OOM risk**: ASIC_DB / COUNTERS_DB の scale が大きいと memory swap が発生。`maxmemory-policy` を `noeviction` にしないと counter が消える。
- **FEATURE state の race**: container 起動と FEATURE state 更新が非同期で、依存先を先に起動してしまう例がある。`delayed` と `auto_restart` を組み合わせる。

## 将来計画 / ロードマップ

- `system ready` HLD の最終形に向けて、closest UP status の整理と sysmonitor の集約ロジックが拡張中。
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
