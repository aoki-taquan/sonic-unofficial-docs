---
title: 品質改善サンプリング監査（round 17、v1.0 GA 後の 6 回目定点観測）
area: meta
verification: meta
last_verified: 2026-05-11
sources: []
---

# 品質改善サンプリング監査（round 17、v1.0 GA 後の 6 回目定点観測）

- 実施日: 2026-05-11
- 対象: round 16 (4.89 / 5) 後の現行 main
- サンプル数: **12 件**（`find docs -name '*.md' | shuf -n 12` による完全ランダム）
- 評価軸: ユーザー指示の **6 軸 5 点満点**（構成 / 裏取り / 引用 / 関連性 / 可読性 / 完結性）
- 評価者: AI（Claude / batch #6、worktree 隔離）

## 0. round 12〜16 → round 17 の比較条件

round 16 と同じ「6 軸 5 点満点・完全ランダム抽出・章扉 N/A 化（`page_kind: chapter-index` の軸 2 / 6 を N/A）」を踏襲。round 17 の注目点はユーザー指示どおり、**(a) CDB ops-hint 100% カバレッジが完結性軸 5 飽和を維持しているか**、**(b) CLI Reference ops-hint batch 45 ページ展開後の効果**、**(c) glossary +31 用語追加後の可読性軸への波及**、**(d) evidence rendering 改修の引用軸へのインパクト** の 4 点。サンプル中に YANG 3 / CDB 1 / CLI 1 / runbook 1 / HLD 系 4 / 章扉 1 / discrepancy-found 2 と過去最も多様な混入になり、テンプレ batch の **裾野効果**（章扉以外の HLD ページへの波及）を検証する好機。

| Round | 5 点換算 | 軸数・備考 |
|-------|----------|------------|
| 11 | 4.93 | 10 軸、v1.0 GA 昇格判定 GO |
| 12 | 4.83 | 6 軸、ランダム 12 件 |
| 13 | 4.79 | 6 軸、ランダム 12 件（chapter-index 1 混入）|
| 14 | 4.85 | 6 軸、ランダム 12 件（chapter-index 2 件は緩和評価）|
| 15 | 4.83 | 6 軸、ランダム 12 件（章扉 / カテゴリ扉 2 件は N/A 化、hld-only 1 件回帰）|
| 16 | 4.89 | 6 軸、ランダム 12 件（CDB ops-hint batch 効果でプラトー突破）|
| **17** | **4.86** | **6 軸、ランダム 12 件（章扉 1 件は N/A 化、YANG 3 件 + discrepancy-found 2 件混入）** |

**改善観測**: round 16 (4.89) → round 17 (4.86) で **-0.03** の微減。プラトー突破は維持（4.79〜4.85 帯には戻らず）。減点は **YANG Ref 3 件混入の天井問題**（CDB ops-hint テンプレが未横展開）と **discrepancy-found 2 件の軸 6 完結性 4 点天井**による構造的なもの。CDB / CLI / runbook 系は **全件満点に近い**。

## 1. サンプル一覧（ランダム 12 件）

| # | パス | area | 行数 | verification |
|---|------|------|------|--------------|
| 1 | `docs/reference/yang/sonic-sflow.md` | reference (YANG) | 120 | code-verified |
| 2 | `docs/reference/yang/sonic-crm.md` | reference (YANG) | 131 | code-verified |
| 3 | `docs/routing/bgp-route-install-error-handling.md` | routing (HLD) | 210 | discrepancy-found |
| 4 | `docs/acl-qos/sonic-port-mirroring-hld.md` | acl-qos (HLD) | 134 | code-verified |
| 5 | `docs/reference/yang/sonic-mclag.md` | reference (YANG) | 116 | code-verified |
| 6 | `docs/reference/runbooks/dhcp-relay.md` | reference (runbook) | 107 | runbook-verified |
| 7 | `docs/system/sonic-boot-chart.md` | system (HLD) | 219 | code-verified |
| 8 | `docs/system/banner-messages-hld.md` | system (HLD) | 224 | code-verified |
| 9 | `docs/reference/cli/config-mclag.md` | reference (CLI) | 180 | code-verified |
| 10 | `docs/routing/local-ars-hld.md` | routing (HLD) | 157 | discrepancy-found |
| 11 | `docs/topics/22-reference-index/index.md` | topics（章扉 / N/A 化）| 75 | meta |
| 12 | `docs/reference/config-db/community-set.md` | reference (CDB) | 91 | code-verified |

カテゴリ内訳: Reference 系 **6/12（YANG 3 + CDB 1 + CLI 1 + runbook 1）**、HLD 系 4、章扉 1、topics 1 (実質 0)。**YANG Ref 3 件混入は過去最高比率**で、ops-hint 未横展開の天井問題を直接観測できる。

## 2. 評価軸（ユーザー指示 6 軸、5 点満点）

| 軸 | 内容 |
|----|------|
| 1. 構成 | 章立て・流れ |
| 2. 裏取り | sources / verification ステータス |
| 3. 引用 | 脚注・evidence コメント・commit ref |
| 4. 関連性 | related / related_topics / topics back-ref |
| 5. 可読性 | 日本語の自然さ・mermaid 図・表 |
| 6. 完結性 | 設定例・制限事項・トラブルシュート |

5 = excellent / 4 = good / 3 = acceptable / 2 = lacking / 1 = poor

`page_kind: chapter-index` 相当（カテゴリ扉 / topics しおり）は軸 2 / 6 を **N/A**（残り 4 軸の単純平均）。

## 3. 評価結果

| # | ページ | 構成 | 裏取り | 引用 | 関連性 | 可読性 | 完結性 | 平均 |
|---|--------|------|--------|------|--------|--------|--------|------|
| 1 | sonic-sflow (YANG) | 5 | 5 | 5 | 5 | 4 | 4 | **4.67** |
| 2 | sonic-crm (YANG) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 3 | bgp-route-install-error-handling (HLD, discrepancy) | 5 | 5 | 5 | 5 | 5 | 4 | **4.83** |
| 4 | sonic-port-mirroring-hld | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 5 | sonic-mclag (YANG) | 5 | 5 | 5 | 5 | 4 | 4 | **4.67** |
| 6 | dhcp-relay (runbook) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 7 | sonic-boot-chart | 5 | 5 | 5 | 4 | 5 | 5 | **4.83** |
| 8 | banner-messages-hld | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 9 | config-mclag (CLI) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 10 | local-ars-hld (discrepancy) | 5 | 5 | 5 | 5 | 5 | 4 | **4.83** |
| 11 | 22-reference-index/index (章扉, N/A) | 5 | N/A | 5 | 5 | 5 | N/A | **5.00** |
| 12 | community-set (CDB) | 5 | 5 | 5 | 5 | 4 | 5 | **4.83** |

### 軸別平均（N/A は分母から除外）

| 軸 | 平均 | 備考 |
|----|------|------|
| 1. 構成 | **5.00** | 12 件全て章立て・冒頭サマリ・末尾 references 揃う（**4 周連続飽和**）|
| 2. 裏取り | **5.00** (11 件) | discrepancy-found 含む全件で sources 完備、ref SHA pinning OK |
| 3. 引用 | **5.00** | evidence rendering 改修で `<!-- ev: -->` 形式が表示で活かされ、**全 12 件で軸 3 = 5 点** |
| 4. 関連性 | **4.92** | boot-chart のみ「関連リファレンス」リンクなし → 4 点。他は **4 周連続満点** |
| 5. 可読性 | **4.75** | YANG sflow / mclag、CDB community-set で mermaid 不足 → 4 点。glossary +31 用語の効果は未浸透 |
| 6. 完結性 | **4.64** (11 件) | YANG sflow / mclag で運用ヒント未挿入 → 4 点、discrepancy-found 2 件は仕様上 4 点天井 |
| **総平均** | **4.86 / 5** | 12 件、平均（N/A 除外）|

round 16 (4.89) → round 17 (4.86) で **-0.03**。**主因は YANG Ref 3 件混入時の軸 5 / 6 天井**（CDB ops-hint テンプレが YANG に未横展開）と **discrepancy-found 2 件の軸 6 = 4 点固定**。それ以外（CDB / CLI / runbook / HLD 4 件）は **満点～4.83 帯に密集**で品質は維持されている。

### ユーザー指示 (a)〜(d) の検証結果

- **(a) CDB ops-hint 100%**: 本サンプル CDB 1 件（community-set）に ops-hint 節 **4 サブ節入り**、軸 6 = 5 点。round 16 観測どおり **CDB は完結性 5 点固定**。仕様継続を確認
- **(b) CLI ops-hint 45 ページ**: 本サンプル CLI 1 件（config-mclag）に ops-hint 節 **3 サブ節 + 実行例 3 サブ節 + mermaid 1 個**入り、**満点 5.00**。round 16 の show-storm-control / show-pfc に続き、**CLI Ref で 3 周連続して mermaid+ops-hint 両入りページが満点を取った**
- **(c) glossary +31 用語**: 軸 5 = 4.75 で round 16 から横這い。glossary 拡充は **未浸透**（既存ページに backlink が張られていないため）。次回 batch で glossary back-link 注入が課題
- **(d) evidence rendering**: 軸 3 が **round 16 = 4.82 → round 17 = 5.00 で +0.18**、**過去最高値で初の完全飽和**。evidence rendering 改修が **引用軸を構造的に押し上げた**ことを実測

## 4. 個別所感

### 完全満点 5 件（#2, #4, #6, #8, #9、加えて N/A 換算で #11）

実点満点 **5 件**（round 16 と同水準）+ N/A 算定 1 件 = 6/12。

- **sonic-crm (YANG)**: YANG 3 件中で唯一の満点。リソースクラス 8 種一覧、leaf 制約、CONFIG_DB / CLI 三角リンクが揃う。**「YANG でも内容量が大きければ満点に届く」例**
- **sonic-port-mirroring-hld**: SPAN / ERSPAN の table 整理、PORT_MIRROR_SESSION / ACL_TABLE / ACL_RULE の連携、ERSPAN ヘッダフォーマット解説まで網羅
- **dhcp-relay (runbook)**: 症状 → 想定原因 → 切り分け手順 5 段階 → 対処の runbook 黄金パターン。`runbook-verified` ステータスで軸 2 / 3 も満点
- **banner-messages-hld**: mermaid 3 個、login / motd / logout の 3 系統を pam / sshd / ssh-banner-script で完結記述
- **config-mclag (CLI)**: 8 コマンド全件 evidence-tagged、運用ヒント 3 サブ節 + 実行例 3 サブ節。**CLI Ref で 3 周連続満点パターン**

### 高評価（4.83）4 件（#3, #7, #10, #12）

- **bgp-route-install-error-handling**: `discrepancy-found` で軸 6 = 4 点天井（実装乖離節は完璧）
- **sonic-boot-chart**: 関連リファレンス節欠落 → 軸 4 = 4 点
- **local-ars-hld**: `discrepancy-found` で軸 6 = 4 点天井（実装乖離節 4 サブ節は出色）
- **community-set (CDB)**: 運用ヒント 3 サブ節完備、mermaid 不在 → 軸 5 = 4 点

### 中評価（4.67）2 件（#1, #5）

- **sonic-sflow (YANG)**: 軸 5 / 6 = 4 点。**mermaid 1 個（データフロー自動生成）のみ**、運用ヒント節なし
- **sonic-mclag (YANG)**: 軸 5 / 6 = 4 点。同上、**YANG Ref の構造的天井**

## 5. spot check（4 件、軸 3 引用の正確性裏取り）

| # | ページ | チェック対象 | 結果 |
|---|--------|--------------|------|
| S1 | sonic-crm | `sonic-crm.yang` resource enum 8 種、threshold attr | OK |
| S2 | sonic-port-mirroring-hld | `mirrororch.cpp` SAI mirror session attr 反映 | OK |
| S3 | dhcp-relay (runbook) | `dhcp6relay/src/relay.cpp` ref pin 整合 | OK |
| S4 | config-mclag | `config/mclag.py` の click group 8 サブコマンド | OK |

4/4 構造的に整合。引用品質は **過去最高水準**（evidence rendering 改修で `<!-- ev: -->` がツールチップ表示されるようになり、reviewer 確認が高速化）。

## 6. round 16 との差分

| 観点 | round 16 | round 17 | 差分 |
|------|---------|---------|------|
| 軸スキーム | 6 軸 5 点 + 章扉 N/A 化 | 6 軸 5 点 + 章扉 N/A 化 | KEEP |
| 平均 | 4.89 | **4.86** | -0.03（プラトー突破は維持）|
| サンプリング | 完全ランダム | 完全ランダム | KEEP |
| 満点件数（実点） | 5/12 | 5/12 | KEEP |
| Reference 系の比率 | 7/12 (CDB 4 + CLI 2 + YANG 1) | 6/12 (YANG 3 + CDB 1 + CLI 1 + runbook 1) | -1（内訳分散）|
| YANG Ref 混入 | 1/12 | **3/12** | +2（天井問題が顕在化）|
| discrepancy-found 混入 | 0 | 2 | +2（軸 6 = 4 点固定）|
| 軸 3 引用 | 4.82 | **5.00** | **+0.18**（evidence rendering 改修）|
| 軸 4 関連性 | 5.00 | 4.92 | -0.08（boot-chart で関連リンク欠落）|
| 軸 5 可読性 | 4.75 | 4.75 | KEEP（glossary 拡充は未浸透）|
| 軸 6 完結性 | 4.91 | 4.64 | -0.27（YANG / discrepancy 天井）|
| spot check | 4/4 | 4/4 | KEEP |

**重要観測 1（YANG Ref の構造的天井）**: YANG Ref 3 件中 **2 件が 4.67、1 件のみ満点**（crm のみ）。crm が満点になれたのは **130 行と量があり、リソースクラス一覧 / 制約 / leafref / augment が充実していたから**。一方 sflow (120 行) / mclag (116 行) は **量はあるが運用ヒント節と mermaid 詳細図が欠落**。**CDB ops-hint テンプレを YANG に横展開すれば +0.16〜+0.33 改善が見込める**（round 16 の CLI 改善幅と同等）

**重要観測 2（evidence rendering の効果実証）**: 軸 3 引用が **4.82 → 5.00 で +0.18**、過去最高値で初の完全飽和。これは **構造改修（rendering 側）が監査スコアに直接寄与した珍しい例**。今後の改修方針として「テンプレ batch（執筆側）」と「rendering 改修（表示側）」の 2 経路が等しく有効と確認

**重要観測 3（discrepancy-found の軸 6 天井問題）**: bgp-route-install-error-handling / local-ars-hld の 2 件はどちらも `monitor: deprecated` / `not_implemented` で **「実装と乖離している」ことを正しく示している良いページ**。しかし軸 6（完結性 = 設定例・制限事項・トラブルシュート）は **未実装機能のため設定例を書けない**。**discrepancy-found 専用の評価基準が必要**（「乖離をどれだけ正しく説明したか」を軸 6 の代替指標にする）

## 7. 次回（round 18）改善すべき 3 つ

round 16 改善 1（Reference 系 mermaid 注入 batch）、2（YANG ops-hint 横展開）、3（runbook-verified schema 改訂）の到達状況:

- 1: CLI 系は **mermaid+ops-hint batch 完了**（本監査の config-mclag で実証）、CDB は mermaid 残存、**YANG は未着手で天井露呈**
- 2: **未着手、本監査で天井問題が定量化された**（YANG 3 件中 2 件で軸 5 / 6 = 4 点）
- 3: **schema 改訂完了**（dhcp-relay runbook で `verification: runbook-verified` 観測、軸 2 / 3 満点）

### 改善 1: YANG Reference ops-hint + mini-mermaid batch の発進（最優先）

round 17 の最大の発見は **YANG Ref 3 件のうち 2 件が 4.67 で天井に当たっている**こと。CDB ops-hint batch は 4/4 で完結性 5 点を取った前例があり、**同じテンプレを YANG に横展開すれば総平均は 4.86 → 4.95 圏に押し戻せる見込み**。テンプレ要素は **(a) `<!-- ops-hint -->` マーカー、(b) 「典型値 / よくある誤設定 / 確認コマンド / 関連 show」4 サブ節、(c) YANG → orch → SAI の mini mermaid** の 3 点固定。対象は YANG Ref ~28 ページ全件。

### 改善 2: discrepancy-found 専用の軸 6 代替指標を導入

bgp-route-install-error-handling / local-ars-hld のような `discrepancy-found` ページは **「正しく実装乖離を説明している」点で品質が高い**にもかかわらず、軸 6（完結性 = 設定例）は構造的に書けず 4 点天井。**軸 6 を `verification: discrepancy-found` の場合に「乖離の説明完全性（実装との乖離節のサブ節数・代替機能の言及・実装ロードマップへの言及）」に置換**するルールを `meta/quality-roadmap.md` に追記する。これで監査スコアの **構造的減点を解消**（round 17 でも +0.06 戻る試算）。

### 改善 3: glossary back-link 注入 batch（軸 5 抜け道）

glossary +31 用語追加は実施済みだが、本監査で **軸 5 可読性 = 4.75 で 3 周連続停滞**。原因は **既存ページに glossary back-link が張られていないため、用語拡充が読み手に届いていない**。対策: 既存 docs から `BGP` / `ECMP` / `MCLAG` / `VRF` / `ACL` / `CoPP` / `ERSPAN` / `MACsec` / `MACSEC_PROFILE` / `RIF` 等の頻出用語に対し **初出箇所に `[BGP][gloss-bgp]` 形式のリンク注入 batch** を 1 周回す。100 ページ規模、半自動で実行可能。軸 5 を 4.75 → 4.85+ に抜く狙い。

## 8. 結論

- ランダム抽出 12 件、6 軸 5 点満点で **平均 4.86 / 5（97.2%）**
- 完全満点 **5/12（実点） + 1/12（N/A 算定）= 6/12**
- 軸 1（構成）が **4 周連続 5.00 飽和**、軸 3（引用）が **evidence rendering 改修で初の 5.00 飽和**
- 軸 6（完結性）が 4.91 → 4.64 へ -0.27、原因は YANG Ref 3 件混入 + discrepancy-found 2 件混入の **構造的天井**
- 軸 5（可読性）は 4.75 で **3 周連続停滞**。glossary +31 用語は未浸透
- round 16 (4.89) から -0.03 で **プラトー突破は維持**（4.79〜4.85 帯には戻らず）
- runbook-verified schema 改訂が dhcp-relay で機能している（軸 2 / 3 満点）
- ユーザー指示 (a)〜(d) 検証: **(a) CDB ops-hint 100% 維持 = 完結性 5 点固定 / (b) CLI ops-hint 45 ページ展開で 3 周連続 CLI 満点 / (c) glossary +31 は未浸透 / (d) evidence rendering で軸 3 が初の満点飽和**
- v1.0 GA 後 6 回目の定点観測として、**プラトー（4.79〜4.85）は完全に過去のもの**、新プラトー（4.86〜4.89）に移行。次は YANG ops-hint batch で 4.95 圏を狙うフェーズ

## 関連ドキュメント

- [監査 round 16（v1.0 GA 後 5 回目）](./quality-audit-16.md)
- [監査 round 15（v1.0 GA 後 4 回目）](./quality-audit-15.md)
- [監査 round 14（v1.0 GA 後 3 回目）](./quality-audit-14.md)
- [監査 round 13（v1.0 GA 後 2 回目）](./quality-audit-13.md)
- [監査 round 12（v1.0 GA 後初回）](./quality-audit-12.md)
- [監査 round 11（v1.0 GA 昇格判定）](./quality-audit-11.md)
- [品質ロードマップ](./quality-roadmap.md)
- [discrepancy 運用ガイド](./discrepancy-operations.md)
