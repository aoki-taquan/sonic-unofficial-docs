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

全 **902** ページ。

| 状態 | 件数 |
|------|-----:|
| code-verified | 566 |
| runbook-verified | 27 |
| discrepancy-found | 102 |
| issue-confirmed | 0 |
| hld-only | 0 |
| meta | 198 |
| stub | 9 |

## area 別マトリクス

| area | code-verified | runbook-verified | discrepancy-found | issue-confirmed | hld-only | meta | stub | 合計 |
|------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| `_meta` | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 5 |
| `_root` | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 3 |
| `acl-qos` | 29 | 0 | 6 | 0 | 0 | 0 | 1 | 36 |
| `architecture` | 32 | 0 | 25 | 0 | 0 | 0 | 1 | 58 |
| `categories` | 0 | 0 | 0 | 0 | 0 | 11 | 0 | 11 |
| `guides` | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 5 |
| `internals` | 10 | 0 | 6 | 0 | 0 | 0 | 1 | 17 |
| `management` | 31 | 0 | 16 | 0 | 0 | 0 | 1 | 48 |
| `overlay` | 16 | 0 | 1 | 0 | 0 | 0 | 1 | 18 |
| `platform` | 35 | 0 | 12 | 0 | 0 | 0 | 1 | 48 |
| `reference` | 304 | 27 | 1 | 0 | 0 | 12 | 0 | 344 |
| `routing` | 43 | 0 | 8 | 0 | 0 | 0 | 1 | 52 |
| `switching` | 15 | 0 | 8 | 0 | 0 | 0 | 1 | 24 |
| `system` | 51 | 0 | 19 | 0 | 0 | 1 | 1 | 72 |
| `topics` | 0 | 0 | 0 | 0 | 0 | 161 | 0 | 161 |

推移情報（時系列）は本ページでは扱いません。スナップショットのみ。
