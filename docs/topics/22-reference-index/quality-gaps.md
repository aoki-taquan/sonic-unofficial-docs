---
title: 品質と gap
description: 品質と gap — 本ページは、Phase 6 以降の検証作業で残った 2 種類の「不完全さ」をどこで追跡するかをまとめる。
area: topics
verification: meta
last_verified: 2026-05-10
related:
  cli:
  - show techsupport
  config_db: []
  yang: []
  _no_related_config_db: true
  _no_related_yang: true
---

# 品質と gap

本ページは、Phase 6 以降の検証作業で残った 2 種類の「不完全さ」をどこで追跡するかをまとめる。

- **discrepancy**: [HLD](../../reference/glossary.md#term-hld) と現行実装の挙動が一致していないと裏取りで分かった点。`docs/_meta/discrepancies.md` に集約。
- **reference gap**: CLI / [CONFIG_DB](../../reference/glossary.md#term-config_db) / [YANG](../../reference/glossary.md#term-yang) のうち、まだ辞書化が追いついていない名前。`meta/reference-gaps.md` に集約。

## discrepancy の追跡

Phase 6 で `verification: hld-only` のページを 0 件にし、すべて `code-verified` か `discrepancy-found` に振り分けた。`discrepancy-found` が付いたページは [Discrepancy index](../../reference/verification/discrepancy-index.md) から area 別・`monitor` タグ別に一覧できる（自動生成）。

各ページ本文末尾には、HLD 記述と実装の差分が「実装との乖離」節として記録されている。読み手は次の優先順で読むと安全である。

1. 章のページ (topics) で機能の意図を掴む。
2. 関連する HLD 派生ページ冒頭の `verification` フィールドを確認する。
3. `discrepancy-found` の場合は本文末尾の「実装との乖離」節を読む。
4. discrepancy 一覧 ([Discrepancy index](../../reference/verification/discrepancy-index.md)) で同じ area の他ページの傾向も確認する。

discrepancy が新規に追加される導線は次の通り。

- Verifier ロール (`meta/prompts/verifier.md`) が `code-verified` ページを抜き打ちで再検証する。
- 既存ページに `last_verified` から 1 年以上経過したものが出てきた場合、再検証対象に上げる。
- 新規 HLD 移植 (Writer) は最初から `code-verified` か `discrepancy-found` を付ける運用に統一済み。

## reference gap の追跡

`meta/reference-gaps.md` には、Indexer が `sonic-net/sonic-utilities` の CLI / `sonic-yang-models` の YANG モジュール / CONFIG_DB の table を棚卸ししたうちで、まだ辞書化が追いついていないものを並べてある。2026-05-10 時点の傾向は次の通り。

- **CLI**: 72 ページが辞書化済 (`docs/reference/cli/`)。残りはサブグループ単位で重要度評価済み。
- **CONFIG_DB**: 293 ページが辞書化済 (`docs/reference/config-db/`)。残りは派生 / 内部 / [DPU](../../reference/glossary.md#term-dpu) 専用などを中心に未カバー。
- **YANG**: 84 / 136 モジュール (約 62 %) を辞書化 (`docs/reference/yang/`)。

機能章を書く際の運用は次の通り。

- 章の本文中で参照したい reference ページがまだ無いと気付いた場合、その時点で `meta/reference-gaps.md` を更新する代わりに、章本文側で table 名 / コマンド名を文中に残しておき、後続の Reference Writer バッチで拾えるようにする。
- 章本文に「ここで本来引きたい reference ページが未作成」と明示する場合は、機能章の該当ページに簡潔に書き添える (章スコープでは新規辞書ページを作らない)。

## Phase B の追跡方法

Phase B の章実装は、機能章ごとに 1 PR で進める。各章実装後に reference 側へ波及する変更が出た場合は、別 PR (reference バッチ) で reference 辞書を追加する。両者を 1 PR に混ぜないことで、章のレビュー観点 (読み物としての構造) と reference のレビュー観点 (辞書の正確さ) を分離できる。

discrepancy の解消は、HLD 側を書き換えるのではなく、実装と差分のある章本文側に明記する方向で運用する。HLD は外部リソースであり、本ドキュメントが直接修正する対象ではない。

## 関連ページ

- [Discrepancy index](../../reference/verification/discrepancy-index.md)
- [リファレンス トップ](../../reference/index.md)
- [リファレンス横断索引 トップ](index.md)

<!-- glossary-links-injected: ae9992096eee -->
