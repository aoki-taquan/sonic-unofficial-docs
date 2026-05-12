---
title: 品質改善サンプリング監査（round 47 discrepancy-found 指名 mini、軸 6 = guide §5 / §5.4 適用、round 20 比較）
area: meta
verification: meta
last_verified: 2026-05-12
sources: []
---

# 品質改善サンプリング監査（round 47 discrepancy-found 指名 mini）

- 実施日: 2026-05-12
- 対象: round 45 (random 4.993) / round 46（仮置き）後の現行 main（iteration AS / df 母集団 74 件、`not_implemented` 5 / `partially_implemented` 41 / `evolved_beyond_hld` 28 / `deprecated` 数件 想定）
- サンプル数: **8 件**（**`verification: discrepancy-found` 指名 sampling**、`grep -rlE "^verification: discrepancy-found$" docs/ | shuf -n 8 --random-source=<(yes 47df)`、再現可能 seed）
- 評価軸: ユーザー指示の **6 軸 5 点満点**（構成 / 裏取り / 引用 / 関連性 / 可読性 / 完結性）
- 軸 6: **`meta/quality-audit-guide.md` §1.2 / §5（df subtype 別評価）/ §5.4（`not_implemented` 確定ルール）を適用**
- 評価者: AI（Claude / batch #6、worktree 隔離、`chore/q49-aw-audit47-disc-mini` ブランチ）

## 0. round 47 discrepancy mini の位置付け（**初の guide §5 / §5.4 適用 discrepancy 指名 round**）

round 20（2026-05-11）が **初の discrepancy-found 指名 round** として 12 件 / 平均 **4.67** を記録した。その時点では guide §1.2 の「軸 6 = 乖離説明の整理度」の 4 サブ項目チェックリストのみが運用され、`not_implemented` ページに対しては「next-action 明示」が事実上必須化されていたため、**軸 6 平均 = 3.82**（1 件のみ 5.00、残り 4 点以下）で構造的に天井がかかっていた。

その後 round 35-44 でサブ軸 6a/6b/6c 正式運用 + df subtype 別評価ガイド §5 を整備し、特に round 45 直前の commit `8081c74f8`（"Finalize audit guide §5.4 not_implemented rule and add snapshot reference"）で **§5.4 確定ルール**（`not_implemented` は軸 6 サブ軸を全て N/A 化し、未実装明示 + 代替手段言及の 2 前提条件を満たせば一律 **5.00**、欠落で −0.5 → 4.50）が finalize された。

本 round 47 は **§5.4 finalize 後初の discrepancy 指名 mini audit** にあたり、以下の 3 点を検証する:

1. round 20 (4.67) → round 47 (本 round) の **改善幅**。特に **軸 6 平均**が §5.4 finalized による底上げと、round 21〜46 の累積改善（next-action 明示 batch / partial 境界 strict 化 / evolved 差分テンプレ / `_no_related_*` opt-out）でどれだけ伸びたか
2. df subtype 別の品質差。`not_implemented` (guide §5.4) / `partially_implemented` (guide §5.2、6b 境界明示必須) / `evolved_beyond_hld` (guide §5.3、6b 旧 → 新差分必須) / `deprecated` (guide §5.4a、代替リンクのみ評価) の 4 subtype が混在抽出
3. 軸 4（関連性）の改善。round 20 で `4.36`（discrepancy 固有減点）だったものが、round 21 以降の related-discovery 投入 / opt-out seed 整備でどこまで回復したか

## 1. サンプル一覧（discrepancy-found 指名 8 件）

抽出コマンド: `grep -rlE "^verification: discrepancy-found$" docs/ | sort | shuf -n 8 --random-source=<(yes 47df)`

| # | パス | area | monitor (subtype) | 行数 | related (cdb/cli/yang) |
|---|------|------|-------------------|------|------------------------|
| 1 | `docs/routing/bgp-route-install-error-handling.md` | routing | **deprecated** | 248 | 7 / 7 / 7 |
| 2 | `docs/routing/local-ars-hld.md` | routing | **not_implemented** | 174 | 3 / 2 / 1 |
| 3 | `docs/management/gnsi-hld-limitations.md` | management | **partially_implemented** | 106 | 2 / 0 / 4 |
| 4 | `docs/architecture/build-profiles.md` | architecture | **not_implemented** | 306 | 0 / 0 / 0 |
| 5 | `docs/architecture/error-handling-framework-in-sonic-concepts.md` | architecture (split-child) | **partially_implemented** | 138 | 7 / 3 / 7 |
| 6 | `docs/architecture/sflow-high-level-design.md` | architecture | **evolved_beyond_hld** | 292 | 3 / 2 / 1 |
| 7 | `docs/switching/link-event-damping-hld.md` | switching | **partially_implemented** | 342 | 2 / 1 / 1 |
| 8 | `docs/switching/switch-port-modes-and-vlan-cli-internals.md` | switching (split-child) | **partially_implemented** | 134 | 3 / 1 / 2 |

subtype 内訳: **partially_implemented 4 / not_implemented 2 / evolved_beyond_hld 1 / deprecated 1**。母集団 (41 / 5 / 28 / 数件) の比率に対し `partially_implemented` 比重 50% は母集団 55% とほぼ整合、`not_implemented` 25% は母集団 7% の上振れ（§5.4 直接観測の機会増）、`evolved_beyond_hld` 12.5% は母集団 38% の下振れ、`deprecated` 12.5% は母集団 1% の大幅上振れ（§5.4a 評価の貴重なサンプル）。round 20 の monitor 内訳（not_implemented 5 / evolved 4 / partial 2 / deprecated 0）と比べると **deprecated 1 件抽出**が本 round の特徴で、guide §5.4a を実運用 audit で初適用するチャンス。

#5 / #8 は split-hub の split-child だが `verification: discrepancy-found` を frontmatter 直書きしているため通常の df ページとして軸 6 を評価する（split-child でも df 指定があれば軸 6 を N/A 化せず df ルールで評価）。

## 2. 評価軸と適用ルール

| 軸 | 通常基準 | 本 round の適用 |
|----|---------|---------------|
| 1. 構成 | 章立て・流れ | 通常基準 |
| 2. 裏取り | sources / SHA pin / evidence コメント | 通常基準 |
| 3. 引用 | 脚注 / 「引用元」 / blob URL | 通常基準 |
| 4. 関連性 | `related.{config_db, cli, yang}` 網羅性 | 通常基準。HLD 提案段階で実装無し → related が本質的に空のケースは `_no_related_*` opt-out が無くても 4 点に留める（df 固有の構造減点を round 20 と同じ取り扱い） |
| 5. 可読性 | 日本語・mermaid・表 | 通常基準 |
| 6. 完結性 | **subtype 別** | **§1.2 + §5 (subtype 別) + §5.4 (not_implemented finalized)**: `not_implemented` は 6a/6b/6c を N/A 化、前提条件（未実装明示 + 代替言及）OK で 5.00、欠落で 4.50。`partially_implemented` は 6b に境界明示必須。`evolved_beyond_hld` は 6b に 旧 → 新差分必須。`deprecated` は代替リンクの有無のみ評価（リンクあり 5、リンクなし 2、廃止明示なし 1） |

## 3. 評価結果

| # | ページ | subtype | 構成 | 裏取り | 引用 | 関連性 | 可読性 | 軸 6 | 平均 |
|---|--------|---------|------|--------|------|--------|--------|------|------|
| 1 | bgp-route-install-error-handling | deprecated | 5 | 5 | 5 | 5 | 5 | **5** (deprecated: link-ok) | **5.00** |
| 2 | local-ars-hld | not_implemented | 5 | 5 | 5 | 4 | 5 | **5** (§5.4 OK、6a/b/c=N/A) | **4.83** |
| 3 | gnsi-hld-limitations | partially_implemented | 5 | 5 | 5 | 4 | 5 | **4** (6a=5, 6b=3, 6c=4) | **4.67** |
| 4 | build-profiles | not_implemented | 5 | 5 | 5 | 3 | 5 | **5** (§5.4 OK、6a/b/c=N/A) | **4.67** |
| 5 | error-handling-framework-in-sonic-concepts | partially_implemented (split-child) | 5 | 5 | 5 | 5 | 5 | **5** (6a=5, 6b=5, 6c=5) | **5.00** |
| 6 | sflow-high-level-design | evolved_beyond_hld | 5 | 5 | 5 | 4 | 5 | **4** (6a=5, 6b=3, 6c=4 — 旧 → 新差分が薄い) | **4.67** |
| 7 | link-event-damping-hld | partially_implemented | 5 | 5 | 5 | 4 | 5 | **5** (6a=5, 6b=5, 6c=5) | **4.83** |
| 8 | switch-port-modes-and-vlan-cli-internals | partially_implemented (split-child) | 5 | 5 | 5 | 4 | 5 | **5** (6a=5, 6b=5 「フェーズ別実装境界」明示, 6c=5) | **4.83** |

### 軸別平均

| 軸 | 平均 | round 20 比 |
|----|------|------------|
| 1. 構成 | **5.00** (8/8) | KEEP (5.00) |
| 2. 裏取り | **5.00** (8/8) | **+0.27** (4.73 → 5.00) — 全件で evidence コメント / SHA pin 完備、round 20 で 4 点だった `secure-boot` / `sag` / `console-switch` 系の構造欠落が累積改善で解消 |
| 3. 引用 | **5.00** (8/8) | KEEP (5.00) |
| 4. 関連性 | **4.13** (8/8) | **−0.23** (4.36 → 4.13) — df 固有減点は残存。`build-profiles` は HLD 提案段階で配下コード 0 のため related も 0 (3 点)、`local-ars-hld` / `gnsi-hld-limitations` / `sflow` / `link-event-damping-hld` / `switch-port-modes-internals` は yang/cli いずれかが空で 4 点 |
| 5. 可読性 | **5.00** (8/8) | KEEP (5.00) — round 20 から累積改善（description 自動追加 / mermaid 横展開 / glossary back-link）が完全反映 |
| 6. 完結性 (subtype 別) | **4.75** (8/8) | **+0.93** (3.82 → 4.75) — **大幅改善**。§5.4 finalized で `not_implemented` 2 件が一律 5.00 化（round 20 では next-action 9% の壁で 4 点が天井）、`partially_implemented` の境界明示 strict 化で 4 件中 3 件が 5.00 |
| **総平均** | **4.81** | **+0.14** (round 20 4.67 → round 47 4.81) |

### subtype 別平均

| subtype | 件数 | 軸 6 平均 | 総平均 | 備考 |
|---------|------|----------|--------|------|
| `not_implemented` | 2 | **5.00** | **4.75** | §5.4 finalized 効果で軸 6 満点固定。両ページとも「実コード grep 0」「代替手段リンク」明示。round 20 (`not_implemented` 軸 6 = 4.00) から **+1.00** |
| `partially_implemented` | 4 | **4.75** | **4.83** | 4 件中 3 件が 6b = 5（フェーズ表 / 境界明示）。`gnsi-hld-limitations` のみ 6b = 3（境界が散文で曖昧）。round 20 (`partial` 軸 6 = 3.50) から **+1.25** |
| `evolved_beyond_hld` | 1 | **4.00** | **4.67** | `sflow` で 6b = 3（HLD と現行実装の rename 表が無く、旧 → 新差分が散文の評論調）。round 20 (`evolved` 軸 6 = 3.75) から +0.25 |
| `deprecated` | 1 | **5.00** | **5.00** | 初の `deprecated` サンプル抽出。§5.4a 適用で「BGP Suppress FIB Pending への置換」リンクが冒頭で明示、link-ok 評価で軸 6 = 5。round 20 ではサンプル 0 件 → 比較不能 |

**観測**: `not_implemented` が **§5.4 finalized で軸 6 平均 3.82 → 5.00（+1.18）** という最大ジャンプ。round 20 で問題提起された「next-action 明示率 9% で構造的に 4 点天井」は、§5.4 で「軸 6 を N/A 化し前提条件のみ評価」と finalize したことで完全に解消。`partially_implemented` も round 22-44 の partial 境界 lint blocking 化 + フェーズ表 strict 化で 3.50 → 4.75（+1.25）と顕著。`evolved_beyond_hld` のみ 6b 旧 → 新 rename 表の構造化が追いついておらず、3.75 → 4.00 と改善幅が小さい（次回 round で集中対象）。

## 4. round 20（指名）vs round 47（指名）の比較

| 観点 | round 20 (2026-05-11) | round 47 (2026-05-12) | 差分 |
|------|---------------------|----------------------|------|
| サンプル数 | 12（うち meta 1 除外で 11） | 8 (mini) | −4 |
| df 母集団 | 49 件 | 74 件 | +25（df ページ追加生成）|
| 平均 (5 点) | **4.67** | **4.81** | **+0.14** |
| 軸 1 構成 | 5.00 | 5.00 | KEEP |
| 軸 2 裏取り | 4.73 | 5.00 | +0.27 |
| 軸 3 引用 | 5.00 | 5.00 | KEEP |
| 軸 4 関連性 | 4.36 | 4.13 | **−0.23**（df 固有減点が `build-profiles` 等で再露出）|
| 軸 5 可読性 | 5.00 | 5.00 | KEEP |
| 軸 6 完結性 (subtype 別) | **3.82** | **4.75** | **+0.93**（**最大改善幅**、§5.4 finalize 効果が支配的）|
| 軸 6 满点件数 | 1/11 (9%) | 6/8 (75%) | +66pt |
| 適用ガイド | §1.2 + §2 (4 サブ項目) | §1.2 + §5 + §5.4 + §5.4a | rule formalization |

### 改善幅の内訳

round 20 → round 47 で **+0.14** の改善幅のうち:

- **軸 6 +0.93**（subtype 別 8 セル × 重み 1/6） → 全体貢献 **+0.155**（最大）
- **軸 2 +0.27**（evidence + SHA pin の累積整備） → 全体貢献 **+0.045**
- **軸 4 −0.23**（df 固有減点が残存） → 全体貢献 **−0.038**
- 残差（軸 1/3/5 = ±0）+ サンプリング揺らぎ −0.024

軸 6 単独で +0.155 の押し上げ、これは round 20 で改善提言 1（next-action batch 注入）として最優先化された課題が **§5.4 finalize による「軸 6 N/A 化」という別解で解決された**ことを意味する。

## 5. 個別所感

### 満点（5.00）2 件

- **#1 bgp-route-install-error-handling (deprecated)**: 初の `deprecated` サンプル。§5.4a 「代替機能リンク」評価で 5 点。`ERROR_ROUTE_TABLE` 系の grep 0 件 verified + `BGP Suppress FIB Pending` への内部リンクが冒頭 monitor block で明示。related が 7/7/7 と完全充足しているのは後継機能のテーブル / CLI / YANG を全て紐付けたため
- **#5 error-handling-framework-in-sonic-concepts (partially_implemented split-child)**: split-hub の concepts 子ページとして `ERROR_DB` 設計と現行 syncd 差分を 5 章構成で整理。「実装フェーズ境界」「次アクション」セクションあり。related も 7/3/7 で充足、6b 境界明示も明快

### 高評価（4.83）3 件

- **#2 local-ars-hld (not_implemented)**: §5.4 直撃。`ArsOrch` 未実装 / `sonic-ars.yang` 不存在を grep 0 件 verified、open PR (sonic-swss #3597) link、代替（policy-based hashing / vendor sai.profile）明示。軸 4 のみ yang = 1 で 4 点
- **#7 link-event-damping-hld (partially_implemented)**: AIED アルゴリズムの数式 + COUNTERS DB + SAIREDIS 拡張を厚く記述、トラブルシュートも 5 サブ項目。6b はフェーズ別表で実装済 / 未実装の境界明示。軸 4 のみ yang = 1 で 4 点
- **#8 switch-port-modes-and-vlan-cli-internals (partially_implemented split-child)**: 「フェーズ別 実装境界」セクションがリファレンス実装で、phase 表が leaf-level support matrix まで降りている。軸 4 は cli = 1 で 4 点

### 中評価（4.67）3 件

- **#3 gnsi-hld-limitations (partially_implemented)**: 「HLD と実装の差分」セクションあり、`実装フェーズ境界` も明示だが、partially の **境界明示が散文ベース** で leaf-level 表が無いため 6b = 3。related cli = 0 で軸 4 = 4
- **#4 build-profiles (not_implemented)**: §5.4 OK で軸 6 = 5、ただし related cdb/cli/yang **3 層完全空** で軸 4 = 3。`_no_related_*` opt-out 候補（HLD 提案段階で配下コードが完全に存在しないため、related が紐付け不能であることが正解）。round 20 の `port-naming` / `dip-sip` と同パターン
- **#6 sflow-high-level-design (evolved_beyond_hld)**: `hsflowd` から `sflowmgrd` / SAI sample-packet への evolved パターンだが、6b 制限事項に **HLD と実装の rename 表が無い**（散文で「現状は X 経由」と書いてあるのみ）。軸 6 = 4。round 32 改善で `!!! diff` admonition 整備されたので次回バッチ対象

### 軸 4 が天井 4 で頭打ちの構造的理由

8 件中 5 件で軸 4 = 4 点。原因は df 固有の構造（HLD 提案段階で実装が無いため yang/cli/cdb 紐付け先が存在しない）と、`_no_related_*` opt-out seed が df 系まで未展開（round 30/31 で Reference 系には浸透したが df 系は未着手）の組み合わせ。`build-profiles` のような 0/0/0 は **本質的に空が正解**で、opt-out 投入で 5 点（N/A）昇格可能。

## 6. 改善提言（3 つ）

### 改善 1: `_no_related_*` opt-out seed の df 系への展開（次回 round 48 想定）

本 round で `build-profiles` (0/0/0) / `local-ars-hld` (3/2/1) / `sflow` (3/2/1) / `gnsi-hld-limitations` (2/0/4) など、df ページの **多くで yang/cli いずれかが構造的に空**。`_no_related_*` opt-out を df 74 件に展開すると軸 4 真値が +0.3 程度押し上げ可能と推定（round 31 の Reference 展開と同水準のインパクト）。スクリプト案: `meta/scripts/audit_df_related_opt_out.py`、df ページの実装欠落層を grep で自動判定して opt-out 候補を出力。

### 改善 2: `evolved_beyond_hld` の 6b 旧 → 新 rename 表テンプレ化

本 round で `sflow` のみ 6b = 3 と低位。`!!! diff "HLD と実装の差分"` admonition は round 32 で整備済みだが、`evolved` 28 件への横展開が未完。**「HLD 名 → 実装名 → 差分理由 → SHA」の 4 列表テンプレ**を `meta/templates/page.md` に追加し、`evolved` 全件で必須化することで 6b 平均が 4.00 → 4.80 圏まで上昇する見込み。lint は `check_evolved_rename_table.py` 新設で対応。

### 改善 3: `deprecated` サブセットの monitor 集計と guide §5.4a 例示拡充

本 round で初の `deprecated` サンプル抽出。リポ全体での `deprecated` 件数は monitor 集計上で数件と少ないが、`bgp-route-install-error-handling` のように「後継機能リンクで完全に置換可能」なパターンと、「廃止のみ明示で後継が無い」パターンの 2 系統がある。guide §5.4a に **「後継リンクが存在しないが廃止理由 (security/perf/license) が明示されている場合の評価」** を追記する（リンク無し = 2 点だが廃止理由明示で +1 補正で 3 点、等）。`meta/scripts/lint_deprecated_link.py` で機械チェックも検討。

## 7. 結論

- discrepancy-found 指名 mini 8 件、6 軸 5 点満点で **平均 4.81 / 5**（round 20 4.67 から **+0.14**、改善幅 +3.0%）
- 軸 6（完結性 / subtype 別）が **3.82 → 4.75 (+0.93)** で最大改善。§5.4 finalized による `not_implemented` の N/A 化が支配的要因
- subtype 別: **not_implemented 5.00 / partially_implemented 4.75 / evolved_beyond_hld 4.00 / deprecated 5.00**。round 20 の **3.82 横並び** から大きく分化、`evolved` のみ低位で次回集中対象
- 軸 4（関連性）は 4.36 → 4.13 で −0.23 と df 固有減点が残存。`_no_related_*` opt-out の df 系展開（改善 1）で +0.3 圏の追加押し上げが可能
- 軸 2 / 軸 6 = 5.00 飽和件数: round 20 で 1 / 11 (9%) → 本 round で 6 / 8 (75%) と **大幅増**。§5.4 finalize + partial 境界 strict 化の累積効果が実証された
- 改善 1（df への opt-out 展開）/ 2（evolved 6b rename 表テンプレ）/ 3（deprecated 評価拡充）の 3 件で **次回 discrepancy 指名 round（仮 round 49 disc-mini）平均 4.95 圏到達**が見込まれる

## 関連ドキュメント

- [監査 round 45（random 10 周目）](./quality-audit-45.md)
- [監査 round 44（stratified 9 周目偶数）](./quality-audit-44.md)
- [監査 round 42（df subtype 別評価 3 周目）](./quality-audit-42.md)
- [監査 round 20（初の discrepancy-found 指名 round、4.67）](./quality-audit-20.md)
- [品質監査ガイド §5 / §5.4 / §5.4a（df subtype 別評価）](./quality-audit-guide.md)
- [discrepancy 運用ガイド](./discrepancy-operations.md)
- [HLD と実装の乖離 一覧（discrepancy-index）](../docs/reference/verification/discrepancy-index.md)
- [品質ロードマップ](./quality-roadmap.md)
