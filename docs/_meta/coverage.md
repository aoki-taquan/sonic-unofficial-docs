---
title: カバレッジ
verification: meta
last_verified: 2026-05-11
---

# カバレッジ

このページは `docs/**/*.md` の frontmatter `verification` フィールドを集計したものです。`meta/scripts/gen_coverage.py` で自動生成されます。

各状態の意味は次のとおりです。

- **code-verified**: HLD と現行 master 実装を突き合わせて整合が取れているページ
- **discrepancy-found**: 実装と HLD の間に乖離が確認されたページ（[一覧](discrepancies.md)）
- **issue-confirmed**: GitHub issue / PR で裏取り済みだが実コード突き合わせ未完了のページ
- **hld-only**: HLD のみを根拠にしたページ（読み手は鵜呑みにせず実コード確認推奨）
- **meta**: プロジェクト運用のメタページ（このページや discrepancies など）
- **stub**: 雛形のみ・frontmatter 未設定のページ

## 全体合計

全 **835** ページ。

| 状態 | 件数 |
|------|-----:|
| code-verified | 597 |
| discrepancy-found | 46 |
| issue-confirmed | 0 |
| hld-only | 0 |
| meta | 182 |
| stub | 10 |

## area 別マトリクス

| area | code-verified | discrepancy-found | issue-confirmed | hld-only | meta | stub | 合計 |
|------|-----:|-----:|-----:|-----:|-----:|-----:|-----:|
| `_meta` | 0 | 0 | 0 | 0 | 2 | 0 | 2 |
| `_root` | 0 | 0 | 0 | 0 | 3 | 0 | 3 |
| `acl-qos` | 29 | 2 | 0 | 0 | 0 | 1 | 32 |
| `architecture` | 33 | 8 | 0 | 0 | 0 | 1 | 42 |
| `categories` | 0 | 0 | 0 | 0 | 11 | 0 | 11 |
| `guides` | 0 | 0 | 0 | 0 | 5 | 0 | 5 |
| `internals` | 11 | 1 | 0 | 0 | 0 | 1 | 13 |
| `management` | 35 | 8 | 0 | 0 | 0 | 1 | 44 |
| `overlay` | 8 | 1 | 0 | 0 | 0 | 1 | 10 |
| `platform` | 36 | 7 | 0 | 0 | 0 | 1 | 44 |
| `reference` | 324 | 0 | 0 | 0 | 5 | 1 | 330 |
| `routing` | 45 | 6 | 0 | 0 | 0 | 1 | 52 |
| `switching` | 15 | 4 | 0 | 0 | 0 | 1 | 20 |
| `system` | 61 | 9 | 0 | 0 | 1 | 1 | 72 |
| `topics` | 0 | 0 | 0 | 0 | 155 | 0 | 155 |

推移情報（時系列）は本ページでは扱いません。スナップショットのみ。
