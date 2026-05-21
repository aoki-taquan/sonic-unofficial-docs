---
title: SONiC 非公式ドキュメント
description: "SONiC NOS (community master) を AI が日本語で再構成した非公式ドキュメント。学ぶ / 設定する / 修理する の 3 つの入り口から、全文検索可能なリファレンスへ。"
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

<!-- no-quality-banner -->

# SONiC 非公式ドキュメント (日本語)

[SONiC](./reference/glossary.md#term-sonic) NOS (community `master`) を AI が日本語で再構成した**非公式**ドキュメント。
公式 [HLD](./reference/glossary.md#term-hld) の分散・古さ・実装乖離を、複数リポジトリ横断の引用付きで補う。

<div class="grid cards" markdown>

-   :material-school: **学ぶ**

    ---

    22 章の Topics 扉から、概念 / 設定 / 運用 / 内部実装 / 障害切り分けへ進む。

    [はじめての方はこちら :material-arrow-right:](topics/01-overview/index.md){ .md-button .md-button--primary }
    [Topics 目次](topics/index.md)

-   :material-cog: **設定する**

    ---

    CLI / [CONFIG_DB](./reference/glossary.md#term-config_db) / [YANG](./reference/glossary.md#term-yang) の 3 系統リファレンス。Mermaid 図 100% 添付、相互リンク完備。

    [Reference 目次](reference/index.md){ .md-button }
    [カテゴリで探す](categories/index.md)

-   :material-tools: **修理する**

    ---

    現場で「動かない」を解く Runbook と、実装と HLD の乖離の一覧。

    [Runbook 一覧](reference/runbooks/index.md){ .md-button }
    [実装との乖離](_meta/discrepancies.md)

</div>

---

## このサイトについて

- **非公式** — Microsoft / SONiC コミュニティ / SONiC Foundation とは無関係
- **[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja)** ライセンス
- **AI 主導の再構成 + 機械検証** — `mkdocs build --strict` / frontmatter lint / code-verified パイプラインで品質担保
- **対象**: コミュニティ版 SONiC の `master` ブランチのみ（ベンダー版・リリースブランチは対象外）

最新の品質指標（総ページ数 / `code-verified` 件数 / 監査平均評価など）は [スナップショット](_meta/snapshot.md) を参照。プロジェクトの全体像・運用ポリシーは [このドキュメントについて](about.md) にまとまっています。

## フィードバック

誤情報の報告・改善要望を歓迎します（AI 生成のため誤りは構造的に発生し得ます）:

- [GitHub Issues](https://github.com/aoki-taquan/sonic-unofficial-docs/issues/new/choose) — 誤情報報告・記述漏れ・リンク切れ
- [GitHub Discussions](https://github.com/aoki-taquan/sonic-unofficial-docs/discussions) — 質問・運用相談
- <a href="feed_rss_created.xml">RSS で更新を購読</a>（最近作成された 30 ページ）

<!-- glossary-links-injected: 8ba32e5aa69d -->
