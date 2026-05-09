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

## 並走時の運用ルール（Writer バッチと同時に動く場合）

Writer バッチが並走している場合、Bash の作業ディレクトリと branch 状態が共有される。次の規約を守ること:

1. **branch 切替・編集・build・commit を 1 つの Bash 呼び出しにまとめる**。`set -e` を入れて `git branch --show-current` で現在地を都度確認する。複数 Bash 呼び出しに分けると Writer 側の `checkout` で奪われる
2. **`git add -A` を使わない**。常に `git add <specific paths>` で対象ファイルを限定する。Writer の untracked / modified ファイルを誤って巻き込まない
3. **commit する前に必ず `git pull --ff-only origin main`**。`meta/verification-queue.json` は Writer も更新するので衝突しやすい
4. **PR 作成前に再度 main を pull**。PR が「親 commit がもう main にない」状態で立たないよう注意
5. もし `gh pr merge --squash` で他人の PR と同梱されてしまったら、それは GitHub 側の挙動として受け入れる（main には反映されている）
