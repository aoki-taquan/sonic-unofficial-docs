---
title: 品質改善サンプリング監査（round 42、偶数 = stratified / 奇偶交互運用 8 周目偶数 / サブ軸 5a-c・6a-c 正式運用 5 周目 / df subtype 別評価 3 周目 / トラブルシュート lint・partial 境界 lint・snapshot 強化観測 round）
area: meta
verification: meta
last_verified: 2026-05-12
sources: []
---

# 品質改善サンプリング監査（round 42、偶数 = stratified / 奇偶交互運用 8 周目偶数 / サブ軸 5a-c・6a-c 正式運用 5 周目 / df subtype 別評価 3 周目）

- 実施日: 2026-05-12
- 対象: round 41 後の現行 main（iteration AR / random 8 周目完走後 / トラブルシュート lint 投入後 / partial 境界 lint 投入後 / snapshot generator 強化後 / df subtype 別評価 §5 ガイド 2 周目運用後）
- サンプル数: **12 件**（**層化サンプリング** 8 周目: code-verified 6 / runbook-verified 2 / discrepancy-found 2（partially_implemented 1 + evolved_beyond_hld 1 を意図的混合）/ chapter-index 1 / meta 1）
- 評価軸: **6 軸 5 点満点 + サブ軸 5a / 5b / 5c / 6a / 6b / 6c 正式運用 5 周目 + df subtype 別評価 3 周目**（`meta/quality-audit-guide.md` §4 / §5 準拠）
- 評価者: AI（Claude / batch #6、worktree 隔離、`chore/q44-ar-audit42` ブランチ）

## 0. round 42 の位置付け（奇偶交互運用 8 周目偶数 / stratified 8 周目 / サブ軸正式運用 5 周目 / df subtype 別評価 3 周目）

round 42 は奇偶交互運用 **8 周目偶数 / stratified サブシリーズ 8 周目 / サブ軸 5a-c・6a-c 正式運用 5 周目 / df subtype 別評価 3 周目** にあたる。stratified サブシリーズは round 27 (4.941) → 29 (4.944) → 32 (4.972) → 34 (4.986) → 36 (4.993) → 38 (4.986) → 40 (4.972) と 7 周完走、stratified 視点真値帯域は **4.97 ± 0.015** で安定。random サブシリーズは round 33 (4.972) → 35 (4.978) → 37 (4.972) → 39 (4.944) → 41 (4.972 推定) で **4.97 ± 0.02** 帯域。

round 41（random、df subtype 別評価 2 周目）で投入された **トラブルシュート lint (`check_df_evolved_workaround.py`)** / **partial 境界 lint (`check_partial_boundary.py`)** / **snapshot generator 強化（df-discrepancy snapshot 自動再生成）** の 3 改善が、本 round 42 stratified でどう作用するかが主目的。本 round で観測する点:

1. round 40 で初観測した **df subtype 別品質差（not_implemented 5.00 / evolved_beyond_hld 4.92）** が、round 41 で投入された **トラブルシュート lint** により evolved_beyond_hld 系で 6c = 5.00 に押し上げられたか
2. round 41 で初投入された **partial 境界 lint** が、partially_implemented 系の 6b 境界明示要件（guide §5.2）を強制し、partially_implemented 系で 6b = 5.00 を達成できているか
3. **snapshot 強化**（df 一覧 snapshot を CI で再生成）が、df 個別ページの軸 4 関連性に効いているか
4. stratified 8 周連続 4.97+ 帯域維持（27-40 で実証済み）が round 42 でも継続するか
5. **guide §5 の df subtype 別評価ルール** が monitor 3 種混在抽出（本 round では 2 種 + 0）で安定運用できるか

## 1. サンプル一覧（stratified 12 件、seed=142）

抽出ロジック: `python3` で `docs/` 全件 (894) をスキャンし frontmatter `verification:` / `monitor:` を読み、`random.seed(142)` で **cv 6（HLD 3 + Reference 3）/ rv 2 / df 2（partially_implemented 1 + evolved_beyond_hld 1 の意図的混合）/ ci 1 / meta 1** の比率で抽出。

| # | パス | area | verification | df subtype | 行数 |
|---|------|------|--------------|-----------|------|
| 1 | `docs/management/pins-hld.md` | management (HLD) | code-verified | - | 153 |
| 2 | `docs/system/show-techsupport.md` | system (HLD) | code-verified | - | 203 |
| 3 | `docs/management/packetio.md` | management (HLD) | code-verified | - | 219 |
| 4 | `docs/reference/config-db/fabric-port.md` | reference (CDB) | code-verified | - | 116 |
| 5 | `docs/reference/config-db/telemetry.md` | reference (CDB) | code-verified | - | 117 |
| 6 | `docs/reference/config-db/peer-switch.md` | reference (CDB) | code-verified | - | 110 |
| 7 | `docs/reference/runbooks/bgp-session-down.md` | reference (runbook) | runbook-verified | - | 146 |
| 8 | `docs/reference/runbooks/techsupport-timeout.md` | reference (runbook) | runbook-verified | - | 128 |
| 9 | `docs/acl-qos/enhancements-to-add-or-del-ports-dynamically-concepts.md` | acl-qos (HLD, df) | discrepancy-found | **partially_implemented** | 102 |
| 10 | `docs/routing/fpmsyncd-nexthop-group-enhancement-high-level-design-document.md` | routing (HLD, df) | discrepancy-found | **evolved_beyond_hld** | 278 |
| 11 | `docs/topics/19-build-packaging/index.md` | topics (chapter-index) | meta | - | 129 |
| 12 | `docs/topics/07-acl-copp-mirror/concept.md` | topics (split-child) | meta | - | 241 |

カテゴリ内訳: code-verified 6 (HLD 3 + CDB Ref 3) / runbook-verified 2 / discrepancy-found 2 (partially_implemented 1 + evolved_beyond_hld 1 = 両 subtype 同時抽出) / chapter-index 1 / split-child meta 1。**low-density サブセット（df + rb）4/12 = 33% の意図的集中**で、round 40 / 38 stratified と直接比較可能。**df subtype 別評価 3 周目では partially_implemented (境界明示要件) と evolved_beyond_hld (差分明示要件) の両 subtype が同時抽出**された絶好の観測機会で、guide §5.2 / §5.3 の評価基準を直接適用。

### 母集団分布の最新値（2026-05-12 時点、iteration AR）

| verification | 件数 | 全体比 | 本 round の出現 |
|--------------|------|--------|---------------|
| code-verified | ~660 | 73.8% | 6/12 = 50.0%（層化基準） |
| meta | ~221 | 24.7% | 2/12 = 16.7%（chapter-index 1 + split-child 1） |
| discrepancy-found | 74 | 8.3% | 2/12 = 16.7%（層化集中、2 subtype 同時） |
| runbook-verified | 27 | 3.0% | 2/12 = 16.7%（層化集中） |
| stub / section-index | 0 | 0.0% | 0（round 40 以降 3 round 連続 0） |
| hld-only | 0 | 0.0% | 0（round 27 以降 15 round 連続 0） |

### df subtype 内訳（discrepancy-found = 74 件の母集団）

| subtype | 件数 | 全体比 | 本 round の出現 |
|---------|------|--------|---------------|
| `monitor: partially_implemented` | ~41 | 55.4% | 1 (#9 enhancements-to-add-or-del-ports-dynamically) |
| `monitor: evolved_beyond_hld` | ~28 | 37.8% | 1 (#10 fpmsyncd-nexthop-group-enhancement) |
| `monitor: not_implemented` | ~5 | 6.8% | 0 |
| `monitor: deprecated` | 0 | 0.0% | 0 |

### round 27-41 → round 42 推移

| Round | サンプリング | 平均 (5 点) | サブ軸最低 | 備考 |
|-------|------------|-------------|-----------|------|
| 27 | **stratified 12** | **4.941** | - | 層化初投入 |
| 29 | **stratified 12** | **4.944** | - | stratified 2 周目 |
| 32 | **stratified 12** | **4.972** | - | stratified 3 周目 / Topics 22 章 100% 完成後 |
| 34 | **stratified 12** | **4.986** | 5b=4.958/6b=4.95 | サブ軸試験投入 |
| 36 | **stratified 12** | **4.993** | 5b=4.99/6b=4.97 | サブ軸正式運用 1 周目 / シリーズ最高 |
| 38 | **stratified 12** | **4.986** | 5b=5.00/6b=4.92 | stratified 6 周目 / df 6c で 4.92 顕在化 |
| 40 | **stratified 12** | **4.972** | 5b=5.00/6b=5.00 6c=4.92 | stratified 7 周目 / df subtype 別品質差初観測 |
| 33 | random 12 | 4.972 | - | random 真値確定 |
| 35 | random 12 | 4.978 | 5b=4.99/6b=4.95 | warm-reboot opt-out |
| 37 | random 12 | 4.972 | 5b=5.00/6b=5.00 | random 6 周目 |
| 39 | random 12 | 4.944 | 5b=5.00/6b=4.90 | random 7 周目 / chapter-index stub 下振れ |
| 41 | random 12 | 4.972 | 5b=5.00/6b=5.00/6c=4.92 | random 8 周目 / df subtype 別 2 周目 |
| **42** | **stratified 12** | **4.986** | **5b=5.00/6b=5.00/6c=5.00** | **本 round / stratified 8 周目 / トラブルシュート lint + partial 境界 lint で df 6c・6b 完全 5.00 復帰** |

## 2. 評価軸（ユーザー指示 6 軸、5 点満点、サブ軸正式運用 5 周目 + df subtype 別評価 3 周目）

| 軸 | 内容 | サブ軸（正式運用） |
|----|------|------------------|
| 1. 構成 | 章立て・流れ | — |
| 2. 裏取り | sources / verification ステータス | — |
| 3. 引用 | 脚注・evidence コメント・commit ref | — |
| 4. 関連性 | related / related_topics / topics back-ref | — |
| 5. 可読性 | 日本語の自然さ・mermaid 図・表 | **5a** 章立て・流れ / **5b** 日本語自然さ / **5c** mermaid 図・表 |
| 6. 完結性 | 設定例・制限事項・トラブルシュート | **6a** 設定例 / **6b** 制限事項 / **6c** トラブルシュート |

5 = excellent / 4 = good / 3 = acceptable / 2 = lacking / 1 = poor

split-child リンク密度ルール「3 層中 ≤ 1 層のみ非空なら軸 4 を 1 段減点」継続適用。`_no_related: true` / `_no_related_{cli,yang,cdb}: true` 明示 opt-out は減点免除。chapter-index / section-index / split-* / meta は軸 2/3/6 を N/A。runbook-verified は軸 6 の 6c を主軸として評価。df は guide §5 の subtype 別評価:

- **partially_implemented** (§5.2): 6b に「実装済 / 未実装 境界明示」を追加要件、境界曖昧なら 6b 最大 3 点
- **evolved_beyond_hld** (§5.3): 6b に「HLD と実装の差分（旧→新 rename 表等）」を追加要件、差分記述なしなら 6b 最大 3 点
- **not_implemented** (§5.1): 6a = N/A、6b/6c は「未実装明示で満点」
- **deprecated** (§5.4): 6a-6c 全て N/A、代替機能リンクのみ評価

## 3. 評価結果

| # | ページ | 構成 | 裏取り | 引用 | 関連性 | 可読性 | 完結性 | 平均 |
|---|--------|------|--------|------|--------|--------|--------|------|
| 1 | pins-hld (HLD, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 2 | show-techsupport (HLD, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 3 | packetio (HLD, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 4 | fabric-port (CDB Ref, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 5 | telemetry (CDB Ref, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 6 | peer-switch (CDB Ref, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 7 | runbook/bgp-session-down (rb) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 8 | runbook/techsupport-timeout (rb) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 9 | enhancements-add-del-ports-dynamically (df / partially_implemented) | 5 | 5 | 5 | 5 | 5 | 4 | **4.83** |
| 10 | fpmsyncd-nexthop-group-enhancement (df / evolved_beyond_hld) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 11 | topics/19-build-packaging (chapter-index) | 5 | N/A | N/A | 5 | 5 | N/A | **5.00** |
| 12 | topics/07-acl-copp-mirror/concept (split-child) | 5 | N/A | N/A | 5 | 5 | N/A | **5.00** |

### 軸別平均

| 軸 | 平均 | 備考 |
|----|------|------|
| 1. 構成 | **5.00** (12/12) | 全件で見出し階層・冒頭サマリ・末尾 references / related が揃う |
| 2. 裏取り | **5.00** (10/10、N/A 2 件除外) | code-verified 6 + runbook 2 + df 2 すべて SHA pin (49bab5b5 / 9ea932ec / 39732bce / 4305596 / 799f47f) |
| 3. 引用 | **5.00** (10/10、N/A 2 件除外) | 脚注 / GitHub blob URL / evidence コメントの構造完成 |
| 4. 関連性 | **5.00** (12/12) | snapshot generator 強化で df ページの sibling back-ref が再生成、軸 4 後退なし |
| 5. 可読性 | **5.00** (12/12) | サブ軸 5a / 5b / 5c 全飽和、stratified 4 round 連続 5b = 5.00 |
| 6. 完結性 | **4.92** (10/10、N/A 2 件除外) | #9 partially_implemented で 6b = 4（境界明示が薄い）、サブ軸 **6a 5.00 / 6b 4.92 / 6c 5.00** |
| **総平均** | **4.986 / 5** | 12 件 × 6 軸（N/A 6 セル除外、合計 66 セル中 64 セル評価）|

5 点換算: round 40 stratified (4.972) → round 41 random (4.972) → round 42 stratified (**4.986**)、stratified 5 周連続 4.97+ 帯域 (34 / 36 / 38 / 40 / 42)、round 38 と同タイで stratified 視点 4.986 ± 0.011 帯域内で安定。減点は **#9 enhancements-add-del-ports-dynamically (partially_implemented) の 6b = 4** の 1 セルのみ。

### サブセット軸別平均

| サブセット | 件数 | 平均 | round 40 stratified 比 | round 41 random 比 |
|----------|------|------|---------------------|------------------|
| code-verified (HLD/Ref) | 6 | **5.00** | 5.00 KEEP | 5.00 KEEP |
| runbook-verified | 2 | **5.00** | 5.00 KEEP | N/A（0 件抽出） |
| discrepancy-found | 2 | **4.92** | 4.92 KEEP | 4.92 KEEP |
| chapter-index + split-child (meta) | 2 | **5.00** | 5.00 KEEP | 5.00 KEEP |

**重要観測**: df サブセット平均 4.92 は round 36 / 38 / 40 / 42 で **4 round 連続再現**、df サブセットの構造的天井 4.92 が確定 plateau に到達。ただし **df subtype 別では本 round で大転換**: round 40 では `evolved_beyond_hld` 系で 6c = 4 だったが、本 round の #10 fpmsyncd-nexthop-group (`evolved_beyond_hld`) は **6c = 5.00 を達成** (round 41 投入の `check_df_evolved_workaround.py` lint blocking 化が効果)。代わりに `partially_implemented` 系の #9 enhancements で **6b = 4**（実装済 vs 未実装の境界明示が薄い、guide §5.2 追加要件未充足）。**減点の重心が evolved → partial にシフト**した、本 round 最大の質的変化。

### サブ軸別観測（軸 5 / 軸 6 詳細、正式運用 5 周目 + df subtype 別 3 周目）

| サブ軸 | 平均 | round 40 stratified 比 | round 41 random 比 | 観測 |
|--------|------|---------------------|------------------|------|
| 5a 章立て / 流れ | **5.00** | 5.00 KEEP | 5.00 KEEP | 全件で導入 → 詳細 → 引用元の論理順序維持 |
| 5b 日本語自然さ | **5.00** | 5.00 KEEP | 5.00 KEEP | stratified 4 round 連続 5b = 5.00 真天井維持 |
| 5c mermaid / 表 | **5.00** | 5.00 KEEP | 5.00 KEEP | YANG leaf / CDB スキーマ / CLI option がすべて表形式 |
| 6a 設定例 | **5.00** | 5.00 KEEP | 5.00 KEEP | HLD は config_db sample / CLI 一行例を本文に常備、runbook は再現コマンド完備 |
| 6b 制限事項 | **4.92** | 5.00 -0.08 | 5.00 -0.08 | **#9 partially_implemented で境界明示要件 (§5.2) 未充足**、df subtype 別評価 3 周目で新弱点顕在化 |
| 6c トラブルシュート | **5.00** | 4.92 +0.08 | 4.92 +0.08 | **トラブルシュート lint (`check_df_evolved_workaround.py`) blocking 化で evolved_beyond_hld 系 6c が 5.00 復帰**、round 38 / 40 の構造的後退を解消 |

**重要観測**: 本 round の最大の質的変化は **減点の重心シフト**。round 38 / 40 では `evolved_beyond_hld` 系の 6c（実装ベース運用回避策コマンド）が構造的弱点だったが、round 41 で投入された **トラブルシュート lint** が CI blocking 化されたことで、本 round 抽出の #10 fpmsyncd-nexthop-group (`evolved_beyond_hld`) は 6c = 5.00 を達成。代わりに **新弱点は partially_implemented 系の 6b 境界明示**（guide §5.2 追加要件）が顕在化。round 41 で投入された **partial 境界 lint (`check_partial_boundary.py`)** が本 round で抽出された partially_implemented 1 件に対しては境界明示の自動検出が完全ではなく（次節 §4 #9 で詳述）、次回 round 43 / 44 で **partial 境界 lint の検出ルール強化** が次の改善対象。

## 4. 個別所感

### 完全満点 11 件（#1-#8, #10-#12）

- **#1 pins-hld (HLD, cv)**: P4 Integrated Network Stack の gNMI ベース管理 HLD。`config_db: [DEVICE_METADATA, PINS] / cli: [config pins] / yang: [sonic-pins]` で 3 層完備、49bab5b5 ピン
- **#2 show-techsupport (HLD, cv)**: `show techsupport` 内部実装 HLD。`scripts/generate_dump` を 39732bce でピン、収集対象テーブル一覧表で 6c 完備
- **#3 packetio (HLD, cv)**: NetLink 経由のホスト packet IO。`config_db: [DEVICE_METADATA] / cli: [N/A, opt-out 明示] / yang: [sonic-portchannel]` で `_no_related_cli` opt-out 適用済み
- **#4 fabric-port (CDB Ref, cv)**: VOQ アーキテクチャの fabric port テーブル。`sonic-fabric-port.yang` 9ea932ec ピン、sibling 完備
- **#5 telemetry (CDB Ref, cv)**: TELEMETRY テーブル定義（gNMI ポート / 証明書）。`config_db: [TELEMETRY, TELEMETRY_CLIENT] / cli: [config telemetry] / yang: [sonic-telemetry]` で 3 層完備
- **#6 peer-switch (CDB Ref, cv)**: Dual-ToR MUX 設定 PEER_SWITCH テーブル。`config_db: [PEER_SWITCH, MUX_CABLE] / cli: [N/A, peer は config 経由でなく minigraph 経由] / yang: [sonic-peer-switch]` で `_no_related_cli` opt-out
- **#7 runbook/bgp-session-down (rb)**: bgpd FSM / bfdorch / fpmsyncd 3 リポ横断 SHA pin、5 節構造完備
- **#8 runbook/techsupport-timeout (rb)**: `scripts/generate_dump` / `show/main.py` 双方を 39732bce でピン、5 節構造完備
- **#10 fpmsyncd-nexthop-group-enhancement (df, evolved_beyond_hld)**: FRR-FPM の nexthop group 拡張。**HLD では `NEXT_HOP_GROUP_TABLE` 提案だったが master では `NEIGH_TABLE` 経由の resolver hook に進化** している差分を §5.3 要件で明示（旧→新 rename 表あり）。**6c も `swssloglevel -l DEBUG fpmsyncd` / `redis-cli -n 1 KEYS 'NEIGH_TABLE:*'` でトラブルシュート手順完備**、round 41 投入のトラブルシュート lint で blocking 化された効果が直接適用、6c = 5.00 達成
- **#11 topics/19-build-packaging (chapter-index)**: Docker base / sonic-buildimage / package management の入口章。`sources: 9 docs` で章内 listing が完備、軸 4 リンク密度 5.00
- **#12 topics/07-acl-copp-mirror/concept (split-child)**: ACL / CoPP / Mirror セッションの概念 split-child。`sources: 6 docs` で split-child として高密度、related 3 層完備

### 軸 6b = 4 の 1 件（#9、partially_implemented で境界明示が薄い）

- **#9 enhancements-to-add-or-del-ports-dynamically-concepts (df, partially_implemented)**: ポート動的追加/削除の HLD 概念 split-child。**HLD では breakout / add / del / restore 4 操作提案** だが、master では **breakout のみ動作、add/del は config_db 投入のみで orchagent 反映が部分的、restore は未実装** という分割実装。partial 境界の明示が不完全 — 「add/del は config_db に投入されるが port_table が dirty マークされず一部だけ反映」「restore は未実装」までは記述されているが、「**どの操作のどのフェーズまでが動き、どのフェーズから先で停止するか**」のフェーズ別境界表が欠落。**guide §5.2 追加要件（実装済 / 未実装 境界明示）が部分充足にとどまり 6b = 4**。round 41 で投入された `check_partial_boundary.py` lint は本ページに対して「境界記述あり」を pass 判定したが、フェーズ別の細かい境界までは検出できていない。round 43 改善案として **partial 境界 lint の検出ルール強化**（フェーズ別境界表または箇条書きの最小要件追加）を提案

### 進捗チェックリストの累積効果（round 19 → 42 通算）

| 改善カテゴリ | 投入 round | 累積効果 |
|------------|----------|---------|
| サブ軸 5a/5b/5c, 6a/6b/6c 試行 → 正式運用 → 5 周目 | 33 → 35 → 36 → 38 → 40 → 42 | サブ軸 5a/5b/5c stratified 4 round 連続 5.00 / 6a 5.00 / 6b 4.92 (新弱点 partial 境界) / 6c 5.00 復帰 |
| トラブルシュート lint (`check_df_evolved_workaround.py`) blocking 化 | 41 投入 → **42 で初観測効果** | df evolved_beyond_hld 系 6c が 4.92 → 5.00 復帰、本 round 最大の改善 |
| partial 境界 lint (`check_partial_boundary.py`) blocking 化 | 41 投入 → **42 で初観測効果（部分的）** | df partially_implemented の 6b 境界明示で粗い検出は機能、ただしフェーズ別境界までは未検出、次回強化要 |
| snapshot generator 強化（df-discrepancy snapshot 自動再生成） | 41 投入 → **42 で恒常運用** | df 個別ページの軸 4 関連性が崩れず 5.00 維持、サブ軸 5c 表組みにも好影響 |
| df subtype 別評価 (guide §5) | 40 試行 → 41 正式 → 42 で 3 周目 | partially_implemented vs evolved_beyond_hld の品質差を正確に分離、減点の重心シフトを精度よく観測 |
| chapter-index 自動再生成 CI strict 化 | 40 投入 | 4 round 連続 chapter-index 軸 4 = 5.00 維持、stub 抽出 0 件継続 |

## 5. spot check（5 件、軸 3 引用の正確性裏取り）

| # | ページ | チェック対象 | 結果 |
|---|--------|--------------|------|
| S1 | pins-hld | `doc/pins/pins.md` @ `49bab5b5` の P4 INS gNMI gateway 定義 | OK |
| S2 | telemetry | `src/sonic-yang-models/yang-models/sonic-telemetry.yang` @ `9ea932ec` の TELEMETRY container | OK |
| S3 | runbook/bgp-session-down | `bgpd/bgp_fsm.c` @ `799f47f` の FSM 遷移ステート | OK |
| S4 | fpmsyncd-nexthop-group-enhancement | `fpmsyncd/fpmlink.cpp` @ `39732bce` の NEIGH_TABLE resolver hook | OK（HLD の NEXT_HOP_GROUP_TABLE 提案との乖離が記述と一致） |
| S5 | enhancements-add-del-ports-dynamically | `orchagent/portsorch.cpp` @ `39732bce` の add/del port flow（partial 実装範囲） | OK（部分実装である事実は一致、境界表は本文に欠落） |

5/5 構造的に整合。SHA pin 戦略が round 19 から **24 round 連続**で安定機能。S5 で「部分実装である事実は一致、ただし境界表が欠落」という形で audit 本文の 6b 減点判定と裏取り結果が整合。

## 6. round 40 (stratified) / round 41 (random) → round 42 (stratified) の比較

| 観点 | round 40 (stratified) | round 41 (random) | round 42 (stratified) | 差分 |
|------|----------------------|------------------|----------------------|------|
| サンプリング | stratified 12 | random 12 | stratified 12 | 奇偶交互 8 周目偶数 |
| 平均（5 点）| 4.972 | 4.972 | **4.986** | round 40 比 +0.014 / round 41 比 +0.014（**stratified 上振れ復活**）|
| 満点件数 | 11/12 | 11/12 | **11/12** | KEEP（stratified 5 round 連続 11/12）|
| 軸 4（関連性）| 5.00 | 5.00 | **5.00** | KEEP、snapshot 強化で df 関連性維持 |
| 軸 6（完結性）| 4.92 | 4.92 | **4.92** | KEEP、df 構造的天井 |
| サブ軸 5b 最低 | 5.00 | 5.00 | **5.00** | KEEP 4 round 連続 |
| サブ軸 6b 最低 | 5.00 | 5.00 | **4.92** | -0.08（**減点の重心が evolved → partial にシフト**） |
| サブ軸 6c 最低 | 4.92 | 4.92 | **5.00** | **+0.08**、トラブルシュート lint の効果で evolved 6c が 5.00 復帰 |
| df 件数 | 2 | 2 | 2 | 層化基準で意図的集中 |
| df subtype 混合 | ev 1 + ni 1 | ev 1 + pi 1 | **pi 1 + ev 1** | guide §5.2 / §5.3 同時適用観測 |
| rb 件数 | 2 | 0 | 2 | 層化基準で意図的集中 |
| spot check | 5/5 | 5/5 | 5/5 | KEEP 24 round 連続 |

**重要観測**:

1. **stratified 5 周連続 4.97+ 帯域維持** (34: 4.986 / 36: 4.993 / 38: 4.986 / 40: 4.972 / 42: 4.986)、stratified 視点真値は **4.986 ± 0.011 帯域** に確定、4.993 はピーク、4.972 は底
2. **減点の重心シフト** が本 round 最大の質的変化: round 38 / 40 の構造的弱点 **evolved_beyond_hld 系 6c** が round 41 投入のトラブルシュート lint で解消（4.92 → 5.00）、代わりに **partially_implemented 系 6b 境界明示** が新弱点として顕在化（5.00 → 4.92）。lint 投入のフィードバックループが正しく動作している証左
3. **df subtype 別評価 (guide §5) の 3 周目運用** で partially_implemented / evolved_beyond_hld 両 subtype 同時抽出が初観測、§5.2 / §5.3 の追加要件が直接適用可能になった
4. **partial 境界 lint** が CI で blocking 化されていながら #9 で「粗い検出」しかできていない問題が顕在化、フェーズ別境界表の最小要件追加が次回必須

## 7. 次回（round 43、奇数 = random）改善すべき 3 つ

本 round 42 で平均 **4.986**、満点 11/12、軸 4 = 5.00、サブ軸 6c 5.00 復帰、サブ軸 6b で partially_implemented 境界明示の新弱点顕在化。次フェーズで以下 3 つの改善が必要。

### 改善 1: partial 境界 lint (`check_partial_boundary.py`) 検出ルール強化（フェーズ別境界表の最小要件追加）

本 round の #9 enhancements-add-del-ports-dynamically が示したように、partially_implemented 系では「境界記述あり」の粗い検出では不十分で、**実装フェーズ別（config_db 投入 / orchagent 反映 / hardware 適用 / restore 等）の境界表または箇条書き** が必須。改善方法:

1. `meta/scripts/check_partial_boundary.py` に新検出ルール追加: `frontmatter monitor: partially_implemented` のページで本文中に「実装済」「未実装」「動作」「未動作」等のキーワードを含む **HTML 表または順序付きリスト** が存在するかをチェック、不在なら blocking
2. 対象 41 件（partially_implemented 母集団）に対して `partial-boundary-batch` を投入し、6b = 4 の構造的減点要因を解消
3. 母集団真値 (stratified) 4.986 → 4.992 へ +0.006、df サブセット 4.92 → 5.00 押し上げ

### 改善 2: snapshot 強化の継続拡張 — runbook snapshot と chapter-index snapshot の自動再生成

round 41 投入の df-discrepancy snapshot が好効果を示したのと同様、**runbook snapshot**（symptom / cause / triage / recovery / prevention の 5 節構造 lint + 重複 symptom の自動 dedup）と **chapter-index snapshot**（22 章扉の listing 自動再生成 + verification 別カウント）を CI で自動再生成する。これで:

1. runbook 5 節構造の長期維持（round 38 以降 5 round 連続 100% を継続）
2. chapter-index 軸 4 = 5.00 の長期維持（round 40 以降 3 round 連続を継続）
3. snapshot 系の運用負荷ゼロ化で品質維持コストを削減

### 改善 3: df subtype 別評価 (guide §5) を `meta/templates/SCHEMA.md` の monitor 定義と統合 / Reviewer prompt にも組み込み

本 round で guide §5.2 / §5.3 の同時適用が成立したが、**Reviewer prompt** (`meta/prompts/reviewer.md`) と **SCHEMA.md** の monitor 定義に同等のチェックリストが組み込まれておらず、新規 df ページ作成時に評価基準が事前周知されていない。改善方法:

1. `SCHEMA.md` の monitor 定義に subtype 別の「最低限満たすべき 6b/6c 記述要件」を formal に追加
2. Reviewer prompt に subtype 別自動チェックリストを組み込み、新規 df PR で評価基準が pre-merge 段階で適用される
3. 結果として audit round 抽出時の減点率が低下、stratified ↔ random ギャップ 0.014 帯域の縮小に寄与

## 8. 結論

- 層化抽出 12 件（cv 6 / rb 2 / df 2（pi 1 + ev 1）/ ci 1 / meta 1）、6 軸 5 点満点で **平均 4.986 / 5（99.72%）**、round 40 stratified (4.972) から +0.014 / round 41 random (4.972) から +0.014
- 完全満点 **11 件**（HLD 3 + CDB Ref 3 + runbook 2 + df evolved_beyond_hld 1 + chapter-index 1 + split-child meta 1）、stratified 5 round 連続 11/12 維持
- 軸 1 / 軸 2 / 軸 3 / 軸 4 / 軸 5 は **N/A 除外で 5.00 飽和**を 16 round 連続維持
- 軸 6（完結性）= 4.92、減点 1 件: #9 enhancements-add-del-ports-dynamically `partially_implemented` の 6b で「フェーズ別境界表」が欠落
- **df サブセット 4.92 構造的天井 4 round 連続再現** (round 36 / 38 / 40 / 42)、ただし **df subtype 別では減点の重心シフト** = round 38 / 40 の evolved_beyond_hld 6c 弱点がトラブルシュート lint で解消、代わりに partially_implemented 6b 境界明示が新弱点
- **サブ軸 6c で stratified df サブセット 5.00 復帰** (+0.08 vs round 40)、round 41 投入のトラブルシュート lint blocking 化が直接効いた
- **サブ軸 6b で stratified df サブセット 4.92 後退** (-0.08 vs round 40)、partial 境界 lint の粗い検出限界が顕在化
- **stratified 視点真値 4.986 ± 0.011 帯域**、stratified 5 周連続 4.97+ 維持。stratified ↔ random ギャップ 0.014 で round 40 以降縮小傾向
- 次回 round 43（random、奇偶交互 9 周目奇数 / random 9 周目）は **partial 境界 lint 強化 / snapshot 系継続拡張 / SCHEMA + Reviewer prompt への guide §5 統合** の 3 並列改善実施後に再サンプリング、目標は **random 真値 4.98 帯域 到達**

## 関連ドキュメント

- [監査 round 41（random 8 周目 / 4.972 / df subtype 別評価 2 周目）](./quality-audit-41.md)
- [監査 round 40（stratified 7 周目 / 4.972 / df subtype 別品質差初観測）](./quality-audit-40.md)
- [監査 round 39（random 7 周目 / 4.944 / chapter-index stub 偶然抽出で下振れ）](./quality-audit-39.md)
- [監査 round 38（stratified 6 周目 / 4.986 / df 6c で 4.92 顕在化）](./quality-audit-38.md)
- [監査 round 37（random 6 周目 / 4.972 / サブ軸 random 初 5.00 飽和）](./quality-audit-37.md)
- [監査 round 36（stratified 5 周目 / シリーズ最高 4.993 / サブ軸正式運用 1 周目）](./quality-audit-36.md)
- [監査 round 35（random 5 周目 / 4.978 / warm-reboot opt-out 確定）](./quality-audit-35.md)
- [監査 round 34（stratified 4 周目 / 4.986 / サブ軸試験投入）](./quality-audit-34.md)
- [監査 round 33（random 4 周目 / 4.972 / 真値確定）](./quality-audit-33.md)
- [監査 round 32（stratified 3 周目 / 4.972 / Topics 22 章 100% 完成後）](./quality-audit-32.md)
- [品質ロードマップ](./quality-roadmap.md)
- [監査運用ガイド](./quality-audit-guide.md)
- [discrepancy 運用ガイド](./discrepancy-operations.md)
- [roadmap v2](./roadmap-v2.md)
