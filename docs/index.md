---
title: SONiC 非公式ドキュメント
verification: meta
---

# SONiC 非公式ドキュメント

[SONiC NOS](https://github.com/sonic-net/SONiC) の日本語非公式ドキュメントへようこそ。

!!! warning "非公式ドキュメントについて"
    このドキュメントは有志による非公式ドキュメントです。SONiC プロジェクトおよび SONiC Foundation とは関係ありません。
    内容の正確性についてはベストエフォートで管理していますが、最新の正確な情報は [公式リポジトリ](https://github.com/sonic-net/SONiC) を参照してください。

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

## ライセンス

本ドキュメントの内容は、特に断りのない限り [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja) のもとで提供されます。
