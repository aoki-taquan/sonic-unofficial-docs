---
title: 品質監査ガイド（quality-audit-N シリーズ運用ルール）
area: meta
verification: meta
last_verified: 2026-05-12
sources: []
---

# 品質監査ガイド（quality-audit-N シリーズ運用ルール）

`meta/quality-audit-1.md` 〜 `meta/quality-audit-NN.md` の **6 軸 5 点満点サンプリング監査** を継続実施するための運用ルールをここに集約する。新規 round を起票する監査ロールは本ドキュメントを参照し、各軸の評価基準のブレを最小化すること。

## 0. 評価軸（6 軸 5 点満点）

| # | 軸 | 通常ページの基準（要旨） |
|---|----|--------------------------|
| 1 | 構成 | 見出し階層 / セクション分割 / 導入 → 詳細 → 引用元の流れ |
| 2 | 裏取り | code-verified 度合い / evidence コメントの密度 / SHA 固定 |
| 3 | 引用 | frontmatter `sources[]` / 本文脚注 / 「引用元」セクションの整備 |
| 4 | 関連性 | `related.config_db` / `related.cli` / `related.yang` の網羅性と妥当性 |
| 5 | 可読性 | 用語統一 / glossary 整合 / 図表の有効性 / 1 ページの分量バランス |
| 6 | 完結性 | 機能の網羅性 / ops-hint / troubleshooting / 読み手が次に取れる行動 |

## 1. ページ種別による軸の読み替え

通常ページに対して上記基準をそのまま適用すると、特定ページ種別が構造的に低評価へ張り付く問題があり、これまでの round で実害が観測されている。本プロジェクトでは以下の読み替えを **formal なルール** として採用する。

### 1.1 `page_kind: chapter-index`（章扉）

22 章の扉ページ (`docs/topics/NN-slug/index.md`)。配下ページへのリンク集が本体。

- **N/A 化する軸**: 軸 2 (裏取り) / 軸 6 (完結性)
- **維持する軸**: 軸 1 / 3 / 4 / 5
- **理由**: 章扉は個別主張を持たないため evidence は不要、また「機能としての完結」も求めない
- 集計時は N/A 軸を除いた平均で 5 点換算する

詳細は `meta/templates/SCHEMA.md` の `page_kind` セクションを参照。

### 1.2 `verification: discrepancy-found` ページ

HLD と実装に差分があるページ。

- **読み替える軸**: 軸 6 (完結性) → **「乖離説明の構造的整理が出来ているか」**
- 他の軸 (1〜5) は通常ページと同じ基準
- 評価サブ項目は `meta/templates/SCHEMA.md` の「`discrepancy-found` ページの軸 6 評価基準」セクションを参照（monitor タグ妥当性 / 「実装との乖離」セクションの構造化 / 裏取り evidence / 読み手への next-action の 4 サブ項目）
- **理由**: 実装が未着手 / 進化済み / 廃止済みのため「機能としての完結」を本文で書きようがなく、通常基準では構造的に 4 点天井になる。代わりに「読み手に乖離を有益な形で渡せているか」で評価する

### 1.3 `verification: stub` / `meta` ページ

監査対象外（サンプリングで引いた場合は再抽選または N/A 評価）。

## 2. `discrepancy-found` 監査時のチェックリスト

新規 round で `discrepancy-found` ページをサンプリングに引いた場合、軸 6 評価は以下のチェックリストで行う:

- [ ] frontmatter `monitor:` が 4 値 (`not_implemented` / `evolved_beyond_hld` / `partially_implemented` / `deprecated`) のいずれかで、本文の乖離パターンと整合している
- [ ] 「実装との乖離」「現行実装との乖離」「HLD と実装の乖離」見出しのセクションが存在し、HLD 側の主張 / 現行 master の状態 / 差分のインパクトの 3 点が読み分けられる
- [ ] 「実装が存在しない」「別名で実装されている」等の判定根拠が evidence コメント（`source:` / `excerpt:` / `reasoning:`）で埋め込まれている
- [ ] 読み手が現行 master でこの HLD をどう取り扱うべきかの next-action が明示されている

4 項目すべて満たすと軸 6 = 5 点。1 つ欠けると 4 点、2 つ欠けると 3 点、それ以下も同様に下げる。

## 3. round 集計時の表記

quality-audit-N.md の冒頭サマリには、本ガイドの読み替えを適用したことを明記する。例:

> `verification: discrepancy-found` ページの軸 6 は `meta/quality-audit-guide.md` および `meta/templates/SCHEMA.md` の規定に従い「乖離説明の整理度」で評価した。

過去 round（round 17 以前）は通常基準で評価されており、`discrepancy-found` ページが軸 6 = 4 点で天井に当たっていた。round 18 以降は本ガイドの読み替えを適用する。

## 3.1. サンプリング戦略（奇偶交互運用、round 28 で確立）

round 28 以降、サンプリング方式を round 番号のパリティで機械的に決定する:

| パリティ | サンプリング | 目的 |
|---------|------------|------|
| **奇数 round** | **random 12**（`find docs -name '*.md' \| shuf -n 12`） | 母集団 unbiased estimator、構造的偏り検知 |
| **偶数 round** | **stratified 12**（cv 6 / rv 2 / df 2 / ci 1 / meta 1） | サブセット軸別平均の安定監視 |

stratified の比率は `quality-audit-27.md` §1 の抽出シェルを参照。stratified round では母集団重み補正後の期待値を生サンプル平均と並記し、続く random round の生サンプル平均との乖離を測ることで stratified scheme の mature 度を継続検証する（乖離 0.05 以下で mature）。

round 28 で round 27 (stratified, 4.941) と round 28 (random, 4.94) の乖離が 0.001 と確認され、stratified scheme は mature 判定済み。

## 4. サブ軸定義（軸 5 / 軸 6、round 35 から正式運用）

audit round 32 の改善提言を受け、軸 5 (可読性) と軸 6 (完結性) を 3 つのサブ軸に分割して評価する運用を round 33・round 34 で 2 round 試行し、stratified / random 両サブシリーズで母集団真値 4.97 → 4.98 帯域押し上げに寄与することを確認した。これを受け **round 35 以降は正式運用** とする。

### 4.0 運用ルール（formal）

以下を本プロジェクトの formal なルールとして固定する:

1. **サブ軸 5 点満点**: 各サブ軸 (5a / 5b / 5c / 6a / 6b / 6c) は通常軸と同様の 5 点満点で評価する（0.5 段刻み可、round 33 から導入の細評価を継続）
2. **軸スコア = サブ軸平均**: 軸 5 / 軸 6 のスコアは、適用可能なサブ軸の **単純平均** とする（小数第 2 位四捨五入）。サブ軸が全部 5 点なら軸スコアも 5.00、(5, 4, 5) なら 4.67
3. **N/A はサブ軸単位で適用可**: 単一サブ軸が当該ページに構造的に該当しない場合（例: 設定が存在しない overlay 概念ページの 6a、図表が不要な極短ページの 5c）は当該サブ軸を N/A とし、残りのサブ軸の平均で軸スコアを算出する。軸単位で全サブ軸が N/A になる場合のみ軸自体を N/A とする
4. **round 32 以前との互換**: round 32 以前の audit はサブ軸を持たない軸単位評価が引き続き有効。サブ軸方式は **前向き運用** とし、既存 audit ファイルは遡及修正しない
5. **新規 audit ファイル**: round 35 以降の `meta/quality-audit-N.md` は `meta/templates/quality-audit-page.md` を雛形とし、サブ軸内訳を必ず併記する

### 4.1 軸 5 (可読性) サブ軸

| サブ軸 | 名称 | 評価対象 |
|--------|------|---------|
| **5a** | 章立て / 流れ | 見出し階層の妥当性、導入 → 詳細 → 引用元の論理的順序、セクション分割の粒度、読み進めるリズム |
| **5b** | 日本語の自然さ | 用語統一（glossary 整合）、助詞・語尾のブレ、機械翻訳調の不自然さ、専門用語の和訳一貫性 |
| **5c** | mermaid / 表の有無と質 | 図表が必要な箇所への配置、mermaid のラベル明確さ、表ヘッダの妥当性、PNG 等スコープ外形式を使っていないこと |

### 4.2 軸 6 (完結性) サブ軸

| サブ軸 | 名称 | 評価対象 |
|--------|------|---------|
| **6a** | 設定例の有無 | CLI / config_db JSON / YANG payload など実際の設定スニペットが提示されているか、最小例と典型例の網羅 |
| **6b** | 制限事項の有無 | 既知の制限・スケール上限・未サポート機能・前提条件（プラットフォーム依存等）の明示 |
| **6c** | トラブルシュート / 確認コマンドの有無 | `show` 系コマンド、ログ確認ポイント、debug の足がかり、典型エラーと対処の整理 |

### 4.3 集計表記

サブ軸を適用した round (round 33 以降) では、各ページの評価表に軸スコアと並んで `(5a/5b/5c)` `(6a/6b/6c)` の内訳を必ず併記する。例:

> 軸 5: 4.67 (5a=5, 5b=4, 5c=5) / 軸 6: 4.00 (6a=5, 6b=3, 6c=4)

N/A を含む場合の例:

> 軸 5: 4.50 (5a=5, 5b=4, 5c=N/A) / 軸 6: 4.50 (6a=5, 6b=4, 6c=N/A)

`page_kind: chapter-index` の軸 6 は引き続き軸単位で N/A とし、サブ軸も評価しない。`verification: discrepancy-found` ページの軸 6 は §1.2 / §2 の「乖離説明の整理度」基準を優先し、サブ軸 6a-6c は副次情報として併記のみ可（軸スコアの算出には用いない）。

### 4.4 テンプレ

新規 round の audit ファイルは `meta/templates/quality-audit-page.md` を雛形として使用する。サブ軸 5a-c / 6a-c の評価表セクションが定義済み。

## 5. 関連ドキュメント

- `meta/templates/SCHEMA.md`: frontmatter スキーマ全体および `page_kind` / `monitor` の定義
- `meta/prompts/reviewer.md`: Reviewer ロールの自動チェック
- `docs/reference/verification/discrepancy-index.md`: `discrepancy-found` ページの自動生成一覧（軸 6 読み替えの注記あり）
- `meta/scripts/gen_discrepancy_index.py`: 上記一覧の生成スクリプト
