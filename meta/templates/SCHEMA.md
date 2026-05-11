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
| `monitor` | conditional | enum | `not_implemented` / `evolved_beyond_hld` / `partially_implemented` / `deprecated`。`verification: discrepancy-found` のとき **必須**。それ以外は optional |

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

## monitor の意味（discrepancy-found 専用タグ）

`verification: discrepancy-found` のページは、HLD と実装の差分の **性質** を表す `monitor:` タグを必ず持つ。Verifier / 読み手が「設計が未着手なのか、それとも実装が進化して別物になったのか」を一目で判別できるようにするため。

| 値 | 意味 | 判定基準 |
|----|------|---------|
| `not_implemented` | HLD は提案段階で、master に対応コードが一切無い | 関連 orch / table / CLI / yang を grep してヒット 0 件。HLD は採用見送りか着手前 |
| `evolved_beyond_hld` | 実装は HLD から進化し、名前・構造・経路が異なる | 機能としては存在するが、CONFIG_DB テーブル名 / 引数 / 変数名 / クラス名 / 設定経路が HLD と一致しない |
| `partially_implemented` | HLD のうち一部だけ取り込まれ、残りは欠落 | 取り込み済み要素と未取り込み要素が **両方** 列挙されており、ユーザに見える機能境界が HLD と一致しない |
| `deprecated` | HLD の方針自体が廃止され、後発別機能に置き換えられた | 「本 HLD は採用されず X に置き換えられている」「migration-to-Y で置換」等を本文に明記 |

判定が迷う場合の優先順位は **`deprecated` > `not_implemented` > `partially_implemented` > `evolved_beyond_hld`**。後発の置き換えがあるなら `deprecated`、全く取り込まれていないなら `not_implemented`、一部のみなら `partially_implemented`、全部実装はあるが形が違うなら `evolved_beyond_hld`。

`verification` が `discrepancy-found` 以外（`hld-only` / `code-verified` 等）でも、将来 monitor タグを再利用する余地はあるが現状は optional 扱い。

## 引用ルール

- ページ末に **「引用元」セクション必須**。frontmatter `sources` と本文中の脚注を統合する
- 本文中で込み入った主張には脚注 `[^1]` で commit パーマリンクを付与
- HTML コメントで詳細なエビデンス（実コード抜粋・推論）を埋め込む。Verifier がここを根拠に裏取り判定する
- evidence の `source: <repo>/<path>#L<start>-L<end>` の行範囲は **「該当行を含む」程度の精度で良い**。完全一致は要求しない（参照ヒントとしての誤差は許容する）

## related フィールドの表記

- `related.config_db`: テーブル名のみ（例: `BGP_NEIGHBOR`、`PORT_STORM_CONTROL`）
- `related.cli`: コマンドの先頭フォーム（例: `config bgp`、`show interface counters`）
- `related.yang`: YANG モジュール名のみ。**拡張子 `.yang` やリビジョンは付けない**（例: `sonic-bgp`、`sonic-port`）

## title の長さ

- frontmatter `title`（日本語）は **40 字を目安**。長い注釈は本文 H1 以降の説明文で扱う
- nav 表示が崩れない範囲で短く意味重視

## verification-queue.entries[].concerns の表現ガイド

- 各 concern は **動詞句で終わる**（「〜の確認」「〜の実装存在確認」「〜が現行 master にあるか未確認」等）
- 主語は省略可、対象（Orch / daemon / DB スキーマ / CLI / SAI 属性）を必ず含める
- 1 行 60 〜 120 字程度に収める。長くなるなら分ける
- 6 軸を網羅できれば十分: **(1) Orch / daemon の実装存在 (2) CONFIG_DB / STATE_DB スキーマ (3) CLI 取り込み (4) SAI 属性 / API (5) HLD 改訂日と現行 master の乖離 (6) upstream 仕様との差分**

## エビデンスコメントの形式

```markdown
<!-- evidence:
source: <repo>/<path>#L<start>-L<end> (sha: <commit-sha>)
excerpt: |
  <該当コードまたは HLD の生抜粋>
reasoning: <この記述が妥当である理由>
-->
```
