---
title: スナップショット
area: meta
verification: meta
last_verified: 2026-06-04
sources: []
---

# スナップショット

リポジトリ全体の状態を 1 ページに集約した自動生成サマリ。個別の詳細は `coverage.md` / `sitemap.md` / `discrepancies.md` を参照。

!!! note "生成元"
    `python3 meta/scripts/gen_snapshot.py` で再生成。
    `--check` で drift 検出 (CI integration 用)。

## verification 分布

全 **1104** ページ。

| verification | 件数 |
|---|---:|
| code-verified | 761 |
| runbook-verified | 27 |
| discrepancy-found | 113 |
| issue-confirmed | 7 |
| hld-only | 1 |
| meta | 194 |
| stub | 1 |
| **合計** | **1104** |

## last_verified 鮮度

基準日 **2026-06-04**。

| バケツ | 件数 |
|---|---:|
| 今日 (0d) | 43 |
| 7 日以内 (1-7d) | 2 |
| 30 日以内 (8-30d) | 1056 |
| 30 日超 / 古い | 0 |
| 不明 / パース不可 | 3 |

## Topics 22 章 sub-page 完成度

5 種 (concept/setup/operations/internals/advanced) × 22 章 = 110 想定。閾値: 本文 100 行未満は placeholder 扱い。

| 状態 | 件数 |
|---|---:|
| 完成 | 71 |
| placeholder | 39 |
| 欠落 | 0 |
| **合計** | **110** |

## Reference カバレッジ

| 種別 | 公開ページ | 索引総数 | カバレッジ |
|---|---:|---:|---:|
| CLI | 72 | 298 | 24.2% |
| CONFIG_DB | 293 | — | — |
| YANG | 84 | 136 | 61.8% |

## Mermaid カバレッジ (Reference 系)

各 Reference サブツリーで ` ```mermaid ` ブロックを含むページ比率。

| 種別 | mermaid あり | 総ページ | カバレッジ |
|---|---:|---:|---:|
| CONFIG_DB | 232 | 293 | 79.2% |
| CLI | 72 | 72 | 100.0% |
| YANG | 84 | 84 | 100.0% |

## ops-hint カバレッジ (CLI Reference)

`<!-- ops-hint -->` 埋め込み済み: **45 / 72** (62.5%)

## Glossary

| 項目 | 値 |
|---|---:|
| 用語数 (`### ` アンカー) | 325 |
| docs 内被リンク数 | 20001 |

## 直近 5 round quality-audit

| round | 総平均スコア / 5 |
|---:|---:|
| 52 | 4.986 |
| 51 | 4.986 |
| 50 | 4.972 |
| 49 | 4.974 |
| 48 | 5.000 |

- 最新詳細: `meta/quality-audit-52.md`

## Lint / informational 検出件数

各レポート (`meta/*-report*.md` / `meta/*-violations.md`) から抽出した検出件数。strict / informational を区別せず一覧化する。

| 項目 | 件数 |
|---|---:|
| frontmatter-lint (hard) | 0 |
| frontmatter-lint (warn) | 0 |
| link-density low (<2.0/1k) | 68 |
| link-density high (>30.0/1k) | 0 |
| discrepancy-related-yang violations | 0 |
| related.* empty pages | 0 |
| daemon-name violations | 0 |

## その他指標

| 項目 | 値 |
|---|---:|
| 低密度ページ残数 (link-density < 2) | 68 |
| backlog 残数 (active) | 8 |

## 関連メタページ

本スナップショットと併読する自動生成メタ系ページ。それぞれ独立した観点で repo 全体を俯瞰する。

- [residual-tasks](../reference/verification/residual-tasks.md) — verification 残タスク / 未裏取り箇所の一覧
- [stale-verified](../reference/verification/stale-verified.md) — `last_verified` が古いページ (再裏取り候補)
- [sources-freshness](../reference/verification/sources-freshness.md) — 引用元 SHA の鮮度 / 参照リポジトリの追従状況
- [changelog](changelog.md) — 主要変更履歴 (自動生成サマリ含む)
- [discrepancy-index](../reference/verification/discrepancy-index.md) — HLD と実装の乖離を抽出したインデックス

