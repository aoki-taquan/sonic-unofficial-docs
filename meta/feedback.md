# フィードバック処理方針

本ドキュメントは AI が再構成して書いている非公式資料であり、誤情報・記述漏れは構造的に避けられない。読者フィードバックは品質改善の主要な入力として扱う。

## 受付チャネル

| チャネル | 用途 |
|----------|------|
| GitHub Issues `type/feedback`（[`feedback.yml`](../.github/ISSUE_TEMPLATE/feedback.yml)） | 誤情報報告・記述漏れ・分かりにくさの指摘・リンク切れ |
| GitHub Discussions | 質問・雑談・運用相談・大きめの方針議論 |

Issues 側にはテンプレを用意してあり、種別・対象ページ・根拠の最低限を機械的に集める。

## トリアージ

Issue が立ったらラベルで仕分ける。

- `type/feedback` + `kind/error`: 誤情報の報告。最優先。該当ページの `verification` が `code-verified` だった場合は特に重く扱う
- `type/feedback` + `kind/missing`: 記述漏れ・追加要望。backlog 候補
- `type/feedback` + `kind/clarity`: 分かりにくさ。リライト候補
- `type/feedback` + `kind/build`: リンク切れ・mkdocs build 不具合。即修正

## 処理フロー

1. **裏取り** — 報告内容を SONiC 実コード / HLD / 関連 issue で確認する
2. **判定** — 以下のいずれかに分類
   - **誤情報を確認**: 該当ページを修正。frontmatter の `verification` を見直し（必要なら `discrepancy-found` に再分類）し、PR を出す
   - **両論ある / 仕様の範囲内**: ページに補足を加える、または Issue 内で議論
   - **却下**: スコープ外（ベンダー版 SONiC / 翻訳 / 古いブランチ）の場合は丁寧に閉じる
3. **記録** — 大きめの誤情報修正は `docs/_meta/discrepancies.md` への影響（実装と HLD の乖離だったのか、本ドキュメント側のミスだったのか）を切り分け、後者は再発防止のためにメタプロンプト（`meta/prompts/writer.md` 等）にフィードバックする

## 報告者への期待値

- AI が書いた非公式資料という前提で読んでもらう
- 「公式 SONiC として正しい挙動はどうあるべきか」という議論はスコープ外（上流 SONiC コミュニティへ）
- 一次情報の URL や PR 番号を添えてもらえると裏取りが早い

## SLA

非公式・有志運用なので明示的な SLA は設けない。緊急度の高い誤情報（実運用を誤らせる可能性のあるもの）は優先して処理する。

## カバレッジとの関係

[`docs/_meta/coverage.md`](../docs/_meta/coverage.md) は本ドキュメント全体の裏取り状況のスナップショット。`hld-only` や `stub` が多いページは特に読者フィードバックの価値が高く、レビュー優先度を上げる目安として使う。
