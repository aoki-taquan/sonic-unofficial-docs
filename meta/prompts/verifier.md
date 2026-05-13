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
   - **`discrepancy-found` を付ける場合は frontmatter に `monitor:` タグを必ず追加する**（`not_implemented` / `evolved_beyond_hld` / `partially_implemented` / `deprecated` のいずれか、SCHEMA.md 参照）。判定優先度は `deprecated` > `not_implemented` > `partially_implemented` > `evolved_beyond_hld`
   - **`monitor` の subtype 別評価基準** は [`meta/quality-audit-guide.md` §5](../quality-audit-guide.md#5-discrepancy-found-subtype-別評価基準) に従う。とくに次の機械検査が PR 通過の前提:
     - `partially_implemented`: 本文に「実装済 / 未実装 境界明示」（推奨形はフェーズ別境界表 `| Phase | 実装済 | 未実装 |`）が必要 → `meta/scripts/check_partial_boundary.py`
     - `evolved_beyond_hld`: 「実装との乖離」セクションが `!!! diff "HLD と実装の差分"` admonition で包まれていること（自動化: `meta/scripts/inject_diff_admonition.py`）、または `## 制限事項` + `!!! diff` で差分を扱うこと → `meta/scripts/check_evolved_6c.py`
     - `not_implemented`: 「未実装である旨の明示」+「代替手段の有無の明示」の 2 点が本文に含まれること（§5.4 確定ルール）
     - `deprecated`: 代替機能への内部リンクが本文必須
5. **`last_verified` を当日の日付に更新する**。状態に変化なし（再裏取りで同じ結論）の場合でも `last_verified` だけは必ず更新する。`sources[].ref` も最新の master HEAD SHA に取り直す
6. `.venv/bin/python3 meta/scripts/aggregate_queue.py` を実行して集約ビューを再生成し、PR に含める
7. 以下の lint を順に走らせて pass を確認する:
   - `.venv/bin/python3 meta/scripts/frontmatter_lint.py`（enum 違反 / opt-out マーカーの誤用）
   - `.venv/bin/python3 meta/scripts/check_mermaid_syntax.py --check`（mermaid 構文）
   - 該当する場合: `check_partial_boundary.py` / `check_evolved_6c.py` / `check_limitations_section.py` / `check_troubleshoot_section.py` / `check_runbook_structure.py`
   - `cd "$WT" && ./.venv/bin/mkdocs build --strict`

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

## 定期見直し（discrepancy-found ページの再裏取り）

`verification: discrepancy-found` のページは「動的なメタデータ」として継続メンテナンスが必要。Verifier は新規裏取りに加えて、以下の再裏取りトリガを担う。詳細手順は [`meta/discrepancy-operations.md`](../discrepancy-operations.md) を参照。

### 再裏取りトリガ

| トリガ | 対象ページ | 頻度 |
|--------|-----------|------|
| 四半期サイクル | `monitor` が `not_implemented` / `partially_implemented` / `evolved_beyond_hld` のページ全件 | quarterly |
| 半年サイクル | `monitor: deprecated` のページ | biannual |
| `last_verified` から 90 日以上経過 | 該当ページ全件 | 検知次第 |
| 該当 HLD に紐づく新規 PR / issue を観測 | 該当ページ | 都度 |

### 再裏取りのアクション分岐

1. **HLD と実装が一致するようになっていた**: `discrepancy-found` → `code-verified` に昇格（monitor フィールドを削除、`sources[].ref` を最新 SHA に更新、本文の差分セクションを「一致確認」に書き換え）。詳細は `meta/discrepancy-operations.md` 第 3 節
2. **monitor 区分が変わった**: 例えば `not_implemented` だった機能の一部が取り込まれた場合は `partially_implemented` に変更。判定フローは `meta/discrepancy-operations.md` 第 2 節の mermaid を参照
3. **状態に変化なし**: `last_verified` だけ更新し、`sources[].ref` も最新化（HEAD を取り直して同一結論が得られたことを確認）
4. **後発別機能で置換された**: `monitor: deprecated` に切り替え、本文先頭に置換先リンクを追記

### per-page queue 投入

再裏取り対象は per-page queue に `meta/queue/verification-recheck/<area>-<slug>.json` 形式で投入する（または既存の `meta/queue/<area>-<slug>.json` を `priority: low` で復活させる）。集約は `aggregate_queue.py` で。

### discrepancy-index 再生成

再裏取り後は `meta/scripts/gen_discrepancy_index.py` を走らせて `docs/reference/verification/discrepancy-index.md` を更新する（昇格したページは消え、新規に discrepancy 判定されたページは追加される）。
