---
title: L3 Scaling と Performance 強化 概念（スケール目標 / 性能目標 / 3 系統の改善）
description: "L3 Scaling と Performance 強化 HLD の概念整理。ARP/ND エントリ数と route/ECMP のスケール目標、route programming 時間短縮と show コマンド応答短縮の性能目標、kernel gc tuning / sairedis bulk / fpmsyncd 最適化 / show arp の 4 系統の改善ポイントの位置づけ。"
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
  config_db: []
  cli: []
  yang: []
---

# L3 Scaling と Performance 強化 概念

このページは [L3 Scaling と Performance 強化（概要ハブ）](l3-scaling-and-performance-enhancements.md) の派生で、**スケール目標・性能目標・改善対象の全体マップ** に絞る。設定 / CLI は [l3-scaling-and-performance-enhancements-operations.md](l3-scaling-and-performance-enhancements-operations.md)、内部実装は [l3-scaling-and-performance-enhancements-internals.md](l3-scaling-and-performance-enhancements-internals.md)、制限事項と乖離は [l3-scaling-and-performance-enhancements-limitations.md](l3-scaling-and-performance-enhancements-limitations.md) を参照。

## 1. なぜスケールと性能を別個に扱うか

旧 SONiC は ARP/ND ~2400 entry が上限で、route programming も `1 経路 = 1 sairedis call` でレイテンシが大きかった[^1]。これを改善するには **kernel cache 拡大** と **app→ASIC データパス bulk 化** の 2 つを同時にやる必要がある。スケールと性能をそれぞれ独立軸として目標値を設定したのが本 HLD のスタンス。

## 2. スケール目標

| 項目 | 目標 |
|------|------|
| IPv4 ARP entry | 32k |
| IPv6 ND entry | 16k |
| IPv4 route | 200k |
| IPv6 route | 65k |
| ECMP | 512×32, 256×64, 128×128 |

> 注: HLD 提案の `gc_thresh` 値は現行 master に取り込まれていないため、これらのスケール値は HLD 上の目標であって実機で kernel cache が自動的に到達する値ではない（[limitations](l3-scaling-and-performance-enhancements-limitations.md) 参照）。

## 3. 性能目標

- IPv4 / IPv6 route programming 時間を短縮
- 未知 ARP / ND 学習時間を短縮
- `show arp` / `show ndp` の応答短縮
- **route programming 時間 30% 短縮** を狙う[^1]

## 4. 改善 4 系統の位置づけ

| 系統 | 対象 | 効果軸 |
|------|------|--------|
| kernel ARP/ND gc tuning | `gc_thresh1/2/3` | スケール（entry 上限）|
| CoPP ARP/ND 上限 | `COPP_TABLE` ARP/ND group | スケール（学習速度）|
| sairedis bulk route | `RouteOrch` / sairedis meta | 性能（Redis message 数）|
| fpmsyncd 最適化 | master device lookup スキップ | 性能（APP_DB 投入時間）|
| sairedis JSON 更新 | nlohmann/json v2 → v3.6 | 性能（dump 時間）|
| `show arp/ndp` 個別 FDB lookup | sonic-utilities CLI | UX（応答時間）|

詳細な算術と実装ファイル位置は [l3-scaling-and-performance-enhancements-internals.md](l3-scaling-and-performance-enhancements-internals.md) を参照。

## 5. 新規 CLI / CONFIG_DB / YANG

**新規 CLI / CONFIG_DB / YANG なし**[^1]。kernel sysctl と `COPP_TABLE` 値の見直しと内部実装の改善が中心。読者にとって明示的な設定変更は通常不要だが、HLD 提案値が現行 default と乖離している点には注意（[limitations](l3-scaling-and-performance-enhancements-limitations.md)）。

## 関連ページ

- [L3 Scaling と Performance 強化（概要ハブ）](l3-scaling-and-performance-enhancements.md)
- [l3-scaling-and-performance-enhancements-operations.md](l3-scaling-and-performance-enhancements-operations.md)
- [l3-scaling-and-performance-enhancements-internals.md](l3-scaling-and-performance-enhancements-internals.md)
- [l3-scaling-and-performance-enhancements-limitations.md](l3-scaling-and-performance-enhancements-limitations.md)

## 引用元

[^1]: `sonic-net/SONiC` `doc/l3-performance-scaling/L3_performance_and_scaling_enchancements_HLD.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- next-action -->
## このページを読んだ後の次アクション

!!! tip "読み手向け"
    - **本機能を実運用で使う場合**: 取り込み済の部分のみ運用可能。欠落部分の利用は不可なので本文「実装との乖離」を確認した上で適用範囲を限定する
    - **upstream 動向を追う場合**: 関連 issue / PR を [sonic-net/SONiC](https://github.com/sonic-net/SONiC) で検索（HLD タイトル / CONFIG_DB テーブル名 / Orch クラス名で grep するのが速い）
    - **代替手段 / 関連 reference**: 本ページの frontmatter `related` が空のため、[Reference 索引](../reference/index.md) から関連テーブル / CLI / YANG を辿る

!!! note "本ドキュメントの追跡"
    - monitor: `partially_implemented` / last_verified: `2026-05-11`
    - 次回再裏取りトリガ: quarterly。一覧は [discrepancy-index](../reference/verification/discrepancy-index.md) を参照（運用詳細は repo の `meta/discrepancy-operations.md`）

<!-- /next-action -->
