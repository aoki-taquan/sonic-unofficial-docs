---
title: 発展トピック
description: 発展トピック — リファレンス索引 (CLI / CONFIG_DB / YANG / cross-reference) を回し続けるための index 再生成スクリプト群、新 mapping
  の追加手順、CI drift の対応をまとめます。22 章は索引そのものを扱うメタ章なので、ここでは「索引を生成する側」の運用を扱います。
area: topics
verification: meta
last_verified: 2026-05-12
sources: []
related:
  cli:
  - show version
  - sonic-cfggen
  config_db:
  - DEVICE_METADATA
  - FEATURE
  yang:
  - sonic-device-metadata
---

# 発展トピック

リファレンス索引 (CLI / [CONFIG_DB](../../reference/glossary.md#term-config_db) / [YANG](../../reference/glossary.md#term-yang) / cross-reference) を回し続けるための index 再生成スクリプト群、新 mapping の追加手順、CI drift の対応をまとめます。22 章は索引そのものを扱うメタ章なので、ここでは「索引を生成する側」の運用を扱います。

## index 再生成スクリプト群

`meta/scripts/` 配下に index 再生成系のスクリプトが集中しています。22 章の運用で日常的に触るのは次の七本です。

| スクリプト | 役割 | 主な出力 |
| --- | --- | --- |
| `gen_coverage.py` | reference ページの verification 内訳 / カバー率を集計 | `docs/reference/index.md` 内の coverage 表 |
| `gen_cross_ref.py` | 章 ↔ reference の双方向リンクを生成 | `docs/topics/*/index.md` の「次に読むべき記事」 |
| `gen_chapter_progress.py` | 各章の 5 サブページ完成度を集計 | 章 index の `<!-- chapter-progress -->` ブロック |
| `gen_next_reads.py` | 関連 [HLD](../../reference/glossary.md#term-hld) / runbook 候補を frontmatter から拾う | 章 index 末尾の関連リンク |
| `gen_ref_triangle.py` | CLI / CONFIG_DB / YANG の三角関係を抽出 | `docs/topics/22-reference-index/*-index.md` |
| `apply_cli_yang_map.py` | `meta/index/*.json` 上の CLI ↔ YANG 対応を frontmatter に反映 | reference / topics ページの `related:` |
| `inject_glossary_links.py` | 用語の最初の出現に glossary リンクを差し込む | 全 docs ページの本文 |

これらは `run_all_generators.sh` で一括実行できます。drift を疑うときも、まずは `run_all_generators.sh && git diff --stat` で差分を眺めるのが入口になります。

## 新 mapping を追加する手順

新規 CLI / CONFIG_DB / YANG ページを追加した、あるいは既存 reference の関係を増やしたいときは、次の順に作業します。

1. **reference ページを書く / 更新する**: `docs/reference/cli/<slug>.md` などに新ページを置き、frontmatter の `related:` に CLI / CONFIG_DB / YANG 三系統の対応を列挙する。
2. **`meta/index/*.json` を更新する**: 自動 Indexer がカバーしていない領域は `meta/index/cli.json` / `config-db.json` / `yang.json` に手動で項目を追加する。`slug`、`title`、`related_areas` を最低限埋める。
3. **`apply_cli_yang_map.py` を回す**: frontmatter ↔ index json の整合を双方向に同期する。CLI/YANG 対応はここで topics 章にも伝播する。
4. **`gen_cross_ref.py` / `gen_ref_triangle.py` を回す**: 22 章の `cli-index.md` / `config-db-index.md` / `yang-index.md` の表が更新される。
5. **`frontmatter_lint.py` を回す**: 必須キーと enum 値、`last_verified` の形式を確認する。
6. **`mkdocs build --strict` で確認**: link 切れと anchor 切れを検出する。

このルートを守れば、人手の txt diff を 22 章本文に書き込まずに索引を更新できます。本ページ・`cli-index.md` ほかは原則 generator の出力で更新する設計です。

## CI drift の対応

generator の出力と human commit の間に drift が出ることが頻繁にあります。代表的なドリフトと処理パターンは次のとおりです。

- **`chapter-progress` の行数差分**: サブページに数行追記しただけで「⚠️ プレースホルダ」「✅ 完成」が遷移する。閾値は本文 100 行。意図しない変動は本文修正側で吸収する。
- **`next-reads` の HLD 候補リスト変動**: 新規ページ追加で関連候補が増減する。CI が `gen_next_reads.py --check` で drift 検出するため、generator 出力をそのまま PR に含める。
- **glossary link の重複 / 抜け**: `inject_glossary_links.py` の hash 表記 (`<!-- glossary-links-injected: <id> -->`) と本文の不整合。再実行で正規化する。
- **`coverage` 数値の zone drift**: verification status の昇格と reference 追加で数値が動く。22 章本文と reference/index の数字が乖離したら本章を引用元へ差し戻す。

drift を恒常的に減らすコツは「人手の編集と generator 出力を同じ PR で混ぜない」「generator 出力だけを含む `chore/regenerate-*` PR を分けて squash する」の二点です。

CI 側では `run_all_checks.sh` が drift 検出を担います。失敗が出たら本番ブランチでは generator を再回し、worktree ブランチでは「自分の編集が generator 出力を上書きしていないか」をまず確認してください。`git diff main -- meta/index/` で json 側差分があるか見るのが最短ルートです。

drift をゼロにすることは目的ではありません。「drift が出たら復元手順が一行で書ける」「人手編集と generator 出力の境界がコミット単位で読める」ことのほうが本質です。

実運用では月一の Indexer 再回し PR と、機能 PR ごとの generator 再回しを分離する二段運用が安定しています。前者は数十ファイル / 後者は数ファイルの差分にとどまり、review コストが大きく下がります。

## 章の出口

- 索引そのものを読む → [CLI 横断索引](cli-index.md) / [CONFIG_DB 横断索引](config-db-index.md) / [YANG 横断索引](yang-index.md)
- 索引の品質を測る → [品質と gap](quality-gaps.md)
- 索引の実装を読む → [内部実装](internals.md)
- 索引が指す reference の本体 → [reference/index.md](../../reference/index.md)

## 関連ページ

- [CLI 横断索引](cli-index.md)
- [CONFIG_DB 横断索引](config-db-index.md)
- [YANG 横断索引](yang-index.md)
- [品質と gap](quality-gaps.md)
- [内部実装](internals.md)
- [reference/index.md](../../reference/index.md)

## 追加の発展トピック

- **OpenConfig vs [SONiC](../../reference/glossary.md#term-sonic) YANG の対応表自動生成**: `sonic-mgmt-common` の transformer 定義から OC ↔ sonic-* YANG のペアを抽出し、`yang-index.md` に差し込む取り組み。10 章 ([gNMI](../../reference/glossary.md#term-gnmi) / OpenConfig) と直接連動する。
- **discrepancy-found ページの一覧ビュー**: `verification: discrepancy-found` のページを横断的に集める dashboard。`gen_discrepancy_index.py` が起点。
- **runbook ↔ reference の双方向リンク**: 症状逆引き (`docs/reference/runbooks/`) と CLI / CONFIG_DB 索引を相互に張る。`gen_cross_ref.py --runbook` で部分自動化。
- **Indexer v3 構想**: HLD メタを SHA 単位で再収集し、reference 側 frontmatter にも `last_synced_sha` を持たせて drift 検出を粒度細かく行う。

## 既知の制約と回避方法

- **generator の冪等性**: いくつかの generator は順序依存があり、`gen_cross_ref` → `gen_next_reads` → `gen_chapter_progress` の順で回さないと drift が残ることがある。`run_all_generators.sh` の順序を変更しない。
- **glossary inject の競合**: 並走 Writer が同一ファイルへ glossary link を差し込むと hash がぶれる。PR ごとに最後に `inject_glossary_links.py` を再実行して揃える。
- **大きな drift の review 困難**: 200+ ファイルが同時更新されると review が事実上不可能。`chore/regenerate-*` PR は generator 種別で分割する。

## 将来計画 / ロードマップ

- Indexer v3 (per-source SHA 追跡) の段階導入。
- discrepancy / hld-only / code-verified の三層ダッシュボード化。
- OpenConfig transformer 対応の自動抽出。
- runbook ↔ reference の双方向リンク自動化の完成。

## 関連 RFC / 仕様書

- [SPDX 2.x](https://spdx.dev/) — reference に SBOM を組み込むときの参照規格。
- [OpenConfig models](https://github.com/openconfig/public) — YANG 索引拡張時の OC 側カタログ。
- [IETF YANG catalog](https://www.yangcatalog.org/) — YANG モジュールのメタデータ照合に利用。

## upstream 開発の最新動向

- `sonic-mgmt-common` の transformer 定義は引き続き OC 側追加と breaking change が散発し、YANG 索引の自動再生成が必要になる。
- `sonic-utilities` の click CLI tree は新サブコマンド追加が定常で、`gen_cli_mermaid.py` の再回しが weekly レベルで発生する。
- `sonic-yang-models` の `must` / `when` 制約強化 PR は CONFIG_DB スキーマ表に直接影響するため、22 章 `config-db-index.md` の追従が必須。
- discrepancy-found ページ群は Verifier フェーズ完走後も継続的に発生 (master 追従) するため、本章の運用フローは長期前提で組む。

<!-- glossary-links-injected: 8ba32e5aa69d -->
