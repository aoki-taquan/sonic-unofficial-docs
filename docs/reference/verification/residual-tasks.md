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

本プロジェクトは v1.0 GA（2026-05-11）到達済みで、以下に挙げる残課題はいずれも **品質ゲートを通過する範囲の low-impact 項目** である。本ページは現時点の数値スナップショットを記録し、次回 iteration（v1.1 サイクル）で取捨選択するための入力として使う。

更新は **手動運用** とする（自動更新フックは v1.1 以降で検討）。再生成時は本ページの「数値の取得元コマンド」セクションのコマンドを順に実行すれば良い。

## 1. backlog 残数（`meta/backlog/<area>/`）

| area | 件数 |
|------|------|
| architecture | 19 |
| system | 10 |
| routing | 5 |
| platform | 4 |
| acl-qos | 1 |
| internals | 1 |
| management | 1 |
| switching | 1 |
| **合計** | **42** |

`architecture` と `system` に偏っており、いずれも generic-name / introduction 系の低品質 stub が中心。Indexer 段で除外ルールを足すか、v1.1 で個別精査するかは未決定。

## 2. discrepancy-found ページの monitor 別分布

`verification: discrepancy-found` のページは合計 **62 件**。monitor 別内訳:

| monitor | 件数 | 性質 |
|---------|------|------|
| `partially_implemented` | 27 | HLD のうち一部だけ取り込まれ、残りは欠落 |
| `evolved_beyond_hld` | 21 | 実装が HLD から進化し、名前 / 構造 / 経路が異なる |
| `not_implemented` | 11 | HLD は提案段階で、master に対応コードが一切無い |
| `deprecated` | 3 | HLD の方針自体が廃止 |

四半期サイクルでの再裏取り対象は `partially_implemented` + `evolved_beyond_hld` + `not_implemented` = **59 件**。`deprecated` 3 件は半年サイクル。

## 3. lint スクリプトの検出残数

| スクリプト | 検出件数 | 種別 | 備考 |
|-----------|---------|------|------|
| `check_broken_links.py` | 0 | error | OK |
| `check_pages_integrity.py` | 0 | error | OK |
| `check_runbook_status.py` | 0 | error | 52 runbook 全て valid |
| `check_monitor_consistency.py` | 0 | warn | suspects 0 |
| `check_link_density.py` | 0 | warn | low/high とも 0、870 ページ評価 |
| `check_citation_quality.py` | 0 | warn | citation-deficient 0 |
| `check_stale_verified.py` | 0 | warn | 90 日超 0 件 |
| `check_discrepancy_related.py` | 0 | warn | discrepancy-found 62 件、空 related.yang 0 |
| `check_verification_self_consistency.py` | **112** | info | code-verified ページ本文中の「未対応 / 未実装 / 未確認 / 要確認」記述。多くは仕様注記として意図的 |
| `check_sources_freshness.py` | - | info | pinned SHA は全リポ origin/master に追従（drift 0） |

`check_verification_self_consistency.py` の 112 件のみが残課題的ボリュームだが、内容を読むと「実装は code-verified だが、ある option は HLD で proposed のまま」のような **意図的注記** が大半。個別に精査して discrepancy-found へ降格すべきものを洗い出すのは v1.1 タスク。

## 4. Topics サブページ未完成残数

`meta/scripts/gen_chapter_progress.py --check` の結果:

| chapter | placeholder | missing |
|---------|------------|---------|
| 01-overview | 0 | 2 |
| 19-build-packaging | 0 | 1 |
| 22-reference-index | 1 | 2 |
| その他 19 章 | 0 | 0 |

合計 **未完成サブページ 6 件**（placeholder 1 + missing 5）。22 章中 19 章は complete。22-reference-index は性質上 reference ハブで自由度が高いため低優先。

## 5. 大型 HLD 未分割ページ Top 5

行数ベース（`_meta/` を除く）で章単位分割の候補:

| 行数 | パス | 検討候補 |
|------|------|---------|
| 392 | `docs/acl-qos/enhancements-to-add-or-del-ports-dynamically.md` | ACL port-add/del flow を operation 別に分割 |
| 386 | `docs/switching/switch-port-modes-and-vlan-cli-enhancement.md` | port modes / VLAN CLI を独立サブページ化 |
| 377 | `docs/overlay/active-standby-dual-tor.md` | DualToR の linkmgrd / mux / orchagent 章を分割 |
| 371 | `docs/platform/fec-flr-support-in-sonic.md` | FEC と FLR を別ページに分離 |
| 371 | `docs/overlay/vxlan-sonic.md` | VXLAN の data-plane / control-plane / EVPN 連携を分離 |

いずれも v1.0 内では「読める長さ」と判断したが、roadmap-v2（v1.2 多言語化）の前に章単位分割しておく方が翻訳コストが下がる。

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
         check_monitor_consistency check_link_density check_citation_quality \
         check_stale_verified check_discrepancy_related \
         check_verification_self_consistency; do
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
