---
title: 正式版 (v1.0) 公開チェックリスト
verification: meta
last_verified: 2026-05-11
---

# v1.0 公開チェックリスト

監査 round 5 / 6 で「β 公開可、v1.0 未到達」と判定された状態から、正式版 (v1.0) として公開アナウンスできる状態に到達するためのチェック項目を整理する。

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
| 7 | `code-verified` 件数 | [x] | 545 件 |
| 8 | `discrepancy-found` 件数 | [x] | 48 件 |
| 9 | 監査平均が 4.95+ 維持 | [x] | round 6: 4.978 / 5.0 |
| 10 | 監査 round 7 の実施 | [ ] | v1.0 昇格条件の一つ。本 PR の対象外 |
| 11 | HLD area 残 ~70 件の翻訳調再構成 | [ ] | イテ 3 回分の Writer 投入が必要 |

## 3. リファレンスカバー率

| # | 項目 | 状態 | 件数 |
|---|------|------|------|
| 12 | CLI Reference | [x] | 63 ページ |
| 13 | CONFIG_DB Reference | [x] | 110 ページ |
| 14 | YANG Reference | [x] | 70 ページ |
| 15 | Runbooks | [x] | 31 ページ |
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
| 23 | LICENSE ファイル | [ ] | README で CC BY 4.0 と明記。リポジトリトップに `LICENSE` ファイルを置くと一層分かりやすい (任意) |
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

round 6 の指摘を踏まえると、v1.0 昇格に必要な残作業は以下:

1. **HLD area 残 ~70 件の再構成** (Writer バッチ #12 以降、イテ 3 回程度)
2. **監査 round 7 で平均 4.95+ 維持**
3. **GitHub Pages の Source 設定 (ユーザー手動)**
4. **(任意) LICENSE ファイルの追加** — 現状 README に CC BY 4.0 と明記済みなので機能上は問題なし

本 PR で「インフラ系」「メタ系」のチェック項目はほぼ全て埋め、残るのは品質再構成 (1) と監査 (2) と人手作業 (3) のみ。

## 8. 次のイテレーションでやること

- [ ] Writer バッチ #12 を起動: HLD area 残 ~70 件の翻訳調撲滅。`isolation: worktree` で 5〜10 並走
- [ ] 監査 round 7 を sampling で実施 (15〜20 件)
- [ ] `gen_index_banner.py` の作成 (`docs/index.md` の `!!! success "最新の品質状態"` バナーを自動更新)
- [ ] ユーザーに GitHub Pages の Source 設定を依頼 (`meta/github-pages-setup.md` を共有)

## 関連ドキュメント

- [監査 round 6](./quality-audit-6.md)
- [監査 round 5](./quality-audit-5.md)
- [GitHub Pages 設定手順](./github-pages-setup.md)
- [フィードバック処理方針](./feedback.md)
