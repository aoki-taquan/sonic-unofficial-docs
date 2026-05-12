---
title: 品質改善サンプリング監査（round N、<奇数 = random / 偶数 = stratified>）
area: meta
verification: meta
last_verified: YYYY-MM-DD
sources: []
---

<!--
このファイルは `meta/quality-audit-N.md` を新規起票するときの雛形です。
新規 round では本ファイルを `meta/quality-audit-<N>.md` にコピーし、
`<...>` 部分を埋めて使ってください。

運用ルールは `meta/quality-audit-guide.md` を参照。
特に §4 (サブ軸 5a-c / 6a-c) は round 35 以降 formal です。
-->

# 品質改善サンプリング監査（round N、<奇数 = random / 偶数 = stratified>）

- 実施日: YYYY-MM-DD
- 対象: round <N-1> 後の現行 main（iteration <X> / 当 round で観測したい改善トピックを箇条書き）
- サンプル数: **12 件**（<random / stratified> サンプリング）
- 評価軸: **6 軸 5 点満点** + **サブ軸 5a / 5b / 5c / 6a / 6b / 6c**（`meta/quality-audit-guide.md` §4 準拠 / 0.5 段刻み）
- 評価者: AI（Claude / batch #<n>、worktree 隔離、`chore/qNN-<tag>-auditNN` ブランチ）

## 0. round N の位置付け

<奇偶交互運用の周回数、前 round からの観測ポイント、本 round の比較対象を 3-5 点記載>

### 母集団分布の最新値（YYYY-MM-DD 時点）

| verification | 件数 | 全体比 | 層化比率（今 round） |
|--------------|------|--------|---------------------|
| code-verified | ~NNN | NN.N% | <random/stratifiedで埋める> |
| meta | ~NNN | NN.N% | ... |
| discrepancy-found | NN | N.N% | ... |
| runbook-verified | NN | N.N% | ... |
| stub / section-index | N | N.N% | 0 |
| hld-only | 0 | 0.0% | 0 |

## 1. サンプル一覧

stratified の場合は `find docs -name '*.md' | shuf -n N` を verification 別に区切って実施。random の場合は全体から `shuf -n 12`。

| # | path | verification | page_kind | サンプリング根拠 |
|---|------|--------------|-----------|----------------|
| 1 | docs/.../foo.md | code-verified | reference | random / stratified-cv |
| ... |

## 2. 評価詳細（サブ軸内訳付き）

各ページについて、軸 1-6 のスコアと軸 5 / 軸 6 のサブ軸内訳 (5a/5b/5c, 6a/6b/6c) を併記する。
N/A サブ軸がある場合は内訳に `N/A` と書き、軸スコアは残りのサブ軸平均で算出する。

### 2.1 page1

- path: `docs/.../foo.md`
- verification: code-verified
- 軸 1 (構成): 5.0
- 軸 2 (裏取り): 5.0
- 軸 3 (引用): 5.0
- 軸 4 (関連性): 5.0
- **軸 5 (可読性): 4.67** (5a=5, 5b=4, 5c=5)
- **軸 6 (完結性): 4.33** (6a=5, 6b=4, 6c=4)
- ページ平均: 4.83
- コメント: <軸ごとの減点理由 / 良い点 / next-action 候補>

<!-- evidence:
source: <repo>/<path>#Lx-Ly (sha: <commit>)
excerpt: |
  <該当箇所の抜粋>
reasoning: <この評価が妥当な理由>
-->

### 2.2 page2

<以下同様にサンプル数だけ繰り返す>

## 3. スコア集計

| # | path | 軸1 | 軸2 | 軸3 | 軸4 | 軸5 (5a/5b/5c) | 軸6 (6a/6b/6c) | ページ平均 |
|---|------|-----|-----|-----|-----|----------------|----------------|------------|
| 1 | ... | 5.0 | 5.0 | 5.0 | 5.0 | 4.67 (5/4/5) | 4.33 (5/4/4) | 4.83 |
| ... |

- **round N 平均**: X.XXX
- **前 round (N-1) 平均**: X.XXX
- 差分: ±0.XXX
- stratified ↔ random 乖離 (mature 判定の継続検証): 0.XXX

## 4. 観測 / 改善提言

### 改善 1: <タイトル>

- 観測: <事実>
- 提言: <具体的アクション>
- 想定影響軸: 軸 N (Na / Nb)
- 推定工数: small / medium / large

### 改善 2: <タイトル>

<同様>

### 改善 3: <タイトル>

<同様>

## 5. 次 round (N+1) への申し送り

- サンプリング方式: <random / stratified>（奇偶交互運用 X 周目 <奇数/偶数>）
- 着目点: <次 round で観測したい変化>
- 改善着手予定: 改善 N（このコメントを次 round の §0 で参照する）

## 6. 関連ドキュメント

- `meta/quality-audit-guide.md`: 評価軸・サブ軸の formal ルール
- `meta/quality-audit-<N-1>.md`: 前 round
- `meta/templates/SCHEMA.md`: page_kind / verification / monitor の定義
