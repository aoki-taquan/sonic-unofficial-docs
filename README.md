# sonic-unofficial-docs

[![CI](https://github.com/aoki-taquan/sonic-unofficial-docs/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aoki-taquan/sonic-unofficial-docs/actions/workflows/ci.yml?query=branch%3Amain)
[![Deploy](https://github.com/aoki-taquan/sonic-unofficial-docs/actions/workflows/deploy.yml/badge.svg?branch=main)](https://github.com/aoki-taquan/sonic-unofficial-docs/actions/workflows/deploy.yml?query=branch%3Amain)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

[SONiC NOS](https://github.com/sonic-net/SONiC) の日本語非公式ドキュメント。

**公開サイト**: <https://aoki-taquan.github.io/sonic-unofficial-docs/>

## これは何

コミュニティ版 SONiC (`sonic-net/SONiC` の `master`) について、リポジトリごとに分散している公式 HLD・実コード・issue を横断して、AI が**再構成**して書き直した日本語ドキュメント。公式 HLD の翻訳ではなく、読み手が探す単位で章立てし、各ページに一次情報の引用と裏取りステータス（`code-verified` / `discrepancy-found` / `hld-only` 等）のバッジを付けている。

## 誰のため

- SONiC を**運用 / 評価 / 検証**したいネットワーク技術者で、英語の HLD を 1 から追うのが重い人
- SONiC に**機能追加 / バグ修正**を入れたい開発者で、どこに何があるかの全体地図がほしい人
- 公式 HLD と実装の**差分**（HLD では未定義 / HLD と実コードが乖離している箇所）を素早く把握したい人

## どう使う

- 公開サイト <https://aoki-taquan.github.io/sonic-unofficial-docs/> をブラウザで読む
- 目的の機能が分かっていれば左ナビから章（routing / switching / overlay / acl-qos / platform / system / management / architecture / internals / reference）を選ぶ
- 設定名・CLI 名から逆引きしたければ `reference/` 配下の CLI / CONFIG_DB / YANG リファレンスを参照
- 各ページのバッジで裏取り状況が見える（`code-verified` は実装を読んで一致確認済み、`discrepancy-found` は HLD と実装に差分がある旨を本文で注記）

## スコープ

- 対象: コミュニティ版 SONiC の `master` のみ（ベンダー版・他ブランチは対象外）
- 言語: 日本語のみ
- 方針: 公式 HLD の翻訳ではなく **再構成**。HLD・実コード・issue を横断して、読み手が探す単位でページを書き直す
- 一次情報の引用を必須とし、各ページに裏取りステータスのバッジを付与する

詳しい運用ルールは [`CONTRIBUTING.md`](./CONTRIBUTING.md) を参照。リポジトリ管理者向けの branch protection 設定は [`meta/branch-protection.md`](./meta/branch-protection.md) を参照。

## 公開状態

公開中: <https://aoki-taquan.github.io/sonic-unofficial-docs/>

最新の品質指標は [`docs/_meta/snapshot.md`](./docs/_meta/snapshot.md) を参照。代表的には `code-verified` / `runbook-verified` ページが大半、`hld-only` は 0 件、定期的な master 追従と verifier 運用で鮮度を維持しています。

更新履歴は [`CHANGELOG.md`](./CHANGELOG.md) を参照。

## フィードバック歓迎

本ドキュメントは AI が再構成して書いている非公式資料です。誤情報・記述漏れ・改善要望はぜひお寄せください。

- 誤情報の報告・改善要望: [GitHub Issues](https://github.com/aoki-taquan/sonic-unofficial-docs/issues/new/choose)（`feedback` テンプレあり）
- 雑談・質問・運用相談: [GitHub Discussions](https://github.com/aoki-taquan/sonic-unofficial-docs/discussions)

フィードバックの処理方針は [`meta/feedback.md`](./meta/feedback.md) を参照。

## ライセンス

本ドキュメントの内容は [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) の下で提供されています。

- ライセンス全文（英語・正本）: [`LICENSE`](./LICENSE)
- 日本語訳（公式・参考）: [`LICENSE.ja`](./LICENSE.ja)
- 概要（Commons Deed・日本語）: <https://creativecommons.org/licenses/by/4.0/deed.ja>

利用条件の要点:

- **表示（Attribution）**: 著作者名（本プロジェクト名 `sonic-unofficial-docs` および本リポジトリ URL）を表示し、ライセンスの種類とリンクを明記し、改変を行った場合はその旨を示してください。
- 商用・非商用を問わず、複製・配布・改変・翻案・派生作物の作成が許諾されます。
- 本ドキュメントが引用する SONiC 上流リポジトリのコード断片・図・HLD 抜粋などは、各上流リポジトリのライセンス（多くは Apache License 2.0）に従います。本リポジトリの CC BY 4.0 は、本ドキュメントとして再構成した日本語解説テキストに対して適用されます。

プロジェクトの目的・スコープ・フィードバック窓口を含む全体像は [`docs/about.md`](./docs/about.md) にまとめています。

## ローカルでのプレビュー / ビルド

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# プレビュー (http://127.0.0.1:8000/)
mkdocs serve

# 静的ビルド (site/ に出力)
mkdocs build --strict
```

`mkdocs build --strict` は CI と同じ条件でビルドする。`--strict` を付けると warning も failure 扱いになるため、PR を出す前に必ず通しておく。
