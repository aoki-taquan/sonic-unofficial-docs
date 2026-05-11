---
title: SONiC 非公式ドキュメント
verification: meta
---

# SONiC 非公式ドキュメント

[SONiC NOS](https://github.com/sonic-net/SONiC) の日本語非公式ドキュメントへようこそ。

!!! warning "非公式ドキュメントについて"
    このドキュメントは有志による非公式ドキュメントです。SONiC プロジェクトおよび SONiC Foundation とは関係ありません。
    内容の正確性についてはベストエフォートで管理していますが、最新の正確な情報は [公式リポジトリ](https://github.com/sonic-net/SONiC) を参照してください。

## 読み手別の入口

目的に応じて、既存ページを読む順番をまとめたガイドです。

- [初学者向け](guides/beginner.md): SONiC の全体像、設定モデル、仮想環境での導入を順に把握したい読者向け。
- [運用者向け](guides/operator.md): 日々の確認、設定変更、障害調査、CONFIG_DB の意味確認を素早く引きたい読者向け。
- [開発者向け](guides/developer.md): HLD、YANG、CONFIG_DB、CLI、daemon / orch、テスト計画の対応関係を追いたい読者向け。
- [評価者向け](guides/evaluator.md): ラボで SONiC を起動し、基本設定と状態確認まで一連の流れを辿りたい読者向け。

## SONiC とは

SONiC（Software for Open Networking in the Cloud）は、Linux（Debian）ベースのオープンソースなネットワーク OS（NOS）です。Microsoft と Open Compute Project（OCP）によって開発され、現在は Linux Foundation 配下のオープンソースプロジェクトとして運営されています。

主要な構成要素:

- **SAI (Switch Abstraction Interface)**: ASIC ベンダーを抽象化する標準 API
- **コンテナ化されたマイクロサービス群**: BGP（FRR）、LLDP、SNMP、PMON など機能ごとに Docker コンテナで分離
- **Redis を中央データベースとした状態管理**: CONFIG_DB / APPL_DB / STATE_DB / ASIC_DB など

## このドキュメントの方針

- 公式 HLD の翻訳ではなく、**再構成**された解説
- HLD・実コード・issue を横断して引用し、各ページの末尾に出典を明示
- 各ページに裏取りステータス（HLD-only / Issue-confirmed / Code-verified）を付与

## 目次

- [読み手別ガイド](guides/index.md)
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

各ページの裏取りステータスは [カバレッジ](_meta/coverage.md) / [実装との乖離](_meta/discrepancies.md) で一覧できます。

## ライセンス

本ドキュメントの内容は、特に断りのない限り [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja) のもとで提供されます。
