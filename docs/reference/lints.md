---
title: Lint 一覧と CI 状態
area: meta
verification: meta
last_verified: 2026-05-12
description: lint 一覧と CI 状態
tags:
- meta
- lint
- ci
related:
  _no_related_cdb: true
---

# Lint 一覧と CI 状態

本リポジトリには `meta/scripts/` 配下に多数の lint / 機械生成スクリプトがあり、
PR ごとに GitHub Actions (`.github/workflows/ci.yml`) で実行される。
各スクリプトの目的と、CI ゲートとしての位置付け（**strict** = 失敗で CI 落ち /
**informational** = 失敗しても CI は通る / **gen-check** = 機械生成出力の drift 検査 /
**local-only** = CI 未連携） を一覧化する。

スクリプト本体は `meta/scripts/<name>.py` にあり、いずれも `python3` で直接実行できる。

## Lint スクリプト (`check_*` / `frontmatter_lint`)

| script | 目的 | CI 状態 |
|---|---|---|
| `frontmatter_lint.py` | frontmatter schema (v2) 検証。verification × sources、verification × 警告 admonition、verification × 「実装との乖離」節、`last_verified` 書式、`title` / `area` enum、`monitor` enum、mojibake / 非 ASCII 制御文字、`sources[].path` 生存性 (cache がある場合のみ)、`description` 推奨 (warn) | strict |
| `check_runbook_status.py` | `docs/reference/runbooks/*.md` の `verification` が `hld-only` / `issue-confirmed` に退化していないか検証 | strict |
| `check_runbook_structure.py` | runbook ページに 5 節 (症状 / 切り分け / 確認コマンド / よくある原因 / 関連) が揃っているか検証 | strict |
| `check_discrepancy_related.py` | `verification: discrepancy-found` ページが `related.yang` を 1 件以上持つか検証 (`_no_related: true` で opt-out) | strict |
| `check_pages_integrity.py` | `docs/**/.pages` (mkdocs-awesome-pages) の `nav:` と実ファイルの整合: missing / orphan / duplicate 検出 | strict |
| `check_monitor_consistency.py` | `verification: discrepancy-found` ページの `monitor` タグと本文キーワードの整合性検証 | informational |
| `check_verification_self_consistency.py` | `code-verified` / `runbook-verified` を名乗りながら本文に「未確認」「TBD」「未実装」等を残しているページの検出 | informational |
| `check_citation_quality.py` | 裏取り済み (`code-verified` / `runbook-verified` / `discrepancy-found`) なのに脚注も `<!-- evidence: -->` も無いページの検出 | informational |
| `check_broken_links.py` | `docs/**/*.md` の intra-doc Markdown リンク (相対パス + `#anchor`) の解決可否を検証 | informational |
| `check_link_density.py` (`--strict-split-child`) | `split-child` のナビゲーション整合性検証 (CI で strict 実行) | **strict** |
| `check_link_density.py` (density report) | 本文字数あたりリンク数 (density) が極端に低い / 高いページの report | informational |
| `check_stale_verified.py` | `last_verified` が閾値日数 (デフォルト 90 日) 以上古いページの検出 | informational |
| `check_sources_freshness.py` | `meta/index/repos.json` の pinned SHA と `.cache/sonic-sources/<repo>/` の HEAD / upstream を突合し behind 件数を表示 | local-only |

## 機械生成スクリプト (`gen_*`)

`gen_*` 系は静的サイトに含めるページや埋め込みブロックを自動生成する。CI では生成出力の
**drift 検査**として `--check` モードで動作し、ローカルで再生成し忘れていないかを検出する。

| script | 目的 | CI 状態 |
|---|---|---|
| `gen_index_banner.py` | `docs/index.md` の品質バナー (verification 集計 + audit 平均) 自動更新 | gen-check (strict) |
| `gen_discrepancy_index.py` | `docs/reference/verification/discrepancy-index.md` の自動生成 (area × monitor 一覧) | gen-check (strict) |
| `gen_coverage.py` | `docs/_meta/coverage.md` の area × verification マトリクス自動生成 | gen-check (strict) |
| `gen_cross_ref.py` | Topics ↔ area ページ間の双方向 back-ref ブロック (`<!-- topics-back-ref -->`) | gen-check (strict) |
| `gen_glossary_xref.py` | `docs/reference/glossary.md` の用語別逆引き索引 (`<!-- glossary-xref -->`) | gen-check (strict) |
| `gen_next_reads.py` | Topics 章 index の「次に読むべき記事」ブロック | gen-check (informational) |
| `gen_chapter_progress.py` | Topics 章 index の「章構成と進捗」テーブル | gen-check (informational) |
| `gen_sitemap.py` | `docs/_meta/sitemap.md` 自動生成 | gen-check (informational) |
| `gen_changelog.py` | `docs/_meta/changelog.md` を merged PR 一覧から生成 | local-only |
| `gen_descriptions.py` | 各ページの `description:` frontmatter を H1 + 冒頭段落から自動補完 | local-only |
| `gen_cdb_mermaid.py` | [CONFIG_DB](../reference/glossary.md#term-config_db) reference ページにミニ data-flow mermaid 埋め込み | local-only |
| `gen_cli_mermaid.py` | CLI reference ページにミニ data-flow mermaid 埋め込み | local-only |
| `gen_yang_mermaid.py` | [YANG](../reference/glossary.md#term-yang) reference ページにミニ data-flow mermaid 埋め込み | local-only |
| `gen_ref_triangle.py` | Reference (YANG ↔ CONFIG_DB ↔ CLI) sibling 三角リンクの埋め込み | local-only |
| `gen_topics_admonition.py` | [HLD](../reference/glossary.md#term-hld) 派生ページ冒頭に Topics 章への誘導 admonition を挿入 | local-only |

## CI ワークフロー

CI の実体は `.github/workflows/ci.yml` にあり、以下ジョブに分かれる:

- `build` — `mkdocs build --strict` で全ページのビルド検証
- `frontmatter-lint` — `frontmatter_lint.py` を始め、上記 lint 群の大部分を実行
- `quality-banner` — `gen_index_banner.py --check`
- `discrepancy-index` — `gen_discrepancy_index.py --check`
- `coverage-matrix` — `gen_coverage.py --check` + `check_stale_verified.py --check` + `gen_sitemap.py --check`
- `topics-back-ref` — `gen_cross_ref.py --check`
- `glossary-xref` — `gen_glossary_xref.py --check`

deploy は `.github/workflows/deploy.yml` が main push 契機で `gh-pages` ブランチへ `mkdocs gh-deploy --force --clean` を実行する。

## 運用メモ

- **strict lint を新規追加するときは**、先に `informational` で 1 リリース走らせ、違反 0 を確認してから `--check` 失敗で exit 1 に昇格させる。違反 0 のうちに strict 化しないと既存ページが大量に refused されて運用が止まる
- **gen-check** が drift で落ちたときは、ローカルで対応する `gen_*.py` を `--check` 無しで再実行 → 出力ファイルを commit に含めて push し直すのが手順
- `check_sources_freshness.py` / `gen_changelog.py` 等の **local-only** スクリプトは `.cache/` や `gh` 認証に依存するため CI からは除外している。定期メンテのときに手動で回す
- すべての lint は `python3 meta/scripts/<name>.py --help` で詳細オプションを確認できる

<!-- glossary-links-injected: 20dbc11976b6 -->
