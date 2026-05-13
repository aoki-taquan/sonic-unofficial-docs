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
   - 食い違いを発見した場合: `discrepancy-found` + 本文に注記 + `monitor:` タグ必須
     - `not_implemented`: HLD は提案だが master に対応コードが一切無い（grep で 0 件）
     - `evolved_beyond_hld`: 実装は存在するが、テーブル名・引数・変数名・クラス名・経路が HLD と異なる
     - `partially_implemented`: HLD のうち一部のみ取り込み、残りは未実装
     - `deprecated`: 本 HLD の方針は採用されず、後発の別機能（後継 HLD / FRR 機能等）に置き換えられた
     - 判定優先度: `deprecated` > `not_implemented` > `partially_implemented` > `evolved_beyond_hld`。詳細は `meta/templates/SCHEMA.md` の "monitor の意味" 節を参照
5. 関連する CONFIG_DB テーブル / CLI コマンド / YANG モジュールを `related.*` に列挙
   - **opt-out マーカー 4 種** (`_no_related` / `_no_related_yang` / `_no_related_cli` / `_no_related_config_db`) を `related:` 配下に置くと該当 lint が抑止される。**設計として埋まる余地が無いページに限定**して使うこと（Reference index / glossary / 404 / SAI 内部レイヤなど）。詳細は `meta/templates/SCHEMA.md` の「related の opt-out マーカー」節を参照
6. 図は **mermaid**。スクリーンショット・PNG は使わない
   - HLD 側に PNG 参照（例: `images/foo.png`）が含まれる場合、画像をそのままコピー・参照しない。図の意味を読み取り **mermaid（フローチャート / シーケンス / 状態遷移）で再描画**する
   - mermaid 化が冗長になる場合（テキストと表だけで十分な場合）は無理に図を作らない。**読み手の理解に貢献する場合のみ**作図する
   - **mermaid 構文ルール**（`meta/scripts/check_mermaid_syntax.py` で機械検査）:
     - flowchart のラベル `[label]` 内に裸の `(`, `)`, `|`, `/`, `<`, `>`, `&` を入れない（必要なら `["label (note)"]` のように quote する）
     - `subgraph TITLE` の TITLE に特殊文字を含めない
     - 方向指定は `LR` / `RL` / `TB` / `TD` / `BT` のみ。typo すると build が落ちる
     - 自動修正は `meta/scripts/fix_mermaid_syntax.py` で可能（ただし最終的に PR には人の目で確認した結果のみ含める）
7. 文体はである調・敬体禁止。専門用語は原語のまま（必要なら括弧で日本語訳）
8. **タイトル二段運用**: frontmatter の `title` は日本語で短く意味重視（例: 「BGP unnumbered ピアリング」）。一方ファイル slug は backlog 由来で英語のままで良い（例: `bgp-unnumbered.md`）。両者は無理に揃えなくて良い
   - **slug が backlog 由来で意味不明・冗長な場合（例: `smart-switch-gnmi-feedback-design-omit-in-toc`）、`title` は Writer が自由にリネームしてよい**

## 必須 H2 セクション（lint で機械検査）

ページ種別に応じて以下の H2 が必須。`mkdocs build --strict` の前に該当 lint を走らせて確認すること。

### HLD 系（`docs/<area>/*.md` の area が `routing` / `switching` / `overlay` / `acl-qos` / `system` / `management` / `platform` / `architecture`、100 行以上、`verification` が `code-verified` または `discrepancy-found`）

- `## 制限事項` （または `## Limitations` / `## 制限` / `## 既知の制限`）
  - 検査: `meta/scripts/check_limitations_section.py --check`
- `## 確認コマンド` （または `## トラブルシュート` / `## トラブルシューティング` / `## Troubleshooting` / `## 動作確認`）
  - セクション本文に **3 行以上の非空行 + 1 個以上のコードブロック** を含むこと（内容充実度）
  - 検査: `meta/scripts/check_troubleshoot_section.py --check`

### Runbook 系（`docs/reference/runbooks/*.md`、`verification: runbook-verified`）

以下 **5 節** がすべて必須:

1. `## 症状`
2. `## 切り分け` / `## 切り分けフロー` / `## 切り分け手順` のいずれか
3. `## 確認コマンド` / `## コマンド` / `## 確認` のいずれか（または切り分け節配下に bash 系コードブロックが 1 つ以上）
4. `## よくある原因` / `## 原因` / `## 想定原因` / `## 想定原因（優先度順）` のいずれか
5. `## 関連` / `## 関連ページ` / `## 関連 reference` / `## 関連 reference / topics` のいずれか

検査: `meta/scripts/check_runbook_structure.py --check`

### `discrepancy-found` 系の追加要件

- `monitor: evolved_beyond_hld` のページは **`!!! diff "HLD と実装の差分"` admonition** で「実装との乖離」セクションを包む（`meta/scripts/inject_diff_admonition.py` で自動 wrap 可能）。または `## 制限事項` で差分を扱う。検査: `meta/scripts/check_evolved_6c.py`
- `monitor: partially_implemented` のページは本文に「実装済 / 未実装 境界明示」が必要（推奨形はフェーズ別境界表 `| Phase | 実装済 | 未実装 |`）。検査: `meta/scripts/check_partial_boundary.py`
- `monitor: not_implemented` は「未実装である旨の明示」+「代替手段の有無の明示」が前提条件。詳細は `meta/quality-audit-guide.md` §5.4
- `monitor: deprecated` は代替機能への内部リンクが本文必須

## last_verified の更新ポリシー

- 新規 Writer: ページを書いた **当日** の日付（`YYYY-MM-DD`）
- 更新（既存ページの追記・修正）: 編集を行った **当日** の日付に更新
- Verifier の昇格 PR では Verifier が当日に更新する（Writer は触らない）
- 90 日以上経過した `last_verified` は `meta/scripts/check_stale_verified.py` で informational に検出される（Verifier の再裏取りトリガ）

## PR 本文に書くこと

PR 本文には次を必ず含める（Reviewer の機械チェック対象）:
- `Closes #<issue番号>`
- 対応する backlog ファイルパス（例: `meta/backlog/<area>/<slug>.json`）
- 参照した一次情報のリスト（commit SHA 込み）
- 自分で気付いた懸念点（HLD と実装の差分の可能性 等）

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

## worktree 動作ルール（isolation: worktree で動いている場合）

worktree モードのサブエージェントは独立した working tree で動くが、**`cd /home/coder/sonic-unofficial-docs` を実行すると main worktree 側に飛んでしまい、`git checkout -b` 等が main 側で動いて事故になる**。次を厳守:

1. 起動直後に `WT=$(pwd); echo "$WT"` で自分の worktree path を控える
2. 以降の git / mkdocs 操作は **絶対パス + `git -C "$WT"`** または `cd "$WT"` で自 worktree を確実に対象にする
3. `cd /home/coder/sonic-unofficial-docs` は禁止（main worktree を奪う）
4. `mkdocs build --strict` も `cd "$WT" && ./.venv/bin/mkdocs build --strict` で実行
5. もし誤って main に commit してしまった場合は revert せず（コンテンツが妥当ならそのまま）、PR で正規化する

## 裏取りキューへの登録

Writer が `verification: hld-only` 等で残した懸念点（HLD と実装の差分の可能性、要件レベル止まりで実装未確認、CONFIG_DB が未定義 等）は、PR 本文に書くだけでなく **`meta/queue/<area>-<slug>.json`** に新規ファイルを作成して登録する。Verifier が優先度順に拾えるようにするため。

> **編集レース回避のため per-page ファイル方式を採用**。`meta/verification-queue.json` は `meta/queue/*.json` の集約ビューであり、Writer が直接編集してはならない。集約ビューは `.venv/bin/python3 meta/scripts/aggregate_queue.py` で再生成する（PR に含めて良い）。

ファイル名規則:

- `<area>` = `docs/<area>/<slug>.md` の area 部分（例: `routing`）
- `<slug>` = `.md` を除いた basename。slug にスラッシュが含まれる場合は `-` に置換
- 例: `docs/routing/default-route.md` → `meta/queue/routing-default-route.json`

1 ファイル 1 entry。エントリ形式:

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

**`pr` フィールドは Writer 段階では未確定で良い**（PR 作成前にエントリを書くため）。PR 番号が決まり次第、Reviewer または Merger 段階で同じエントリの `pr` を後埋めする（per-page ファイルを編集 → `aggregate_queue.py` を再実行）。
