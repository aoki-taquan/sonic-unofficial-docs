# sonic-unofficial-docs

[Sonic](https://github.com/valeriansaliou/sonic) の日本語非公式ドキュメント。

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

## ライセンス

ドキュメントの内容は [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja)。
