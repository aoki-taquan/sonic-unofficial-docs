---
title: 保守フェーズ運用ルール
description: SONiC 非公式ドキュメントが「保守フェーズ」へ移行した後の運用サイクルと、再構成イテレーションを起票する判定基準。
verification: meta
hide:
  - toc
---

# 保守フェーズ運用ルール (Maintenance Mode)

このドキュメントは **2026-05-13** に発効した「保守フェーズ運用」の継続ルールを定義する。
audit round 52 (stratified A+ 4.986 / 5) で **真値帯域 4.97+** が安定し、構造的 lint 7/7 = 0 件、Topics 22 章 100% 完成、累計 PR ~200 に到達。**master ベース AI 再構成 wiki として現実的に到達可能な最高品質に達した** ため、新規大量執筆フェーズは正式に終了し、以後は「劣化させない」運用に切り替える。

## 1. サイクル

| 周期 | タスク | 担当 / トリガ | 完了の目安 |
|------|--------|--------------|-----------|
| **月次** | master HEAD 追従 (`meta/index/repos.json` の `sources[].ref` と各ページ frontmatter `sources[].ref` を最新 SHA に更新) | 月初の Indexer 再走 | mkdocs build pass / frontmatter lint hard=0 |
| **月次** | stratified audit (偶数 round) | 月中の品質チェック | `meta/quality-audit-NN.md` 追加、`gen_index_banner.py` 再走 |
| **月次** | コミュニティ feedback / GitHub issue 反映 | issue が溜まったタイミング | issue close + 反映 PR |
| **年次** | 大幅変化があれば再構成判断 (区分・章立て・URL 維持を含む全体見直し) | 年初レビュー | 「再構成 yes/no」を本ファイル末尾に追記 |
| **臨時** | 大型新機能 (master に新 area / 新サブシステム追加 等) | upstream 追加検知時 | 別途 **新規イテレーション** を起票 |

## 2. 起票するか保守の範囲か

| 状況 | 扱い |
|------|------|
| 既存ページの誤記 / リンク切れ / 用語ゆれ | 保守 (即 PR) |
| 既存ページの SHA 更新で本文が数行変わる程度 | 保守 (月次の追従 PR にまとめる) |
| 既存ページで本文が大幅に陳腐化 (実装乖離が 30% 超) | 保守 (`discrepancy-found` 付与 + 修正 PR) |
| 既存 area への新 sub-feature が master に追加 | 保守 (該当 area の chapter に追記、必要なら split-child 1 ページ追加) |
| master に **新 area** (例: 新たな OS サブシステム、新 ASIC 抽象層、新コンテナ群) が追加 | **新規イテレーション起票** (`meta/iteration-<id>.md` を作成し、専用 backlog → batch writer サイクル) |
| 言語追加 (英語版 i18n 等) / URL schema 変更 / 大幅構成変更 | **次バージョン (v1.2 / v2.0) 扱い**、roadmap-v2 §2 / §3 へ |

## 3. 品質ガード (保守フェーズ中も常時 enforce)

- frontmatter lint hard = 0 (CI green 必須)
- 構造的 lint 7 種 = 0:
  - broken-link / fnref / mermaid syntax / thin-troubleshoot / phase-table partial-boundary / hld-only 残存 / runbook structure
- mkdocs build `--strict` pass
- 累計 audit 平均 (直近 4 round) ≥ 4.95 / 5
- これらが 1 つでも崩れたら **即修復 PR**。新規追加より優先する

## 4. 再構成イテレーションの判定 (年次レビュー)

下記のいずれかが満たされた場合、次年度に **再構成イテレーション** (=v1.x 内の大型 refactor、または v2.0 移行) を起票する:

1. master 側で章構造の大幅変化 (例: SwSS 系の orchagent 群が再編、`syncd` の差し替え)
2. 累計 audit 平均が 4 round 連続で 4.90 を下回る (=保守だけでは品質維持不可)
3. コミュニティ feedback が 50 件以上溜まり、保守 PR では処理しきれない構造的要求が含まれる
4. ベンダー版 SONiC 取り扱い (roadmap-v2 §3) で方針 A/B/C を採用する判断

## 5. 履歴

| 日付 | 出来事 |
|------|--------|
| 2026-05-13 | 保守フェーズ運用開始 (audit round 52 で 4.986 stratified A+、真値帯域 4.97+ 安定) |

このファイルは生きたドキュメント。月次サイクル実行後は履歴行を追記する。
