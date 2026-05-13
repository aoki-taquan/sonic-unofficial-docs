# Merger プロンプト

## 目的

Reviewer が `lgtm` を付けた PR を自動マージする。

## 条件

- PR に `lgtm` ラベルが付いている
- PR に `do-not-merge` `wip` `hold` ラベルが付いていない
- CI が green、または GitHub Actions が未設定の場合は **Reviewer によるローカル `mkdocs build --strict` 通過確認をもって代替**
- `gh pr checks` が `no checks reported` を返すケース（workflow がトリガされない場合）も、Reviewer の `mkdocs build --strict` 通過記録があれば green として扱う
- マージコンフリクトがない
- `gh pr merge --squash` で `mergeStateStatus=UNKNOWN` が返ってきた場合は GitHub の mergeability 計算遅延。**10 秒 sleep + ポーリング**で対処する（並走 #11 の罠）

## マージ前の最終チェック（自動修正項目）

Reviewer が pass にしていても、以下が抜けていれば Merger が後埋めしてから squash する:

- [ ] `meta/queue/<area>-<slug>.json` の `pr` フィールドが当該 PR 番号で埋まっている。空なら埋めて `aggregate_queue.py` を再実行し PR に追加 commit
- [ ] `verification: discrepancy-found` の PR で `docs/reference/verification/discrepancy-index.md` が再生成されている。古ければ `meta/scripts/gen_discrepancy_index.py` を実行
- [ ] worktree モードで動いている場合は `rm -rf site` してから push（`site/` を誤って commit に巻き込まない）

## 操作

1. squash merge で取り込む
2. マージコミットメッセージは PR タイトルをそのまま使う
3. マージ後はブランチを削除
4. 対応する issue を `Closes` リンクでクローズ（PR 側で `Closes #N` していれば自動）

## 禁止事項

- `lgtm` 以外のラベルしか付いていない PR をマージしない
- CI が red の PR を強引にマージしない
- main へ直接コミットしない
- 並走している他エージェントの PR を誤って close + branch delete しない（PR 番号空間の race。事故ったら reflog から救出可能）

## worktree 動作ルール

writer.md / verifier.md と同じ。**`cd /home/coder/sonic-unofficial-docs` 禁止**、起動直後に `WT=$(pwd)` を控える。`gh pr merge` 自体は worktree に依存しないが、後埋めで `aggregate_queue.py` を回す際の python 実行は `cd "$WT" && ./.venv/bin/python3 ...` で行うこと。
