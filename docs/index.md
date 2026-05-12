---
title: SONiC 非公式ドキュメント
description: "SONiC 非公式ドキュメント — 目的別に「最初に開くべきページ」をまとめました。読み進める順番に並んでいます。"
verification: meta
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# SONiC 非公式ドキュメント

[SONiC NOS](https://github.com/sonic-net/SONiC) の日本語非公式ドキュメントへようこそ。

!!! warning "非公式ドキュメントについて"
    このドキュメントは有志による非公式ドキュメントです。SONiC プロジェクトおよび SONiC Foundation とは関係ありません。
    内容の正確性についてはベストエフォートで管理していますが、最新の正確な情報は [公式リポジトリ](https://github.com/sonic-net/SONiC) を参照してください。

<!-- quality-banner-start -->
!!! success "最新の品質状態"
    - **code-verified ページ**: 586 件（HLD と実コードを照合済み）
    - **runbook-verified ページ**: 27 件（Runbook 専用。実運用で症状再現性が確認済み）
    - **discrepancy-found ページ**: 74 件（HLD と実装の乖離を明示）
    - **監査平均評価**: round 41 集計中（`meta/quality-audit-41.md`）
    - すべての本文ページが `hld-only` を脱却し、`code-verified` または `discrepancy-found` に到達済み
<!-- quality-banner-end -->

## 初めての方はここから

目的別に「最初に開くべきページ」をまとめました。読み進める順番に並んでいます。

<div class="grid cards" markdown>

-   :material-book-open-variant: __概念を知りたい__

    ---

    SONiC のアーキテクチャ、CONFIG_DB / APPL_DB の流れ、各機能の設計思想を理解したい方向け。

    - [SONiC 全体像 (01-overview/concept)](topics/01-overview/concept.md)
    - [アーキテクチャ (01-overview/architecture)](topics/01-overview/architecture.md)
    - [BGP の概念 (02-bgp/concept)](topics/02-bgp/concept.md)
    - [VXLAN/EVPN の概念 (03-vxlan-evpn/concept)](topics/03-vxlan-evpn/concept.md)
    - [読み手別ガイド (developer)](guides/developer.md)

-   :material-cog: __設定したい__

    ---

    実機・VS で SONiC を設定・運用する方向け。`setup.md` 系と CLI リファレンスを横並びに引きます。

    - [01-overview の設定](topics/01-overview/configuration.md)
    - [BGP セットアップ (02-bgp/setup)](topics/02-bgp/setup.md)
    - [VXLAN/EVPN セットアップ](topics/03-vxlan-evpn/setup.md)
    - [L2 VLAN/LAG セットアップ](topics/06-l2-vlan-lag/setup.md)
    - [CLI リファレンス](reference/cli/index.md)
    - [CONFIG_DB リファレンス](reference/config-db/index.md)
    - [評価者向けガイド](guides/evaluator.md)

-   :material-tools: __障害切り分けたい__

    ---

    現場で「動かない」を解くための Runbook 集。30 件以上の典型障害シナリオを症状起点で整理。

    - [Runbook 一覧 (reference/runbooks)](reference/runbooks/index.md)
    - [BGP セッションが上がらない](reference/runbooks/bgp-session-down.md)
    - [EVPN Type-2 が広告されない](reference/runbooks/evpn-type2-not-advertised.md)
    - [Dual-ToR MUX 不整合](reference/runbooks/dualtor-mux.md)
    - [warm-reboot 失敗](reference/runbooks/warm-reboot-failure.md)
    - [運用者向けガイド](guides/operator.md)

</div>

## 読み手別の入口

目的に応じて、既存ページを読む順番をまとめたガイドです。

- [初学者向け](guides/beginner.md): SONiC の全体像、設定モデル、仮想環境での導入を順に把握したい読者向け。
- [運用者向け](guides/operator.md): 日々の確認、設定変更、障害調査、[CONFIG_DB](./reference/glossary.md#term-config_db) の意味確認を素早く引きたい読者向け。
- [開発者向け](guides/developer.md): [HLD](./reference/glossary.md#term-hld)、[YANG](./reference/glossary.md#term-yang)、CONFIG_DB、CLI、daemon / orch、テスト計画の対応関係を追いたい読者向け。
- [評価者向け](guides/evaluator.md): ラボで SONiC を起動し、基本設定と状態確認まで一連の流れを辿りたい読者向け。

## SONiC とは

SONiC（Software for Open Networking in the Cloud）は、Linux（Debian）ベースのオープンソースなネットワーク OS（NOS）です。Microsoft と Open Compute Project（OCP）によって開発され、現在は Linux Foundation 配下のオープンソースプロジェクトとして運営されています。

主要な構成要素:

- **[SAI](./reference/glossary.md#term-sai) (Switch Abstraction Interface)**: ASIC ベンダーを抽象化する標準 API
- **コンテナ化されたマイクロサービス群**: [BGP](./reference/glossary.md#term-bgp)（[FRR](./reference/glossary.md#term-frr)）、[LLDP](./reference/glossary.md#term-lldp)、[SNMP](./reference/glossary.md#term-snmp)、PMON など機能ごとに Docker コンテナで分離
- **[Redis](./reference/glossary.md#term-redis) を中央データベースとした状態管理**: CONFIG_DB / [APPL_DB](./reference/glossary.md#term-appl_db) / [STATE_DB](./reference/glossary.md#term-state_db) / [ASIC_DB](./reference/glossary.md#term-asic_db) など

## このドキュメントの方針

- 公式 HLD の翻訳ではなく、**再構成**された解説
- HLD・実コード・issue を横断して引用し、各ページの末尾に出典を明示
- 各ページに裏取りステータス（HLD-only / Issue-confirmed / Code-verified / Discrepancy-found）を付与

## 最新の追加

直近で merge された主な変更（[変更履歴](_meta/changelog.md) から最新 10 件）:

- 2026-05-11 #987 [reference] 横断索引強化
- 2026-05-11 #988 [reference] 頻出 SAI 属性早見表
- 2026-05-11 #989 [quality] area HLD ページに Topics 誘導 admonition 追加
- 2026-05-11 #986 [reference] 用語集 (glossary) 新設
- 2026-05-11 #985 [meta] 品質改善 サンプリング監査 (round 11)
- 2026-05-11 #984 [reference] CONFIG_DB ↔ [orchagent](./reference/glossary.md#term-orchagent) クラス対応表
- 2026-05-11 #983 [meta] area Topics back-link 強化 + CI drift check
- 2026-05-11 #982 [meta] 全ページ frontmatter description 追加
- 2026-05-11 #981 [quality] HLD 中規模残 8 件 再構成
- 2026-05-11 #979 [meta] 品質改善 サンプリング監査 (round 10)

完全な履歴は [変更履歴](_meta/changelog.md) を参照してください。

## 品質指標

サイト全体の現時点での主な品質指標です。

- **code-verified ページ**: 586 件（実コードと照合済み）
- **監査平均評価**: round 32 で **4.972 / 5.0**（過去 32 ラウンドの最高値）
- **Topics 章カバレッジ**: 22 章 すべて 100%（概念 / 設定 / 運用 / 内部実装 / 障害切り分け 全部揃い）
- **Reference Mermaid 図カバレッジ**: CONFIG_DB / CLI / YANG いずれも 100%（各 Reference ページにスキーマ・フロー図を必ず添付）
- **本文 hld-only ページ**: 0 件（v1.0 GA 達成時点）

詳細は [カバレッジ](_meta/coverage.md) / [実装との乖離](_meta/discrepancies.md) / [変更履歴](_meta/changelog.md) を参照してください。

## 貢献方法

誤情報の報告・改善提案・Pull Request いずれも歓迎します。

- 軽い報告は [GitHub Issues](https://github.com/aoki-taquan/sonic-unofficial-docs/issues/new/choose) / [Discussions](https://github.com/aoki-taquan/sonic-unofficial-docs/discussions) へ
- Pull Request を送る場合は [CONTRIBUTING.md](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/CONTRIBUTING.md) の運用ルール（branch 命名、frontmatter 規約、Mermaid のみ、一次情報引用必須）に従ってください
- プロジェクトの目的・スコープ・ライセンス・運用方針の全体像は [このドキュメントについて](about.md) にまとまっています

## 検索のヒント

本サイトは [mkdocs-material](https://squidfunk.github.io/mkdocs-material/) の全文検索を備えています。

- 画面右上の検索ボックス（または `/` キー）から横断検索ができます
- 単語をスペース区切りで複数入れると AND 検索になります（例: `bgp graceful`）
- 日本語キーワードと英語キーワードの両方が効きます（例: `バッファ pool`、`route-map`）
- ヒット結果はページ内見出しまで降りるので、長いリファレンスでも目的のセクションへ直接飛べます
- CLI コマンド名・CONFIG_DB テーブル名・YANG モジュール名は原則として原文表記で索引化しています

## 更新サイクル

- **追従対象**: SONiC コミュニティ版 `master` ブランチのみ。ベンダー版・リリースブランチは対象外
- **裏取り**: 主要ページは `meta/index/repos.json` に記録した SHA に対して `.cache/sonic-sources/` の実コードと照合
- **頻度**: 不定期。新規 HLD・大型 PR をトリガに `meta/backlog/` を更新し、Writer → Reviewer → Verifier のパイプラインで反映
- **乖離検出**: 実装が HLD と食い違う箇所は `verification: discrepancy-found` として明示し、[実装との乖離](_meta/discrepancies.md) で一覧化

## 目次

- [読み手別ガイド](guides/index.md)
- [トピック](topics/index.md)
- [アーキテクチャ](architecture/index.md)
- [ルーティング](routing/index.md)
- [スイッチング](switching/index.md)
- [オーバーレイ](overlay/index.md)
- [ACL & QoS](acl-qos/index.md)
- [システム](system/index.md)
- [マネジメント](management/index.md)
- [プラットフォーム](platform/index.md)
- [内部実装](internals/index.md)
- [リファレンス](reference/index.md)

## フィードバック歓迎

本ドキュメントは AI が再構成して書いている非公式資料です。誤情報・記述漏れ・改善要望は歓迎します。

- 誤情報の報告・改善要望: [GitHub Issues](https://github.com/aoki-taquan/sonic-unofficial-docs/issues/new/choose)（`feedback` テンプレを用意しています）
- 雑談・質問・運用相談: [GitHub Discussions](https://github.com/aoki-taquan/sonic-unofficial-docs/discussions)

各ページの裏取りステータスは [カバレッジ](_meta/coverage.md) / [実装との乖離](reference/verification/discrepancy-index.md) で一覧できます。

## ライセンス

本ドキュメントの内容は、特に断りのない限り [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja) のもとで提供されます。

<!-- glossary-links-injected: e2892b76fd9a -->
