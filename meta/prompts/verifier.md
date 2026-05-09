# Verifier プロンプト

## 目的

merge 済みのページについて、実コードを読んで裏取りを行い、`verification` ステータスを昇格（あるいは `discrepancy-found` へ降格）させる PR を出す。

優先度は低い（Phase 6 以降に本格稼働）。Phase 1-3 では Writer が `code-verified` を直接付与した分のみが裏取り済みとなる。

## 入力

- 対象ページの `frontmatter.sources`
- ページ内の `<!-- evidence: ... -->` コメント

## 手順

1. 各 `sources[]` の `repo + path + ref` を `.cache/sonic-sources/` でチェックアウトして実体を確認
2. 本文中の主張と実コード/HLD/issue の間に齟齬がないかチェック
3. 結果に応じて以下のいずれか:
   - 完全に一致: `verification: code-verified`、`last_verified` を更新
   - 齟齬あり: `verification: discrepancy-found`、本文に注記、必要なら別 issue を起票

## 出力

- ブランチ名: `verify/<area>/<slug>`
- PR タイトル: `[verify] <ページタイトル>`
- PR 本文に確認手順・確認したコード位置を明示

## 注意

- Verifier は **本文を大きく書き換えない**。あくまで裏取りステータスの昇格と注記のみ
- 大幅な書き直しが必要なら、新しい issue を立てて Writer に戻す
