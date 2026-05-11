# sonic-unofficial-docs

[SONiC NOS](https://github.com/sonic-net/SONiC) の日本語非公式ドキュメント。

公式ドキュメントは品質と分散の問題があり、HLD はリポジトリごとに散らばり、HLD にも書かれていない仕様が実コードや issue にしか存在しない、という状況がある。本プロジェクトはそれを AI 駆動で再構成して読みやすい形に整え直すことを目的とする。

## スコープ

- 対象: コミュニティ版 SONiC の `master` のみ（ベンダー版・他ブランチは対象外）
- 言語: 日本語のみ
- 方針: 公式 HLD の翻訳ではなく **再構成**。HLD・実コード・issue を横断して、読み手が探す単位でページを書き直す
- 一次情報の引用を必須とし、各ページに裏取りステータスのバッジを付与する

詳しい運用ルールは [`CONTRIBUTING.md`](./CONTRIBUTING.md) を参照。

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

ドキュメントの内容は [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja)。
