---
title: 品質監査ガイド（quality-audit-N シリーズ運用ルール）
area: meta
verification: meta
last_verified: 2026-05-11
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

## 4. 関連ドキュメント

- `meta/templates/SCHEMA.md`: frontmatter スキーマ全体および `page_kind` / `monitor` の定義
- `meta/prompts/reviewer.md`: Reviewer ロールの自動チェック
- `docs/reference/verification/discrepancy-index.md`: `discrepancy-found` ページの自動生成一覧（軸 6 読み替えの注記あり）
- `meta/scripts/gen_discrepancy_index.py`: 上記一覧の生成スクリプト
