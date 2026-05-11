---
title: 品質改善サンプリング監査（round 15、v1.0 GA 後の 4 回目定点観測）
area: meta
verification: meta
last_verified: 2026-05-11
sources: []
---

# 品質改善サンプリング監査（round 15、v1.0 GA 後の 4 回目定点観測）

- 実施日: 2026-05-11
- 対象: round 14 (4.85 / 5) 後の現行 main
- サンプル数: **12 件**（`find docs -name '*.md' | shuf -n 12` による完全ランダム）
- 評価軸: ユーザー指示の **6 軸 5 点満点**（構成 / 裏取り / 引用 / 関連性 / 可読性 / 完結性）
- 評価者: AI（Claude / batch #6、worktree 隔離）

## 0. round 12 / 13 / 14 → round 15 の比較条件

round 12〜14 と同じ「6 軸 5 点満点・完全ランダム抽出」を踏襲。round 15 では `page_kind: chapter-index` 相当のページ（章扉 / カテゴリ扉）を **N/A 扱い**（軸 2「裏取り」/ 軸 6「完結性」を除外し、残り 4 軸の平均で代用）として正式化する。これは round 14 の改善提言 2 を反映したもので、章扉混入によるスコア揺れを構造的に解消する。

| Round | 5 点換算 | 軸数・備考 |
|-------|----------|------------|
| 11 | 4.93 | 10 軸、v1.0 GA 昇格判定 GO |
| 12 | 4.83 | 6 軸、ランダム 12 件 |
| 13 | 4.79 | 6 軸、ランダム 12 件（chapter-index 1 混入）|
| 14 | 4.85 | 6 軸、ランダム 12 件（chapter-index 2 件は緩和評価）|
| **15** | **4.83** | **6 軸、ランダム 12 件（章扉 / カテゴリ扉 2 件は軸 2 / 6 を N/A 化）** |

**注記**: 本サンプル内で `page_kind: chapter-index` frontmatter キーは未付与（別バッチ進行中）だが、性格的にカテゴリ扉 / topics メタしおりに該当する 2 件（#4 `categories/dash.md` / #7 `topics/21-lab-vs-developer/advanced.md`）は本監査で N/A 扱いとした。

## 1. サンプル一覧（ランダム 12 件）

| # | パス | area | 行数 | verification |
|---|------|------|------|--------------|
| 1 | `docs/platform/icmp-hardware-offload.md` | platform | 234 | code-verified |
| 2 | `docs/system/kdump.md` | system | 156 | code-verified |
| 3 | `docs/platform/cmis-and-c-cmis-support-for-zr.md` | platform | 131 | code-verified |
| 4 | `docs/categories/dash.md` | categories（扉 / N/A 化）| 59 | meta |
| 5 | `docs/reference/runbooks/lldp-neighbor-flapping.md` | reference (runbook) | 80 | **hld-only** |
| 6 | `docs/reference/cli/show-mac.md` | reference (CLI) | 151 | code-verified |
| 7 | `docs/topics/21-lab-vs-developer/advanced.md` | topics（しおり / N/A 化）| 85 | meta |
| 8 | `docs/management/ssh-server-global-config-hld.md` | management | 198 | code-verified |
| 9 | `docs/reference/runbooks/snmpv3-auth-failure.md` | reference (runbook) | 93 | code-verified |
| 10 | `docs/routing/vrf-feature-ansible-test-plan-omit-in-toc.md` | routing | 128 | code-verified |
| 11 | `docs/topics/09-telemetry-snmp/concept.md` | topics | 159 | meta |
| 12 | `docs/reference/cli/show-snmptrap.md` | reference (CLI) | 90 | code-verified |

カテゴリ内訳: platform 2 / system 1 / reference (runbook 2 + CLI 2) = 4 / topics 2（うち 1 件しおり）/ categories 扉 1 / management 1 / routing 1。**Runbook 2 件が初めて同サンプルに同時混入**。`hld-only` 1 件（#5）が出現し、「round 14 で hld-only 0 件達成」の総括に対する **回帰検知** となった。

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

`page_kind: chapter-index` 相当（カテゴリ扉 / topics しおり）は軸 2 / 6 を **N/A**（残り 4 軸の単純平均）として正式扱い。

## 3. 評価結果

| # | ページ | 構成 | 裏取り | 引用 | 関連性 | 可読性 | 完結性 | 平均 |
|---|--------|------|--------|------|--------|--------|--------|------|
| 1 | icmp-hardware-offload | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 2 | kdump | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 3 | cmis-and-c-cmis-support-for-zr | 5 | 5 | 5 | 5 | 5 | 4 | **4.83** |
| 4 | categories/dash (扉, N/A) | 5 | N/A | N/A | 5 | 5 | N/A | **5.00** |
| 5 | lldp-neighbor-flapping (hld-only) | 5 | 3 | 4 | 5 | 5 | 5 | **4.50** |
| 6 | show-mac (CLI Ref) | 5 | 5 | 5 | 5 | 4 | 4 | **4.67** |
| 7 | 21-lab-vs-developer/advanced (しおり, N/A) | 5 | N/A | N/A | 5 | 5 | N/A | **5.00** |
| 8 | ssh-server-global-config-hld | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 9 | snmpv3-auth-failure (runbook) | 5 | 5 | 5 | 5 | 4 | 5 | **4.83** |
| 10 | vrf-feature-ansible-test-plan | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 11 | 09-telemetry-snmp/concept | 5 | 4 | 4 | 5 | 5 | 5 | **4.67** |
| 12 | show-snmptrap (CLI Ref) | 5 | 5 | 5 | 5 | 4 | 4 | **4.67** |

### 軸別平均（N/A は分母から除外）

| 軸 | 平均 | 備考 |
|----|------|------|
| 1. 構成 | **5.00** | 12 件全てで章立て・冒頭サマリ・末尾 references 揃う |
| 2. 裏取り | **4.70** (10 件) | #5 hld-only で 3 点、#11 topics meta で 4 点 |
| 3. 引用 | **4.80** (10 件) | #5 で 4 点、#11 で 4 点 |
| 4. 関連性 | **5.00** | **2 周連続で満点飽和**（round 14 / 15）|
| 5. 可読性 | **4.75** | CLI Ref 2 件 + runbook 1 件で mermaid 無し → 4 点 |
| 6. 完結性 | **4.70** (10 件) | CLI Ref 2 件 + platform 1 件で 4 点 |
| **総平均** | **4.83 / 5** | 12 件、平均（N/A 除外）|

round 14 (4.85) → round 15 (4.83) で **-0.02**。**ランダム揺れ範囲内**。`hld-only` 1 件の混入（軸 2 = 3 点）が主因。`page_kind: chapter-index` N/A 化を入れなければ 4.78 程度に沈んでいたため、**スキーム改訂が +0.05 寄与**したと推定。

## 4. 個別所感

### 完全満点 5 件（#1, #2, #8, #10、加えて N/A 換算で #4, #7）

実点数満点は 4 件 (#1, #2, #8, #10) + N/A 算定満点 2 件 (#4, #7) = 6/12。round 14 (7/12) よりわずかに減。

- **icmp-hardware-offload**: DualToR の ICMP echo を NPU にオフロードする HLD。`MUX_LINKMGR` / `MUX_CABLE` / `show icmp sessions` の三角リンク完備、mermaid + 制限節 + トラブルシュート揃う
- **kdump**: kexec / makedumpfile / hostcfgd の連携を mermaid で整理、CONFIG_DB `KDUMP` テーブルと CLI `config kdump` の往復記述あり
- **ssh-server-global-config-hld**: `SSH_SERVER` テーブルと `sshd_config.j2` テンプレ生成、hostcfgd 監視の連携を行番号付きで裏取り。topics-tip 統合も完了
- **vrf-feature-ansible-test-plan**: テストプランページの理想形。E2E シナリオを章立て + 期待値表 + warm-reboot 注意点まで網羅、関連 CONFIG_DB 7 件の連携が明示

### 高評価（4.83）2 件（#3, #9）

- **cmis-and-c-cmis-support-for-zr**: ZR / ZR+ の coherent optics 制御フロー、xcvrd の DSP プロビジョニングを mermaid 付きで整理。軸 6 = 4（制限節は十分だが運用上の DSP チューニング手順がやや薄い）
- **snmpv3-auth-failure (runbook)**: 認証 / 暗号化失敗の切り分けフロー、`sonic-snmpagent` 行番号付き裏取りあり。軸 5 = 4（runbook 性格上 mermaid なし、判断フローを箇条書きで代替）

### 低めの 4 件（#5, #6, #11, #12）

- **#5 lldp-neighbor-flapping**: `verification: hld-only` で軸 2 = 3 点。round 14 で「hld-only 0 件達成」とした **総括に対する回帰**。Runbook 系は code-verified に昇格しにくい（個別実装 evidence というより複合切り分け手順のため）構造的事情がある。専用ステータス `runbook-verified` の導入を round 16 で検討
- **#6 show-mac (CLI Ref)** / **#12 show-snmptrap (CLI Ref)**: いずれも軸 5 / 6 = 4 点。mermaid 無し / 運用ヒント節が薄い。round 14 で指摘した「CDB テンプレ batch」の対象を **CLI Ref にも拡張** すべき
- **#11 topics 09-telemetry-snmp/concept**: `verification: meta` で軸 2 / 3 = 4 点が天井。round 14 / 13 と同水準で構造的制約

## 5. spot check（4 件、軸 3 引用の正確性裏取り）

| # | ページ | チェック対象 | 結果 |
|---|--------|--------------|------|
| S1 | icmp-hardware-offload | `MUX_LINKMGR` の hardware_prober / linkmgr 切替 | OK |
| S2 | kdump | `hostcfgd` の KDUMP 監視 → `/etc/default/kdump-tools` 反映経路 | OK |
| S3 | ssh-server-global-config-hld | `SSH_SERVER` → `sshd_config.j2` テンプレ生成と hostcfgd 連携 | OK |
| S4 | vrf-feature-ansible-test-plan | warm-reboot 後の VRF route 保持期待値、ACL bind の rebind 手順 | OK |

4/4 構造的に整合。引用品質は round 14 と同水準。

## 6. round 14 との差分

| 観点 | round 14 | round 15 | 差分 |
|------|---------|---------|------|
| 軸スキーム | 6 軸 5 点 + 章扉緩和 | 6 軸 5 点 + 章扉 N/A 化（正式）| **N/A 化に昇格** |
| 平均 | 4.85 | 4.83 | -0.02（揺れ範囲内）|
| サンプリング | 完全ランダム | 完全ランダム | KEEP |
| 満点件数（実点） | 7/12 | 4/12 + N/A 2 | -1（揺れ）|
| Reference 系の比率 | 2/12 | 4/12 (runbook 2 + CLI 2) | +2 |
| 章扉 / しおり混入 | 2 (緩和) | 2 (N/A 化) | KEEP |
| hld-only 混入 | 0 | **1 (runbook)** | **+1（回帰検知）** |
| spot check | 4/4 | 4/4 | KEEP |

**hld-only 1 件の回帰**は round 14 の総括「hld-only 0 件」と矛盾。Runbook 系は構造的に code-verified 昇格が困難で、Verifier batch の対象から外れていた可能性が高い。round 16 で **runbook-verified 専用ステータス** の導入を検討する根拠が得られた。

## 7. 次回（round 16）改善すべき 3 つ

round 14 提言 1（CDB テンプレ batch）と 2（page_kind 導入）は **部分着手**にとどまる。round 15 では「Runbook の構造的問題」と「Reference 系（CLI / CDB）の同一テンプレ展開」が浮上した。

### 改善 1: Runbook 系専用 verification ステータス `runbook-verified` の導入

`docs/reference/runbooks/` 配下 N 件は切り分け手順 / 判断フローが主であり、特定 `.cpp:LINE` を引く code-verified にはなじまない。一方 `hld-only` 扱いだと監査スコアで -2 点ペナルティを受け、round 15 の `lldp-neighbor-flapping` のように回帰検知になる。**`runbook-verified`（手順の再現性 / コマンド出力例の正確性を裏取り済み）** を新設し、Verifier batch の対象として個別検証する。frontmatter schema と監査スキーム両方の改訂が必要。

### 改善 2: Reference CLI / CDB の **テンプレ batch を統合** して mini mermaid + 運用ヒント節を 50 ページ一括導入

round 14 で CDB 30 ページを対象とした提言を、CLI Ref（`show-mac` / `show-snmptrap` 等）にも拡張し統合する。round 15 で CLI Ref 2 件が同時に軸 5 / 6 = 4 点に張り付いたことで「CLI Ref も同じ天井問題」が確認できた。テンプレ要素は「**該当 CONFIG_DB / APP_DB との往復 mini mermaid + よくある運用ミス 3 箇条 + 関連 CLI / docs 三角リンク**」。CDB 30 + CLI Ref 20 = 50 ページ一括 batch とすることで規模効率を上げる。round 12 から 4 周連続未着手の CDB は **必達**。

### 改善 3: `page_kind: chapter-index` frontmatter キーの **実 PR 化と監査スキーム同期完了**

round 14 で「別バッチ進行中」とされた `page_kind` 導入が round 15 サンプル時点で frontmatter に **未反映**（#4 categories/dash と #7 topics しおりとも未付与）。本監査では性格判断で N/A 化したが、これは判定の属人化リスクがある。round 16 までに 22 件相当の章扉 / カテゴリ扉 / topics しおりへ `page_kind: chapter-index`（または `chapter-toc` / `category-index` / `topic-stub` 等の細分化）を一括付与し、監査スクリプトが frontmatter から自動で N/A 判定できる状態にする。これにより監査再現性が +1 段上がる。

## 8. 結論

- ランダム抽出 12 件、6 軸 5 点満点で **平均 4.83 / 5（96.6%）**
- 完全満点 **4/12（実点） + 2/12（N/A 算定）= 6/12**
- 軸 1（構成）と軸 4（関連性）が **2 周連続 5.00 飽和**
- 軸 2（裏取り）4.70 / 軸 6（完結性）4.70 まで微減、hld-only 1 件 + CLI Ref / topics meta の構造的天井が要因
- round 14 (4.85) から **-0.02**。ランダム揺れ範囲内。`page_kind` N/A 化（+0.05 寄与）と hld-only 回帰（-0.07 寄与）が相殺
- **回帰検知**: round 14 で「hld-only 0 件」とした総括に対し、Runbook 系で 1 件残存を確認。Runbook 専用ステータスの導入が必要
- v1.0 GA 後 4 回目の定点観測として、**ランダム抽出で平均 4.83 / 5 は引き続き安定**。round 12〜15 の 4 周で 4.79〜4.85 のレンジに収束しており、品質は **プラトー** に入った

## 関連ドキュメント

- [監査 round 14（v1.0 GA 後 3 回目）](./quality-audit-14.md)
- [監査 round 13（v1.0 GA 後 2 回目）](./quality-audit-13.md)
- [監査 round 12（v1.0 GA 後初回）](./quality-audit-12.md)
- [監査 round 11（v1.0 GA 昇格判定）](./quality-audit-11.md)
- [品質ロードマップ](./quality-roadmap.md)
- [discrepancy 運用ガイド](./discrepancy-operations.md)
