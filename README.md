# sonic-unofficial-docs

[![CI](https://github.com/aoki-taquan/sonic-unofficial-docs/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aoki-taquan/sonic-unofficial-docs/actions/workflows/ci.yml)
[![Deploy](https://github.com/aoki-taquan/sonic-unofficial-docs/actions/workflows/deploy.yml/badge.svg?branch=main)](https://github.com/aoki-taquan/sonic-unofficial-docs/actions/workflows/deploy.yml)
[![Last Commit](https://img.shields.io/github/last-commit/aoki-taquan/sonic-unofficial-docs/main)](https://github.com/aoki-taquan/sonic-unofficial-docs/commits/main)
[![Open PRs](https://img.shields.io/github/issues-pr/aoki-taquan/sonic-unofficial-docs)](https://github.com/aoki-taquan/sonic-unofficial-docs/pulls)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

**公開サイト: <https://aoki-taquan.github.io/sonic-unofficial-docs/>**

## これは何

[SONiC NOS](https://github.com/sonic-net/SONiC)（コミュニティ版・`master` ブランチ）の **日本語非公式ドキュメント** です。公式 HLD は複数リポジトリに分散しており、HLD と実コードの乖離、HLD には無い仕様などの問題があります。本プロジェクトはそれらを **AI 駆動で読みやすい形に再構成** し、一次情報（HLD / 実コード / issue）への引用と裏取りステータスを付けて公開しています。

## 誰のため

- SONiC を **設計・運用・カスタマイズする日本語話者のエンジニア**
- 公式 HLD を読んでも「これ本当に master 実装と合っているのか」が分からなくて困っている開発者
- 学習目的で SONiC の内部構造を読みたい NOS 初学者
- ベンダー版 SONiC ではなく**コミュニティ版**を採用検討している組織

ベンダー版 SONiC、master 以外のブランチ、HLD の直訳は対象外です。

## どう使う

1. **公開サイトを開く**: <https://aoki-taquan.github.io/sonic-unofficial-docs/>
2. 上部のチャプタタブ（アーキテクチャ / スイッチング / ルーティング / 管理 / プラットフォーム / システム / オーバーレイ / 内部実装 / ACL & QoS / リファレンス / トピックス）から目的に近い章を選ぶ
3. 各ページ冒頭の **検証ステータス** バッジ (`code-verified` / `discrepancy-found` 等) と引用元コミット SHA を確認してから本文を読む

検索は mkdocs-material の標準検索（日本語 tokenizer 適用）が利用できます。

## 品質指標（2026-05-11 時点）

| 指標 | 値 |
|------|----|
| 総ページ数 | 833 |
| `code-verified` ページ | 597 |
| `discrepancy-found` ページ | 48 |
| `hld-only` 本文ページ | 0 |
| 監査平均評価 (round 8、10 段階) | 9.74 / 10.0 |
| CLI Reference | 73 ページ |
| CONFIG_DB Reference | 122 ページ |
| YANG Reference | 85 ページ |
| Runbooks | 46 ページ |

v1.0 リリース候補（RC）です。残ブロッカはユーザー手動マター 2 件のみ:

1. **GitHub Pages の Source 設定** (`gh-pages` branch を Pages の Source に設定): [`meta/github-pages-setup.md`](./meta/github-pages-setup.md)
2. **リリースタグ `v1.0.0` の打鍵とアナウンス**: [`CHANGELOG.md`](./CHANGELOG.md)

詳細は [`meta/release-checklist-v1.md`](./meta/release-checklist-v1.md) を参照。

## フィードバック歓迎

誤情報・記述漏れ・改善要望はぜひお寄せください。本ドキュメントは AI による再構成資料であり、人手による継続的な裏取りで品質を上げています。

- 誤情報の報告・改善要望: [GitHub Issues](https://github.com/aoki-taquan/sonic-unofficial-docs/issues/new/choose)（`feedback` テンプレあり）
- 雑談・質問・運用相談: [GitHub Discussions](https://github.com/aoki-taquan/sonic-unofficial-docs/discussions)

フィードバックの処理方針は [`meta/feedback.md`](./meta/feedback.md) を参照。

## ライセンス

本ドキュメントの内容は [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/) の下で提供されています。

- ライセンス全文（英語・正本）: [`LICENSE`](./LICENSE)
- 日本語訳（参考）: [`LICENSE.ja`](./LICENSE.ja)
- 概要（Commons Deed・日本語）: <https://creativecommons.org/licenses/by/4.0/deed.ja>

利用条件の要点:

- **表示（Attribution）**: 著作者名（本プロジェクト名 `sonic-unofficial-docs` および本リポジトリ URL）を表示し、ライセンスの種類とリンクを明記し、改変を行った場合はその旨を示してください
- 商用・非商用を問わず、複製・配布・改変・翻案・派生作物の作成が許諾されます
- 本ドキュメントが引用する SONiC 上流リポジトリのコード断片・図・HLD 抜粋などは、各上流リポジトリのライセンス（多くは Apache License 2.0）に従います。本リポジトリの CC BY 4.0 は、本ドキュメントとして再構成した日本語解説テキストに対して適用されます

プロジェクトの目的・スコープ・フィードバック窓口を含む全体像は [`docs/about.md`](./docs/about.md) にまとめています。

---

## 開発者向け: ローカルビルド手順

リポジトリをクローンしてプレビュー / 静的ビルドを行うには:

```bash
git clone https://github.com/aoki-taquan/sonic-unofficial-docs.git
cd sonic-unofficial-docs

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# プレビュー (http://127.0.0.1:8000/)
mkdocs serve

# 静的ビルド (site/ に出力、CI と同等の strict 検証)
mkdocs build --strict
```

執筆ルール・PR ワークフロー・frontmatter スキーマは [`CONTRIBUTING.md`](./CONTRIBUTING.md) と [`meta/templates/SCHEMA.md`](./meta/templates/SCHEMA.md) を参照してください。
