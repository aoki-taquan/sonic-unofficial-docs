# Changelog

`sonic-unofficial-docs` の主要マイルストーン履歴。日付は本リポジトリの commit 時系列ベース、版数はプロジェクト内部での節目を表す（リリースタグそのものではない）。

形式は [Keep a Changelog](https://keepachangelog.com/) を緩く参考にしている。

## [1.0.0-rc] - 2026-05-11

v1.0 リリース候補。自動化可能なチェック項目は全て達成済み、残ブロッカはユーザー手動マター 2 件（GitHub Pages の Source 設定、`v1.0.0` タグ打鍵）のみ。

### 追加

- `CHANGELOG.md`（本ファイル）を新設。
- `README.md` の「公開状態」セクションを v1.0 RC 仕様に更新（公開後 URL、リリースノート参照、残ブロッカ明示）。
- `meta/release-checklist-v1.md` を最終チェック更新。

### 品質状態（2026-05-11 時点）

- 総ページ数: 833
- `code-verified`: 597
- `discrepancy-found`: 48
- `hld-only` 本文ページ: 0
- 監査 round 8（10 段階）: **9.74 / 10.0**

## [0.10] - 2026-05-11 — イテレーション J（品質改善）

- HLD 5 件再構成 + Topics concept 5 件補強（PR #965）
- Runbook +15 件、合計 46 件（PR #964）
- 監査 round 8（10 段階、9.74）を実施（PR #963）
- Topics ↔ area 横断リンクを双方向化（PR #962）
- discrepancy ページ 36 件に GitHub Issue / PR 紐づけを追加（PR #961）

## [0.9] - 2026-05-11 — イテレーション I（品質改善）

- HLD 最終残 8 件 再構成（PR #960）
- Reference 三角リンク（YANG ↔ CDB ↔ CLI）を Reference 277 ページに反映（PR #959）
- 品質バナー自動更新スクリプト + CI 統合（PR #958）
- CLI reference batch D（10 ページ）、CONFIG_DB batch D（12 テーブル）

## [0.8] - 2026-05-11 — イテレーション H（品質改善）

- HLD 横断・高優先残 8 件 再構成（PR #955）
- categories 10 ページ充実（PR #956）
- HLD routing 中規模残 5 件、HLD acl-qos 残 5 件 再構成
- LICENSE ファイル追加 + about ページ整備（PR #952）
- 監査 round 7（10 段階、9.65）を実施（PR #951）

## [0.7] - 2026-05-10 — イテレーション G（品質改善）

- Topics 章間クロスリファレンス強化（PR #950）
- YANG reference batch C（15 件）、CONFIG_DB batch D（12 件）
- HLD overlay / management / platform / system 各 5 件 再構成
- 購読者欄 daemon 名 grep 裏取り（PR #942）
- frontmatter linter v2（mojibake + path liveness）と violation fix（PR #940）

## [0.6] - 2026-05-10 — イテレーション F（品質改善）

- Topics advanced 全章を強化（PR #941）
- HLD internals / architecture 6 件 再構成
- 監査 round 6（4.978 / 5.0）を実施（PR #939）

## [0.5] - 2026-05-10 — イテレーション E（品質改善）

- HLD architecture / routing / acl-qos / management / platform 各 5 件 再構成
- `discrepancy-index.md` 自動生成（PR #929）
- Runbook 既存 15 件にロールバック手順を追記（PR #933）
- 監査 round 5（4.97）を実施（PR #932）

## [0.4] - 2026-05-10 — イテレーション D（品質改善）

- SCHEMA.md monitor enum 確定 + linter 拡張（PR #931）
- HLD system 5 件 再構成（読み手の質問順）（PR #930）
- frontmatter linter を CI に追加（PR #927）
- `docs/index.md` 動線改善（PR #928）
- Runbook +15 件（合計 30 件、PR #926）

## [0.3] - 2026-05-10 — イテレーション B/C（品質改善）

- Phase 6 までの大量生成ページに対する **品質改善 (Quality) フェーズ** を開始。
- 監査 round 1〜4 を実施し、4.60 → 4.97 まで底上げ。
- discrepancy ページの整備、横断カテゴリ (`docs/categories/`) 新設、読み手別ガイド (`docs/guides/`) 新設。

## [0.2] - 2026-05-09 — Phase 6（大量化フェーズ完了）

- 累計 455 ページ merge 済み（HLD 系 + CLI Ref 25 + CONFIG_DB Ref 66 + YANG Ref 28）。
- `verification: hld-only` のページ 0 件達成（全ページ `code-verified` / `discrepancy-found` に到達）。
- バッチ Writer #1〜#11 完走（合計 ~290 ページ）。
- Verifier #1〜#27 完走（200+ ページ裏取り、~40 件の discrepancy 発見）。
- per-page queue (`meta/queue/<area>-<slug>.json`) + `aggregate_queue.py` で並走衝突解消。

## [0.1] - 2026-05-09 — Phase 0–5（パイプライン構築）

- Phase 0: 構造設計レビュー（diataxis / IA / personas / radical / devil / third 各観点）を 5 回転、最終 v4 構造に収束。
- Phase 1: Indexer (`.cache/sonic-sources` を棚卸し → `meta/index/*.json`)。HLD 386 件、CLI ツリー、YANG モジュール、対象 15 リポと SHA を確定。
- Phase 2: Backlog Generator (`meta/backlog/<area>/*.json`)。
- Phase 3: Writer → Reviewer → Merger パイプライン稼働開始（バッチ Writer #1〜#5）。
- Phase 4: Verifier 起動（`meta/verification-queue.json` の裏取り → verification ステータス昇格 PR）。
- Phase 5: CI/Deploy workflow 構築（`.github/workflows/ci.yml` + `deploy.yml` の `gh-pages` 自動 publish）。
- 累計 152 ページ merge（HLD 130 + CLI Ref 13 + Verifier 8 昇格 + index/その他）。Indexer v2 が HLD メタ強化を完了。

---

## バージョニング方針

- `0.x` は内部マイルストーン番号で、リポジトリのタグ／リリースとは独立。
- `1.0.0` の正式タグはユーザー（リポジトリオーナー）が手動で打鍵する（[`meta/release-checklist-v1.md`](./meta/release-checklist-v1.md) 第 6 章参照）。
- 以後の品質改善はマイナー (`1.x`) で、HLD 再構成・Reference 拡充・監査 round 9 以降を含む。
