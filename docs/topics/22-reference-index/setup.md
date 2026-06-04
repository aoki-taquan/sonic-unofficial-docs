---
title: 設定
description: 設定 — リファレンス索引章での「設定」は、reference 索引そのものを生成・更新するための meta 設定を扱う。読者が CLI
  / CONFIG_DB / YANG を辿るための frontmatter スキーマ、related ブロックの書き方、自動生成スクリプトの入口を整理する。
area: topics
verification: meta
last_verified: 2026-05-12
sources: []
keywords:
- Reference
- 索引
- frontmatter
- related
- 自動生成
- CLI index
- CONFIG_DB index
- YANG index
related:
  cli: []
  config_db: []
  yang: []
  _no_related_cli: true
  _no_related_cdb: true
  _no_related_yang: true
---

# 設定

リファレンス索引章での「設定」は、`docs/reference/` 配下の辞書ページ群と機能章の往復を支える **frontmatter / related / 自動生成スクリプト** の使い方を整理する。読者が「索引を読みやすく保ち、自動チェックを通す」ための meta 設定が中心になる。

## frontmatter スキーマの要点

reference ページと機能章は同じ frontmatter スキーマで管理されている。索引が成立する最低条件は次の通り。詳細は [`meta/templates/SCHEMA.md`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/meta/templates/SCHEMA.md) を読む。

| キー | 必須 | 用途 |
| --- | --- | --- |
| `title` | yes | 索引や `.pages` のラベル |
| `description` | yes | 検索結果や OG description に出る |
| `area` | yes | `topics` / `reference` / `categories` / `architecture` … |
| `verification` | yes | `meta` / `code-verified` / `discrepancy-found` |
| `last_verified` | yes | 裏取り日付。CI で stale 検出に使う |
| `sources` | recommended | reference や [HLD](../../reference/glossary.md#term-hld) への根拠リンク |
| `related.cli` / `related.config_db` / `related.yang` | recommended | 機能章 → reference の前方リンク |
| `keywords` | optional | search index 用 |

機能章は `related` を埋め、reference ページは `sources` を埋めるのが基本配置である。`related` に並べた名前は対応する reference ページが存在する前提なので、無い場合は reference を新規作成するか `meta/reference-gaps.md` に記録する。

## related ブロックの書き方

機能章の `index.md` と各サブページに `related.cli` / `related.config_db` / `related.yang` を書く。書式は YAML list で、reference ページの **slug ではなく表示名** を入れる。

```yaml
related:
  cli:
    - config bgp
    - show bgp
  config_db:
    - BGP_NEIGHBOR
    - BGP_PEER_GROUP
  yang:
    - sonic-bgp-global
    - sonic-bgp-neighbor
```

CI lint (`meta/scripts/frontmatter_lint.py` 系) が、これらが reference ページ slug に解決できるかを確認する。失敗時は次のいずれかが原因なので順に潰す。

- 表記揺れ (`BGP_neighbor` のような大文字小文字違い、`-` と `_` の混在)。
- reference ページ未作成 (`meta/reference-gaps.md` に追記し、Writer に拾わせる)。
- 機能章側の typo (`related` の親キー名違いなど)。

## 自動生成スクリプトの入口

reference 索引と機能章の進捗は、いくつかのスクリプトでメタ情報を再計算する。手元で動かす時の入口は次の通り。

```bash
# 章ごとの進捗表 (placeholder/missing/complete) を index.md に埋める
python3 meta/scripts/gen_chapter_progress.py

# drift 検出のみ (CI で使用)
python3 meta/scripts/gen_chapter_progress.py --check

# per-page verification queue を集約
python3 meta/scripts/aggregate_queue.py

# frontmatter lint
python3 meta/scripts/frontmatter_lint.py docs/
```

`gen_chapter_progress.py` は `docs/topics/<NN>-*/{concept,setup,operations,internals,advanced}.md` を走査し、各 sub-page の行数と `verification` を読み、章 `index.md` に `<!-- chapter-progress -->` ブロックを書き戻す。閾値は 100 行 (本文)。

`aggregate_queue.py` は `meta/queue/*.json` を読み、`meta/verification-queue.json` に再集約する。並走バッチでの編集レースを避けるための per-page 分割と統合ステップになっている。

## ローカルでの build / lint チェック

reference 索引に変更を入れたら、push 前に次の 3 段を回す。

```bash
# 1. frontmatter / link 健全性
python3 meta/scripts/frontmatter_lint.py docs/

# 2. 進捗表の再計算 (drift があれば commit)
python3 meta/scripts/gen_chapter_progress.py

# 3. site build (strict)
. .venv/bin/activate
mkdocs build --strict
```

`--strict` で死に link や mkdocs の warning を CI と同条件で検出できる。事前に `rm -rf site` で旧成果物を消す。

## つまずきパターン

- **`related` に書いた CLI 名が reference に解決できない**: コマンド群の slug 設計を `docs/reference/cli/index.md` で確認し、`config-bgp` (subgroup) と `config` (root) の混同を直す。
- **章 `index.md` の `<!-- chapter-progress -->` ブロックが手で書き換えられている**: 次回 `gen_chapter_progress.py` で上書きされる。本文側に書きたい補足は `<!-- next-reads -->` の上に出す。
- **`reference-gaps.md` がずっと積み上がる**: Indexer の出力に対し Writer が拾い切れていない。`meta/backlog/22-reference-index/*.json` に新規 issue として書き戻す。
- **新規 reference ページを足したのに機能章の `related` に出てこない**: 機能章の frontmatter を手で追記する必要がある。`related` は自動投影されない。

## CI で走るチェック一覧

GitHub Actions では PR ごとに次のチェックが走る。索引層の保護に直結するのは frontmatter と進捗表の 2 つ。

| ステップ | 失敗時に起きること |
| --- | --- |
| `frontmatter_lint.py` | `related` の表記揺れや必須キー欠落で PR が赤くなる |
| `gen_chapter_progress.py --check` | 章の placeholder/missing 数と本文の実態が乖離していると赤くなる |
| `aggregate_queue.py` (manual / batch) | per-page queue と全体 queue がずれていると赤くなる |
| `mkdocs build --strict` | dead link / 重複 anchor / yaml 構文エラー |
| pre-commit (`.pre-commit-config.yaml`) | EOF / trailing whitespace 等の体裁 |

ローカルで先に同じ stack を回しておくと PR で何度も赤を踏まない。

## 索引メンテの優先順位

reference 索引と機能章の往復を維持するうえで、メンテの優先順位は次の通り。

1. **既存 dead link を直す** (`mkdocs build --strict` で発見されるもの)。索引が壊れる最も直接的な要因。
2. **`related` の表記揺れを直す**。一度直すと frontmatter_lint が以降を防いでくれる。
3. **placeholder ページの本文を埋める**。`gen_chapter_progress.py --check` を緑にする。
4. **reference 未カバー (`meta/reference-gaps.md`) を Writer に流す**。新規 reference を作成し `related` に追加する。
5. **discrepancy の昇格 PR を Verifier から流す**。`hld-only` を残さない不変条件を守る。

(1) と (2) は CI で機械的に検出されるので毎日触る。(3)〜(5) は週次〜月次のサイクルで回せばよい。

## 章の出口

- 索引の運用 → [運用](operations.md)。
- 索引の品質と未カバー領域 → [品質と gap](quality-gaps.md)。
- frontmatter / 命名規約の根拠 → [`meta/templates/SCHEMA.md`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/meta/templates/SCHEMA.md)。

<!-- glossary-links-injected: 167700005048 -->
