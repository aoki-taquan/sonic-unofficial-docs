---
title: カバレッジ
description: "カバレッジ — このページは docs/**/*.md の frontmatter verification フィールドを集計したものです。meta/scripts/gen_coverage.py で自動生成されます。"
verification: meta
last_verified: 2026-05-11
---

# カバレッジ

このページは `docs/**/*.md` の frontmatter `verification` フィールドを集計したものです。`meta/scripts/gen_coverage.py` で自動生成されます。

各状態の意味は次のとおりです。

- **code-verified**: HLD と現行 master 実装を突き合わせて整合が取れているページ
- **runbook-verified**: Runbook 専用ステータス。実運用で症状再現性が確認されており、HLD 一致は副次的
- **discrepancy-found**: 実装と HLD の間に乖離が確認されたページ（[一覧](discrepancies.md)）
- **issue-confirmed**: GitHub issue / PR で裏取り済みだが実コード突き合わせ未完了のページ
- **hld-only**: HLD のみを根拠にしたページ（読み手は鵜呑みにせず実コード確認推奨）
- **meta**: プロジェクト運用のメタページ（このページや discrepancies など）
- **stub**: 雛形のみ・frontmatter 未設定のページ

## 全体合計

全 **1104** ページ。

| 状態 | 件数 |
|------|-----:|
| code-verified | 762 |
| runbook-verified | 27 |
| discrepancy-found | 113 |
| issue-confirmed | 6 |
| hld-only | 1 |
| meta | 194 |
| stub | 1 |

## area 別マトリクス

| area | code-verified | runbook-verified | discrepancy-found | issue-confirmed | hld-only | meta | stub | 合計 |
|------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| `_meta` | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 5 |
| `_root` | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 4 |
| `acl-qos` | 29 | 0 | 6 | 0 | 0 | 1 | 0 | 36 |
| `architecture` | 34 | 0 | 25 | 0 | 1 | 1 | 0 | 61 |
| `categories` | 0 | 0 | 0 | 0 | 0 | 11 | 0 | 11 |
| `guides` | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 5 |
| `internals` | 12 | 0 | 6 | 0 | 0 | 1 | 0 | 19 |
| `management` | 32 | 0 | 16 | 2 | 0 | 1 | 0 | 51 |
| `overlay` | 19 | 0 | 1 | 0 | 0 | 1 | 0 | 21 |
| `platform` | 35 | 0 | 13 | 3 | 0 | 1 | 0 | 52 |
| `reference` | 467 | 27 | 8 | 0 | 0 | 13 | 1 | 516 |
| `routing` | 45 | 0 | 12 | 0 | 0 | 1 | 0 | 58 |
| `switching` | 18 | 0 | 8 | 0 | 0 | 1 | 0 | 27 |
| `system` | 56 | 0 | 18 | 1 | 0 | 2 | 0 | 77 |
| `topics` | 15 | 0 | 0 | 0 | 0 | 146 | 0 | 161 |

推移情報（時系列）は本ページでは扱いません。スナップショットのみ。
