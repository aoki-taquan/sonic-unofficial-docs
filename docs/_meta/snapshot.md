---
title: スナップショット
area: meta
verification: meta
last_verified: 2026-05-12
sources: []
---

# スナップショット

リポジトリ全体の状態を 1 ページに集約した自動生成サマリ。個別の詳細は `coverage.md` / `sitemap.md` / `discrepancies.md` を参照。

!!! note "生成元"
    `python3 meta/scripts/gen_snapshot.py` で再生成。
    `--check` で drift 検出 (CI integration 用)。

## verification 分布

全 **894** ページ。

| verification | 件数 |
|---|---:|
| code-verified | 586 |
| runbook-verified | 27 |
| discrepancy-found | 74 |
| issue-confirmed | 0 |
| hld-only | 0 |
| meta | 198 |
| stub | 9 |
| **合計** | **894** |

## Topics 22 章 sub-page 完成度

5 種 (concept/setup/operations/internals/advanced) × 22 章 = 110 想定。閾値: 本文 100 行未満は placeholder 扱い。

| 状態 | 件数 |
|---|---:|
| 完成 | 68 |
| placeholder | 42 |
| 欠落 | 0 |
| **合計** | **110** |

## Reference カバレッジ

| 種別 | 公開ページ | 索引総数 | カバレッジ |
|---|---:|---:|---:|
| CLI | 72 | 298 | 24.2% |
| CONFIG_DB | 121 | — | — |
| YANG | 84 | 136 | 61.8% |

## 最新 quality-audit

- round **38** — 総平均スコア **4.986 / 5**
- 詳細: `meta/quality-audit-38.md`

## その他指標

| 項目 | 値 |
|---|---:|
| 低密度ページ残数 (link-density < 2) | 0 |
| backlog 残数 (active) | 10 |

