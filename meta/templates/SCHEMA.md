# ページ frontmatter スキーマ

すべてのドキュメントページは以下の frontmatter を持つ。Reviewer はこのスキーマに従って機械検査する。

## フィールド

| キー | 必須 | 値 | 説明 |
|------|------|----|------|
| `title` | ✅ | string | 表示タイトル |
| `area` | ✅ | enum | `routing` / `switching` / `overlay` / `acl-qos` / `system` / `management` / `platform` / `architecture` / `internals` / `reference` |
| `verification` | ✅ | enum | `hld-only` / `issue-confirmed` / `code-verified` / `discrepancy-found` / `stub` / `meta` |
| `last_verified` | ✅ | date | `YYYY-MM-DD`。裏取りまたは更新を行った日 |
| `sources` | ✅ | list | このページの根拠となる一次情報のリスト |
| `sources[].repo` | ✅ | string | `sonic-net/<repo>` 形式 |
| `sources[].path` | ✅ | string | リポジトリルートからの相対パス |
| `sources[].ref` | ✅ | string | commit SHA（master のスナップショット固定） |
| `related.config_db` | optional | list | 関連 CONFIG_DB テーブル名 |
| `related.cli` | optional | list | 関連 CLI コマンド |
| `related.yang` | optional | list | 関連 YANG モジュール |

`related.*` は **空配列でも合格**。HLD で言及されていない実装由来の項目を推測で書いてはならない。確実なもののみ列挙し、不明なら空配列にして本文側に「該当する CLI / CONFIG_DB は HLD では未定義」等を注記する。

## verification の意味

| 値 | 意味 | 表示バッジ |
|----|------|----------|
| `stub` | 章 index 等のプレースホルダ | （非表示） |
| `meta` | プロジェクト説明など SONiC 仕様外のページ | （非表示） |
| `hld-only` | 公式 HLD だけを根拠に書いた。コード未確認 | 📘 HLD-only |
| `issue-confirmed` | issue/PR コメントで補強済み | 🔍 Issue-confirmed |
| `code-verified` | 該当実装を読んで一致確認済み | ✅ Code-verified |
| `discrepancy-found` | HLD と実装に差分あり。本文に注記 | ⚠️ Discrepancy-found |

## 引用ルール

- ページ末に **「引用元」セクション必須**。frontmatter `sources` と本文中の脚注を統合する
- 本文中で込み入った主張には脚注 `[^1]` で commit パーマリンクを付与
- HTML コメントで詳細なエビデンス（実コード抜粋・推論）を埋め込む。Verifier がここを根拠に裏取り判定する

## エビデンスコメントの形式

```markdown
<!-- evidence:
source: <repo>/<path>#L<start>-L<end> (sha: <commit-sha>)
excerpt: |
  <該当コードまたは HLD の生抜粋>
reasoning: <この記述が妥当である理由>
-->
```
