---
title: このドキュメントについて
description: このドキュメントについて — 本ページは sonic-unofficial-docs プロジェクトの目的・スコープ・ライセンス・フィードバック窓口・貢献方法をまとめた概要ページです。トップページ
  (index.md) が「読み始める入口」であるのに対し、本ページは「プロジェクトの性格・規約」を集約する位置付けです。
verification: meta
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# このドキュメントについて

本ページは `sonic-unofficial-docs` プロジェクトの目的・スコープ・ライセンス・フィードバック窓口・貢献方法をまとめた概要ページです。トップページ ([index.md](index.md)) が「読み始める入口」であるのに対し、本ページは「プロジェクトの性格・規約」を集約する位置付けです。

## ワンライナー

> [SONiC](./reference/glossary.md#term-sonic) NOS（コミュニティ版・`master` ブランチ）の高水準設計（HLD）・実コード・YANG・CLI・GitHub Issue を AI が横断的に**再構成**して書く、**日本語の非公式ドキュメント**です。

## プロジェクトの目的

[SONiC NOS](https://github.com/sonic-net/SONiC)（Software for Open Networking in the Cloud）のコミュニティ版を対象に、AI 駆動で**日本語の非公式ドキュメントを再構成**することを目的としています。

SONiC の公式ドキュメントには以下のような構造的な課題があります。

- [HLD](./reference/glossary.md#term-hld)（High-Level Design）が複数のリポジトリ（[SONiC](https://github.com/sonic-net/SONiC), [sonic-buildimage](https://github.com/sonic-net/sonic-buildimage), [sonic-swss](https://github.com/sonic-net/sonic-swss) など）に散在している。
- HLD と実装の更新タイミングが乖離しており、HLD に書かれていない仕様が実コードや GitHub Issue にしか存在しないケースが多い。
- 設定（[CONFIG_DB](./reference/glossary.md#term-config_db)）、CLI、[YANG](./reference/glossary.md#term-yang)、daemon／orch 実装の対応関係を機械的に追える資料がない。

本プロジェクトは公式 HLD の翻訳ではなく、**HLD・実コード・YANG・CLI・Issue を横断して再構成**することにより、読み手が「探す単位」でページを引けるドキュメントを目指しています。

## 対象読者

本ドキュメントが特に有用と考える読者:

- **SONiC をこれから触る方**: 全体像・アーキテクチャ・設定モデル・仮想環境での導入手順を順に把握したい（→ [初学者向けガイド](guides/beginner.md)）
- **運用者**: 日々の状態確認、設定変更、障害切り分けを CLI / [CONFIG_DB](./reference/glossary.md#term-config_db) / Runbook の単位で素早く引きたい（→ [運用者向けガイド](guides/operator.md) / [Runbook 一覧](reference/runbooks/index.md)）
- **開発者**: [HLD](./reference/glossary.md#term-hld) / [YANG](./reference/glossary.md#term-yang) / CONFIG_DB / daemon／orch 実装の対応関係を追って機能追加・パッチを書きたい（→ [開発者向けガイド](guides/developer.md)）
- **評価者・PoC 担当**: ラボで SONiC を起動し基本設定と状態確認まで一気通貫で確認したい（→ [評価者向けガイド](guides/evaluator.md)）

## 対象外

以下は本プロジェクトのスコープ外であり、扱いません。

- ベンダー版 SONiC（NVIDIA / Edgecore / Cisco / [AsterNOS](./reference/glossary.md#term-asternos) など）の独自機能や差分
- コミュニティ版 SONiC の `master` 以外のブランチ（リリースブランチ・古いブランチ）
- 公式 HLD の直訳・公式ドキュメントの翻訳
- スクリーンショット / PNG（図は Mermaid のみ）
- 英語・その他言語版（将来的に再検討）

## スコープ

| 項目 | 対象 | 対象外 |
|------|------|--------|
| ディストリビューション | コミュニティ版 SONiC（[sonic-net 配下](https://github.com/sonic-net)） | ベンダー版 SONiC（NVIDIA / Edgecore / Cisco / [AsterNOS](./reference/glossary.md#term-asternos) など） |
| ブランチ | `master` のみ | リリースブランチ・古いブランチ |
| 言語 | 日本語のみ | 多言語化（英語版は公式リポジトリを参照） |
| 形式 | HLD・実コード・YANG・CLI を横断した再構成 | HLD の直訳・スクリーンショット集 |
| 図 | Mermaid のみ | PNG／手書き図 |

## 一次情報の引用と裏取りステータス

各ページの frontmatter には `verification` フィールドで裏取り状況を明示しています。

| ステータス | 意味 |
|------------|------|
| `code-verified` | 実コード（SONiC リポジトリの該当 SHA）との照合済み |
| `discrepancy-found` | HLD と実装の乖離を確認し、その旨を本文中に明記している |
| `meta` | プロジェクト運営に関するメタページ（本ページなど） |
| `stub` | 執筆途中のスタブ（β 段階では極力残さない） |

品質指標（2026-05-12 時点）:

- 総ページ数: 833
- `code-verified` ページ: 597
- `discrepancy-found` ページ: 48
- `hld-only` 本文ページ: 0
- 監査平均評価 (round 32、5 段階): **4.972 / 5.0**
- Topics 22 章 すべて 100% カバレッジ（概念 / 設定 / 運用 / 内部実装 / 障害切り分け 全部揃い）
- Reference Mermaid 図カバレッジ: CONFIG_DB / CLI / YANG いずれも 100%
- CLI Reference: 73 ページ / CONFIG_DB Reference: 122 ページ / YANG Reference: 85 ページ / Runbooks: 46 ページ

最新の品質状態とロードマップは [`CHANGELOG`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/CHANGELOG.md) と `meta/roadmap-v2.md` を参照してください。

## ライセンス

本ドキュメントの内容は [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) の下で提供されています。

- ライセンス全文（英語・正本）: [`LICENSE`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/LICENSE)
- 日本語訳（公式・参考）: [`LICENSE.ja`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/LICENSE.ja)
- 概要（Commons Deed・日本語）: <https://creativecommons.org/licenses/by/4.0/deed.ja>

利用条件の要点:

- **表示（Attribution）**: 利用時には著作者名（本プロジェクト名 `sonic-unofficial-docs` および本リポジトリ URL）を表示し、ライセンスの種類とリンクを明記し、改変を行った場合はその旨を示してください。
- 商用・非商用を問わず、複製・配布・改変・翻案・派生作物の作成が許諾されます。
- 本ドキュメントが引用する SONiC 上流リポジトリのコード断片・図・HLD 抜粋などは、各上流リポジトリのライセンス（多くは Apache License 2.0）に従います。本リポジトリの CC BY 4.0 は、本ドキュメントとして再構成した日本語解説テキストに対して適用されます。

クレジット表記の例:

```text
本資料は sonic-unofficial-docs (https://github.com/aoki-taquan/sonic-unofficial-docs) に基づく。
CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)
```

## 非公式である旨の明記

本ドキュメントは有志による非公式ドキュメントであり、SONiC プロジェクトおよび SONiC Foundation とは関係ありません。内容の正確性についてはベストエフォートで管理していますが、最新の正確な情報は [公式リポジトリ](https://github.com/sonic-net/SONiC) を参照してください。

## フィードバック

AI が再構成して書いている非公式資料という性質上、誤情報・記述漏れは構造的に発生し得ます。読者からのフィードバックを品質改善の主要な入力として扱います。

| チャネル | 用途 |
|----------|------|
| [GitHub Issues](https://github.com/aoki-taquan/sonic-unofficial-docs/issues/new/choose) (`type/feedback`) | 誤情報報告・記述漏れ・分かりにくさの指摘・リンク切れ |
| [GitHub Discussions](https://github.com/aoki-taquan/sonic-unofficial-docs/discussions) | 質問・雑談・運用相談・大きめの方針議論 |

報告時には、対象ページの URL と、可能であれば SONiC 上流の一次情報（コード行・PR 番号・Issue 番号）を添えていただけると裏取りが早くなります。

フィードバックの処理フロー・SLA・トリアージ方針は [`meta/feedback.md`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/meta/feedback.md) を参照してください。

## 貢献方法

本リポジトリへの直接的なコントリビューションを歓迎します。

- **誤りの報告のみ**: 上記の Issue / Discussions チャネルへ。
- **Pull Request を送る**: [`CONTRIBUTING.md`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/CONTRIBUTING.md) に運用ルール（branch 命名、frontmatter 規約、Mermaid のみ・PNG 不可、一次情報引用必須など）を記載しています。
- **新規ページ追加・大幅改稿**: `meta/templates/page.md` のテンプレートと `meta/templates/SCHEMA.md` の frontmatter 規約に従ってください。

AI 駆動の運用パイプライン（Indexer → Backlog Generator → Writer → Reviewer → Merger → Verifier）の概要は `CONTRIBUTING.md` と `meta/prompts/` 配下のロール定義に記載しています。

## 関連ページ

- [トップページ](index.md)
- [初学者向けガイド](guides/beginner.md)
- [運用者向けガイド](guides/operator.md)
- [開発者向けガイド](guides/developer.md)
- [評価者向けガイド](guides/evaluator.md)
- [カバレッジ状況 (_meta/coverage)](_meta/coverage.md)
- [HLD と実装の乖離一覧 (_meta/discrepancies)](_meta/discrepancies.md)

<!-- glossary-links-injected: 8ba32e5aa69d -->
