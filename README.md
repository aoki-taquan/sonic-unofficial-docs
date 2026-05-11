# sonic-unofficial-docs

[SONiC NOS](https://github.com/sonic-net/SONiC) の日本語非公式ドキュメント。

公式ドキュメントは品質と分散の問題があり、HLD はリポジトリごとに散らばり、HLD にも書かれていない仕様が実コードや issue にしか存在しない、という状況がある。本プロジェクトはそれを AI 駆動で再構成して読みやすい形に整え直すことを目的とする。

## スコープ

- 対象: コミュニティ版 SONiC の `master` のみ（ベンダー版・他ブランチは対象外）
- 言語: 日本語のみ
- 方針: 公式 HLD の翻訳ではなく **再構成**。HLD・実コード・issue を横断して、読み手が探す単位でページを書き直す
- 一次情報の引用を必須とし、各ページに裏取りステータスのバッジを付与する

詳しい運用ルールは [`CONTRIBUTING.md`](./CONTRIBUTING.md) を参照。

## 公開状態

現在の公開ステータス: **β リリース可（v1.0 未到達）**

品質指標 (2026-05-11 時点):

| 指標 | 値 |
|------|----|
| 総ページ数 | 779 |
| `code-verified` ページ | 545 |
| `discrepancy-found` ページ | 48 |
| `hld-only` 本文ページ | 0 |
| 監査平均評価 (round 6) | 4.978 / 5.0 |
| CLI Reference | 63 ページ |
| CONFIG_DB Reference | 110 ページ |
| YANG Reference | 70 ページ |
| Runbooks | 31 ページ |

v1.0 昇格までの残作業は [`meta/release-checklist-v1.md`](./meta/release-checklist-v1.md) を参照。GitHub Pages の Source 設定手順は [`meta/github-pages-setup.md`](./meta/github-pages-setup.md) を参照。

## ローカルでのプレビュー

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdocs serve
```

`http://127.0.0.1:8000/` でプレビューできます。

## ビルド

```bash
mkdocs build
```

`site/` ディレクトリに静的ファイルが出力されます。

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
