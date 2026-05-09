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
   - HLD 側に PNG 参照（例: `images/foo.png`）が含まれる場合、画像をそのままコピー・参照しない。図の意味を読み取り **mermaid（フローチャート / シーケンス / 状態遷移）で再描画**する
   - mermaid 化が冗長になる場合（テキストと表だけで十分な場合）は無理に図を作らない。**読み手の理解に貢献する場合のみ**作図する
7. 文体はである調・敬体禁止。専門用語は原語のまま（必要なら括弧で日本語訳）
8. **タイトル二段運用**: frontmatter の `title` は日本語で短く意味重視（例: 「BGP unnumbered ピアリング」）。一方ファイル slug は backlog 由来で英語のままで良い（例: `bgp-unnumbered.md`）。両者は無理に揃えなくて良い

## 出力

1. `docs/<area>/<slug>.md` を作成または更新
2. **`mkdocs.yml` を編集してはならない**。nav は awesome-pages プラグインが自動生成する。並び順を変えたい場合のみ該当ディレクトリの `.pages` を編集する
3. `mkdocs build --strict` がローカルで通ることを確認（`/home/coder/sonic-unofficial-docs/.venv/bin/mkdocs build --strict`）
4. ブランチ名: `page/<area>/<slug>`
5. PR タイトル: `[<area>] <ページタイトル>`
6. PR 本文に以下を含める:
   - 対応する issue 番号 (`Closes #N`)
   - 参照した一次情報のリスト
   - 自分で気付いた懸念点（HLD と実装の差分の可能性 等）

`related.config_db` `related.cli` `related.yang` は HLD に関連記述が無ければ空配列で良い。その場合は本文に「該当する CLI / CONFIG_DB は無い」または「未確認」と明記する。

## 禁止事項

- 一次情報の URL を捏造しない
- 自信のない記述には `verification: hld-only` 以下に留める
- HLD の翻訳調をそのまま貼り付けない
- 機能の存在自体を推測で書かない（実体が確認できたものだけ）

## 古い HLD / upstream / 未採用提案 HLD の取扱い

冒頭に **`!!! warning` admonition** で次のいずれかに該当する旨を明記する:

- **古い HLD**: 改訂履歴 (Revision Table) や最終更新日が 3 年以上前。`verification-queue.priority = high`
- **upstream 由来**: SONiC 独自仕様ではなく upstream 文書（`sonic-frr/doc/` の FRR 上流文書、SAI 仕様書 等）。差分が分かるなら併記
- **採否不明な提案**: 「Proposal」「Future Work」等のステータスで、現行 master に取り込まれているか不確かな HLD。本文の主要な記述に対して「（採択されたか未確認）」を併記し、`priority = high` で `verification-queue` に登録
- **2 年以上前 + Initial Proposal**: 改訂 2 年以上経過していて Status が "Initial" / "Proposal" のままの HLD は、未採用の可能性が高いため上記の "採否不明な提案" と同様に扱う

## 大きな HLD (>25KB) の扱い

- 1 ページに無理やり押し込まない。**主要な architecturally distinctive な要素**（仕組みのコア・他機能との境界・CONFIG_DB / SAI 属性追加）に絞り、詳細フローや edge case は概要のみで本文 H1 末に「詳細は HLD `<path>` を参照」と書く
- 章単位で分割ページ化したい場合は backlog にまだ無い派生 slug を別 issue として立ててもよい

## ソースファイルの読み方

- HLD のパス・ディレクトリ名にスペースや特殊文字が含まれる場合（例: `doc/layer2-forwarding-enhancements/SONiC Layer 2 Forwarding Enhancements HLD.md`）、シェルの `cat` ではなく Read ツールで開く。`bash` 経由だとクォート漏れで読めないことがある
- `related.config_db` `related.cli` `related.yang` に **HLD で言及されていない実装由来の項目を推測で書かない**。確実なもののみ列挙し、不明なら空配列にして本文側に注記する

## 裏取りキューへの登録

Writer が `verification: hld-only` 等で残した懸念点（HLD と実装の差分の可能性、要件レベル止まりで実装未確認、CONFIG_DB が未定義 等）は、PR 本文に書くだけでなく **`meta/verification-queue.json`** に追記する。Verifier が優先度順に拾えるようにするため。

エントリ形式:

```json
{
  "page": "docs/routing/default-route.md",
  "issue": 1,
  "pr": 7,
  "verification": "hld-only",
  "concerns": [
    "実装側 (sonic-linkmgrd の MuxOrch) の状態遷移がドキュメントと一致するか未確認",
    "CONFIG_DB の MUX_CABLE テーブルとの対応が未確認"
  ],
  "priority": "medium"
}
```

`priority` は `high` / `medium` / `low`。`high` は「現役機能で陳腐化リスク大」、`low` は「廃止予定 / 限定的なシナリオのみ」。

**`pr` フィールドは Writer 段階では未確定で良い**（PR 作成前にエントリを書くため）。PR 番号が決まり次第、Reviewer または Merger 段階で同じエントリの `pr` を後埋めする。
