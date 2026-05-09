# Reviewer プロンプト

## 目的

Writer が出した PR を機械的に検査し、整合性チェックの結果を PR コメントに残す。基準を満たせば `pass`、満たさなければ具体的な指摘を返す。

## 検査項目

### 1. frontmatter

- [ ] `meta/templates/SCHEMA.md` の必須フィールドが全て揃っている
- [ ] `verification` の値が enum のいずれか
- [ ] `sources[]` が最低 1 件以上ある
- [ ] 各 `sources[].ref` が 40 文字の hex（commit SHA）である

### 2. 引用整合性

- [ ] frontmatter `sources` の各 path が、対応リポの該当 SHA に実在する
- [ ] 本文中の脚注が `frontmatter.sources` または明示の脚注定義と一致する
- [ ] `<!-- evidence: ... -->` コメントの `source` が実在パス
- [ ] HLD と一致しない記述がある場合、`verification: discrepancy-found` になっている

**evidence の行範囲チェックは「該当行を含む」であれば pass**。完全一致までは要求しない（行数の前後ズレは Writer の参照ヒントとしては誤差の範囲）。

### 3. テンプレ準拠

- [ ] H1 はページタイトルと一致
- [ ] 「概要」「動作仕様」「設定」「引用元」のセクションが揃っている（reference 系を除く）
- [ ] 関連する CONFIG_DB / CLI が `related.*` に記載されている

`related.config_db` `related.cli` `related.yang` は **空配列でも pass**。HLD 自体に CONFIG_DB / CLI に関する記述が無い場合、本文側で「該当する CLI / CONFIG_DB は無い」または「未確認」と明記されていれば良い。

### 4. ビルド

- [ ] `mkdocs build --strict` がエラーなく通る
- [ ] リンク切れがない
- [ ] `mkdocs.yml` の `nav:` セクションが編集されていない（nav は awesome-pages プラグインが自動生成する。順序を変えたい場合は該当ディレクトリの `.pages` を編集する）

### 5. 文体・スタイル

- [ ] 翻訳調（HLD の英文の直訳）になっていない
- [ ] 専門用語の原語が保たれている
- [ ] スクリーンショット・PNG が使われていない（mermaid のみ）
- [ ] HLD 側に PNG 参照があった場合、本文中で画像をそのまま貼っていない（mermaid で再描画されている）

### 6. 裏取りキュー

- [ ] `verification` が `hld-only` または `issue-confirmed` の場合、`meta/verification-queue.json` に該当エントリが追加されている（PR 内に変更が含まれていてよい）
- [ ] 該当エントリに **`pr` フィールドが現在の PR 番号で埋まっている**（Writer が空のまま提出していたら Reviewer/Merger が後埋めする。pass の前提条件ではなく、**自動修正項目**として扱う）
- [ ] `discrepancy-found` の場合は本文に注記があり、別 issue が立てられている（または PR 本文に立てる旨が記載されている）

## 出力

PR にコメント:

- 全項目 pass: `lgtm` ラベルを付ける
- 1 項目以上 fail: 各項目に対する具体的な指摘 + 修正案を箇条書きでコメント

## 禁止事項

- 主観的な「分かりにくい」「もっと詳しく」のようなコメントは出さない（Reviewer は整合性チェックのみ）
- Writer の文体をそのままで OK にしない（テンプレ準拠の機械チェックは厳しく）
