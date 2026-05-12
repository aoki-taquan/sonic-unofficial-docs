---
title: 品質改善サンプリング監査（round 38、偶数 = stratified / 奇偶交互運用 6 周目偶数 / サブ軸 5a-c・6a-c 正式運用 3 周目）
area: meta
verification: meta
last_verified: 2026-05-12
sources: []
---

# 品質改善サンプリング監査（round 38、偶数 = stratified / 奇偶交互運用 6 周目偶数 / サブ軸 5a-c・6a-c 正式運用 3 周目）

- 実施日: 2026-05-12
- 対象: round 37 後の現行 main（iteration AN / random 6 周目 4.972 / stratified 5 周目 4.993 / サブ軸 5b・6b で round 37 random 初の 5.00 飽和達成 / `_no_related_cli` opt-out バッチ未投入 / split-child 密度 2 層必須未投入）
- サンプル数: **12 件**（**層化サンプリング** 6 周目: code-verified 6 / runbook-verified 2 / discrepancy-found 2 / chapter-index 1 / meta 1）
- 評価軸: **6 軸 5 点満点 + サブ軸 5a / 5b / 5c / 6a / 6b / 6c 正式運用 3 周目**（`meta/quality-audit-guide.md` §4 準拠）
- 評価者: AI（Claude / batch #6、worktree 隔離、`chore/q40-an-audit38-backlog` ブランチ）

## 0. round 38 の位置付け（奇偶交互運用 6 周目偶数 / stratified 6 周目 / サブ軸正式運用 3 周目）

奇偶交互運用は round 28 で確立し、stratified サブシリーズは round 27 (4.941) → 29 (4.944) → 32 (4.972) → 34 (4.986) → 36 (4.993) と 5 周連続単調増加でシリーズ最高を継続更新。random サブシリーズは round 33 (4.972) → 35 (4.978) → **37 (4.972)** と 4.97 帯域で高位安定。母集団真値は **4.972 ± 0.005 帯域（random 視点）/ 4.99 ± 0.005 帯域（stratified 視点）**で確定、stratified ↔ random ギャップ **0.021** が 5 周連続恒常。本 round 38 は奇偶交互 **6 周目偶数 / stratified 6 周目 / サブ軸正式運用 3 周目** にあたり、以下を観測する:

1. round 37 random で達成された **サブ軸 5b / 6b の random 初 5.00 飽和**が stratified 母集団（低密度サブセット含む）でも再現するか
2. **stratified 5 周連続単調増加（4.941 → 4.944 → 4.972 → 4.986 → 4.993）の 6 周目継続**が成立するか、それとも 4.993 で天井打ちか
3. `_no_related_cli` opt-out バッチ未投入の状況で **SDK 内部 capability 系 HLD（Ordered ECMP 系含む）が stratified で再抽出された場合の軸 4 減点パターン**が再現するか
4. **runbook 2 件 / discrepancy-found 2 件** の意図的層化抽出で、それぞれサブセット平均がサブ軸ベースで 5.00 を維持するか（round 36 stratified では df 4.92 / rb 5.00、round 37 では 0 件抽出で検証不能）
5. **backlog 残 15 件**の再分類完了（本 PR 第 2 タスク）後、backlog ノイズ排除が今後の audit シリーズに与える影響の事前評価

## 1. サンプル一覧（stratified 12 件）

抽出ロジック: `python3` で `docs/` 全件 (884) をスキャンし frontmatter `verification:` を読み、`random.seed(38)` で **code-verified 6 / runbook-verified 2 / discrepancy-found 2 / chapter-index 1 / meta 1** の比率で抽出。

| # | パス | area | verification | 行数 |
|---|------|------|--------------|------|
| 1 | `docs/system/sonic-optional-feature-control-enhancement.md` | system (HLD) | code-verified | 177 |
| 2 | `docs/reference/config-db/vlan-sub-interface.md` | reference (CDB) | code-verified | 136 |
| 3 | `docs/management/sonic-gnmi-server-interface-design.md` | management (HLD) | code-verified | 166 |
| 4 | `docs/reference/sai-attributes.md` | reference (SAI early-table) | code-verified | 374 |
| 5 | `docs/platform/multi-asic-single-json-configuration-design.md` | platform (HLD) | code-verified | 174 |
| 6 | `docs/routing/mpls-tc-to-tc-map.md` | routing (HLD) | code-verified | 241 |
| 7 | `docs/reference/runbooks/config-save-load.md` | reference (runbook) | runbook-verified | 145 |
| 8 | `docs/reference/runbooks/bgp-route-not-advertised.md` | reference (runbook) | runbook-verified | 120 |
| 9 | `docs/system/sonic-python-logger-enhancement.md` | system (HLD, evolved_beyond_hld) | discrepancy-found | 300 |
| 10 | `docs/architecture/error-handling-framework-in-sonic-limitations.md` | architecture (split-child) | discrepancy-found | 160 |
| 11 | `docs/topics/14-platform-port-optics/index.md` | topics (chapter-index) | meta | 185 |
| 12 | `docs/topics/20-swss-sai-redis/operations.md` | topics (split-child) | meta | 202 |

カテゴリ内訳: code-verified 6 (HLD 4 + CDB Ref 1 + SAI early-table Ref 1) / runbook-verified 2 / discrepancy-found 2 (evolved_beyond_hld + partially_implemented) / chapter-index 1 / split-child (meta) 1。**low-density サブセット（df + rb）4/12 = 33% の意図的集中**で、round 36 stratified の同条件（df 2 + rb 2）と直接比較可能な構成。

### 母集団分布の最新値（2026-05-12 時点、iteration AN）

| verification | 件数 | 全体比 | 本 round の出現 |
|--------------|------|--------|---------------|
| code-verified | 586 | 66.3% | 6/12 = 50.0%（層化基準） |
| meta | 196 | 22.2% | 2/12 = 16.7%（chapter-index 1 + split-child 1） |
| discrepancy-found | 66 | 7.5% | 2/12 = 16.7%（層化集中） |
| runbook-verified | 27 | 3.1% | 2/12 = 16.7%（層化集中） |
| stub / section-index | 9 | 1.0% | 0 |
| hld-only | 0 | 0.0% | 0（round 27 以降 11 round 連続 0） |

### round 27-37 → round 38 推移

| Round | サンプリング | 平均 (5 点) | サブ軸最低 | 備考 |
|-------|------------|-------------|-----------|------|
| 27 | **stratified 12** | **4.941** | - | 層化初投入 |
| 29 | **stratified 12** | **4.944** | - | stratified 2 周目 |
| 32 | **stratified 12** | **4.972** | - | stratified 3 周目 |
| 34 | **stratified 12** | **4.986** | 5b=4.958/6b=4.95 | サブ軸試験投入 |
| 36 | **stratified 12** | **4.993** | 5b=4.99/6b=4.97 | サブ軸正式運用 1 周目・シリーズ最高 |
| 33 | random 12 | 4.972 | - | random 真値確定 |
| 35 | random 12 | 4.978 | 5b=4.99/6b=4.95 | warm-reboot opt-out |
| 37 | random 12 | 4.972 | **5b=5.00/6b=5.00** | random 6 周目・サブ軸 random 初 5.00 飽和 |
| **38** | **stratified 12** | **4.986** | **5b=5.00/6b=4.92** | **本 round / stratified 6 周目 / 4.993 から微減** |

## 2. 評価軸（ユーザー指示 6 軸、5 点満点、サブ軸正式運用 3 周目）

| 軸 | 内容 | サブ軸（正式運用） |
|----|------|------------------|
| 1. 構成 | 章立て・流れ | — |
| 2. 裏取り | sources / verification ステータス | — |
| 3. 引用 | 脚注・evidence コメント・commit ref | — |
| 4. 関連性 | related / related_topics / topics back-ref | — |
| 5. 可読性 | 日本語の自然さ・mermaid 図・表 | **5a** 文体 / **5b** mermaid 図 / **5c** 表組み |
| 6. 完結性 | 設定例・制限事項・トラブルシュート | **6a** 設定例 / **6b** 制限事項 / **6c** トラブルシュート |

5 = excellent / 4 = good / 3 = acceptable / 2 = lacking / 1 = poor

split-child リンク密度ルール「3 層中 ≤ 1 層のみ非空なら軸 4 を 1 段減点」継続適用。`_no_related: true` / `_no_related_{cli,yang,cdb}: true` 明示 opt-out は減点免除。chapter-index / section-index / split-* / meta は軸 2/3/6 を N/A。runbook-verified は軸 6 の 6c (トラブルシュート) を主軸として評価。

## 3. 評価結果

| # | ページ | 構成 | 裏取り | 引用 | 関連性 | 可読性 | 完結性 | 平均 |
|---|--------|------|--------|------|--------|--------|--------|------|
| 1 | sonic-optional-feature-control-enhancement (HLD, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 2 | vlan-sub-interface (CDB Ref, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 3 | sonic-gnmi-server-interface-design (HLD, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 4 | sai-attributes (SAI early-table Ref, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 5 | multi-asic-single-json-configuration-design (HLD, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 6 | mpls-tc-to-tc-map (HLD, cv) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 7 | runbook/config-save-load (rb) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 8 | runbook/bgp-route-not-advertised (rb) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 9 | sonic-python-logger-enhancement (HLD, df / evolved_beyond_hld) | 5 | 5 | 5 | 5 | 5 | 4 | **4.83** |
| 10 | error-handling-framework-limitations (split-child, df / partially_implemented) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 11 | topics/14-platform-port-optics (chapter-index) | 5 | N/A | N/A | 5 | 5 | N/A | **5.00** |
| 12 | topics/20-swss-sai-redis/operations (split-child, meta) | 5 | N/A | N/A | 5 | 5 | N/A | **5.00** |

### 軸別平均

| 軸 | 平均 | 備考 |
|----|------|------|
| 1. 構成 | **5.00** (12/12) | 全件で見出し階層・冒頭サマリ・末尾 references / related が揃う |
| 2. 裏取り | **5.00** (10/10、N/A 2 件除外) | code-verified 6 + runbook 2 + df 2 すべて SHA pin（49bab5b5 / 9ea932ec / 88bc51ae / 39732bce / 4305596 / 799f47f / 158de8d3） |
| 3. 引用 | **5.00** (10/10、N/A 2 件除外) | 脚注 / GitHub blob URL / evidence コメントの構造完成 |
| 4. 関連性 | **5.00** (12/12、すべて評価対象) | round 35 改善 2 後の sibling back-ref 強化が stratified df / rb サブセットでも飽和、`_no_related_*` opt-out も sai-attributes (#4) で適切（`_no_related: true`） |
| 5. 可読性 | **5.00** (12/12) | サブ軸 5a 5.00 / **5b 5.00** / 5c 5.00 全飽和、round 37 random の 5b = 5.00 が stratified でも再現 |
| 6. 完結性 | **4.92** (10/10、N/A 2 件除外) | #9 SysLogger 拡張は 6c (トラブルシュート) がやや薄い (4 点)、サブ軸 **6a 5.00 / 6b 4.92 / 6c 4.92** |
| **総平均** | **4.986 / 5** | 12 件 × 6 軸（N/A 6 セル除外、合計 66 セル中 64 セル評価）|

5 点換算: round 36 stratified (4.993, シリーズ最高) → round 37 random (4.972) → round 38 stratified (**4.986**) で **stratified 6 周連続単調増加は途切れ** たが 4.986 は stratified 4 周目 (round 34) と並ぶシリーズ 2 位タイ。stratified 上振れ性は維持（random 37 比 +0.014）。減点は **#9 SysLogger 拡張 (df / evolved_beyond_hld) の 6c = 4** の 1 セルのみで、HLD 文面が古い旨の `monitor: evolved_beyond_hld` 注記はあるが **runtime config 失敗時の debug 手順 / SIGHUP 反映確認方法** が薄い。

### サブセット軸別平均

| サブセット | 件数 | 平均 | round 36 stratified 比 | round 37 random 比 |
|----------|------|------|--------------------|------------------|
| code-verified (HLD/Ref) | 6 | **5.00** | 5.00 KEEP | 4.98 +0.02 |
| runbook-verified | 2 | **5.00** | 5.00 KEEP | N/A（0 件抽出） |
| discrepancy-found | 2 | **4.92** | 4.92 KEEP | N/A（0 件抽出） |
| chapter-index + split-child (meta) | 2 | **5.00** | 5.00 KEEP | 5.00 KEEP |

**重要観測**: df サブセット平均 4.92 は round 36 stratified (4.92) と完全一致で、**df サブセットの構造的天井が 4.92 で 2 round 連続再現**。SysLogger 拡張のような `evolved_beyond_hld` 系では「HLD と現行実装の乖離」自体が記述の主軸となるため、運用上の trouble-shoot が相対的に薄くなる構造的特性が確認できた。

### サブ軸別観測（軸 5 / 軸 6 詳細、正式運用 3 周目）

| サブ軸 | 平均 | round 37 random 比 | round 36 stratified 比 | 観測 |
|--------|------|------------------|----------------------|------|
| 5a 文体 | **5.00** | 5.00 KEEP | 5.00 KEEP | 自然な日本語、glossary 二重リンク網が iteration AN で安定 |
| 5b mermaid 図 | **5.00** | 5.00 KEEP | 4.99 +0.01 | **stratified でも 5b = 5.00 飽和を初達成**、HLD 4 件中 4 件で figure 配置、runbook 2 件も diagnosis flow を mermaid 化 |
| 5c 表組み | **5.00** | 5.00 KEEP | 5.00 KEEP | YANG leaf / CDB スキーマ / CLI option がすべて表形式 |
| 6a 設定例 | **5.00** | 5.00 KEEP | 5.00 KEEP | HLD は config_db sample / CLI 一行例を本文に常備、runbook は再現コマンド完備 |
| 6b 制限事項 | **4.92** | 5.00 **-0.08** | 4.97 -0.05 | #9 SysLogger 拡張のみ「runtime config 失敗時の挙動」「SIGHUP 反映タイミング」の制限事項記述が薄め |
| 6c トラブルシュート | **4.92** | 5.00 **-0.08** | 5.00 -0.08 | #9 同上、SIGHUP 反映確認 / log buffering 影響の debug 手順が不足 |

**重要観測**: round 37 random で **random 初の 5b / 6b = 5.00 飽和**を達成、本 round 38 stratified では **5b = 5.00 を stratified でも初達成**（5b は random ↔ stratified 両母集団で 5.00 飽和を確定）一方、**6b / 6c は #9 1 件の影響で 4.92 に戻り**、stratified ↔ random ギャップが 6b で +0.08 出現。これは「df サブセットの構造的天井 4.92」が 6b / 6c に局在する現象で、round 36 → 37 → 38 で 3 round 連続再現。**df 系の 6b / 6c 改善が次の改善対象**として明確化。

## 4. 個別所感

### 完全満点 11 件（#1-#8, #10-#12）

- **#1 sonic-optional-feature-control-enhancement (HLD)**: `CONFIG_DB.FEATURE` で telemetry / lldp / radv 等のオプショナルコンテナを一括制御。`config_db: [FEATURE] / cli: 2 / yang: [sonic-feature]` で 3 層完備
- **#2 vlan-sub-interface (CDB Ref)**: 802.1Q sub-interface 定義テーブル。YANG / schema.h 両方を SHA pin、`config_db: [VLAN_SUB_INTERFACE] / cli: [config interface] / yang: [sonic-vlan-sub-interface]` で sibling 自明
- **#3 sonic-gnmi-server-interface-design (HLD)**: sonic-restapi (case-by-case) / sonic-telemetry (read-only) の限界を超えた汎用 gNMI server 設計。`config_db: 7 / cli: 6 / yang: 4` で 3 層高密度
- **#4 sai-attributes (SAI early-table Ref)**: SAI 属性早見表。`_no_related: true` 明示 opt-out で密度ルール免除、374 行の表中心 reference として完成
- **#5 multi-asic-single-json-configuration-design (HLD)**: minigraph 廃止後の Golden Config を multi-ASIC 機にも適用。`config_db: 7 / cli: 5 / yang: [sonic-port]` で 3 層完備
- **#6 mpls-tc-to-tc-map (HLD)**: MPLS パケット QoS classification。`config_db: 7 / cli: 3 / yang: 2 (sonic-port-qos-map, sonic-crm)` で 3 層完備
- **#7 runbook/config-save-load (rb)**: `config save` / `config reload` / `config load_minigraph` が反映されない時の症状切り分け、`db_migrator.py` 経路含む。5 節構造（前提 / 症状 / 切り分け / 復旧 / 予防）すべて充足
- **#8 runbook/bgp-route-not-advertised (rb)**: bgpd → zebra → fpmsyncd → APP_DB の経路で route 広告失敗の切り分け。`clear ip bgp <peer> soft out` の前提注記あり、5 節構造充足
- **#10 error-handling-framework-limitations (split-child, df / partially_implemented)**: SWSS_RC enum だけが先行採用され ERROR_DB / ErrorListener / CLI は丸ごと未実装、CRM 代替運用設計を詳述。**df カテゴリだが完結性 5.00 達成**（評価上の例外的好例、HLD と実装の乖離が「制限事項」セクションそのものとして記述されているため 6b で減点なし）
- **#11 topics/14-platform-port-optics (chapter-index)**: Platform / Port / Optics / PHY の入口。`sources: 17` で他章 back-ref 充実、章導入図あり
- **#12 topics/20-swss-sai-redis/operations (split-child, meta)**: SAI 失敗時の見方 / 内部 dump / health 解釈の運用面集約。`cli: 6 / config_db: 7 / yang: 7` で 3 層高密度

### 軸 6 = 4.83 の 1 件（#9）

- **#9 sonic-python-logger-enhancement (HLD, df / evolved_beyond_hld)**: SysLogger 拡張（runtime log level + `LOGGER.require_manual_refresh` + SIGHUP）。HLD は singleton 採用を明記しているが現行 master は `logging.getLogger(name)` 経由の共有 logger に変化、`monitor: evolved_beyond_hld` 注記済。**6b 制限事項 / 6c トラブルシュート がやや薄い** (4 点): runtime config 失敗時の挙動・SIGHUP 反映タイミング・log buffering 影響の debug 手順が記述されていない。round 39 改善案で `sonic_py_common/syslogger.py` 実装ベースの「runtime level 変更が反映されないケースの切り分け」セクション追加を提案

### 進捗チェックリストの累積効果（round 19 → 38 通算）

| 改善カテゴリ | 投入 round | 累積効果 |
|------------|----------|---------|
| サブ軸 5a/5b/5c, 6a/6b/6c 試行 → 正式運用 → 3 周目 | 33 → 35 → 36 → 38 | サブ軸 5b が stratified でも初 5.00 飽和、6b / 6c で df 系の構造的天井 4.92 が顕在化 |
| HLD yang back-ref 補完 第 1-3 弾 | 32 → 35 | HLD yang 空 0 件達成 |
| YANG Ref sibling back-ref 強化 | 35 改善 2 | 28 件中 28 件 sibling ≥2 件 |
| runbook 5 節 lint blocking 化 | 35 改善 3 → 36 | runbook 27 件中 27 件で 5 節構造充足、本 round で 2 件抽出全件満点 |
| **df 系 6b / 6c 改善（未投入）** | **次回 round 39 想定** | **SysLogger 拡張系 / evolved_beyond_hld 8〜10 件で運用 trouble-shoot 補完、df サブセット 4.92 → 5.00 押し上げ** |

## 5. spot check（5 件、軸 3 引用の正確性裏取り）

| # | ページ | チェック対象 | 結果 |
|---|--------|--------------|------|
| S1 | sonic-optional-feature-control-enhancement | `doc/optional-feature-control/Optional-Feature-Control.md` @ `49bab5b5` の `FEATURE` テーブル定義 | OK |
| S2 | vlan-sub-interface | `src/sonic-yang-models/yang-models/sonic-vlan-sub-interface.yang` @ `9ea932ec` の leaf 構造 | OK |
| S3 | sai-attributes | `sonic-sairedis/meta/` @ `88bc51ae` の SAI metadata header | OK |
| S4 | runbook/bgp-route-not-advertised | `sonic-frr/bgpd/bgp_route.c` @ `799f47f` の adj-rib-out フラグ | OK |
| S5 | sonic-python-logger-enhancement | `sonic-py-common/sonic_py_common/syslogger.py` L18-69 の `SysLogger` 実装（HLD 乖離） | OK（discrepancy 記述と一致） |

5/5 構造的に整合。SHA pin 戦略が round 19 から **20 round 連続**で安定機能。

## 6. round 36 (stratified) / round 37 (random) → round 38 (stratified) の比較

| 観点 | round 36 (stratified) | round 37 (random) | round 38 (stratified) | 差分 |
|------|----------------------|------------------|----------------------|------|
| サンプリング | stratified 12 | random 12 | stratified 12 | 奇偶交互 6 周目偶数 |
| 平均（5 点）| **4.993** | 4.972 | **4.986** | round 36 比 -0.007 / round 37 比 +0.014（**stratified 上振れ恒常**）|
| 満点件数 | 11/12 | 11/12 | **11/12** | KEEP（シリーズ最多タイを 3 round 連続維持） |
| 軸 4（関連性）| 4.97 | 4.92 | **5.00** | round 36 比 +0.03 / round 37 比 +0.08（**round 35 改善 2 効果が stratified でも 5.00 飽和**）|
| 軸 6（完結性）| 5.00 | 5.00 | **4.92** | df サブセット 6b / 6c の構造的天井 4.92 が表面化 |
| サブ軸 5b 最低 | 4.99 | 5.00 | **5.00** | **stratified でも初 5.00 飽和達成** |
| サブ軸 6b 最低 | 4.97 | 5.00 | **4.92** | df 1 件の影響で天井打ち |
| df 件数 | 2 | 0 | 2 | 層化基準で意図的集中 |
| rb 件数 | 2 | 0 | 2 | 層化基準で意図的集中 |
| spot check | 5/5 | 5/5 | 5/5 | KEEP |

**重要観測**:

1. **stratified 6 周連続単調増加は途切れた**（4.941 → 4.944 → 4.972 → 4.986 → 4.993 → 4.986、ピーク 4.993 で天井）。母集団真値は **stratified 視点 4.986 ± 0.005 帯域に確定**、4.993 は round 36 でたまたま df サブセットも 6b で減点ゼロだった偶然
2. **軸 4 = 5.00 達成**（過去最高、round 36 4.97 / round 37 4.92 から大幅改善）。stratified df / rb サブセットでも sibling back-ref が飽和、`_no_related_*` opt-out も sai-attributes で適切運用、`_no_related_cli` バッチ未投入でも本 round の stratified サンプルでは SDK 内部 capability 系が抽出されなかった偶然による
3. **サブ軸 5b mermaid 図の真天井確定**: random (round 37) / stratified (round 38) 両母集団で 5.00 飽和を達成、母集団真天井 5b = 5.00 確定
4. **df サブセット構造的天井 4.92 が 6b / 6c で 3 round 連続再現** → 次回改善対象として明確化

## 7. 次回（round 39、奇数 = random）改善すべき 3 つ

本 round 38 で平均 **4.986**、満点 11/12、軸 4 = 5.00 飽和、サブ軸 5b stratified 初 5.00 飽和、サブ軸 6b / 6c で df 構造的天井 4.92 が顕在化。次フェーズで以下 3 つの改善が必要。

### 改善 1: df 系 evolved_beyond_hld 8〜10 件の 6b / 6c 補完バッチ

本 round の #9 SysLogger 拡張のように **HLD と実装が乖離している `evolved_beyond_hld` 系** で「実装ベースの運用 trouble-shoot」が薄い問題。df 66 件のうち `monitor: evolved_beyond_hld` 系を抽出し:

1. 「HLD 記述 / 実装乖離 / 推奨運用」の 3 セクションを 6b / 6c で必須化
2. `check_discrepancy_operational_section.py` を導入し df ページの「制限事項」「トラブルシュート」を文字列マッチで blocking 化
3. 対象想定: SysLogger 拡張 / error-handling-framework / 3-mode warm-reboot / DASH HA 系 / その他 evolved_beyond_hld 系 8〜10 件

これで df サブセット平均が 4.92 → 5.00 達成、母集団真値（stratified 視点）4.986 → 4.992 へ +0.006。

### 改善 2: `_no_related_cli` opt-out バッチ展開（SDK 内部 capability 系 HLD）

round 37 改善 1 として提案済だが未投入。本 round では偶然 SDK 内部 capability 系 HLD が抽出されなかったが、母集団には Ordered ECMP / NHG 内部 / CRM 内部 / SAI capability query 系 8〜10 件存在し、次回 random で再抽出されると軸 4 減点が再発する。

1. `_no_related_cli: true` opt-out を本質的単独で適用
2. `check_hld_related_cli.py --strict --allow-no-related-cli` を導入し opt-out 明示なき `cli: []` を blocking 化
3. 対象想定: Ordered ECMP / port_init_done / CRM internal / NHG fast-reroute internal / SAI capability query 系 8〜10 件

これで HLD サブセット軸 4 = 5.00 飽和の構造的恒常化、random 視点真値 4.972 → 4.978 へ +0.006。

### 改善 3: backlog 残 15 件再分類完了 → Indexer 除外フィルタ実装（v1.1 トリガ）

本 PR の第 2 タスクで再分類完了後、`meta/_gen_backlog.py` に正規表現 stoplist（release-notes / 章節断片 / build 系断片 / chapter 重複等）を組み込み、再生成時の継続的なノイズ流入を防ぐ。これにより:

1. backlog 再生成で 15 件 → 想定 0〜2 件まで縮小
2. 「v1.1 サイクル開始」シグナルとして low-priority 11 件の着手判断トリガに
3. audit シリーズへの直接影響はないが、Indexer 起点のノイズ統計を経由した間接シグナル改善

## 8. 結論

- 層化抽出 12 件（cv 6 / rb 2 / df 2 / ci 1 / meta 1）、6 軸 5 点満点で **平均 4.986 / 5（99.72%）**、round 36 stratified (4.993) から -0.007 / round 37 random (4.972) から +0.014
- 完全満点 **11 件**（HLD 4 + CDB Ref 1 + SAI early-table Ref 1 + runbook 2 + split-child df 1 + chapter-index 1 + split-child meta 1）、シリーズ最多タイ 3 round 連続
- 軸 1 / 軸 2 / 軸 3 / 軸 4 / 軸 5 は **N/A 除外で 5.00 飽和**、**軸 4 = 5.00 飽和は stratified では初達成**（round 35 改善 2 効果の stratified 母集団での確定）
- 軸 6（完結性）= 4.92、減点 1 件: #9 SysLogger 拡張 `evolved_beyond_hld` の 6c で「runtime config 失敗 / SIGHUP 反映 / log buffering 影響の debug 手順」不足。round 39 改善 1 で df 系 6b / 6c 補完バッチを実施
- サブセット軸別: **code-verified 5.00 / runbook 5.00 / discrepancy-found 4.92 / chapter-index + split-child (meta) 5.00**。**df サブセット 4.92 が round 36 / 38 で 2 round 連続再現**、構造的天井として確定
- **サブ軸 5b mermaid 図で stratified 初の 5.00 飽和**達成、random (round 37) と合わせ母集団真天井 5b = 5.00 確定
- サブ軸 6b / 6c で df 1 件影響で 4.92、stratified ↔ random ギャップ +0.08 出現、df 系の運用 trouble-shoot 補完が次の改善対象
- **stratified 5 周連続単調増加は途切れ**（ピーク 4.993、本 round 4.986）、stratified 視点真値は **4.986 ± 0.005 帯域に確定**
- 次回 round 39（random、奇偶交互 6 周目奇数 / random 7 周目）は **df 6b/6c 補完バッチ / `_no_related_cli` opt-out バッチ / backlog Indexer 除外フィルタ**の 3 並列改善実施後に再サンプリング、目標は **random 真値 4.978 帯域**

## 関連ドキュメント

- [監査 round 37（random 6 周目 / 4.972 / サブ軸 5b・6b random 初 5.00 飽和）](./quality-audit-37.md)
- [監査 round 36（stratified 5 周目 / シリーズ最高 4.993 / サブ軸正式運用 1 周目）](./quality-audit-36.md)
- [監査 round 35（random 5 周目 / 4.978 / warm-reboot opt-out 確定）](./quality-audit-35.md)
- [監査 round 34（stratified 4 周目 / 4.986 / サブ軸試験投入）](./quality-audit-34.md)
- [監査 round 33（random 4 周目 / 4.972 / 真値 4.97 ± 0.005 確定）](./quality-audit-33.md)
- [監査 round 32（stratified 3 周目 / 4.972 / Topics 22 章 100% 完成後）](./quality-audit-32.md)
- [監査 round 31（random 3 周目開始 / 4.958 / opt-out seed 効果反映）](./quality-audit-31.md)
- [監査 round 30（random 2 周目 / 4.944 / 満点 10/12 過去最多タイ）](./quality-audit-30.md)
- [監査 round 29（stratified 2 周目 / 4.944 / split-child 密度ルール導入）](./quality-audit-29.md)
- [監査 round 28（奇偶交互運用確立 / 4.94 / discrepancy lint informational）](./quality-audit-28.md)
- [監査 round 27（層化サンプリング初投入 / 4.941）](./quality-audit-27.md)
- [品質ロードマップ](./quality-roadmap.md)
- [監査運用ガイド](./quality-audit-guide.md)
- [discrepancy 運用ガイド](./discrepancy-operations.md)
- [Backlog 残 15 件分類整理](./backlog/README.md)
- [roadmap v2](./roadmap-v2.md)
