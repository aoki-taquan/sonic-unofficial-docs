---
title: 品質改善サンプリング監査（round 18、v1.0 GA 後の 7 回目定点観測）
area: meta
verification: meta
last_verified: 2026-05-11
sources: []
---

# 品質改善サンプリング監査（round 18、v1.0 GA 後の 7 回目定点観測）

- 実施日: 2026-05-11
- 対象: round 17 (4.86 / 5) 後の現行 main
- サンプル数: **12 件**（`find docs -name '*.md' | shuf -n 12` による完全ランダム）
- 評価軸: ユーザー指示の **6 軸 5 点満点**（構成 / 裏取り / 引用 / 関連性 / 可読性 / 完結性）
- 評価者: AI（Claude / batch #6、worktree 隔離）

## 0. round 12〜17 → round 18 の比較条件

round 17 と同じ「6 軸 5 点満点・完全ランダム抽出・章扉 N/A 化（`page_kind: chapter-index` の軸 2 / 6 を N/A）」を踏襲。round 18 の注目点はユーザー指示どおり、**(a) YANG ops-hint batch（50 ページ追加）が完結性軸の天井を抜いたか**、**(b) CDB mermaid 97.5% 化が可読性軸 5 飽和を取ったか**、**(c) CLI mermaid 71% で残る空白が顕在化するか**、**(d) runbook-verified 27 件への拡大が裏取り / 引用軸を底上げしたか** の 4 点。サンプル中に CLI 2 / runbook 1 / HLD 系 6 / 章扉系 2 / meta 1 と HLD 系が再び多めの混入になり、テンプレ batch の **横展開フェーズが新規 HLD ページにも届いているか** を検証する好機。

| Round | 5 点換算 | 軸数・備考 |
|-------|----------|------------|
| 11 | 4.93 | 10 軸、v1.0 GA 昇格判定 GO |
| 12 | 4.83 | 6 軸、ランダム 12 件 |
| 13 | 4.79 | 6 軸、ランダム 12 件（chapter-index 1 混入）|
| 14 | 4.85 | 6 軸、ランダム 12 件（chapter-index 2 件は緩和評価）|
| 15 | 4.83 | 6 軸、ランダム 12 件（章扉 / カテゴリ扉 2 件は N/A 化、hld-only 1 件回帰）|
| 16 | 4.89 | 6 軸、ランダム 12 件（CDB ops-hint batch 効果でプラトー突破）|
| 17 | 4.86 | 6 軸、ランダム 12 件（章扉 1 件 N/A 化、YANG 3 件 + discrepancy-found 2 件混入）|
| **18** | **4.88** | **6 軸、ランダム 12 件（章扉系 2 件は N/A 化、HLD 系 6 件混入）** |

**改善観測**: round 17 (4.86) → round 18 (4.88) で **+0.02** の微増。新プラトー（4.86〜4.89）帯の維持を確認、4.95 圏には未到達。YANG ops-hint batch（+50 ページ）はサンプル中の YANG Ref 混入が 0 件のため直接観測できなかったが、**runbook-verified 拡大の効果は vlan-tagging で観測**（軸 2 / 3 満点）。HLD 系 6 件のうち 4 件が 4.83 以上で、HLD への横展開も進展。

## 1. サンプル一覧（ランダム 12 件）

| # | パス | area | 行数 | verification |
|---|------|------|------|--------------|
| 1 | `docs/acl-qos/enhancements-on-show-acl-commands.md` | acl-qos (HLD) | 179 | code-verified |
| 2 | `docs/reference/runbooks/vlan-tagging.md` | reference (runbook) | 118 | runbook-verified |
| 3 | `docs/reference/cli/config-vrf.md` | reference (CLI) | 202 | code-verified |
| 4 | `docs/system/sonic-container-hardening.md` | system (HLD) | 105 | code-verified |
| 5 | `docs/topics/10-gnmi-openconfig/internals.md` | topics (内部実装) | 132 | meta |
| 6 | `docs/architecture/smart-switch-database-design.md` | architecture (HLD) | 213 | code-verified |
| 7 | `docs/reference/cli/config-acl.md` | reference (CLI) | 224 | code-verified |
| 8 | `docs/internals/support-redis-databases-in-multiple-namespaces.md` | internals (HLD) | 268 | code-verified |
| 9 | `docs/topics/22-reference-index/config-db-index.md` | topics（横断索引 / N/A 化）| 126 | meta |
| 10 | `docs/reference/verification/index.md` | reference（運用方針 / N/A 化）| 76 | meta |
| 11 | `docs/management/save-on-set-hld.md` | management (HLD) | 209 | code-verified |
| 12 | `docs/routing/sonic-fine-grained-ecmp.md` | routing (HLD) | 207 | code-verified |

カテゴリ内訳: Reference 系 **4/12（CLI 2 + runbook 1 + verification index 1）**、HLD 系 6、章扉 / 横断索引 2（うち 1 は meta）、topics 内部実装 1。**HLD 系 6/12 はバッチ書庫の横展開到達度を測る好サンプル**。YANG Ref が 0 件混入のため、YANG ops-hint batch 50 ページの効果は次回 round 19 以降で観測予定。

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

`page_kind: chapter-index` 相当（横断索引 / 運用方針扉）は軸 2 / 6 を **N/A**（残り 4 軸の単純平均）。

## 3. 評価結果

| # | ページ | 構成 | 裏取り | 引用 | 関連性 | 可読性 | 完結性 | 平均 |
|---|--------|------|--------|------|--------|--------|--------|------|
| 1 | enhancements-on-show-acl-commands | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 2 | vlan-tagging (runbook) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 3 | config-vrf (CLI) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 4 | sonic-container-hardening | 5 | 4 | 4 | 4 | 4 | 4 | **4.17** |
| 5 | gnmi-openconfig/internals (topics) | 5 | 4 | 4 | 5 | 5 | 5 | **4.67** |
| 6 | smart-switch-database-design | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 7 | config-acl (CLI) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 8 | support-redis-databases-multi-ns | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 9 | config-db-index (横断索引, N/A) | 5 | N/A | 5 | 5 | 5 | N/A | **5.00** |
| 10 | verification/index (運用方針, N/A) | 5 | N/A | 5 | 5 | 5 | N/A | **5.00** |
| 11 | save-on-set-hld | 5 | 4 | 5 | 5 | 5 | 5 | **4.83** |
| 12 | sonic-fine-grained-ecmp | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |

### 軸別平均（N/A は分母から除外）

| 軸 | 平均 | 備考 |
|----|------|------|
| 1. 構成 | **5.00** | 12 件全件で章立て・冒頭サマリ・末尾 references 揃う（**5 周連続飽和**）|
| 2. 裏取り | **4.80** (10 件) | container-hardening が `code-verified` を名乗りつつ警告で「未確認」記載 → 4、save-on-set も同様 → 4 |
| 3. 引用 | **4.83** | container-hardening / gnmi-openconfig internals (topics) で個別 evidence マーカー薄 → 4。他 10 件は満点 |
| 4. 関連性 | **4.92** | container-hardening が related 全空（CONFIG_DB / CLI / YANG 全て []）→ 4。他全件満点 |
| 5. 可読性 | **4.92** | container-hardening が mermaid 1 個のみで本文 mermaid 不足 → 4。他全件満点（glossary back-link batch の効果が浸透開始）|
| 6. 完結性 | **4.80** (10 件) | container-hardening / save-on-set が `code-verified` 自称ながら実コード裏取り未済の自己申告 → 4。他は全件満点 |
| **総平均** | **4.88 / 5** | 12 件、平均（N/A 除外）|

round 17 (4.86) → round 18 (4.88) で **+0.02**。**主因は container-hardening 1 件が広く減点**（軸 2 / 3 / 4 / 5 / 6 で 4 点固定、平均 4.17）。これが無ければ全体は 4.95 圏に届く水準。**HLD 6 件中 5 件が満点〜4.83 帯**で、テンプレ batch の HLD 横展開は順調と確認。

### ユーザー指示 (a)〜(d) の検証結果

- **(a) YANG ops-hint batch (+50 ページ)**: サンプルに YANG Ref が 0 件混入のため直接観測不可。**round 19 以降に持ち越し**。ただし round 17 で天井問題が定量化された YANG Ref の母集団が 50 ページ拡張されたため、次回ランダム抽出で YANG 混入時の軸 5 / 6 改善幅を測定する
- **(b) CDB mermaid 97.5%**: サンプルに CDB ref 0 件混入のため直接観測不可。横断索引 (config-db-index) のみ混入し満点。**round 19 以降に持ち越し**
- **(c) CLI mermaid 71%**: サンプル CLI 2 件（config-vrf 3 mermaid / config-acl 3 mermaid）の **2/2 で mermaid 入り** = 軸 5 満点。**残り 29% の mermaid 空白 CLI ページは本サンプルに引き当たらず**、潜在的な減点リスクは未顕在化。次回 CLI ヒット時に検証継続
- **(d) runbook-verified 27 件拡大**: 本サンプル runbook 1 件（vlan-tagging）が `runbook-verified` で **軸 2 / 3 / 6 全て満点**。**round 17 の dhcp-relay に続き 2 周連続で runbook-verified が監査満点を取った**。schema 改訂と sources pin の効果は確実に出ている

## 4. 個別所感

### 完全満点 7 件（#1, #2, #3, #6, #7, #8, #12、加えて N/A 換算で #9 #10）

実点満点 **7 件（過去最高、round 16 / 17 = 5 件を 2 件上回る）** + N/A 算定 2 件 = 9/12。

- **enhancements-on-show-acl-commands**: STATE_DB.ACL_TABLE_TABLE / ACL_RULE_TABLE の status エンコード、旧フロー vs 新フロー比較、CLI 出力例、制限・干渉・トラブルシュート全節完備
- **vlan-tagging (runbook)**: `systemctl restart swss` の 5〜30 秒中断警告 + backup 手順 + ロールバック手順という **runbook 黄金パターンの新規例**。symptom → cause → 切り分け → 対処の流れが完璧
- **config-vrf (CLI)**: 3 mermaid 入り、VRF / MGMT_VRF_CONFIG / VXLAN_TUNNEL_MAP / SYSLOG_SERVER の 4 CDB 連携を明示、L3 VNI マッピング解説まで網羅
- **smart-switch-database-design**: `has_per_dpu_scope` の sonic-yang-models / featured / database_global.json.j2 / docker-database-init.sh の 4 経路裏取り、mermaid 2 個、Smart Switch の DPU overlay DB を完結記述
- **config-acl (CLI)**: 3 mermaid + **ops-hint マーカー 2 個入り**（CLI ops-hint batch の効果実証）、acl-loader 起動経路、JSON 一括ロード設計、CLI フラグ追加不可の制約を明示
- **support-redis-databases-multi-ns**: 268 行の大型ページで `dbconnector.h:L44-49, L107, L149/L151` および cpp:L225 の精密 line pinning、`database_global.json` 構造、include directive、per-namespace 集約形式まで完結記述。**HLD 系で過去最高水準の裏取り**
- **sonic-fine-grained-ecmp**: 10 セクション構成、match_mode 3 種比較、bank 動作の図解、warm boot、SAI インタフェースまで完結。FG_NHG / FG_NHG_PREFIX / FG_NHG_MEMBER の 3 table 連携を明示

### 高評価（4.83）1 件（#11）

- **save-on-set-hld**: `code-verified` 自称ながら警告セクションに「sonic-gnmi の Set ハンドラ / sonic-host-services の DBUS / telemetry.sh 起動スクリプトの実コード裏取りは未済」と自己申告 → 軸 2 = 4 点。他軸満点で構成は出色

### 中評価（4.67）1 件（#5）

- **gnmi-openconfig/internals (topics 内部実装)**: topics 配下の内部実装解説で sources が空 (`sources: []`) のため軸 2 = 4、個別 evidence マーカー薄 → 軸 3 = 4。ただし mermaid 1 個入り、GET / SET / SUBSCRIBE の 3 経路解説は出色

### 低評価（4.17）1 件（#4）

- **sonic-container-hardening**: `code-verified` 自称ながら warning ボックスに **「各 docker の現行 supervisor / docker_image_ctl テンプレートでの cap-drop / read-only 適用状況は未確認」** と自己申告。HLD ベースで進めると明示しており、Verifier 注記もあるが、**軸 2 / 3 / 4 / 5 / 6 で広く 4 点減点**：
  - 軸 2: 自称 code-verified なのに本文で未確認を認めている → 4
  - 軸 3: 個別 evidence マーカーが薄い → 4
  - 軸 4: related の config_db / cli / yang が全て空 → 4
  - 軸 5: mermaid 1 個のみで本文の図解が不足 → 4
  - 軸 6: 自己申告で実装裏取り未済 → 4

**本ページは構造的に「verification を `code-verified` から `hld-only` または `discrepancy-found` に降格すべき候補」**。次回 batch の Verifier で再評価が必要。

## 5. spot check（4 件、軸 3 引用の正確性裏取り）

| # | ページ | チェック対象 | 結果 |
|---|--------|--------------|------|
| S1 | support-redis-databases-multi-ns | `sonic-swss-common/common/dbconnector.h:L44-49, L107, L149/L151` | OK |
| S2 | smart-switch-database-design | `sonic-yang-models/yang-models/sonic-feature.yang:85` / `featured:86,415` | OK |
| S3 | vlan-tagging (runbook) | `sonic-swss @ 4305596 cfgmgr/vlanmgr.cpp` / `sonic-utilities @ 39732bceb config/vlan.py` | OK |
| S4 | config-vrf | `sonic-utilities @ 39732bceb config/main.py` の click group | OK |

4/4 構造的に整合。引用品質は **round 17 と同水準（過去最高水準を維持）**、evidence rendering 改修の効果は持続。

## 6. round 17 との差分

| 観点 | round 17 | round 18 | 差分 |
|------|---------|---------|------|
| 軸スキーム | 6 軸 5 点 + 章扉 N/A 化 | 6 軸 5 点 + 章扉 N/A 化 | KEEP |
| 平均 | 4.86 | **4.88** | +0.02（新プラトー帯維持）|
| サンプリング | 完全ランダム | 完全ランダム | KEEP |
| 満点件数（実点） | 5/12 | **7/12** | +2（過去最高）|
| Reference 系の比率 | 6/12 | 4/12 | -2（CDB / YANG が引き当たらず）|
| HLD 系混入 | 4/12 | **6/12** | +2（横展開度の検証好機）|
| YANG Ref 混入 | 3/12 | 0/12 | -3（YANG ops-hint batch 効果は次回観測）|
| runbook-verified 混入 | 1/12 (dhcp-relay) | 1/12 (vlan-tagging) | KEEP（2 周連続で監査満点）|
| 軸 2 裏取り | 5.00 | 4.80 | -0.20（container-hardening / save-on-set の自己申告減点）|
| 軸 3 引用 | 5.00 | 4.83 | -0.17（container-hardening / topics internals）|
| 軸 4 関連性 | 4.92 | 4.92 | KEEP |
| 軸 5 可読性 | 4.75 | **4.92** | **+0.17**（glossary back-link batch + CLI / CDB mermaid 拡張の波及）|
| 軸 6 完結性 | 4.64 | **4.80** | **+0.16**（YANG 0 件混入と HLD への ops-hint 横展開）|
| spot check | 4/4 | 4/4 | KEEP |

**重要観測 1（軸 5 / 6 のリバウンド）**: 軸 5 が 4.75 → 4.92 で **+0.17**、軸 6 が 4.64 → 4.80 で **+0.16** と、round 17 で停滞・天井露呈していた 2 軸が同時にリバウンドした。原因は **(a) YANG Ref 0 件混入による天井問題の不顕在化、(b) glossary back-link batch / CDB mermaid 97.5% の波及、(c) HLD 系へのテンプレ横展開（save-on-set / fine-grained-ecmp 等で章立てが整備）**。**ただしリバウンドの一部はサンプルバイアスなので、round 19 で YANG が引き当たれば再評価必要**

**重要観測 2（自己申告 code-verified の減点 2 件）**: container-hardening / save-on-set の 2 件が **`code-verified` を名乗りつつ本文で未済を申告**するという構造的不整合を起こしている。これは round 14 / 15 時点でも観測されており、**verification ステータスの自動降格 lint** が未実装の課題が再露呈。container-hardening は降格 (`hld-only`) が妥当、save-on-set は実装読みを完了して継続が妥当

**重要観測 3（runbook-verified の安定性実証）**: round 17 (dhcp-relay) + round 18 (vlan-tagging) と 2 周連続で runbook 1 件混入 → 監査満点。**runbook-verified schema は安定運用フェーズに入った**と判定可能。残 25 件の runbook が同水準なら、軸 2 / 3 / 6 のベースラインを 4.95+ に押し上げる強い要因になる

## 7. 次回（round 19）改善すべき 3 つ

round 17 改善 1（YANG ops-hint batch）、2（discrepancy-found 専用軸 6）、3（glossary back-link batch）の到達状況:

- 1: **+50 ページ YANG ops-hint 追加で実施済み**。本サンプル未混入のため次回観測待ち
- 2: 未着手、`meta/quality-roadmap.md` への追記課題が残る
- 3: **glossary back-link batch は浸透開始**（軸 5 = 4.92 にリバウンド）。継続拡大が望ましい

### 改善 1: verification ステータス自動降格 lint の導入（最優先）

round 18 で最大の発見は **container-hardening / save-on-set のような「自称 `code-verified` ながら本文で未済を申告」する構造的不整合**。これは round 14 / 15 でも観測された反復問題で、**人手 Verifier に依存している限り再発する**。対策: `scripts/lint_verification.py` を新設し、(a) frontmatter `verification: code-verified` のページで本文に `未確認 | 未済 | HLD のみ | 裏取りは未済` 等のフレーズがある場合に **warning を発する**、(b) `mkdocs build --strict` で fail させる。対象は全 ~500 ページ、半自動で実行可能。本 lint 1 つで監査スコアの **構造的減点を解消**（round 18 の container-hardening / save-on-set が修正されれば総平均 4.88 → 4.95 圏）

### 改善 2: container-hardening / save-on-set 等の自称 code-verified 個別 Verifier batch

改善 1 の lint 実装と並走で、**現時点で既に該当している ~10 件**（container-hardening / save-on-set 等）を Verifier batch で個別精査し、`code-verified` を維持できるなら本文 warning を削除、できないなら `hld-only` に降格、または `discrepancy-found` に転換する。`grep -rn "未確認\|未済\|裏取りは未済" docs/` で対象を機械抽出可能

### 改善 3: 大型 HLD の章単位分割継続（章扉サブカテゴリ化）

本監査で `support-redis-databases-multi-ns` (268 行) / `config-acl` (224 行) / `smart-switch-database-design` (213 行) など **大型ページが軒並み満点**を取った。これは「大型 = 内容量が monitor 値を満たす」効果。一方で **MCLAG / DASH / EVPN-VXLAN / SmartSwitch HA 等の超大型 HLD は単一ページのまま**。これらを章単位（200〜250 行 × 3〜5 ページ）に分割すれば、**完結性軸を保ちつつページ単位の評価点を上げられる**（round 14 で MCLAG 分割を試行した前例あり）。next batch で残り 4〜6 大型 HLD を分割する

## 8. 結論

- ランダム抽出 12 件、6 軸 5 点満点で **平均 4.88 / 5（97.6%）**
- 完全満点 **7/12（実点、過去最高） + 2/12（N/A 算定）= 9/12**
- 軸 1（構成）が **5 周連続 5.00 飽和**、軸 5（可読性）が 4.75 → 4.92 で **+0.17 リバウンド**、軸 6（完結性）も 4.64 → 4.80 で **+0.16 リバウンド**
- 軸 2 / 3 / 4 / 6 で container-hardening 1 件が **5 軸減点の主因**。verification ステータス自動降格 lint が未実装の課題が再露呈
- round 17 (4.86) から +0.02 で **新プラトー帯（4.86〜4.89）を 3 周連続で維持**
- ユーザー指示 (a)〜(d) 検証: **(a) YANG ops-hint batch は次回観測待ち / (b) CDB mermaid 97.5% も次回観測待ち / (c) CLI mermaid 2/2 = 軸 5 満点（残 29% 空白は未顕在化）/ (d) runbook-verified 拡大は 2 周連続で監査満点を実証**
- v1.0 GA 後 7 回目の定点観測として、**新プラトー（4.86〜4.89）は完全に定着**、次は verification lint で 4.95 圏を狙うフェーズ

## 関連ドキュメント

- [監査 round 17（v1.0 GA 後 6 回目）](./quality-audit-17.md)
- [監査 round 16（v1.0 GA 後 5 回目）](./quality-audit-16.md)
- [監査 round 15（v1.0 GA 後 4 回目）](./quality-audit-15.md)
- [監査 round 14（v1.0 GA 後 3 回目）](./quality-audit-14.md)
- [監査 round 13（v1.0 GA 後 2 回目）](./quality-audit-13.md)
- [監査 round 12（v1.0 GA 後初回）](./quality-audit-12.md)
- [監査 round 11（v1.0 GA 昇格判定）](./quality-audit-11.md)
- [品質ロードマップ](./quality-roadmap.md)
- [discrepancy 運用ガイド](./discrepancy-operations.md)
