---
title: SONiC 非公式ドキュメント
description: "SONiC NOS (community master) を AI が日本語で再構成した非公式ドキュメント。学ぶ / 設定する / 修理する の 3 つの入り口から、1089 ページの全文検索可能なリファレンスへ。"
verification: meta
hide:
  - navigation
  - toc
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# SONiC 非公式ドキュメント (日本語)

[SONiC](./reference/glossary.md#term-sonic) NOS (community master) の AI 再構成 日本語ドキュメント。
公式 [HLD](./reference/glossary.md#term-hld) の分散・古さ・実装乖離を補い、引用付きで master を追う。

[はじめての方は概要から :material-arrow-right:](topics/01-overview/index.md){ .md-button .md-button--primary }
[直接トラブルシュート :material-rocket-launch:](reference/runbooks/index.md){ .md-button }
<a href="feed_rss_created.xml" class="md-button" title="RSS feed (最近作成された 30 ページ)">更新を購読 (RSS)</a>

---

## 何ができる？

3 つの読み手別の入り口:

<!-- quality-banner-start -->
!!! success "最新の品質状態"
    - **code-verified ページ**: 735 件（HLD と実コードを照合済み）
    - **runbook-verified ページ**: 27 件（Runbook 専用。実運用で症状再現性が確認済み）
    - **discrepancy-found ページ**: 106 件（HLD と実装の乖離を明示）
    - **監査平均評価**: 4.99 / 5.0（quality-audit round 52）
    - **hld-only ページ**: 2 件（裏取り待ち）
    - **保守フェーズ運用中** (2026-05-13〜): 月次 master 追従 / 偶数 round stratified audit / feedback 反映で 4.97+ プラトーを維持 (`meta/maintenance-mode.md`)
<!-- quality-banner-end -->

<div class="grid cards" markdown>

-   :material-school: __学ぶ__

    ---

    22 章の Topics 扉から、概念 / 設定 / 運用 / 内部実装 / 障害切り分けへ。

    [Topics 目次](topics/index.md)

-   :material-cog: __設定する__

    ---

    CLI / CONFIG_DB / YANG の 3 系統リファレンス。Mermaid 図 100% 添付。

    [Reference 目次](reference/index.md)

-   :material-tools: __修理する__

    ---

    現場で「動かない」を解く Runbook 27 件 + 実装と HLD の乖離 115 件の一覧。

    [Runbook 一覧](reference/runbooks/index.md)

</div>

## 品質指標 (最新スナップショット)

- 全 **1089** ページ (code-verified 737 + runbook-verified 27 + discrepancy-found 115 + reference/meta)
- mermaid 構文エラー 0、broken link 0、frontmatter 違反 0
- サンプリング監査 round 50: **4.972 / 5**
- 本文 `hld-only` ページ 0 件

詳細は [スナップショット](_meta/snapshot.md) / [カバレッジ](_meta/coverage.md) / [実装との乖離](_meta/discrepancies.md) を参照。

## このサイトは

- **非公式** (Microsoft / SONiC コミュニティとは無関係)
- **[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja)** ライセンス
- **AI 主導の再構成 + 機械検証** (`mkdocs build --strict` / frontmatter lint / code-verified パイプラインで品質担保)

誤情報の報告・改善要望は [GitHub Issues](https://github.com/aoki-taquan/sonic-unofficial-docs/issues/new/choose) / [Discussions](https://github.com/aoki-taquan/sonic-unofficial-docs/discussions) へ。プロジェクトの全体像は [このドキュメントについて](about.md) にまとまっています。

<!-- glossary-links-injected: 8ba32e5aa69d -->
