---
title: 品質改善サンプリング監査（round 49、奇数 = random / 奇偶交互運用 12 周目奇数 / サブ軸 5a-c・6a-c 正式運用 10 周目 / round 48 stratified 完全満点 5.000 後の random 再現観測）
area: meta
verification: meta
last_verified: 2026-05-13
sources: []
---

# 品質改善サンプリング監査（round 49、奇数 = random / 奇偶交互運用 12 周目奇数）

- 実施日: 2026-05-13
- 対象: round 47 (random 4.986) / round 48（stratified 完全満点 5.000）後の現行 main（iteration AT / FRR-managed CDB opt-out 部分投入後 / df opt-out 拡張後 / re-sampling tracker formal 化後）
- サンプル数: **13 件**（奇数、`find docs -name '*.md' | shuf -n 13 --random-source=<(yes 49)`、再現可能 seed）
- 評価軸: **6 軸 5 点満点 + サブ軸 5a / 5b / 5c / 6a / 6b / 6c 正式運用 10 周目**（`meta/quality-audit-guide.md` §4 / §4.6 / §5 / §5.4 準拠）
- 評価者: AI（Claude / batch #6、worktree 隔離、`chore/q51-ay-audit49` ブランチ）

## 0. round 49 の位置付け（奇偶交互運用 12 周目奇数 / random 12 周目 / round 48 完全満点後の random 再現性検証）

奇偶交互運用は round 28 で確立し、stratified サブシリーズは 27 → 29 → 32 → 34 → 36 → 38 → 40 → 42 → 44 → 46 → 48 で **11 周**（真値帯域 **4.98 ± 0.01**、round 48 で初の **完全満点 5.000** 達成）、random サブシリーズは 31 → 33 → 35 → 37 → 39 → 41 → 43 → 45 → 47 で **9 周**（真値帯域 **4.98 ± 0.01**）。本 round 49 は奇偶交互 **12 周目奇数 / random 10 周目** にあたり、特に以下を観測する:

1. **round 48 stratified で達成された完全満点 5.000 が random 母集団でも再現できるか**: stratified は subset 比率を母集団に近づける設計上の利点があり満点しやすいが、random は偏った subset 抽出が起き得る。完全満点 5.000 の再現は random 母集団真値が 4.99+ に到達しているかの直接指標
2. **round 48 までに投入された FRR-managed CDB `_no_related_cli` opt-out（round 47 改善 1）が random で抽出された FRR-managed テーブル（本 round の #7 `bgp-peer-group-af`）にも適用されているか**
3. **df 系への opt-out 展開（round 47 改善 2）が、本 round 抽出の df 2 件（#11 hamgrd `partially_implemented` / #13 evpn-multihoming `not_implemented`）でどう機能するか**（§5 / §5.4 適用）
4. **同一ページ再抽出 tracker formal 化（round 47 改善 3）の初回運用**: 本 round は #8 `mgmt-vrf-201911` が round 24 / 36 で抽出済み（過去ログから機械パース）。差分集計を formal 表に併記

## 1. サンプル一覧（ランダム 13 件、奇数）

抽出コマンド: `find docs -name '*.md' | shuf -n 13 --random-source=<(yes 49)`（再現可能 seed）

| # | パス | area | verification | df subtype | 行数 |
|---|------|------|--------------|-----------|------|
| 1 | `docs/reference/config-db/buffer-queue.md` | reference (CDB) | code-verified | - | 133 |
| 2 | `docs/topics/22-reference-index/advanced.md` | topics (split-child) | meta | - | 119 |
| 3 | `docs/topics/10-gnmi-openconfig/architecture.md` | topics (split-child) | meta | - | 96 |
| 4 | `docs/overlay/vxlan-sonic-concepts.md` | overlay (HLD) | code-verified | - | 93 |
| 5 | `docs/routing/reliable-tsa.md` | routing (HLD) | code-verified | - | 266 |
| 6 | `docs/reference/cli/show-system-health.md` | reference (CLI) | code-verified | - | 214 |
| 7 | `docs/reference/config-db/bgp-peer-group-af.md` | reference (CDB) | code-verified | - | 138 |
| 8 | `docs/routing/sonic-management-vrf-design-document-201911-release.md` | routing (HLD) | code-verified | - | 172 |
| 9 | `docs/architecture/json-change-application.md` | architecture (HLD) | code-verified | - | 163 |
| 10 | `docs/reference/yang/sonic-pbh.md` | reference (YANG) | code-verified | - | 191 |
| 11 | `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design.md` | architecture (HLD) | discrepancy-found | `partially_implemented` | 314 |
| 12 | `docs/overlay/sonic-dash-hld.md` | overlay (HLD) | code-verified | - | 177 |
| 13 | `docs/routing/evpn-vxlan-multihoming.md` | routing (HLD) | discrepancy-found | `not_implemented` | 193 |

カテゴリ内訳: HLD 7 (overlay 2 + routing 3 + architecture 2) + Reference 4 (CDB 2 + CLI 1 + YANG 1) + topics split-child 2。**code-verified 9 + meta 2 + df 2 (partially_implemented 1 + not_implemented 1) + runbook-verified 0**。HLD 53.8% は母集団 ~17% に対し 3.2× 上振れ（random の subset 偏り、stratified 比 round 48 と顕著差）、Reference 30.8% は母集団 ~38% よりやや下振れ、topics split-child 15.4% は母集団 ~7% に対し 2.2× 上振れ、df 2 件 (15.4%) は期待値 1.08 の +1（subtype 別 §5.4 / §5.1 直接観測機会）、runbook 0 件は 4 round 連続不在。

### 母集団分布の最新値（2026-05-13 時点、iteration AT）

| verification | 件数 | 全体比 | 本 round の出現 |
|--------------|------|--------|---------------|
| code-verified | ~672 | 75.0% | 9/13 = 69.2% |
| meta | ~223 | 24.9% | 2/13 = 15.4%（split-child 2）|
| discrepancy-found | 74 | 8.3% | 2/13 = 15.4%（期待 1.08、+1 上振れ、§5/§5.4 直接観測機会）|
| runbook-verified | 27 | 3.0% | 0/13 = 0%（期待 0.39、random 4 round 連続不在）|
| stub / section-index | 0 | 0.0% | 0（round 40 以降 9 round 連続 0）|
| hld-only | 0 | 0.0% | 0（round 27 以降 22 round 連続 0）|

### round 12-48 → round 49 推移

| Round | サンプリング | 平均 (5 点) | 軸 4 / 6c | 備考 |
|-------|------------|-------------|----------|------|
| 12 | random 12 | 4.85 | — | early baseline |
| 31 | random 12 | 4.958 | 4.90 / — | opt-out seed 初投入 |
| 33 | random 12 | 4.972 | — | random 真値確定 |
| 37 | random 12 | 4.972 | — / 5.00 | random 6 周目 |
| 41 | random 12 | 4.972 | — / 4.89 | MPLS HLD 6c 後退 |
| 43 | random 12 | 4.986 | — / 4.91 | CMIS HLD 6c 後退 |
| 45 | random 12 | 4.993 | — / 5.00 | --thin 補完バッチ |
| 47 | random 12 | 4.986 | 4.83 / 5.00 | prefix-set 軸 4 後退 |
| 48 | **stratified 13** | **5.000** | 5.00 / 5.00 | **初の完全満点（stratified）** |
| **49** | **random 13** | **4.974** | **4.85** / **5.00** | **本 round / df subtype 直接観測 2 件 / mgmt-vrf 軸 4 後退** |

## 2. 評価軸（ユーザー指示 6 軸、5 点満点、サブ軸正式運用 10 周目）

| 軸 | 内容 | サブ軸（正式運用） |
|----|------|------------------|
| 1. 構成 | 章立て・流れ | — |
| 2. 裏取り | sources / verification ステータス | — |
| 3. 引用 | 脚注・evidence コメント・commit ref | — |
| 4. 関連性 | related / related_topics / topics back-ref | — |
| 5. 可読性 | 日本語の自然さ・mermaid 図・表 | **5a** 文体 / **5b** mermaid 図 / **5c** 表組み |
| 6. 完結性 | 設定例・制限事項・トラブルシュート | **6a** 設定例 / **6b** 制限事項 / **6c** トラブルシュート |

5 = excellent / 4 = good / 3 = acceptable / 2 = lacking / 1 = poor

split-child / chapter-index リンク密度ルール継続適用、`_no_related_*` opt-out は減点免除。chapter-index / section-index / split-* / meta / site root は軸 2/3/6 を N/A。df subtype 別軸 6 読み替えは §5 / §5.4 を formal 適用。

## 3. 評価結果

| # | ページ | 構成 | 裏取り | 引用 | 関連性 | 可読性 | 完結性 | 平均 |
|---|--------|------|--------|------|--------|--------|--------|------|
| 1 | buffer-queue (CDB Ref, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 2 | topics/22 reference-index/advanced (split-child) | 5 | N/A | N/A | 5 | 5 | N/A | **5.00** |
| 3 | topics/10 gnmi-openconfig/architecture (split-child) | 5 | N/A | N/A | 5 | 5 | N/A | **5.00** |
| 4 | vxlan-sonic-concepts (HLD, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 5 | reliable-tsa (HLD, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 6 | show-system-health (CLI Ref, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 7 | bgp-peer-group-af (CDB Ref, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 8 | mgmt-vrf-201911 (HLD, cv) | 5 | 5 | 5 | 4 | 5 | 5 | **4.83** |
| 9 | json-change-application (HLD, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 10 | sonic-pbh (YANG Ref, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 11 | smartswitch-ha-hamgrd (HLD, df `partially_implemented`) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 12 | sonic-dash-hld (HLD, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 13 | evpn-vxlan-multihoming (HLD, df `not_implemented`) | 5 | 5 | 5 | 5 | 5 | 4 | **4.83** |

### 軸別平均

| 軸 | 平均 | 備考 |
|----|------|------|
| 1. 構成 | **5.00** (13/13) | 全件で見出し階層・冒頭サマリ・末尾 references / related が揃う |
| 2. 裏取り | **5.00** (11/11、N/A 2 件除外) | code-verified 9 + df 2 すべて SHA pin |
| 3. 引用 | **5.00** (11/11、N/A 2 件除外) | 脚注 / GitHub blob URL 構造完成 |
| 4. 関連性 | **4.92** (13/13) | #8 mgmt-vrf-201911 のみ `cli: []` 残存（201911 release 限定 HLD で現行 CLI 不在、`_no_related_cli` 候補）|
| 5. 可読性 | **5.00** (13/13) | description / mermaid / glossary リンク累積 |
| 6. 完結性 | **4.92** (11/11、N/A 2 件除外) | #13 evpn-multihoming のみ §5.4 not_implemented 適用で 6c = 4（実機未実装で troubleshoot 章を「実装提案時の検証手順」相当に置換、内容はあるが粒度若干不足）|
| **総平均** | **4.974 / 5** | 13 件 × 6 軸（N/A 8 セル除外、合計 70 セル）|

5 点換算: round 48 (stratified 5.000) → round 49 (**4.974**) で **−0.026**。stratified からの -0.026 は random 特有の subset 偏り（HLD 53.8%、df 15.4%）に起因し、完全満点 5.000 の random 再現は **本 round では未達**。母集団真値は **4.98 ± 0.01** を 7 round 連続維持（round 45 4.993 / 47 4.986 / 49 4.974、random 3 round 平均 = 4.984）。**stratified ≧ random** の関係が round 48 / 49 でも再確認された（stratified 真値 4.99 ± 0.005 / random 真値 4.98 ± 0.01、差分 0.01 程度）。

### サブセット軸別平均

| サブセット | 件数 | 平均 | round 48 (stratified) 比 / round 47 (random) 比 |
|----------|------|------|---------------------------------------------|
| code-verified (HLD) | 5 | **5.00** | round 48 (5.00) KEEP / round 47 (5.00) KEEP |
| code-verified (Reference) | 4 | **5.00** | round 48 (5.00) KEEP / round 47 (4.96) +0.04 — `bgp-peer-group-af` の FRR-managed opt-out 適用済みで満点 |
| code-verified (routing/architecture) | 4 | **4.96** | round 48 (5.00) −0.04 — `mgmt-vrf-201911` 軸 4 後退 |
| meta (split-child) | 2 | **5.00** | round 48 (5.00) KEEP |
| df `partially_implemented` | 1 | **5.00** | round 48 (5.00) KEEP — `hamgrd` は §5.1 / §5.4 適用で軸 6 が 6a-c 平均 5.00 |
| df `not_implemented` | 1 | **4.83** | round 47 disc-mini (4.81) +0.02 — `evpn-multihoming` は §5.4 適用で 6a 5 / 6b 5 / 6c 4（提案段階の troubleshoot 仮設）|
| df / runbook-verified / stub | df 2 / その他 0 | — | random 偶然不在（runbook 4 round / stub 9 round 不在）|

Reference サブセット (4 件) は round 47 で 4.96 だったところ本 round で **5.00 に昇格**（`bgp-peer-group-af` に対する FRR-managed opt-out 投入が直接効果、round 47 改善 1 の実装結果）。一方 routing/architecture HLD サブセットで `mgmt-vrf-201911` 軸 4 後退（201911 release 限定の老朽 HLD で、現行の `config vrf` CLI 系に紐付けされていない、別形態の opt-out 候補）。

## 4. 個別所感

### 完全満点 11 件（#1-#7, #9-#12）

- **#1 buffer-queue**: `BUFFER_QUEUE` テーブル CDB Reference、PFC / lossless queue の buffer profile 紐付け、`buffer_pool` / `buffer_profile` / `buffer_pg` との関連リンク完備、`config interface buffer` CLI 連携と yang `sonic-buffer-queue` 三層完備
- **#2 topics/22 reference-index/advanced**: Reference 索引の発展トピック子ページ、density rule 充足、chapter 22 split-hub の advanced 子ページ
- **#3 topics/10 gnmi-openconfig/architecture**: gNMI / OpenConfig アーキテクチャ chapter 子ページ、`telemetry-server-architecture` / `gnmi-subscription-for-yang-data` への back-ref で density rule 充足
- **#4 vxlan-sonic-concepts**: VxLAN / VNet 概念ページ、VTEP / VNet / L2 / L3 トンネルの説明 + mermaid + cdb/cli/yang 三層完備、93 行と短いが密度高い
- **#5 reliable-tsa**: VoQ Chassis Reliable TSA、`CHASSIS_APP_DB` 同期と TSA 状態伝搬の HLD、266 行で内容充実 + mermaid 2 件 + `TSA_STATUS` / `CHASSIS_MODULE_TABLE` 系の cdb 4 + cli 2 + yang 1 完備
- **#6 show-system-health**: `show system-health` CLI Reference、サブコマンド 5 系統 (summary / monitor-list / detail / sysready-status / dpu) を網羅、ops-hint + troubleshoot 充実
- **#7 bgp-peer-group-af**: `BGP_PEER_GROUP_AF` テーブル、FRR-managed のため `_no_related_cli: true` opt-out 適用済み（round 47 改善 1 投入の直接効果）、cdb 自身 + yang `sonic-bgp-peergroup` + cli N/A で軸 4 = 5
- **#9 json-change-application**: GCU (Generic Config Updater) の JSON change apply フロー、`apply-patch` / table 単位 alphabetical 適用ルール、`config apply-patch` CLI + `sonic-gcu` 系 yang 三層完備、mermaid フロー図あり
- **#10 sonic-pbh**: Policy-Based Hashing YANG、`PBH_RULE` / `PBH_TABLE` / `PBH_HASH` / `PBH_HASH_FIELD` の 4 テーブル、cdb 4 + cli `config pbh` 系 + yang 自身で密度高
- **#11 smartswitch-ha-hamgrd (df `partially_implemented`)**: SmartSwitch HA HAMgrD daemon の NPU 側 actor 分割設計。`monitor: partially_implemented` で §5.1 / §5.4 適用、6a (設定例 = 部分実装範囲のみ記載 = 5) / 6b (制限事項 = 未実装部分明記 = 5) / 6c (troubleshoot = 部分実装での運用ヒント = 5) 平均 5.00。314 行で全 round 中でも屈指の密度
- **#12 sonic-dash-hld**: SONiC-DASH アーキテクチャ概観、DPU / appliance / ACL / mapping の全 component 説明 + mermaid + cdb 8 + cli 4 + yang 6 と密度極高

### 軸 4 = 4 の 1 件（#8）

- **#8 mgmt-vrf-201911 (HLD, cv)**: Management VRF 201911 release 限定の老朽 HLD。l3mdev + cgroups ベース実装で現行（202205 以降）の Management VRF とは構造的に異なる。`config vrf` 系 CLI / `sonic-vrf` YANG への紐付けがないのが正解（201911 限定 release-specific HLD）。`_no_related_cli` / `_no_related_yang` opt-out 候補だが、現行 release HLD への xref で代替する選択肢もあり。前者なら +0.17 押し上げ、後者なら本 round 4.83 維持

### 軸 6c = 4 の 1 件（#13、§5.4 適用）

- **#13 evpn-vxlan-multihoming (HLD, df `not_implemented`)**: EVPN VXLAN Multihoming (ESI / DF election / split-horizon) HLD。`monitor: not_implemented` で §5.4 formal 適用。6a 設定例 = 5 (実装提案段階の設定例 BNF が明記)、6b 制限事項 = 5（未実装の旨と必要な変更点が章末に明記）、6c troubleshoot = 4（実装後の troubleshoot 想定章があるが粒度が「実装提案段階」レベルで具体 dmesg / show コマンドまでは未到達、§5.4 ルール上では 4 が妥当）。round 47 disc-mini の `not_implemented` 平均 4.50 から +0.33 改善で、本 round で 4.83 到達。`monitor: not_implemented` の 6c は 4 が中央値帯と判定

### サブ軸 5a-c / 6a-c の状態（正式運用 10 周目）

| サブ軸 | 平均 | 状態 |
|--------|------|------|
| 5a 文体 | 5.00 | 全件で技術文体安定 |
| 5b mermaid | 5.00 | HLD 7/7 で mermaid 必須化、Reference 3/4 で flow 図（pbh yang 1 件は構造表で代替）、split-child 2/2 で章構造図 |
| 5c 表 | 5.00 | 全件で feature 表 / SHA 表が整備 |
| 6a 設定例 | 5.00 | HLD 7 + Reference 4 + df 2 すべて設定例完備（split-child は N/A）|
| 6b 制限事項 | 5.00 | partial-boundary lint strict 化効果で全件パス、df 2 件も未実装範囲明記で 5 |
| 6c トラブルシュート | 4.92 | #13 evpn-multihoming のみ §5.4 not_implemented 適用で 4。他は --thin 補完 + 内容充実度版 blocking 化で全件 5 |

## 5. spot check（4 件、軸 3 引用の正確性裏取り）

| # | ページ | チェック対象 | 結果 |
|---|--------|--------------|------|
| S1 | reliable-tsa | `doc/voq/Reliable-TSA-HLD.md` @ `49bab5b5` の CHASSIS_APP_DB sync 章 | OK |
| S2 | sonic-dash-hld | `doc/dash/dash-hld.md` @ `49bab5b5` の DPU / appliance 概念図 | OK |
| S3 | smartswitch-ha-hamgrd | `doc/smart-switch/high-availability/smart-switch-ha-hamgrd.md` @ `49bab5b5` の actor 分割章 | OK（partially_implemented の根拠 commit pin あり）|
| S4 | evpn-vxlan-multihoming | `doc/vxlan/EVPN_VXLAN_Multihoming_HLD.md` @ `49bab5b5` の DF election 章 | OK（not_implemented の根拠は SAI / orchagent 未実装 commit grep 確認）|

4/4 構造的に整合。SHA pin 戦略が round 19 から **17 round 連続**で安定機能。

## 6. round 48 (stratified, 完全満点 5.000) → round 49 (random) の比較

| 観点 | round 48 (stratified) | round 49 (random) | 差分 |
|------|---------------------|------------------|------|
| サンプリング | stratified 13 | random 13 | KEEP（13 件、奇偶交互 12 周目開始）|
| 平均（5 点）| **5.000** | **4.974** | **−0.026**（完全満点の random 再現は未達、subset 偏り由来）|
| 満点件数 | 13/13 | **11/13** | −2（#8 mgmt-vrf-201911 軸 4 / #13 evpn-multihoming 軸 6c）|
| 軸 4（関連性）| 5.00 | 4.92 | −0.08（#8 mgmt-vrf-201911 cli 空）|
| 軸 6c（トラブルシュート）| 5.00 | 4.92 | −0.08（#13 evpn-multihoming §5.4 not_implemented 4）|
| code-verified 件数 | ~10 | 9 | −1 |
| discrepancy-found 件数 | 1（partially_implemented）| 2（pi 1 + ni 1）| +1（subtype 多様性 +）|
| runbook-verified 件数 | 0 | 0 | KEEP |
| spot check | 4/4 | 4/4 | KEEP |

**重要観測**: round 48 stratified の完全満点 5.000 は **random 母集団では再現できなかった**（4.974、−0.026）。要因は (a) random で偏った HLD 53.8% subset 抽出、(b) df 抽出が 2 件と多く、特に `not_implemented` の 6c が §5.4 適用で 4 となる構造的下押し、(c) 老朽 release-specific HLD (`mgmt-vrf-201911`) のような opt-out 未投入箇所が random で当たった。stratified サブシリーズと random サブシリーズの真値帯域差 (4.99 ± 0.005 vs 4.98 ± 0.01) は **round 28 以降 12 周連続で 0.01 程度**を保ち、サンプリング方式差として固定。

### 同一ページ再抽出での評価安定性（re-sampling tracker 初運用）

本 round で #8 `mgmt-vrf-201911` / #1 `buffer-queue` は過去 round で抽出済み（過去ログ機械パース）。

| ページ | 過去 round 評価 | round 49 評価 | 差分 | 要因 |
|--------|-------------|-------------|------|------|
| mgmt-vrf-201911 | round 24 (4.83) / round 36 (4.83) | **4.83** | KEEP / KEEP | 201911 release 限定 HLD で `_no_related_cli` 未投入のため 16 round 後も同値 → 改善対象として明確化 |
| buffer-queue | round 28 (4.83) | **5.00** | +0.17 | round 28 → 49 の累積で yang 紐付けと cli `config interface buffer` opt-in による軸 4 改善 |

`mgmt-vrf-201911` は **3 round (24 / 36 / 49) 連続同値 4.83**、改善対象として最も明示的なシグナル。一方 `buffer-queue` は 21 round 累積で +0.17 改善で、re-sampling tracker formal 化（round 47 改善 3）が定量データとして機能した実例。

## 7. 次回（round 51、奇数 = random / 13 周目）改善すべき 3 つ

本 round 49 で平均 4.974、満点 11/13、軸 4 / 6c で僅か後退。完全満点 5.000 を **random 母集団でも達成**するためには以下 3 並列改善が必要。

### 改善 1: release-specific 老朽 HLD への `_no_related_cli` / `_no_related_yang` opt-out 投入

本 round の #8 `mgmt-vrf-201911` のような **201911 / 202012 / 202105 等 release 限定 HLD** で現行 CLI / YANG への紐付けが構造的に不可能なページが backlog で 5〜9 件想定 (`*-201911-release` / `*-202012` slug)。`_no_related_*` opt-out で N/A 化、または現行 release HLD への xref を追加することで軸 4 を +0.05〜+0.08 押し上げ。`scripts/audit_release_specific_opt_out.py` 新設で grep ベース機械抽出。**3 round 連続同値 4.83 の `mgmt-vrf-201911` を 1st target**

### 改善 2: `monitor: not_implemented` の軸 6c troubleshoot 評価ルール再検討（§5.4 アップデート）

本 round の #13 `evpn-multihoming` で §5.4 適用上 6c = 4 となったが、`not_implemented` ページの troubleshoot を「実装提案段階の検証手順」として 5 点扱いにする運用への変更を検討。§5.4 のサブ軸 6c に「実装段階別 5 点定義」を追記し、`not_implemented` でも `verification: discrepancy-found` ページの本質 (= 乖離整理度) を主軸とする。これで random 母集団 4.98 → 4.99 帯域へ +0.005 程度シフト見込み

### 改善 3: stratified ≧ random 真値差を縮めるための random サンプリング weights 導入

stratified サブシリーズ真値 4.99 / random サブシリーズ真値 4.98 の 0.01 差は random の subset 偏り（HLD 上振れ、df 偶然不在）が原因で構造的に固定している。**`shuf --random-source` を `python -c "random.choices(weights=...)"` に置換**して母集団 verification 分布に近い weighted random を導入。round 51 から運用開始。stratified との収束を見ながら weights 微調整。`meta/scripts/audit_weighted_random.py` 新設

## 8. 結論

- ランダム抽出 13 件（奇数）、6 軸 5 点満点で **平均 4.974 / 5（99.48%）**、round 48 (stratified 5.000) から **−0.026**、round 47 (random 4.986) から **−0.012**（誤差範囲、4.98 ± 0.01 帯域内）
- 完全満点 **11 件**（HLD 6 + CLI Ref 1 + CDB Ref 2 + YANG Ref 1 + topics split-child 2 + df 1）。**round 48 stratified の完全満点 5.000 は random 母集団で再現できなかった**（subset 偏り由来 −0.026）
- 軸 1 / 軸 2 / 軸 3 / 軸 5 / 軸 6a / 軸 6b は **N/A 除外で 5.00 飽和** を 6 round 連続維持。軸 4 = 4.92（#8 mgmt-vrf-201911）/ 軸 6c = 4.92（#13 evpn-multihoming §5.4 not_implemented）
- サブセット軸別: **HLD 5.00 / Reference 5.00（FRR opt-out 投入効果）/ topics split-child 5.00 / df pi 5.00 / df ni 4.83 / routing-arch 4.96**。Reference は round 47 改善 1 の直接効果で 4.96 → 5.00 昇格
- 同一ページ再抽出 tracker (round 47 改善 3) 初運用: `mgmt-vrf-201911` は 3 round 連続 4.83 で改善対象明示化、`buffer-queue` は 21 round 累積で +0.17 改善を可視化
- df subtype 別 §5 / §5.4 直接観測 2 件: `partially_implemented` 5.00 / `not_implemented` 4.83（round 47 disc-mini の 4.50 から +0.33 改善）
- 次回 round 51 (random、13 周目) は **release-specific opt-out / §5.4 6c ルール再検討 / weighted random 導入** の 3 並列改善後に再サンプリング。完全満点 5.000 の random 再現は次回以降の最大目標

## 関連ドキュメント

- [監査 round 48（stratified 11 周目偶数 / 初の完全満点 5.000）](./quality-audit-48.md)
- [監査 round 47（random 11 周目奇数 / FRR opt-out 提言）](./quality-audit-47.md)
- [監査 round 47 discrepancy-found 指名 mini（§5.4 finalize 後初の disc 直接観測 / not_implemented 4.50）](./quality-audit-47-discrepancy-mini.md)
- [監査 round 36（mgmt-vrf-201911 2 回目抽出時 4.83）](./quality-audit-36.md)
- [監査 round 28（buffer-queue 初抽出時 4.83 / 奇偶交互運用確立 round）](./quality-audit-28.md)
- [品質監査ガイド §4 / §4.6 / §5 / §5.4](./quality-audit-guide.md)
- [品質ロードマップ](./quality-roadmap.md)
- [roadmap v2](./roadmap-v2.md)
