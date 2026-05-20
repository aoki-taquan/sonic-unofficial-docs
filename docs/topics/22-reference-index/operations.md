---
title: 運用
description: 運用 — リファレンス索引章での「運用」は、reference ページ / 機能章 / categories の整合を維持し、欠落と discrepancy
  を検出して埋めるための定期作業を扱う。Indexer / Writer / Verifier の境界も整理する。
area: topics
verification: meta
last_verified: 2026-05-12
sources:
- meta/templates/SCHEMA.md
- meta/scripts/gen_chapter_progress.py
- meta/scripts/aggregate_queue.py
- meta/prompts/indexer.md
- meta/prompts/writer.md
- meta/prompts/verifier.md
keywords:
- Reference
- 運用
- 索引メンテ
- discrepancy
- reference gap
- verification queue
related:
  cli: []
  config_db: []
  yang: []
  _no_related_cli: true
  _no_related_cdb: true
---

# 運用

リファレンス索引章での「運用」は、reference ページ / 機能章 / categories の整合を維持し、**欠落と discrepancy を検出して埋めるための定期作業** を扱う。本ページは「索引そのものをどう運用するか」が中心で、[SONiC](../../reference/glossary.md#term-sonic) 装置の運用ではないことに注意。

## 定期チェックの流れ

主要な再計算は次の 4 段。CI と手元で同じスクリプトを使う。

```bash
# 1. frontmatter lint (全 docs)
python3 meta/scripts/frontmatter_lint.py docs/

# 2. 章別進捗表の再生成
python3 meta/scripts/gen_chapter_progress.py
python3 meta/scripts/gen_chapter_progress.py --check   # drift 検出だけ

# 3. verification queue の per-page → 全体集約
python3 meta/scripts/aggregate_queue.py

# 4. mkdocs strict build
. .venv/bin/activate && mkdocs build --strict
```

このうち (2) と (3) が「索引のメタ情報」を再計算する。(1) と (4) は CI でも同じく走る安全網。

## reference gap を埋める動線

reference 側に未カバーの項目があると、機能章の `related` に書かれた名前が解決できない、または索引から該当ページに飛べないという事象になる。検出と修復の標準動線は次の通り。

1. **Indexer 出力を見る**: `.cache/sonic-sources/` の最新 clone から `meta/index/cli.json`、`meta/index/yang.json`、`meta/index/config-db.json` を再生成し、reference 側にまだ存在しない slug を抽出する。
2. **`meta/reference-gaps.md` に積む**: 抽出結果は人間レビュー用に `meta/reference-gaps.md` (見出しごとに CLI / [CONFIG_DB](../../reference/glossary.md#term-config_db) / [YANG](../../reference/glossary.md#term-yang)) に追加する。優先度は「機能章が `related` で参照しているのに reference が無い」 > 「Indexer 側にあるが機能章未参照」の順。
3. **Writer に backlog を投入**: `meta/backlog/<area>/<slug>.json` を作って Writer が拾えるようにする。area は `reference-cli` / `reference-config-db` / `reference-yang` を使い分ける。
4. **生成 PR の merge 後に再計算**: reference が増えた後、機能章側の `related` に表示名を足し、`frontmatter_lint.py` で再検査する。

`meta/reference-gaps.md` を空に保つことは原則目標にしない (新規 [HLD](../../reference/glossary.md#term-hld)/CLI が常に増えるため)。一定量を超えたら一括 Writer バッチで掃く運用が現実的。

## discrepancy 運用

`verification: discrepancy-found` のページは、HLD の記述と実コードの挙動が乖離している箇所を示す。索引側での運用は次の通り。

- 各 discrepancy ページは frontmatter に `monitor: not_implemented | evolved_beyond_hld | partially_implemented | deprecated` を持つ。
- `docs/_meta/discrepancies.md` で全 discrepancy ページを一覧化し、`monitor` 値別に分類する。
- 索引から discrepancy 一覧へのリンクは [品質と gap](quality-gaps.md) に集約する。
- HLD 側の改稿や PR で discrepancy が解消したら、`verification: code-verified` に昇格 PR を上げる。Verifier の標準ワークフロー。

discrepancy が増えること自体は問題ではなく、「discrepancy が `hld-only` のまま放置されない」ことが運用上の不変条件である。

## 並走バッチでの索引保護

Writer / Verifier を並列に動かすとき、索引層のメタファイル編集は衝突しやすい。実害が出た過去パターン (CLAUDE.md §9 参照) と対策は次の通り。

| 衝突源 | 症状 | 対策 |
| --- | --- | --- |
| `meta/verification-queue.json` を複数 Writer が同時編集 | commit が握り潰される | per-page `meta/queue/<slug>.json` に分割し、`aggregate_queue.py` で集約 |
| 章 `index.md` の進捗表ブロックを手で編集 | 次回 `gen_chapter_progress.py` で上書き | 進捗表は機械生成領域。補足は `<!-- next-reads -->` の上に書く |
| `related` 更新と新 reference の追加が別 PR | 一時的に lint が落ちる | reference 新規と `related` 追加は同 PR にまとめるか、reference 先行 → `related` 後追いの順を守る |

並走時は worktree (`.claude/worktrees/`) で完全分離し、`git add -A` を避けて対象ファイルだけを add する。

## ナビゲーションの保守

索引としての価値は、3 つの index ページ (`cli-index.md` / `config-db-index.md` / `yang-index.md`) と各 reference ページの `related` の往復で担保される。保守時に注意するのは次の点。

- 新 reference ページを足したら、対応する index ページの分類表 (アルファベット順 / カテゴリ順) に行を足す。
- index ページの並びを変えたら、`docs/.pages` (mkdocs-awesome-pages) を読まれて nav に反映されることを確認する。
- 章番号の振り直し (`NN-` prefix の変更) は全 link 影響が大きいので原則しない。やる場合は専用 PR で `redirects.yml` も同時に追加。

## 失敗・劣化を検出する観点

索引の運用が劣化していると、読者は機能章から reference に飛べず、reference から機能章に戻れなくなる。次の sign を定期チェックする。

- `frontmatter_lint.py` の警告件数が増えている → `related` の表記揺れか reference 欠落。
- `gen_chapter_progress.py --check` が CI で落ちる → 機能章本文の placeholder / missing が増えている。
- `mkdocs build --strict` が dead link で落ちる → reference ページの rename / 削除に追従していない。
- `docs/_meta/discrepancies.md` の `hld-only` 残数が 0 でない → Verifier バッチが追い付いていない。

これらは Phase 6 で 0 まで詰めたメトリクスである。劣化した時点で索引層のメンテをロールバックして原因を特定する。

## メトリクスと閾値

索引層の健全性を測るメトリクスと、運用上の閾値は次の通り。

| メトリクス | 計測元 | 目標値 |
| --- | --- | --- |
| `frontmatter_lint.py` 警告件数 | CI ステップ | 0 |
| `gen_chapter_progress.py --check` の drift | CI ステップ | 0 |
| `verification: hld-only` 残数 | `docs/_meta/discrepancies.md` 集計 | 0 |
| `meta/reference-gaps.md` の未着手項目 | Indexer 出力との差分 | 50 以下 |
| `discrepancy-found` のうち `monitor` 未指定数 | frontmatter スキャン | 0 |
| dead link 数 (mkdocs strict) | `mkdocs build --strict` | 0 |

これらは PR の本文や release note に貼り、推移を可視化できる状態にしておく。劣化が出たら直近 merge から bisect する。

## サイクル運用の例

実運用での 1 週間の例を 1 つ提示する。

- 月曜: 前週末までの merge を集計し、`docs/_meta/discrepancies.md` と `meta/reference-gaps.md` を更新。
- 火曜〜木曜: Writer バッチを並走させて reference-gaps を Top 10 ほど消化。
- 金曜: Verifier バッチで `code-verified` への昇格 PR を 5〜10 件投入。
- 週末 (人) または cron (bot): `gen_chapter_progress.py` と `frontmatter_lint.py` を再実行し、進捗表 PR を作る。

このペースを維持できれば、機能章と reference の往復は破綻しない。

## 章の出口

- 索引そのものの設計 → [概念](concept.md)。
- frontmatter / 生成スクリプトの使い方 → [設定](setup.md)。
- 品質と未カバー → [品質と gap](quality-gaps.md)。
- 内部構造 → [内部実装](internals.md) と [発展](advanced.md)。

<!-- glossary-links-injected: 8ba32e5aa69d -->
