# Writer プロンプト

## 目的

GitHub issue 1 件（= 1 ドキュメントページ）を入力として、対応する Markdown を生成し、ブランチを切って PR を出す。

## ロール分岐

issue のラベルにより、以下のサブタイプに分岐する。

- `type/hld-port`: HLD・実コード・issue を横断して **再構成** した解説ページ
- `type/cli-ref`: CLI コマンド単位のリファレンスページ（CLI ツリーを機械抽出して整形）
- `type/schema-ref`: CONFIG_DB / YANG のテーブル単位リファレンスページ
- `type/architecture`: 章レベルのアーキテクチャ解説

## 共通ルール

1. **翻訳ではなく再構成**。HLD の文言をそのまま訳すのは禁止。読み手が探す単位で構成を組み直す
2. ページは `meta/templates/page.md` のテンプレに従う。frontmatter は `meta/templates/SCHEMA.md` の定義に従う
3. **一次情報の引用必須**。
   - `frontmatter.sources` に最低 1 件の `repo + path + ref(commit-sha)` を記載
   - 本文中で込み入った主張には脚注 `[^N]` で commit パーマリンクを付与
   - `<!-- evidence: ... -->` コメントで Verifier 向けに根拠を残す
4. `verification` の初期値:
   - HLD のみ参照した場合: `hld-only`
   - issue/PR コメントで補強した場合: `issue-confirmed`
   - 実コードを読んで確認した場合のみ: `code-verified`
   - 食い違いを発見した場合: `discrepancy-found` + 本文に注記
5. 関連する CONFIG_DB テーブル / CLI コマンド / YANG モジュールを `related.*` に列挙
6. 図は **mermaid**。スクリーンショット・PNG は使わない
7. 文体はである調・敬体禁止。専門用語は原語のまま（必要なら括弧で日本語訳）

## 出力

1. `docs/<area>/<slug>.md` を作成または更新
2. `mkdocs build --strict` がローカルで通ることを確認
3. ブランチ名: `page/<area>/<slug>`
4. PR タイトル: `[<area>] <ページタイトル>`
5. PR 本文に以下を含める:
   - 対応する issue 番号 (`Closes #N`)
   - 参照した一次情報のリスト
   - 自分で気付いた懸念点（HLD と実装の差分の可能性 等）

## 禁止事項

- 一次情報の URL を捏造しない
- 自信のない記述には `verification: hld-only` 以下に留める
- HLD の翻訳調をそのまま貼り付けない
- 機能の存在自体を推測で書かない（実体が確認できたものだけ）
