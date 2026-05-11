---
title: 品質改善サンプリング監査（round 20、discrepancy-found 指名 round）
area: meta
verification: meta
last_verified: 2026-05-11
sources: []
---

# 品質改善サンプリング監査（round 20、discrepancy-found 指名 round）

- 実施日: 2026-05-11
- 対象: round 19 (4.90 / 5) 後の現行 main
- サンプル数: **12 件**（**`verification: discrepancy-found` 指名 sampling**、`find docs -name '*.md' -exec grep -l 'verification: discrepancy-found' {} \; | shuf -n 12`）
- 評価軸: ユーザー指示の **6 軸 5 点満点**（構成 / 裏取り / 引用 / 関連性 / 可読性 / 完結性）
- 評価者: AI（Claude / batch #6、worktree 隔離）

## 0. round 20 の位置付け（discrepancy-found 指名 round）

round 19 (4.90) までは 8 周連続で「ランダム抽出」を採用してきたが、累積 96 件のサンプルに対して **`verification: discrepancy-found` ページの混入は 2 件のみ**（round 17 で 2 件）に留まり、`meta/quality-audit-guide.md` 1.2 節の **軸 6「乖離説明の整理度」読み替え規定が実運用でほぼ未検証**だった。round 19 の改善 3 で提案したとおり、本 round 20 は **discrepancy-found ページ指名の集中監査**として実施する。

discrepancy-found ページは monitor タグ別に 4 型（`not_implemented` / `partially_implemented` / `evolved_beyond_hld` / `deprecated`）に分かれ、それぞれ「実装が未着手」「部分実装」「進化済み」「廃止済み」と乖離の構造が大きく異なる。本監査では monitor タグ別の集計を行い、どの型が監査基準で構造的に弱いかを定量化する。

### round 12〜19（ランダム抽出）と round 20（指名抽出）の比較

| Round | 5 点換算 | 軸数・備考 |
|-------|----------|------------|
| 12 | 4.83 | 6 軸、ランダム 12 件 |
| 13 | 4.79 | 6 軸、ランダム 12 件（chapter-index 1 混入）|
| 14 | 4.85 | 6 軸、ランダム 12 件 |
| 15 | 4.83 | 6 軸、ランダム 12 件 |
| 16 | 4.89 | 6 軸、ランダム 12 件 |
| 17 | 4.86 | 6 軸、ランダム 12 件（discrepancy-found 2 件混入、軸 6 通常基準で 4 点天井）|
| 18 | 4.88 | 6 軸、ランダム 12 件 |
| 19 | 4.90 | 6 軸、ランダム 12 件（プラトー上限 4.90 到達）|
| **20** | **4.67** | **6 軸、`discrepancy-found` 指名 12 件（軸 6 はガイド 1.2 節読み替えで評価）** |

**観測**: ランダム抽出が形作る母集団平均 (4.86〜4.90) に対し、**discrepancy-found 指名 round は 4.67** と 0.20 ポイント下回る。これは構造的な品質劣化ではなく、**「実装が存在しないため CLI / CONFIG_DB / YANG の related が空になりやすい」「next-action 明記がほぼ全件で抜けている」という discrepancy-found 固有の減点パターン**が露出した結果。本 round の目的はこのパターンを定量的に可視化することにある。

## 1. サンプル一覧（discrepancy-found 指名 12 件）

| # | パス | area | monitor | 行数 |
|---|------|------|---------|------|
| 1 | `docs/overlay/dscp-remapping-for-tunnel-traffic.md` | overlay | evolved_beyond_hld | 233 |
| 2 | `docs/system/hld-secure-boot.md` | system | evolved_beyond_hld | 218 |
| 3 | `docs/platform/smartswitch-dpu-graceful-shutdown.md` | platform | not_implemented | 243 |
| 4 | `docs/platform/sonic-port-naming-convention-change.md` | platform | not_implemented | 251 |
| 5 | `docs/architecture/dip-sip-ptf-validation-high-level-design.md` | architecture | evolved_beyond_hld | 295 |
| 6 | `docs/architecture/sag-high-level-design-for-sonic.md` | architecture | not_implemented | 224 |
| 7 | `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md` | architecture | not_implemented | 264 |
| 8 | `docs/architecture/sflow-high-level-design.md` | architecture | evolved_beyond_hld | 221 |
| 9 | `docs/acl-qos/dhcp-dos-mitigation-in-sonic.md` | acl-qos | not_implemented | 208 |
| 10 | `docs/switching/switch-port-modes-and-vlan-cli-enhancement.md` | switching | partially_implemented | 367 |
| 11 | `docs/management/sonic-console-switch.md` | management | partially_implemented | 195 |
| 12 | `docs/reference/verification/discrepancy-index.md` | reference (meta) | N/A（meta 自動生成）| 292 |

monitor 内訳: **not_implemented 5 / evolved_beyond_hld 4 / partially_implemented 2 / deprecated 0 / N/A (meta) 1**。`deprecated` が混入しなかったのは現行リポ全体で `deprecated` タグが 0 件のためで、構造的欠落ではない。#12 は `verification: meta` だが `grep -l 'verification: discrepancy-found'` で本文ヒットしたため引き当てられた。章扉相当として軸 2 / 6 を N/A 化する。

## 2. 評価軸（ユーザー指示 6 軸、5 点満点、軸 6 は読み替え）

| 軸 | 内容 |
|----|------|
| 1. 構成 | 章立て・流れ |
| 2. 裏取り | sources / verification ステータス / evidence コメント |
| 3. 引用 | 脚注・evidence コメント・commit ref |
| 4. 関連性 | related / related_topics / topics back-ref |
| 5. 可読性 | 日本語の自然さ・mermaid 図・表・glossary 整合 |
| 6. **乖離説明の整理度**（`meta/quality-audit-guide.md` 1.2 節）| monitor タグ妥当性 / 「実装との乖離」セクションの構造化 / 裏取り evidence / next-action |

軸 6 のサブ項目チェック（4/4 = 5 点、3/4 = 4 点、2/4 = 3 点、1/4 = 2 点、0/4 = 1 点）:

- (a) frontmatter `monitor:` が 4 値のいずれかで本文の乖離パターンと整合
- (b) 「実装との乖離」「現行実装との乖離」「HLD と実装の乖離」相当の見出しが存在し、HLD 主張 / master 実態 / 差分インパクトが読み分けられる
- (c) 「実装が存在しない」「別名で実装されている」等の判定根拠が evidence コメント（`source:` / `excerpt:` / `reasoning:`）で埋め込まれている
- (d) 読み手が現行 master でどう取り扱うべきかの next-action が明示されている

## 3. 評価結果

| # | ページ | 構成 | 裏取り | 引用 | 関連性 | 可読性 | 軸 6 | 平均 |
|---|--------|------|--------|------|--------|--------|------|------|
| 1 | dscp-remapping (evolved) | 5 | 5 | 5 | 5 | 5 | 4 | **4.83** |
| 2 | secure-boot (evolved) | 5 | 4 | 5 | 3 | 5 | 3 | **4.17** |
| 3 | smartswitch-dpu-shutdown (not_impl) | 5 | 5 | 5 | 4 | 5 | 4 | **4.67** |
| 4 | port-naming (not_impl) | 5 | 5 | 5 | 3 | 5 | 4 | **4.50** |
| 5 | dip-sip (evolved) | 5 | 5 | 5 | 3 | 5 | 4 | **4.50** |
| 6 | sag (not_impl) | 5 | 4 | 5 | 5 | 5 | 3 | **4.50** |
| 7 | hamgrd (not_impl) | 5 | 5 | 5 | 4 | 5 | 4 | **4.67** |
| 8 | sflow (evolved) | 5 | 5 | 5 | 5 | 5 | 4 | **4.83** |
| 9 | dhcp-dos (not_impl) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 10 | switchport (partial) | 5 | 5 | 5 | 5 | 5 | 4 | **4.83** |
| 11 | console-switch (partial) | 5 | 4 | 5 | 5 | 5 | 3 | **4.50** |
| 12 | discrepancy-index (meta N/A) | 5 | N/A | 5 | 5 | 5 | N/A | **5.00** |

### 軸別平均（N/A 除外）

| 軸 | 平均 | 備考 |
|----|------|------|
| 1. 構成 | **5.00** | 12 件全件で「概要 → 動作仕様 → 設定 → 制限 → 干渉 → トラブルシュート → 実装との乖離 → 引用元」テンプレが浸透（7 周連続飽和）|
| 2. 裏取り | **4.73** (11 件) | secure-boot / sag / console-switch の 3 件で本文 evidence コメント 0 件 → 4 点。残 8 件は evidence 5〜12 個 |
| 3. 引用 | **5.00** | 全 12 件で sources / 「引用元」 / 本文脚注が整備 |
| 4. 関連性 | **4.36** (11 件) | port-naming / dip-sip / secure-boot で `related.config_db / cli / yang` 3 空 → 3 点。smartswitch-dpu / hamgrd で 2 空 → 4 点。**discrepancy-found 固有の構造減点**（実装が無いと related が紐付けられない）|
| 5. 可読性 | **5.00** | 全 12 件で mermaid 1〜2 個 + glossary back-link 3〜14 件、ランダム round 19 と同水準 |
| 6. 乖離説明 | **3.82** (11 件) | **唯一 dhcp-dos のみ 5 点満点**。残 10 件は (d) next-action 明示で失点。secure-boot / sag / console-switch は (c) evidence でも失点で 3 点 |
| **総平均（discrepancy 11 件）** | **4.64** | meta 1 件除外 |
| **総平均（12 件、N/A 除外）** | **4.67** | round 19 (4.90) から **−0.23** |

### monitor タグ別平均（評価対象 11 件、meta 除外）

| monitor | 件数 | 平均 | 軸 6 平均 | 備考 |
|---------|------|------|-----------|------|
| `not_implemented` | 5 | **4.67** | 4.00 | smartswitch-dpu / hamgrd / port-naming / sag / dhcp-dos。**dhcp-dos のみ 5.00**（next-action 明示）、他 4 件は 4 点天井 |
| `evolved_beyond_hld` | 4 | **4.58** | 3.75 | dscp-remap / secure-boot / dip-sip / sflow。secure-boot が evidence 不在で 4.17 まで下げ、グループ平均を引き下げ |
| `partially_implemented` | 2 | **4.67** | 3.50 | switchport / console-switch。switchport は 4.83 で良好だが、console-switch が evidence 不在で 4.50 |
| `deprecated` | 0 | — | — | サンプル混入なし。リポ全体でも `deprecated` タグは 0 件 |

**観測 A**: monitor 別平均は **not_implemented (4.67) ≈ partially_implemented (4.67) > evolved_beyond_hld (4.58)** で、**evolved_beyond_hld 型が最も低い**。evolved 型は「HLD と現行 master の両方を併記して差分を読み分ける」記述負荷が高く、構造的に減点されやすい。

**観測 B**: 軸 6 平均は monitor 横断で **3.82** に張り付き、ランダム round の軸 6 = 4.80〜5.00 と比較して **約 1 点低い**。原因は **(d) next-action 明示の浸透率が 11 件中 1 件（9%）** に留まっていること。これは個別ページの問題ではなく、**discrepancy-found 全体のテンプレ整備の遅れ**を示す。

## 4. round 12〜19（ランダム）vs round 20（指名）の比較

| 観点 | round 19（ランダム）| round 20（discrepancy-found 指名）| 差分 |
|------|---------------------|-----------------------------------|------|
| サンプリング | 完全ランダム 12 件 | discrepancy-found 指名 12 件 | CHANGE |
| 平均 | 4.90 | **4.67** | −0.23 |
| 軸 1 構成 | 5.00 | 5.00 | KEEP |
| 軸 2 裏取り | 5.00 | 4.73 | −0.27 |
| 軸 3 引用 | 5.00 | 5.00 | KEEP |
| 軸 4 関連性 | 4.83 | **4.36** | **−0.47**（実装無しで related 紐付け不能）|
| 軸 5 可読性 | 4.92 | 5.00 | +0.08（mermaid / glossary 浸透）|
| 軸 6 完結性 / 乖離整理度 | 5.00 | **3.82** | **−1.18**（next-action 不在）|
| 満点件数 | 8/12 + N/A 3 | 1/12 + N/A 1 | −7 |
| chapter / meta 系 | 3 件 | 1 件 | −2 |

**重要観測**:

- 軸 1 / 3 / 5 は **ランダム round と同水準**。テンプレ整合・引用・mermaid/glossary は discrepancy-found ページでも同等品質
- 減点は **軸 4 (関連性) と 軸 6 (乖離整理度) に集中**。これらは discrepancy-found 固有の構造課題
- ガイド 1.2 節の読み替えがあって尚 **軸 6 = 3.82** は、現行 discrepancy-found ページ群が「監査ガイドが要求する 4 サブ項目（特に next-action）」を構造的に欠いていることを示す
- ランダム round 平均 (4.86〜4.90) と指名 round 平均 (4.67) のギャップは **0.20〜0.23**。これは **discrepancy-found 49 件全体への一括 batch 改善で −0.20 圏を埋める余地がある**ことを意味する

## 5. 個別所感

### 満点（5.00）1 件: dhcp-dos-mitigation-in-sonic

`not_implemented` 型で唯一 5.00。`tc` qdisc 投入手順を読み手が即時実行できる形で記述、`config interface dhcp-mitigation-rate` の master 取り込み状況、CoPP との使い分け、**「いま master でどこまで効くのか」の next-action が冒頭から明示**されている。**discrepancy-found ページのリファレンス実装**として扱える品質。

### 高評価（4.83）3 件: dscp-remapping / sflow / switchport

3 件とも「実装との乖離」セクションが厚く、related も網羅。軸 6 で next-action のみ欠落で 4 点。switchport は 367 行と最長で、`partially_implemented` 型の理想形に近い（access / trunk / routed の 3 モードのうち、どの遷移が master で動作するかが表で整理）。

### 中評価（4.50〜4.67）6 件

- `smartswitch-dpu-shutdown` / `hamgrd`: 4.67。evidence は厚いが related で CDB だけ埋まり CLI / YANG が空 → 軸 4 = 4。next-action 不在で軸 6 = 4
- `port-naming` / `dip-sip`: 4.50。`related.* 3 空` で軸 4 = 3、軸 6 = 4
- `sag` / `console-switch`: 4.50。related は埋まるが evidence コメント 0 件 → 軸 2 = 4、軸 6 = 3（evidence + next-action 同時欠落）

### 低評価（4.17）1 件: secure-boot

evolved_beyond_hld の中で最低スコア。本文 evidence コメント 0 件、`related.* 3 空`、next-action 不在で **3 つの構造欠落が重なった**。Verifier batch の再起動候補。

### meta N/A（5.00）1 件: discrepancy-index

`meta/scripts/gen_discrepancy_index.py` 自動生成。area 別 / monitor 別の集計表、エントリ一覧、監査基準の読み替え注記が整備。軸 2 / 6 は N/A 化。

## 6. discrepancy-found ページ固有の改善提言（3 つ）

### 改善 1: `next-action` セクションの全 discrepancy-found ページ batch 注入（最優先）

軸 6 平均 = 3.82 の最大要因は **next-action 明示率 9% (1/11)**。`meta/templates/page.md` を改訂し、`discrepancy-found` ページに **「現行 master での取り扱い」セクションを必須化**する。サブ項目テンプレ:

- HLD の機能を **代替実装** で実現するか、**機能を諦めるか** の判断分岐
- 代替実装の具体的コマンド or 設定例（dhcp-dos の `tc` 投入手順がリファレンス）
- master 追従時の watch ポイント（特定 PR / issue / commit）

49 件 × ~10 行の追加で軸 6 を 3.82 → 4.50 圏に押し上げ可能。batch 実装は `scripts/inject_next_action.py` を新設し、monitor タグ別の雛形を流し込む形を推奨。

### 改善 2: monitor タグ精度の自動検証（lint）

本 round のサンプル 11 件中、monitor タグと本文の整合性に明確な誤りは見つからなかったが、`evolved_beyond_hld` と `partially_implemented` の境界は曖昧（switchport は「一部モードのみ動作」で `partially_implemented`、dip-sip は「テスト形式が変更」で `evolved_beyond_hld`、両者の判定基準は本文を精読しないと判らない）。`meta/scripts/lint_monitor_tag.py` を新設し、

- `not_implemented`: 本文に「実装されていない」「未取り込み」「PR 未マージ」相当のフレーズが必須
- `evolved_beyond_hld`: 本文に「別設計に置き換え」「実装は HLD と異なる」相当が必須
- `partially_implemented`: 本文に「一部のみ動作」「<機能 X> は実装、<機能 Y> は未実装」相当が必須
- `deprecated`: 本文に「廃止」「削除済み」相当が必須

の正規表現マッチで警告を出す。CI で実行することで monitor タグの精度を担保。

### 改善 3: 「実装との乖離」セクションの差分テンプレ整備

現行ページの「実装との乖離」セクションは構造がバラバラで、HLD 主張 / master 実態 / 差分インパクトの **3 点読み分けが厳密に揃っているのは 11 件中 6 件**（dscp / smartswitch-dpu / hamgrd / dhcp-dos / switchport / sflow）。残 5 件は箇条書き混在で読み分けが甘い。`meta/templates/page.md` に **`!!! diff` 風カスタムブロック**を追加し、

```
!!! diff "実装との乖離: <一行サマリ>"
    **HLD 主張**: ...
    **master 実態**: ... (evidence: <SHA>:<path>:<line>)
    **差分インパクト**: ...
```

の 3 ブロック構造を強制する。MkDocs の admonition 拡張で実装可能。これにより軸 6 サブ項目 (b) / (c) の構造化が一気に底上げされ、3.82 → 4.70 圏が見える。

## 7. 結論

- discrepancy-found 指名 12 件、6 軸 5 点満点で **平均 4.67 / 5**（ランダム round 19 = 4.90 から −0.23）
- monitor 別: **not_implemented 4.67 / partially_implemented 4.67 / evolved_beyond_hld 4.58 / deprecated サンプル無し**。evolved 型が最も低い
- 軸 6（乖離整理度、ガイド 1.2 節読み替え）= **3.82** が最大の減点軸。next-action 明示率 9% (1/11) が主因
- 軸 4（関連性）= **4.36** で −0.47。実装が無いと related が紐付けられない discrepancy-found 固有の構造減点
- 軸 1 / 3 / 5 はランダム round と同水準（5.00）、テンプレ・引用・可読性は discrepancy ページでも品質維持
- 満点 dhcp-dos がリファレンス実装。軸 6 を満点取れる構造（next-action 明示・代替実装手順・watch ポイント）が確立済み
- 改善 1（next-action batch 注入）/ 2（monitor lint）/ 3（差分テンプレ整備）の 3 件で 4.67 → **4.80 圏到達**が見込まれる

## 関連ドキュメント

- [監査 round 19（プラトー上限 4.90 到達）](./quality-audit-19.md)
- [監査 round 18（v1.0 GA 後 7 回目）](./quality-audit-18.md)
- [監査 round 17（discrepancy-found 2 件混入観測）](./quality-audit-17.md)
- [品質監査ガイド（1.2 節 discrepancy-found 軸 6 読み替え規定）](./quality-audit-guide.md)
- [品質ロードマップ](./quality-roadmap.md)
- [discrepancy 運用ガイド](./discrepancy-operations.md)
- [HLD と実装の乖離 一覧（discrepancy-index）](../docs/reference/verification/discrepancy-index.md)
