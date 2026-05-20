---
title: low-impact 残課題スナップショット
description: "low-impact 残課題のスナップショット"
verification: meta
last_verified: 2026-05-12
tags:
  - meta
  - verification
  - residual
related:
  cli: []
  config_db: []
  yang: []
  _no_related: true
---

# low-impact 残課題スナップショット

以下に挙げる残課題はいずれも **品質ゲートを通過する範囲の low-impact 項目** である。本ページは現時点の数値スナップショットを記録し、次回 iteration で取捨選択するための入力として使う。

更新は **手動運用** とする（自動更新フックは将来的に検討）。再生成時は本ページの「数値の取得元コマンド」セクションのコマンドを順に実行すれば良い。

**最終更新**: 2026-05-12（round 48 stratified 5.00 飽和達成・lint 9 種運用・wave-2 30 件補完バッチ後）。

## 1. backlog 残数（`meta/backlog/<area>/`）

| area | 件数 |
|------|------|
| system | 7 |
| platform | 2 |
| architecture | 1 |
| **合計** | **10** |

**2026-05-12 round 48 update**: backlog 残数は round 38 から **完全 KEEP**（system 7 / platform 2 / architecture 1 = 計 10 件）。round 48 までの 10 round で新規 backlog 流入 0 件。`_archived` は **349 件** に増加（整理で +27 件、indexer v2 の除外フィルタ強化で stub 自動 archive）。

| カテゴリ | 件数 | 処理方針 |
|----------|------|----------|
| low-priority（将来検討） | 10 | 大型 HLD 4 件 + telemetry / openconfig 3 件 + [PINS](../../reference/glossary.md#term-pins) / chassis 2 件 + 第三者拡張 1 件 |
| _archived（累計） | 349 | リリースノート + 章節断片 + ビルド系 + テンプレ + 重複 + defer + stub + indexer v2 除外（round 36 以前の 27 件 + 増分） |

詳細は [`meta/backlog/README.md`](https://github.com/aoki-taquan/sonic-unofficial-docs/blob/main/meta/backlog/README.md) を参照。`meta/_gen_backlog.py` への Indexer 除外フィルタ組込みは次回 iteration 開始時に対応する。

## 2. discrepancy-found ページの monitor 別分布

`verification: discrepancy-found` のページは合計 **74 件**（round 38 比 +12 件、round 46 比 +12 件、partial subtype 派生 split-child を主因に増加）。monitor 別内訳:

| monitor | 件数 | 性質 |
|---------|------|------|
| `partially_implemented` | 39 | [HLD](../../reference/glossary.md#term-hld) のうち一部だけ取り込まれ、残りは欠落 |
| `evolved_beyond_hld` | 21 | 実装が HLD から進化し、名前 / 構造 / 経路が異なる |
| `not_implemented` | 11 | HLD は提案段階で、master に対応コードが一切無い |
| `deprecated` | 3 | HLD の方針自体が廃止 |

四半期サイクルでの再裏取り対象は `partially_implemented` + `evolved_beyond_hld` + `not_implemented` = **71 件**。`deprecated` 3 件は半年サイクル。`not_implemented` 系は round 48 で投入された `check_ni_workaround_depth.py` lint により workaround 章の最低 2 経路を warning 階段運用中、round 49 で blocking 化予定。

## 3. lint スクリプトの検出残数

各スクリプトを `--check` モードで実行した最新結果（2026-05-12）:

| スクリプト | 検出件数 | 種別 | 備考 |
|-----------|---------|------|------|
| `check_broken_links.py` | **20** | info | `#term-syslog` anchor 不在の runbook 群（glossary 側に term-syslog 定義を追加すれば一括解消） |
| `check_pages_integrity.py` | 0 | error | missing=0 orphans=0 duplicates=0 |
| `check_runbook_status.py` | 0 | error | 52 runbook 全て valid |
| `check_runbook_structure.py` | 0 | error | 52 runbook 全て 5 章揃い |
| `check_monitor_consistency.py` | **2** | warn | `enhancements-to-add-or-del-ports-dynamically-operations` + `switch-port-modes-and-vlan-cli-internals` で partially_implemented キーワード不足 |
| `check_link_density.py` | **8** | warn | low-density 8 件（low/high とも閾値外）、890 ページ評価。high-density 0 件 |
| `check_citation_quality.py` | **1** | warn | citation-deficient 1 件 |
| `check_stale_verified.py` | 0 | warn | 90 日超 0 件 |
| `check_discrepancy_related.py` | 0 | warn | discrepancy-found 74 件、空 related.yang 0（`--strict` モード） |
| `check_partial_boundary.py` | 0 | warn | partial-boundary suspects 0（round 38 strict 化以降 10 round 連続 0）|
| `check_limitations_section.py` | **34** | info | 制限事項章が薄い HLD のリスト（split-child 派生 + 大型 HLD 内訳。round 46 比 -5 件 = wave-2 補完バッチで縮小）|
| `check_troubleshoot_section.py` | **190** | info | トラブルシュート章が薄い HLD のリスト（round 46 比 -30 件 = wave-2 補完バッチ効果）|
| `check_ni_workaround_depth.py` | 0 | warn | `not_implemented` 11 件全件で workaround 経路 ≥2 充足（warning 階段運用、round 49 で blocking 化予定）|
| `check_verification_self_consistency.py` | **114** | info | code-verified ページ本文中の「未対応 / 未実装 / 未確認 / 要確認」記述。多くは仕様注記として意図的（round 46 比 +2 件）|
| `check_sources_freshness.py` | - | info | pinned SHA は全リポ origin/master に追従（drift 0） |

**注目 1 — `check_broken_links.py` 20 件**: 全件 `#term-syslog` anchor 不在の runbook 群。`docs/reference/glossary.md` に `syslog` 用語の anchor を追加すれば一括解消（quick win 候補）。

**注目 2 — `check_troubleshoot_section.py` 190 件 → wave-2 補完で減**: round 46 で約 220 件、round 48 で 190 件に縮小。wave-2 30 件補完バッチが直接効果。残 190 件のうち深刻なものは limitations と重複する 34 件。

**注目 3 — `check_verification_self_consistency.py` 114 件のみが残課題的ボリューム**: 個別に精査して discrepancy-found へ降格すべきものを洗い出すのは次回 iteration タスク。round 49 改善 3 で triage スクリプト `triage_self_consistency.py` 試作予定。

**注目 4 — `check_ni_workaround_depth.py` 0 件**: round 46 改善 1 で warning 階段運用開始、round 48 stratified で `not_implemented` 11 件全件 workaround 経路 ≥2 充足を確認。round 49 で blocking 化最終確定予定（`--thin` lint と同じ 2 iteration ルール）。

## 4. Topics サブページ未完成残数

`meta/scripts/gen_chapter_progress.py --check` の結果（2026-05-12）:

| chapter | complete | placeholder | missing |
|---------|---------|------------|---------|
| 01-overview 〜 22-reference-index（全 22 章）| 5 | 0 | 0 |
| **合計** | **110** | **0** | **0** |

**round 48 update**: Topics 22 章 × 5 split-child = **110 サブページ全件 complete**。round 38 時点の 6 件残（01-overview 2 / 19-build-packaging 1 / 22-reference-index 3）が **wave-2 30 件補完バッチに合流して全件解消**、Topics 章は構造的に完成。直近 5 commit (`#841-#845`) で残章 ([BGP](../../reference/glossary.md#term-bgp) / L2-VLAN-[LAG](../../reference/glossary.md#term-lag) / ACL-[CoPP](../../reference/glossary.md#term-copp)-Mirror / [VRF](../../reference/glossary.md#term-vrf)-[ECMP](../../reference/glossary.md#term-ecmp) / [VXLAN](../../reference/glossary.md#term-vxlan)-[EVPN](../../reference/glossary.md#term-evpn)-[VNET](../../reference/glossary.md#term-vnet)) も full topic chapter として merge 済み。

## 5. 大型 HLD 未分割ページ Top 5

行数ベース（`docs/reference/glossary.md` 2136 行と `docs/_meta/` 系を除く）で章単位分割の候補（2026-05-12 計測）:

| 行数 | パス | 検討候補 |
|------|------|---------|
| 429 | `docs/acl-qos/enhancements-to-add-or-del-ports-dynamically.md` | [ACL](../../reference/glossary.md#term-acl) port-add/del flow を operation 別に分割 |
| 412 | `docs/switching/switch-port-modes-and-vlan-cli-enhancement.md` | port modes / [VLAN](../../reference/glossary.md#term-vlan) CLI を独立サブページ化 |
| 390 | `docs/management/gnsi-hld.md` | gNSI accountz / authz / certz / pathz の章別分割 |
| 380 | `docs/architecture/ssdhealth-design.md` | SSD health 監視 daemon 構造を制御プレーン / モニタリング別に分離 |
| 378 | `docs/internals/l3-scaling-and-performance-enhancements.md` | L3 性能強化 4 系統を split-child 派生（**round 47 で 1 件 split-child 派生済**、本体行数 +7 増分は反映遅延）|
| 377 | `docs/overlay/active-standby-dual-tor.md` | DualToR の [linkmgrd](../../reference/glossary.md#term-linkmgrd) / mux / [orchagent](../../reference/glossary.md#term-orchagent) 章を分割 |

**round 48 update**: round 38 時点の Top 5 (`fec-flr-support-in-sonic` 371 / `vxlan-sonic` 371) は **wave-2 補完で章追加** により 410 行付近まで増加して新 Top 5 圏内に再エントリ可能。本気で章単位分割するのは多言語化前（2026-Q4）に再判定。

## 数値の取得元コマンド

本ページの数値は以下の手順で再生成できる（worktree 内 / `.venv` 有効化済み前提）。

```bash
# 1. backlog
for d in meta/backlog/*/; do echo "$(basename $d): $(ls $d*.json 2>/dev/null | wc -l)"; done

# 2. discrepancy monitor breakdown
grep -lE '^verification: discrepancy-found' -r docs/ \
  | xargs -I{} awk '/^monitor:/ {print $2; exit}' {} \
  | sort | uniq -c | sort -rn

# 3. lint
for s in check_broken_links check_pages_integrity check_runbook_status \
         check_runbook_structure check_monitor_consistency check_link_density \
         check_citation_quality check_stale_verified check_discrepancy_related \
         check_partial_boundary check_limitations_section \
         check_troubleshoot_section check_ni_workaround_depth \
         check_verification_self_consistency check_sources_freshness; do
  echo "=== $s ==="; python meta/scripts/$s.py --check 2>&1 | tail -3
done

# 4. chapter progress
python meta/scripts/gen_chapter_progress.py --check

# 5. largest pages
find docs -name '*.md' -not -path 'docs/_meta/*' -exec wc -l {} + \
  | sort -rn | head -10
```

## 関連ページ

- [裏取り運用方針](index.md)
- [HLD と実装の乖離 一覧](discrepancy-index.md)
- [sources-freshness](sources-freshness.md)
- [stale-verified](stale-verified.md)

## 関連スナップショット

- [スナップショット](../../_meta/snapshot.md) — repo 全体の verification / coverage / lint 指標を 1 ページに集約した自動生成サマリ。本ページの残課題が全体指標のどの位置にあるか俯瞰する用途。

<!-- glossary-links-injected: c88af9cfd6d0 -->
