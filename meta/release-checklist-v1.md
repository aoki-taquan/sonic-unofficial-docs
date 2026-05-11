---
title: 正式版 (v1.0) 公開チェックリスト
verification: meta
last_verified: 2026-05-11
---

# v1.0 公開チェックリスト

監査 round 5 / 6 で「β 公開可、v1.0 未到達」と判定された状態から、正式版 (v1.0) として公開アナウンスできる状態に到達するためのチェック項目を整理する。

**2026-05-11 時点: v1.0 リリース候補 (RC) に到達。** 自動化可能な全項目を達成済み。残ブロッカは「6. ユーザー手動マター」の 2 項目のみ。

ステータスは以下の表記:

- `[x]` 達成済み
- `[ ]` 未達成（残作業）
- `[~]` 部分達成（実装はあるが運用上の追加作業が必要）

最終更新: 2026-05-11

## 1. ビルド・CI 健全性

| # | 項目 | 状態 | 備考 |
|---|------|------|------|
| 1 | `mkdocs build --strict` がローカル / CI 双方でエラー無し | [x] | round 6 時点で 60s で build 完了。warning は `INFO` レベルのみ (`#fnref:*` の未参照 footnote のみ) |
| 2 | `frontmatter_lint.py` (v2) が hard violation 0 | [x] | `scanned=779 hard=0 warn=0` |
| 3 | `verify_daemon_names.py` が violation 0 | [x] | 91 unique tokens / 0 violations |
| 4 | CI workflow (`.github/workflows/ci.yml`) が PR ごとに green | [x] | `build` + `frontmatter-lint` の 2 ジョブ |
| 5 | Deploy workflow (`deploy.yml`) が main push で `gh-pages` に publish | [x] | `mkdocs gh-deploy --force --clean` を使用 |

## 2. ページ品質

| # | 項目 | 状態 | 備考 |
|---|------|------|------|
| 6 | 本文ページの `verification: hld-only` が 0 件 | [x] | 残 2 件は `topics/22-reference-index/*.md` で hld-only という文字列を含むだけのメタページ。frontmatter としては全本文ページが脱却済み |
| 7 | `code-verified` 件数 | [x] | 597 件（581+ 達成済み） |
| 8 | `discrepancy-found` 件数 | [x] | 48 件 |
| 9 | 監査平均が 4.95+ 維持 | [x] | round 6: 4.978 / 5.0、round 7: 9.65/10、round 8: **9.74/10** |
| 10 | 監査 round 7 / 8 の実施 | [x] | round 7 (PR #951)、round 8 (PR #963) を実施済み |
| 11 | HLD area 残 ~70 件の翻訳調再構成 | [x] | イテ E〜J で再構成完了。`hld-only` 本文ページは 0 件 |

## 3. リファレンスカバー率

| # | 項目 | 状態 | 件数 |
|---|------|------|------|
| 12 | CLI Reference | [x] | 73 ページ |
| 13 | CONFIG_DB Reference | [x] | 122 ページ |
| 14 | YANG Reference | [x] | 85 ページ |
| 15 | Runbooks | [x] | 46 ページ |
| 16 | discrepancy-index 自動生成 (`gen_discrepancy_index.py`) | [x] | `docs/reference/verification/discrepancy-index.md` |

## 4. ナビゲーション・横断

| # | 項目 | 状態 | 備考 |
|---|------|------|------|
| 17 | 各 area の `index.md` が存在 | [x] | architecture / acl-qos / platform / management / overlay / routing / system / switching / categories / guides / internals / reference / topics の全 area |
| 18 | 読み手別ガイド (`docs/guides/`) | [x] | developer / evaluator / operator など |
| 19 | 横断カテゴリ (`docs/categories/`) | [x] | bgp-evpn / dash / dual-tor / smartswitch ほか |

## 5. メタ / 運用

| # | 項目 | 状態 | 備考 |
|---|------|------|------|
| 20 | `README.md` に公開状態 (β/v1.0) と品質メトリクス記載 | [x] | 本 PR で「公開状態」セクションを追記 |
| 21 | `CONTRIBUTING.md` 整備 | [x] | 既存 |
| 22 | `CLAUDE.md` 整備 | [x] | 永続指示 |
| 23 | LICENSE ファイル | [x] | PR #952 で `LICENSE` / `LICENSE.ja` をリポジトリトップに追加済み |
| 24 | フィードバック導線 (Issues / Discussions) | [x] | README + `meta/feedback.md` + `.github/ISSUE_TEMPLATE/feedback.yml` |
| 25 | `mkdocs.yml` の `site_url` | [x] | `https://aoki-taquan.github.io/sonic-unofficial-docs/` |
| 26 | `mkdocs.yml` の `copyright` (CC BY 4.0) | [x] | 本 PR で追加 |
| 27 | `sitemap.xml` の生成 | [x] | MkDocs は build 時に `site/sitemap.xml` を自動生成 (デフォルト) |
| 28 | 404 ページ整備 | [x] | 本 PR で `docs/404.md` を整備 |
| 29 | 検索 (search plugin) の設定最適化 | [x] | `lang: ja` 設定済み。`separator` のチューニングは将来課題 |

## 6. ユーザー手動マター

| # | 項目 | 状態 | 備考 |
|---|------|------|------|
| 30 | GitHub Pages の Source 設定 (`gh-pages` branch) | [ ] | `meta/github-pages-setup.md` に手順を記載。ユーザー (リポジトリオーナー) のみが実施可 |
| 31 | リリースタグ `v1.0.0` の打鍵とアナウンス | [ ] | チェックリスト全項目グリーン後にユーザーが実施 |

## 7. v1.0 昇格条件サマリ

2026-05-11 時点で、本チェックリスト 1〜5 のうち自動化可能な項目はすべて `[x]`。残るは **6. ユーザー手動マター** の 2 項目のみ:

1. **GitHub Pages の Source 設定** (`gh-pages` branch を Pages の Source として有効化)
2. **リリースタグ `v1.0.0` の打鍵とアナウンス**

この 2 項目はリポジトリオーナーのみが実施可能であり、本リポジトリの自動パイプライン (Indexer / Writer / Reviewer / Merger / Verifier) の範囲外。

## 8. 次のイテレーション（v1.0 後）

v1.0 リリース後の `1.x` マイナーで予定している品質改善:

- [ ] 監査 round 9 を sampling で実施 (15〜20 件、10 段階評価)
- [ ] HLD で更にスタブ気味のページの再構成（generic-name / `introduction-N` / `revision` 等）
- [ ] CLI / CONFIG_DB / YANG Reference の追加カバー
- [ ] discrepancy ページの上流 PR への寄与 (PR を立てるところまでは AI、merge は人手)

## 関連ドキュメント

- [CHANGELOG](../CHANGELOG.md)
- [監査 round 8](./quality-audit-8.md)
- [監査 round 7](./quality-audit-7.md)
- [監査 round 6](./quality-audit-6.md)
- [GitHub Pages 設定手順](./github-pages-setup.md)
- [フィードバック処理方針](./feedback.md)
