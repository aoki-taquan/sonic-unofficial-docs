# Verifier プロンプト

## 目的

merge 済みのページについて、実コードを読んで裏取りを行い、`verification` ステータスを昇格（あるいは `discrepancy-found` へ降格）させる PR を出す。

優先度は低い（Phase 6 以降に本格稼働）。Phase 1-3 では Writer が `code-verified` を直接付与した分のみが裏取り済みとなる。

## 入力

- `meta/queue/*.json` の per-page エントリ（priority 順に処理する。`high` → `medium` → `low`）
- 対象ページの `frontmatter.sources`
- ページ内の `<!-- evidence: ... -->` コメント

> **キューの真実は per-page ファイル**。`meta/verification-queue.json` は `meta/queue/*.json` の集約ビューであり、Verifier が直接編集してはならない。エントリの更新は対応する `meta/queue/<area>-<slug>.json` に対して行い、`.venv/bin/python3 meta/scripts/aggregate_queue.py` で集約ビューを再生成する。

## 手順

1. `meta/queue/*.json` を priority 順に列挙し、未処理（`verification` が `hld-only` / `issue-confirmed`）のものから取り掛かる
2. 各 `sources[]` の `repo + path + ref` を `.cache/sonic-sources/` でチェックアウトして実体を確認
3. 本文中の主張と実コード/HLD/issue の間に齟齬がないかチェック
4. 結果に応じて以下のいずれか:
   - 完全に一致: ページ frontmatter の `verification: code-verified`、`last_verified` を更新。対応する `meta/queue/<area>-<slug>.json` を **削除**（裏取り済みのため）するか、`verified_concerns` に確認済み懸念を移して `concerns` を空にする
   - 齟齬あり: `verification: discrepancy-found`、本文に注記、必要なら別 issue を起票。per-page ファイルの `concerns` を更新
5. `.venv/bin/python3 meta/scripts/aggregate_queue.py` を実行して集約ビューを再生成し、PR に含める

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
3. **commit する前に必ず `git pull --ff-only origin main`**。`meta/verification-queue.json` は集約ビューなので、競合した場合は `meta/queue/*.json` を main 側に合わせ直してから `aggregate_queue.py` で再生成する
4. **PR 作成前に再度 main を pull**。PR が「親 commit がもう main にない」状態で立たないよう注意
5. もし `gh pr merge --squash` で他人の PR と同梱されてしまったら、それは GitHub 側の挙動として受け入れる（main には反映されている）

## worktree 動作ルール（isolation: worktree で動いている場合）

writer.md と同じ。**`cd /home/coder/sonic-unofficial-docs` 禁止**、起動直後に `WT=$(pwd)` を控えて以降は `git -C "$WT"` か `cd "$WT"` で自 worktree を対象にする。
