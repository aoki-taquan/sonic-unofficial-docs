---
title: 古い裏取りページ
description: 古い裏取りページ — last_verified が一定期間以上更新されていないページを一覧する。Verifier 再裏取りのトリガに用いる。
verification: meta
last_verified: 2026-05-11
tags:
  - verification
  - stale
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# 古い裏取りページ

本ページは `docs/**/*.md` の frontmatter `last_verified` を見て、基準日 **2026-05-11** から **90 日以上** 経過したページを一覧する。`meta/scripts/check_stale_verified.py --write` で自動生成される。

対象は `verification` が `meta` / `stub` 以外のページ。上位 50 件まで表示する。

## 再裏取りトリガ

本ページに掲載されたページは Verifier の再裏取り候補になる。詳細な運用手順は `meta/discrepancy-operations.md` および `meta/prompts/verifier.md` を参照（リポジトリ内）。

全 **0** ページが基準を満たした（しきい値 90 日）。

現在、しきい値を超えるページはない。
