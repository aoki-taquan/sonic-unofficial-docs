---
title: Lint 一覧と CI 状態
area: meta
verification: meta
last_verified: 2026-06-06
description: meta/scripts/ 配下の lint / 生成スクリプトの目的と CI ゲート状態を一覧化する。
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
各スクリプトの目的と CI ゲートとしての位置付け を一覧化する。

CI 状態のラベル定義:

- **strict** — exit != 0 で job が落ちる (PR ブロッキング)
- **informational** — `|| true` で吸収。失敗しても CI は通る (report 用途)
- **gen-check** — 機械生成物の drift 検査。strict / informational をさらに併記
- **local-only** — CI に組み込まれていない。手元で手動実行する

スクリプト本体は `meta/scripts/<name>.py` にあり、いずれも `python3` で直接実行できる
(`--help` でオプション確認可能)。

## Lint スクリプト (`check_*` / `frontmatter_lint`)

| script | 目的 | CI 状態 |
|---|---|---|
| `frontmatter_lint.py` | frontmatter schema (v2) 検証。verification × sources、verification × 警告 admonition、verification × 「実装との乖離」節、`last_verified` 書式、`title` / `area` enum、`monitor` enum、mojibake / 非 ASCII 制御文字、`sources[].path` 生存性 (cache がある場合のみ)、`description` 推奨 (warn) | strict |
| `check_invisible_chars.py` | zero-width / bidi 制御 / tag char (prompt-injection ベクター) / NBSP 等の非標準空白を docs と meta 全体から検出。`<!-- allow-invisible -->` でファイル単位の許可可。0 件キープが必須 | strict |
| `check_runbook_status.py` | `docs/reference/runbooks/*.md` の `verification` が `hld-only` / `issue-confirmed` に退化していないか検証 | strict |
| `check_runbook_structure.py` | runbook ページに 5 節 (症状 / 切り分け / 確認コマンド / よくある原因 / 関連) が揃っているか検証 | strict |
| `check_pages_integrity.py` | `docs/**/.pages` (mkdocs-awesome-pages) の `nav:` と実ファイルの整合: missing / orphan / duplicate 検出 | strict |
| `check_discrepancy_related.py` | `verification: discrepancy-found` ページが `related.yang` を 1 件以上持つか検証 (`_no_related: true` で opt-out) | strict |
| `check_link_density.py` (`--strict-split-child`) | `split-child` ページのナビゲーション整合性検証 | strict |
| `check_link_density.py` (density report) | 本文字数あたりリンク数 (density) が極端に低い / 高いページの report | informational |
| `check_mermaid_syntax.py` | mermaid フェンス内の構文を node ベース parser (`mermaid_parse.mjs`) または高確度静的ヒューリスティックで検査 | strict |
| `check_partial_boundary.py` (`--strict-phase-table`) | [HLD](../reference/glossary.md#term-hld) 系 `monitor: partially_implemented` ページにフェーズ別表 (Phase × 実装済 × 未実装 が同一表に揃う) を必須化 | strict |
| `check_partial_boundary.py` (default) | 「実装済」「未実装」両側のキーワード片寄り検出 | informational |
| `check_citation_quality.py` (`--strict`) | 裏取り済み (`code-verified` / `runbook-verified` / `discrepancy-found`) なのに脚注も `<!-- evidence: -->` も無いページの検出。Reference / `_meta` / guides 系はデフォルト除外 | strict |
| `check_broken_links.py` (`--strict`) | `docs/**/*.md` の intra-doc Markdown リンク (相対パス + `#anchor`) の解決可否を検証 | strict |
| `check_heading_hierarchy.py` | a11y: 見出しレベルが 2 段以上跳ぶ (`##` → `####` 等) ページの検出 | strict |
| `check_image_alt.py` | a11y: 空 alt の inline image (`![ ](url)` 形式) を検出 | strict |
| `check_monitor_consistency.py` | `verification: discrepancy-found` ページの `monitor` タグと本文キーワードの整合性検証 | informational |
| `check_verification_self_consistency.py` | `code-verified` / `runbook-verified` を名乗りながら本文に「未確認」「TBD」「未実装」等を残しているページの検出 | informational |
| `check_evolved_6c.py` | `monitor: evolved_beyond_hld` ページが 6C (Change / Cause / Code / Commit / Compat / Citation) を本文で説明しているかの軽量チェック | informational |
| `check_ni_workaround_depth.py` | `monitor: not_implemented` ページに代替 / ワークアラウンド記述の深さがあるかの検出 | informational |
| `check_troubleshoot_section.py` | 100 行以上の HLD 系 `code-verified` / `discrepancy-found` ページに「トラブルシュート / 確認コマンド / 動作確認」セクション + コードブロックがあるか検証 | informational |
| `check_code_lang.py` | 言語タグ無しの fenced code block 検出 (PyMdown superfences ではプレーンテキスト化される) | informational |
| `check_stale_verified.py` | `last_verified` が閾値日数 (デフォルト 90 日) 以上古いページの検出 | informational |
| `check_built_html.py` | `mkdocs build` 後の `site/` 配下を走査し `<h1>` 重複・空 `<a>`/`<img>`・空コードブロック・mermaid placeholder 残骸を `meta/built-html-report.md` に出力 | informational |
| `check_limitations_section.py` | HLD 系ページの「Limitations / 制約」節のカバレッジ報告 | local-only |
| `check_sources_freshness.py` | `meta/index/repos.json` の pinned SHA と `.cache/sonic-sources/<repo>/` の HEAD / upstream を突合し behind 件数を表示 | local-only |

textlint (日本語表記揺れ + prh での [SONiC](../reference/glossary.md#term-sonic) 固有用語統一) と typos (crate-ci/typos) は Python スクリプト
ではなく外部 action / Node ベースで動くため、別 job (`typos` / `textlint`) として並行する。
Python 品質は `ruff check meta/scripts/` (pyflakes + isort + bugbear 一部) を lint job 内で
strict 実行する。

## 機械生成スクリプト (`gen_*` / `inject_*` / `render_*`)

`gen_*` / `inject_*` / `render_*` は静的サイトに含めるページや埋め込みブロックを自動生成する。
CI では生成出力の **drift 検査**として `--check` モードで動作し、ローカルで再生成し忘れていないかを
検出する。strict なものは drift 検出で CI を落とす。

| script | 目的 | CI 状態 |
|---|---|---|
| `gen_index_banner.py` | `docs/index.md` の品質バナー (verification 集計 + audit 平均) 自動更新 | gen-check (strict) |
| `gen_discrepancy_index.py` | `docs/reference/verification/discrepancy-index.md` の自動生成 (area × monitor 一覧) | gen-check (strict) |
| `gen_coverage.py` | `docs/_meta/coverage.md` の area × verification マトリクス自動生成 | gen-check (strict) |
| `gen_cross_ref.py` | Topics ↔ area ページ間の双方向 back-ref ブロック (`<!-- topics-back-ref -->`) | gen-check (strict) |
| `gen_glossary_xref.py` | `docs/reference/glossary.md` の用語別逆引き索引 (`<!-- glossary-xref -->`) | gen-check (strict) |
| `gen_cdb_mermaid.py` | [CONFIG_DB](../reference/glossary.md#term-config_db) reference ページにミニ data-flow mermaid 埋め込み | gen-check (strict) |
| `gen_cli_mermaid.py` | CLI reference ページにミニ data-flow mermaid 埋め込み | gen-check (strict) |
| `gen_yang_mermaid.py` | [YANG](../reference/glossary.md#term-yang) reference ページにミニ data-flow mermaid 埋め込み | gen-check (strict) |
| `gen_changelog.py` | `docs/_meta/changelog.md` を merged PR 一覧から生成 | gen-check (strict) |
| `gen_chapter_progress.py` | Topics 章 index の「章構成と進捗」テーブル | gen-check (strict) |
| `gen_snapshot.py` | `docs/_meta/snapshot.md` を verification 分布 / Reference カバレッジ / audit / lint 件数 / 鮮度などから生成 | gen-check (strict) |
| `inject_yang_xref.py` | YANG ref ページに「関連ページ」ブロック (CONFIG_DB / CLI / HLD への直リンク) 挿入 | gen-check (strict) |
| `inject_yang_sibling.py` | YANG ref ページに sibling YANG モジュール block 挿入 | gen-check (strict) |
| `inject_cli_sibling.py` | CLI ref ページに verb 跨ぎ sibling block 挿入 | gen-check (strict) |
| `inject_glossary_links.py` | glossary 用語の docs 内本文初出箇所を glossary anchor リンク化 | gen-check (strict) |
| `enrich_chapter_index_related.py` | 章 index の `related.{cli,config_db,yang}` を子ページから aggregate | gen-check (strict) |
| `render_evidence.py` | `<!-- evidence: -->` HTML コメントを `<!-- evidence-rendered -->` 内 collapsible admonition として現出 | gen-check (strict) |
| `gen_next_reads.py` | Topics 章 index の「次に読むべき記事」ブロック | gen-check (informational) |
| `gen_sitemap.py` | `docs/_meta/sitemap.md` 自動生成 | gen-check (informational) |
| `gen_descriptions.py` | 各ページの `description:` frontmatter を H1 + 冒頭段落から自動補完 | local-only |
| `gen_ref_triangle.py` | Reference (YANG ↔ CONFIG_DB ↔ CLI) sibling 三角リンクの埋め込み | local-only |
| `gen_topics_admonition.py` | HLD 派生ページ冒頭に Topics 章への誘導 admonition を挿入 | local-only |
| `gen_runtime_trace.py` | runtime trace 系ドキュメントの自動更新 | local-only |

## CI ワークフロー

CI の実体は `.github/workflows/ci.yml` にあり、以下ジョブに分かれる:

- `build` — `mkdocs build --strict` で全ページのビルド検証 + `check_built_html.py` を informational で実行
- `typos` — crate-ci/typos で docs / meta / README / CONTRIBUTING を strict 検査 (`.typos.toml`)
- `textlint` — npx textlint (`.textlintrc.json` + `meta/prh-sonic.yml`) で strict 検査
- `link-check` — lychee で外部 URL を informational 検査 (`.lychee.toml`)
- `lint` — frontmatter_lint と上記 lint 群、`run_all_checks.sh` での drift 検査、ruff を 1 job に集約

`lint` job は strict step (frontmatter_lint / invisible_chars / runbook_status / runbook_structure /
pages_integrity / discrepancy_related / link_density --strict-split-child / mermaid_syntax /
partial_boundary --strict-phase-table / citation_quality --strict / broken_links --strict /
heading_hierarchy / image_alt / enrich_chapter_index_related --check / ruff) と、
`run_all_checks.sh` (上表 gen-check strict の大半 + `gen_snapshot.py` / `gen_chapter_progress.py`) と、
informational step (`gen_next_reads` / `verification_self_consistency` / `monitor_consistency` /
`evolved_6c` / `ni_workaround_depth` / `partial_boundary` default / `link_density` / `code_lang` /
`stale_verified` / `troubleshoot_section` / `gen_sitemap`) を順に流す。

deploy は `.github/workflows/deploy.yml` が main push 契機で `gh-pages` ブランチへ
`mkdocs gh-deploy --force --clean` を実行する。

## 運用メモ

- **strict lint を新規追加するときは**、先に `informational` で 1 リリース走らせ、違反 0 を確認してから `--check` 失敗で exit 1 に昇格させる。違反 0 のうちに strict 化しないと既存ページが大量に refused されて運用が止まる
- **gen-check** が drift で落ちたときは、ローカルで対応する `gen_*.py` を `--check` 無しで再実行 (もしくは `bash meta/scripts/run_all_generators.sh`) → 出力ファイルを commit に含めて push し直すのが手順
- `check_sources_freshness.py` / `gen_descriptions.py` / `gen_ref_triangle.py` 等の **local-only** スクリプトは `.cache/` や `gh` 認証や手元判断に依存するため CI からは除外している。定期メンテのときに手動で回す
- `bash meta/scripts/run_all_checks.sh` を手元で 1 回流せば lint job の strict drift 検査群と同等の結果が得られる
- すべての lint は `python3 meta/scripts/<name>.py --help` で詳細オプションを確認できる

<!-- glossary-links-injected: f4ecfec41d28 -->
