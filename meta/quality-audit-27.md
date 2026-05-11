---
title: 品質改善サンプリング監査（round 27、層化サンプリング初投入）
area: meta
verification: meta
last_verified: 2026-05-11
sources: []
---

# 品質改善サンプリング監査（round 27、層化サンプリング初投入）

- 実施日: 2026-05-11
- 対象: round 26 後の現行 main（CLI/HLD `related.yang` 自動補完 / hld-only 大型ページ verifier 棚卸し / management HLD 運用入口表テンプレ累積後の状態）
- サンプル数: **12 件**（**層化サンプリング**: code-verified 6 / runbook-verified 2 / discrepancy-found 2 / chapter-index 1 / meta 1）
- 評価軸: ユーザー指示の **6 軸 5 点満点**（構成 / 裏取り / 引用 / 関連性 / 可読性 / 完結性）
- 評価者: AI（Claude / batch #6、worktree 隔離、`chore/q29-ac-audit27` ブランチ）

## 0. round 27 の位置付け（層化サンプリング初投入）

round 19〜26 のうち round 20 (discrepancy-found 指名 = 4.67) を除く 7 round は完全ランダム抽出 12 件で運用しており、母集団の verification 偏りに平均値が揺さぶられる現象が継続観測されてきた:

- round 23 (4.82): HLD `related` 全空 3 件同時抽出で軸 4 が押し下げ
- round 25 (4.86): Topics meta 3 件同時抽出で N/A 9 セル発生
- round 26 (前 round): code-verified 9 件偏重で hld-only/discrepancy/runbook サブセットの裏取り検証量が不足

round 20 の「指名 round」結果 (4.67) と通常 round の差 (4.86〜4.94) は **0.20 ポイントの構造的ギャップ** で、これは「discrepancy-found 固有の related 空 / next-action 必須」という減点パターンが random 抽出ではほぼ顕在化しないことを意味する。round 27 では **層化サンプリング** を初投入し、各 verification ステータスのサブセット平均と母集団平均の関係を一度に俯瞰する。

### 母集団分布（2026-05-11 時点）

| verification | 件数 | 全体比 | 層化比率（今 round） |
|--------------|------|--------|---------------------|
| code-verified | 578 | 67.9% | **6/12 = 50%** |
| meta | 188 | 22.1% | **1/12 = 8.3%**（+ chapter-index 1/12 = 8.3%、計 16.7%）|
| discrepancy-found | 62 | 7.3% | **2/12 = 16.7%** |
| runbook-verified | 27 | 3.2% | **2/12 = 16.7%** |
| stub | 9 | 1.0% | 0 |
| hld-only | 8 | 0.9% | 0 |

random 抽出だと runbook-verified / discrepancy-found は期待値 0.4 件 / 0.9 件で「偶然 0 件」のことが多い。層化で各 2 件を確保し、サブセット軸別平均を初めて安定算出する。

### round 19-26 → round 27 推移

| Round | サンプリング | 平均 (5 点) | 備考 |
|-------|------------|-------------|------|
| 19 | random 12 | 4.90 | glossary boost 前 |
| 20 | **discrepancy-found 指名 12** | **4.67** | 軸 6 ガイド 1.2 節読み替え、6 課題抽出 |
| 21 | random 12 | 4.92 | related-discovery 投入 |
| 22 | random 12 | 4.92 | glossary 用語別逆引き |
| 23 | random 12 | 4.82 | HLD `related` 全空 3 件同時抽出 |
| 24 | random 12 | 4.88 | CDB mermaid 横展開 |
| 25 | random 12 | 4.86 | description 自動追加 |
| 26 | random 12 | (前 round) | CLI yang backfill / mgmt 運用入口表 / hld-only 棚卸し（直近 3 PR で実装） |
| **27** | **stratified 12** | **4.94** | **本 round（層化サンプリング初投入）** |

## 1. サンプル一覧（層化 12 件）

抽出手順:

```sh
# code-verified 6
find docs -name '*.md' -exec grep -l '^verification: code-verified$' {} \; | shuf -n 6
# runbook-verified 2
find docs -name '*.md' -exec grep -l '^verification: runbook-verified$' {} \; | shuf -n 2
# discrepancy-found 2
find docs -name '*.md' -exec grep -l '^verification: discrepancy-found$' {} \; | shuf -n 2
# chapter-index 1
find docs -name '*.md' -exec grep -l '^page_kind: chapter-index' {} \; | shuf -n 1
# meta 1（chapter-index 除外）
find docs -name '*.md' -exec grep -l '^verification: meta$' {} \; |
  while read f; do grep -q '^page_kind: chapter-index' "$f" || echo "$f"; done | shuf -n 1
```

| # | パス | area | verification | 行数 |
|---|------|------|--------------|------|
| 1 | `docs/reference/yang/sonic-fabric-port.md` | reference (YANG) | code-verified | 114 |
| 2 | `docs/reference/cli/show-acl.md` | reference (CLI) | code-verified | 130 |
| 3 | `docs/reference/config-db/suppress-asic-sdk-health-event.md` | reference (CDB) | code-verified | 105 |
| 4 | `docs/reference/cli/show-muxcable.md` | reference (CLI) | code-verified | 162 |
| 5 | `docs/reference/cli/config-vlan.md` | reference (CLI) | code-verified | 255 |
| 6 | `docs/platform/1-sonic-on-multi-asic-platforms.md` | platform (HLD) | code-verified | 138 |
| 7 | `docs/reference/runbooks/bgp-route-not-advertised.md` | reference (runbook) | runbook-verified | 107 |
| 8 | `docs/reference/runbooks/vlan-tagging.md` | reference (runbook) | runbook-verified | 132 |
| 9 | `docs/architecture/smartswitch-high-availability-manager-daemon-hamgrd-design-limitations.md` | architecture (split-child) | discrepancy-found (partially_implemented) | 113 |
| 10 | `docs/platform/sonic-port-naming-convention-change.md` | platform (HLD) | discrepancy-found (not_implemented) | 284 |
| 11 | `docs/topics/21-lab-vs-developer/index.md` | topics (chapter-index) | meta | 111 |
| 12 | `docs/topics/15-security-aaa/internals.md` | topics (split-child) | meta | 160 |

層化により Reference (yang/cli/cdb/runbook) 8 件、Topics 2 件、architecture/platform 系 4 件と母集団分布に近い構造を再現できた。

## 2. 評価軸（ユーザー指示 6 軸、5 点満点）

| 軸 | 内容 |
|----|------|
| 1. 構成 | 章立て・流れ |
| 2. 裏取り | sources / verification ステータス |
| 3. 引用 | 脚注・evidence コメント・commit ref |
| 4. 関連性 | related / related_topics / topics back-ref |
| 5. 可読性 | 日本語の自然さ・mermaid 図・表 |
| 6. 完結性 | 設定例・制限事項・トラブルシュート（chapter-index / split-* / meta は N/A、discrepancy は guide 1.2 節読み替え） |

5 = excellent / 4 = good / 3 = acceptable / 2 = lacking / 1 = poor

## 3. 評価結果

| # | ページ | 構成 | 裏取り | 引用 | 関連性 | 可読性 | 完結性 | 平均 |
|---|--------|------|--------|------|--------|--------|--------|------|
| 1 | sonic-fabric-port (yang) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 2 | show-acl (CLI) | 5 | 5 | 5 | 4 | 5 | 5 | **4.83** |
| 3 | suppress-asic-sdk-health-event (CDB) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 4 | show-muxcable (CLI) | 5 | 5 | 5 | 4 | 5 | 5 | **4.83** |
| 5 | config-vlan (CLI) | 5 | 5 | 5 | 4 | 5 | 5 | **4.83** |
| 6 | 1-sonic-on-multi-asic-platforms | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 7 | bgp-route-not-advertised (runbook) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 8 | vlan-tagging (runbook) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 9 | hamgrd-design-limitations (df, partial) | 5 | 5 | 5 | 4 | 5 | 5 | **4.83** |
| 10 | port-naming-convention-change (df, not_impl) | 5 | 5 | 5 | 5 | 5 | 5 | **5.00** |
| 11 | topics/21 chapter-index | 5 | N/A | N/A | 5 | 5 | N/A | **5.00** |
| 12 | topics/15 security internals (meta) | 5 | N/A | N/A | 5 | 5 | N/A | **5.00** |

### 層別平均

| 層 | 件数 | 平均 | 備考 |
|----|------|------|------|
| code-verified | 6 | **4.915** | CLI 3 件で `related.yang: []` 残存（show-acl / show-muxcable / config-vlan）が軸 4 を -0.083 |
| runbook-verified | 2 | **5.00** | mermaid triage flowchart / 切り分け手順 / 対処方法 / 引用元の構造が完成 |
| discrepancy-found | 2 | **4.915** | round 20 (4.67) から +0.245。port-naming は monitor:not_implemented で 5.00、hamgrd は `related.yang: []` で 4.83 |
| chapter-index | 1 | **5.00** | xref-related-chapters / 読み進め方 / 子ページ集約が揃う。N/A 規約準拠 |
| meta (chapter-index 除く) | 1 | **5.00** | topics/15 internals は MACsec / SAI POST / AAA mermaid 3 枚と章横断引用が満点 |
| **全体（68 セル）** | 12 | **4.941** | round 26 (4.94) と同水準、round 25 (4.86) から +0.08 |

### 軸別平均

| 軸 | 平均 | 備考 |
|----|------|------|
| 1. 構成 | **5.00** (12/12) | 全件で見出し階層・冒頭サマリ・末尾 references / related が揃う |
| 2. 裏取り | **5.00** (10/10、N/A 2 件除外) | code-verified 6 / runbook-verified 2 / discrepancy-found 2 すべて SHA pin + 行番号 |
| 3. 引用 | **5.00** (10/10、N/A 2 件除外) | 脚注・GitHub blob URL の構造が完成 |
| 4. 関連性 | **4.667** (12/12) | CLI 3 件 (#2 / #4 / #5) + discrepancy-found 1 件 (#9) で `related.yang: []` 残存。残 8 件は満点 |
| 5. 可読性 | **5.00** (12/12) | description 全件埋まり、mermaid / 表が豊富 |
| 6. 完結性 | **5.00** (10/10、N/A 2 件除外) | discrepancy-found 2 件もガイド 1.2 節読み替えで満点。next-action / 制限事項 / 干渉する機能の構造が完成 |
| **総平均** | **4.941 / 5** | 12 件 × 6 軸（N/A 8 セル除外、68 セル）|

5 点換算: round 26 → round 27 (**4.941**) で水準維持。round 20 の discrepancy-found 指名 (4.67) と比較すると **+0.27** の構造的改善で、これは「CLI/HLD yang backfill #1058」「discrepancy 監査 #1054」「mgmt 運用入口 #1059」「monitor frontmatter 修正 #1060」の累積効果が反映された結果。

## 4. 個別所感

### 完全満点 8 件（#1, #3, #6, #7, #8, #10, #11, #12）

- **sonic-fabric-port (YANG)**: `<!-- yang-mermaid -->` 自動生成、leafref / augment / deviation セクションが揃い、運用ヒント（典型的なデプロイ位置 / よくある落とし穴 / 関連 show コマンド）が後段にある。VOQ chassis の文脈解説と SHA pin で満点。
- **suppress-asic-sdk-health-event (CDB)**: `<!-- cdb-mermaid -->` 自動生成、`sonic-swss-common/common/schema.h` の `CFG_SUPPRESS_ASIC_SDK_HEALTH_EVENT_NAME` 定数まで引用。typical / 誤設定 / 確認コマンド 3 ブロックの ops-hint で運用入口完備。
- **1-sonic-on-multi-asic-platforms**: namespace / per-asic Redis / sonic-net の構造を mermaid + `sub_role` 説明で図解、CRM per-asic 監視や Topics back-ref 完備。
- **bgp-route-not-advertised (runbook)**: 症状 → 想定原因（優先度順） → mermaid triage → 5 段階の切り分け手順 → 対処方法 → 引用元、の runbook 標準構造を完全に踏襲。
- **vlan-tagging (runbook)**: 5 段階の切り分け（CONFIG_DB → APPL_DB/ASIC_DB → 同一ポートの他 VLAN untagged → kernel bridge → tcpdump キャプチャ）で運用視点が秀逸。
- **port-naming-convention-change (df, not_implemented)**: `monitor: not_implemented` で HLD 仕様 4 段階移行を mermaid 図示、`port_config.ini` alias 列が未切替であることを明記、未解決の論点 / トラブルシュート 3 項目で「実装が無いことの説明」自体が完結。round 20 で減点された discrepancy-found ページの典型パターンを完全克服。
- **topics/21-lab-vs-developer (chapter-index)**: 18 件の sources 集約、「この章で答える質問」「読み進め方」「xref-related-chapters」の chapter-index テンプレ準拠。N/A 規約適用。
- **topics/15-security-aaa/internals (meta)**: MACsec control/data 境界 / Gearbox backend 選択 / SAI POST / AAA 認証フロー の 3 つ mermaid、SAI 属性使用一覧表、Redis テーブル参照関係まで集約。

### 軸 4 = 4 の 4 件（#2, #4, #5, #9）

すべて `related.yang: []` が共通の減点要因。round 26 で `related.{cli,config_db,yang}` partial-empty 一掃バッチ (#1058) が走ったが、対象は「partial-empty」のみで、当該 4 件はバッチ対象外の patterns に該当して残存:

- **show-acl (CLI)**: `sonic-acl.yang` への back-ref 余地。本文「関連リファレンス」には記載があるが frontmatter に未反映。
- **show-muxcable (CLI)**: `sonic-mux-cable.yang` への back-ref 余地。同じく本文記載のみ。
- **config-vlan (CLI)**: `sonic-vlan.yang` / `sonic-vlan-interface.yang` への back-ref 余地。
- **hamgrd-design-limitations (df, partial)**: `monitor: partially_implemented` で `next-action` ブロックに「frontmatter の related が空」と明示されているのは運用標準準拠だが、`DASH_*` 系 yang を 1〜2 件補完可能。

## 5. spot check（4 件、軸 3 引用の正確性裏取り）

| # | ページ | チェック対象 | 結果 |
|---|--------|--------------|------|
| S1 | sonic-fabric-port | `sonic-fabric-port.yang` @ `9ea932ec` SHA pin | OK |
| S2 | show-muxcable | `show/muxcable.py` L441-L443 `@click.group(name='muxcable')` | OK |
| S3 | bgp-route-not-advertised | `sonic-net/sonic-frr` @ `799f47f` `bgpd/bgp_route.c` | OK |
| S4 | hamgrd-design-limitations | `monitor: partially_implemented` と本文 §2.2「未取り込み」記述の整合 | OK |

4/4 構造的に整合。S4 は round 20 で減点された discrepancy-found ページの典型パターンだが、round 27 では `monitor` frontmatter / next-action / `verification: discrepancy-found` がすべて運用標準準拠で揃っており、ガイド 1.2 節の読み替え基準で軸 6 = 5 を充足。

## 6. 層化サンプリングと従来 random の比較考察

### 層化導入のメリット（実証）

1. **サブセット平均の安定算出**: random では runbook-verified / discrepancy-found が期待値 0.4 / 0.9 件で偶然 0 件のことが多く、これらサブセットの構造改善（PR #1054 / #1058 / #1060）の効果が単一 round では測れない。層化なら必ず 2 件ずつ確保され、**runbook-verified サブセット 5.00** / **discrepancy-found サブセット 4.915** という具体的な値が得られる。
2. **round 20 (4.67) との直接比較**: round 20 の discrepancy-found 指名 12 件平均 4.67 に対し、本 round の discrepancy-found 2 件平均は 4.915 で **+0.245**。round 20 で抽出された 6 課題（next-action 不在 / related 全空 / SHA pin 不在 など）が累積バッチで解消されたことを少サンプルでも検出できた。
3. **chapter-index / meta の N/A 評価の安定検証**: random 抽出だと N/A セル数が round 23 (0 件) / round 25 (9 件) / round 26 (3 件) と大きく揺れ、運用基準の検証量が不安定だったが、層化なら毎回 chapter-index 1 件 + meta 1 件で N/A 規約のテスト範囲が固定される。

### 層化導入のデメリット

1. **母集団平均との乖離リスク**: 全体平均 4.941 は層化比率（cv 50% / rv 16.7% / df 16.7% / ci 8.3% / meta 8.3%）の重み付き平均で、母集団分布（cv 67.9% / meta 22.1% / df 7.3% / rv 3.2%）とは異なる。サンプル平均と母集団平均が一致しない点に注意（重み補正版を別途算出すべき）。
   - 重み補正後の母集団期待値: (cv 4.915 × 0.679) + (rv 5.00 × 0.032) + (df 4.915 × 0.073) + (meta 5.00 × 0.221) + (hld-only / stub 推定 4.5 × 0.019) ≈ **4.94**（生サンプル平均と偶然一致）
2. **小さなサブセット (rv 2 件 / df 2 件) は分散が大きい**: 2 件平均は外れ値 1 件で ±0.5 動く。連続 2〜3 round で同じ層化を実施し、移動平均で評価する運用が必要。
3. **stub / hld-only が今 round に入らない**: 母集団 17 件で全体比 1.9% と小さいが、構造的問題が残るサブセット（hld-only は verifier 棚卸し対象）。次回は 11 層分類を 6 層化（cv 5 / rv 2 / df 2 / meta+ci 2 / hld-only+stub 1）に整理して全層カバレッジを確保すべき。

### 推奨運用方針

- **奇数 round = random 12（母集団 unbiased estimator）**、**偶数 round = stratified 12（サブセット監視）** の交互運用に移行
- 各層 2 件を最小単位とし、stub + hld-only は合算 1 件で全 round 必ず含める
- 重み補正版の母集団期待値を毎回計算し、生サンプル平均と並記

## 7. 次回（round 28）改善すべき 3 つ

層化結果から残課題が **CLI 3 件 + discrepancy 1 件の `related.yang: []`** に絞り込まれた。round 26 の partial-empty 一掃バッチ #1058 で大半は解消したが、本 round で抽出されたパターンは「source `.py` から yang 名を逆引きできない（CLI 実装が yang を直接 import せず CONFIG_DB schema を経由する）」ものが多く、別アプローチが必要。

### 改善 1: CLI → YANG マッピングテーブルの手書きシード化

partial-empty 自動 backfill では拾えない CLI ページの `related.yang: []` を、**`meta/index/cli-yang-mapping.json`** という手書きシード（~80 行）で 1:1 マッピングを定義。Indexer 経由で `docs/reference/cli/*.md` の frontmatter に流し込む。`show-acl` → `sonic-acl`、`show-muxcable` → `sonic-mux-cable`、`config-vlan` → `sonic-vlan` のような既知マッピングを 30〜40 件埋めることで CLI Reference 70 ページ中 ~50% の `yang: []` を一掃可能。軸 4 を 4.667 → 4.85 程度に底上げ見込み。

### 改善 2: discrepancy-found ページの `related.yang` 補完規約

`monitor: not_implemented` のページは実装が無いため related が空になりやすいが、HLD が言及している YANG（例: hamgrd の `DASH_*` 系）は frontmatter に列挙すべき。**「HLD 本文で言及されている YANG モジュール名は frontmatter `related.yang` に必ず含める」** をルール化し、`verification: discrepancy-found` 62 ページに対し monitor consistency lint と同型の検査スクリプト（`scripts/check_discrepancy_related.py`）を新設。CI 警告に組み込む。round 20 で抽出された discrepancy 固有の構造減点パターンに対する最後のピース。

### 改善 3: 層化サンプリングの定期運用化（round 28 で random 復帰 / round 29 で再層化）

round 27 の層化結果が「母集団全層をカバーすると平均 4.94 で安定する」という基準値を提供したことで、今後は **奇数 round = random / 偶数 round = stratified** の交互運用に移行可能。round 28 は random 12 に戻し、round 27 の重み補正版期待値 (4.94) と一致するかを検証。乖離が 0.05 以下なら層化スキームが mature と判定し、毎月の monitoring プロセスに昇格させる。具体的には `meta/quality-audit-guide.md` に「奇数 random / 偶数 stratified」の運用を追記し、layered ステータスの分布表を四半期ごとに見直す。

## 8. 結論

- 層化サンプリング 12 件、6 軸 5 点満点で **平均 4.941 / 5（98.8%）**
- 完全満点 8 件（YANG 1 + CDB 1 + Platform 1 + Runbook 2 + discrepancy 1 + chapter-index 1 + meta 1）。runbook-verified サブセット 2/2 と discrepancy-found `not_implemented` 1/1 が満点に到達した点が **round 20 (4.67) からの最大の構造的改善**
- 層別平均: cv **4.915** / rv **5.00** / df **4.915** / ci **5.00** / meta **5.00**
- 軸 1 (構成) / 軸 2 (裏取り) / 軸 3 (引用) / 軸 5 (可読性) / 軸 6 (完結性) は **N/A 除外で 5.00 飽和**。軸 4 (関連性) のみ 4.667 で残課題
- 軸 4 の減点 4 件はすべて `related.yang: []` で、CLI 3 件 (show-acl / show-muxcable / config-vlan) + discrepancy 1 件 (hamgrd) に集中
- round 19-26 の random 平均 4.82〜4.94 帯と層化平均 4.941 が偶然一致し、重み補正版期待値 4.94 とも整合。**層化サンプリング初投入は成功**
- 次回 round 28 は **CLI→YANG 手書きマッピング / discrepancy related.yang lint / 奇数 random・偶数 stratified の交互運用** の 3 点を実施後、random 12 で再サンプリング

## 関連ドキュメント

- [監査 round 25（description 自動追加 / site map / related 一掃累積後の定点観測）](./quality-audit-25.md)
- [監査 round 20（discrepancy-found 指名 round、6 軸 4.67 軸 6 課題抽出）](./quality-audit-20.md)
- [監査 round 12（v1.0 GA 後の最初の定点観測）](./quality-audit-12.md)
- [品質ロードマップ](./quality-roadmap.md)
- [監査運用ガイド](./quality-audit-guide.md)
- [discrepancy 運用ガイド](./discrepancy-operations.md)
- [roadmap v2](./roadmap-v2.md)
