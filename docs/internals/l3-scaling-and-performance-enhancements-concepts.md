---
title: L3 Scaling と Performance 強化 概念（スケール目標 / 性能目標 / 6 系統の改善）
description: L3 Scaling と Performance 強化 HLD の概念整理。ARP/ND エントリ数と route/ECMP のスケール目標、route
  programming 時間短縮と show コマンド応答短縮の性能目標、kernel gc tuning / CoPP ARP-ND 上限 / sairedis bulk
  route / fpmsyncd 最適化 / sairedis JSON ライブラリ更新 / show arp の 6 系統の改善ポイントの位置づけを扱う。
area: internals
verification: discrepancy-found
last_verified: 2026-05-11
page_kind: split-child
monitor: partially_implemented
sources:
- repo: sonic-net/SONiC
  path: doc/l3-performance-scaling/L3_performance_and_scaling_enchancements_HLD.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - COPP_GROUP
  - COPP_TRAP
  - NEIGH
  - VLAN_INTERFACE
  - INTERFACE
  cli:
  - show arp
  - show ndp
  yang:
  - sonic-copp
---

# L3 Scaling と Performance 強化 概念

このページは [L3 Scaling と Performance 強化（概要ハブ）](l3-scaling-and-performance-enhancements.md) の派生で、**スケール目標・性能目標・改善対象の全体マップ** に絞る。設定 / CLI は [l3-scaling-and-performance-enhancements-operations.md](l3-scaling-and-performance-enhancements-operations.md)、内部実装は [l3-scaling-and-performance-enhancements-internals.md](l3-scaling-and-performance-enhancements-internals.md)、制限事項と乖離は [l3-scaling-and-performance-enhancements-limitations.md](l3-scaling-and-performance-enhancements-limitations.md) を参照。

## 1. なぜスケールと性能を別個に扱うか

旧 [SONiC](../reference/glossary.md#term-sonic) は [ARP](../reference/glossary.md#term-arp)/ND ~2400 entry が上限で、route programming も `1 経路 = 1 sairedis call` でレイテンシが大きかった[^1]。これを改善するには **kernel cache 拡大** と **app→[ASIC](../reference/glossary.md#term-asic) データパス bulk 化** の 2 つを同時にやる必要がある。スケールと性能をそれぞれ独立軸として目標値を設定したのが本 [HLD](../reference/glossary.md#term-hld) のスタンス。

## 2. スケール目標

| 項目 | 目標 |
|------|------|
| IPv4 ARP entry | 32k |
| IPv6 ND entry | 16k |
| IPv4 route | 200k |
| IPv6 route | 65k |
| [ECMP](../reference/glossary.md#term-ecmp) | 512×32, 256×64, 128×128 |

> 注: HLD 提案の `gc_thresh` 値は現行 master に取り込まれていないため、これらのスケール値は HLD 上の目標であって実機で kernel cache が自動的に到達する値ではない（[limitations](l3-scaling-and-performance-enhancements-limitations.md) 参照）。

## 3. 性能目標

HLD §1.1 の性能要件と §2.2.1.1 のターゲットを以下に集約する[^1]。

- IPv4 / IPv6 route programming 時間を短縮（最終ターゲットは **30% 短縮**）
- 未知 ARP / ND 学習時間を短縮
- `show arp` / `show ndp` の応答短縮

## 4. 改善 6 系統の位置づけ

| 系統 | 対象 | 効果軸 |
|------|------|--------|
| kernel ARP/ND gc tuning | `gc_thresh1/2/3` | スケール（entry 上限）|
| [CoPP](../reference/glossary.md#term-copp) ARP/ND 上限 | `COPP_TABLE` ARP/ND group（CONFIG_DB スキーマ上は [`COPP_GROUP`](../reference/config-db/copp-group.md) + [`COPP_TRAP`](../reference/config-db/copp-trap.md)、`COPP_TABLE` は runtime での [APPL_DB](../reference/glossary.md#term-appl_db) 反映名）| スケール（学習速度）|
| sairedis bulk route | `RouteOrch` / sairedis meta | 性能（[Redis](../reference/glossary.md#term-redis) message 数）|
| [fpmsyncd](../reference/glossary.md#term-fpmsyncd) 最適化 | master device lookup スキップ | 性能（APP_DB 投入時間）|
| sairedis JSON 更新 | nlohmann/json v2 → v3.6 | 性能（dump 時間）|
| `show arp/ndp` 個別 [FDB](../reference/glossary.md#term-fdb) lookup | [sonic-utilities](../reference/glossary.md#term-sonic-utilities) CLI | UX（応答時間）|

詳細な算術と実装ファイル位置は [l3-scaling-and-performance-enhancements-internals.md](l3-scaling-and-performance-enhancements-internals.md) を参照。

## 5. 新規 CLI / CONFIG_DB / YANG

**新規 CLI / [CONFIG_DB](../reference/glossary.md#term-config_db) / [YANG](../reference/glossary.md#term-yang) なし**[^1]。kernel sysctl と `COPP_TABLE` 値の見直しと内部実装の改善が中心。読者にとって明示的な設定変更は通常不要だが、HLD 提案値が現行 default と乖離している点には注意（[limitations](l3-scaling-and-performance-enhancements-limitations.md)）。

## 関連ページ

- [L3 Scaling と Performance 強化（概要ハブ）](l3-scaling-and-performance-enhancements.md)
- [l3-scaling-and-performance-enhancements-operations.md](l3-scaling-and-performance-enhancements-operations.md)
- [l3-scaling-and-performance-enhancements-internals.md](l3-scaling-and-performance-enhancements-internals.md)
- [l3-scaling-and-performance-enhancements-limitations.md](l3-scaling-and-performance-enhancements-limitations.md)

<!-- phase-boundary -->
## 実装フェーズ境界

!!! info "改善 6 系統の master 取り込み状況"
    本ページは `monitor: partially_implemented` で、§4 で列挙した 6 系統の改善が
    **個別に取り込まれている / 値が採用されていない** 状態を扱う。各系統の
    現状は以下のとおり（裏取り根拠は [limitations](l3-scaling-and-performance-enhancements-limitations.md) §2-3）。

    | Phase (系統) | 現状 | 補足 |
    |---|---|---|
    | sairedis bulk route (`RouteOrch` + `gRouteBulker`) | 実装済 (取り込み済) | `sonic-swss/orchagent/routeorch.cpp` L41 ほか |
    | `fpmsyncd` の master device lookup スキップ | 実装済 (取り込み済) | `sonic-swss/fpmsyncd/routesync.cpp` L2077-L2082 |
    | kernel ARP/ND `gc_thresh` 引き上げ | 未実装 (未採用) | 現行値は v4/v6 とも `1024/2048/4096`（HLD 提案 v4 16k/32k/48k は不採用） |
    | CoPP ARP/ND 上限 8000 pps 化 | 未実装 (未採用) | `copp_cfg.j2` で `arp` trap は `queue4_group2`（cir 600 のまま） |
    | sairedis 内 nlohmann/json v3.6 更新 | 未検証 | 取り込み年代が古く本確認のスコープ外 |
    | `show arp` / `show ndp` 個別 FDB lookup | 未検証 | 本確認のスコープ外 |

    凡例: 「実装済 (取り込み済)」=現行 master でコード確認 / 「未実装 (未採用)」=HLD 値は採用されず保守側で据え置き / 「未検証」=本確認スコープ外。
<!-- /phase-boundary -->

## 実装との乖離

`monitor: partially_implemented` — 部分実装 — HLD の中核は実装済みだが、フィールド / API / 制約のいくつかが上流に未取り込み、または挙動が緩和されている。 本ページは split-child のため、差分の主要根拠 / 影響 / 回避策は親ページ [L3 Scaling と Performance 強化 概念 親ページ](l3-scaling-and-performance-enhancements.md) の同セクション（`## 実装との乖離` または `!!! diff` ブロック）を参照のこと。

## 引用元

[^1]: `sonic-net/SONiC` `doc/l3-performance-scaling/L3_performance_and_scaling_enchancements_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- next-action -->
## このページを読んだ後の次アクション

!!! tip "読み手向け"
    - **本機能を実運用で使う場合**: bulk route と `fpmsyncd` 最適化は master 取り込み済のため routing path latency 改善は享受可能。一方、kernel `gc_thresh` と CoPP ARP/ND 値は HLD 提案値が不採用なのでスケール試験設計時に注意（詳細は [limitations](l3-scaling-and-performance-enhancements-limitations.md)）
    - **upstream 動向を追う場合**: VnetOrch の bulker 拡張など継続中の PR は [sonic-swss #4303](https://github.com/sonic-net/sonic-swss/pull/4303) ほか。`RouteOrch` / `fpmsyncd` のクラス名で grep するのが速い
    - **代替手段 / 関連 reference**: frontmatter `related` の [`COPP_GROUP`](../reference/config-db/copp-group.md) / [`COPP_TRAP`](../reference/config-db/copp-trap.md) / `show arp` / `sonic-copp` から関連テーブル / CLI / YANG を辿る

!!! note "本ドキュメントの追跡"
    - monitor: `partially_implemented` / last_verified: `2026-05-11`
    - 次回再裏取りトリガ: quarterly。一覧は [discrepancy-index](../reference/verification/discrepancy-index.md) を参照（運用詳細は repo の `meta/discrepancy-operations.md`）

<!-- /next-action -->

<!-- glossary-links-injected: 9cc90e2e6da0 -->
