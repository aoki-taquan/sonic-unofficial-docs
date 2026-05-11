# 品質改善ロードマップ

作成日: 2026-05-11

## 1. 現状把握スナップショット

### 1.1 verification 分布 (全 docs/)

| status | 件数 |
|---|---|
| code-verified | 401 |
| meta | 164 |
| hld-only | 42 |
| discrepancy-found | 39 |
| stub | 10 |

- hld-only が 42 件残存 (前回 "0 件" を謳ったが再カウントで残骸あり)。`docs/system`、`docs/management`、`docs/architecture`、`docs/acl-qos` に偏在
- topics 配下 143 ページのうち verification frontmatter 付きは 2 ページのみ → topics 章は裏取り対象外として運用されている

### 1.2 area 別ページ数

| area | ページ数 |
|---|---|
| reference | 167 |
| topics | 143 |
| system | 72 |
| routing | 52 |
| management | 44 |
| platform | 44 |
| architecture | 42 |
| acl-qos | 32 |
| switching | 20 |
| internals | 13 |
| categories | 11 |
| overlay | 10 |
| guides | 5 |
| _meta | 1 |

合計 656 ページ。

### 1.3 Topics 22 章の構成

全 22 章に index/concept/setup/operations/internals/architecture(+ advanced) の 5〜7 ページ構成。
平均ページ長 40〜60 行と短く、HLD 翻訳調の概念説明が中心。`setup.md` の具体例(JSON / show 出力)が薄く、`internals.md` のコード参照(orchagent / SAI の行番号)が手薄。

### 1.4 Reference カバー率 (meta/reference-gaps.md より)

| 種別 | 既存 / 全体 | カバー率 | 未カバー数 |
|---|---|---|---|
| CLI groups | 44 / 110 | 40.0% | 66 |
| CONFIG_DB tables | 64 / 207 | 30.9% | 143 |
| YANG modules | 29 / 136 | 21.3% | 107 |

high 重要度の未カバーが、CLI 18 / CONFIG_DB 21 / YANG 20 候補挙がっており、次バッチで即着手可能。

### 1.5 既存メタの残課題

- `meta/restructure-plan.md` (539 行): 階層再編プラン (一部実装済み、guides/categories/topics は完了)
- `meta/topics-plan-{feature,layer,usecase}.md`: トピック章 22 件は完了。各章の "深掘り" は未着手
- `meta/verification-queue.json` + `meta/queue/`: per-page queue に移行済み

## 2. 改善候補 (12 件)

| # | 候補 | 価値 | 工数 | 既存資産活用 | 優先度 |
|---|---|---|---|---|---|
| C1 | hld-only 残 42 件の裏取り → code-verified / discrepancy-found 昇格 | 高 (verifier 信頼性) | M | Verifier プロンプト + per-page queue 流用 | **High** |
| C2 | topics 22 章の `setup.md` 強化 (CLI コマンド + JSON 例 + show 出力 3 点セット) | 高 (運用者) | L | 既存 CLI/CONFIG_DB Ref とリンク | **High** |
| C3 | topics 22 章の `internals.md` 強化 (orchagent / swssconfig / SAI コード参照 + シーケンス図) | 高 (開発者) | L | `.cache/sonic-sources` の sonic-swss / sonic-sairedis | **High** |
| C4 | CLI Ref 未カバー high 18 件 (`config buffer*` / `config qos` / `config vnet` / `show cli pfc*` / `show cli queue` 等) | 中〜高 (評価者) | M | reference-gaps.md にリスト済 | **High** |
| C5 | CONFIG_DB Ref 未カバー high 21 件 (`VNET*` / `NAT*` / `PBH*` / `BGP_GLOBALS_AF*` / `DHCP_*` 等) | 中〜高 (開発者) | M | reference-gaps.md + YANG modules | **High** |
| C6 | YANG Ref 未カバー high 20 件 (`sonic-vnet` / `sonic-pbh` / `sonic-spanning-tree` 等) | 中 (開発者) | M | reference-gaps.md | Medium |
| C7 | `reference/runbooks/` 新設 (症状逆引き 10-15 件: "BGP が落ちた" / "PFC storm" / "warm-reboot で trap が抜ける" 等) | 高 (運用者) | M | discrepancies.md + 既存 ops ページ | **High** |
| C8 | `_meta/discrepancies.md` を per-discrepancy 詳細ページ化 + GitHub Issue 外部リンク追加 | 中 (評価者) | S | 既存 39 ページの discrepancy-found 集約 | Medium |
| C9 | `reference/verification/coverage.md` 自動生成 (verification 分布 + area 別カバレッジ + hld-only 残一覧) スクリプト追加 | 中 (運用継続) | S | grep + meta/scripts/ | Medium |
| C10 | categories 横断ページ 11 件の充実 (現状は index 風で薄い、ユースケース横断の解説に再構成) | 中 (読み手) | M | 既存 topics / area ページへのリンクハブ | Medium |
| C11 | area 配下 HLD 翻訳調ページのリライト (architecture / system に多い長文翻訳調 30 件超を query-driven 構成へ) | 中 (品質) | L | 既存ページ流用 | Low |
| C12 | 大型 HLD の章単位分割 (MCLAG / DASH / EVPN-VXLAN / SmartSwitch HA を派生 slug で詳細化) | 中 (読みやすさ) | L | 既存大ページの分解 | Low |

価値: 高=複数ペルソナに直撃 / 中=単一ペルソナまたは間接 / 低=メンテ性。
工数: S=1-3 ページ / M=8-20 ページ / L=20+ ページ。

## 3. 推奨ロードマップ (次 1〜2 イテレーション)

### イテレーション A (次バッチ、8 並走)

ターゲット: 即効性が高く・並走衝突しないものを集約。

| 並走スロット | 担当 | 内容 | 期待アウトプット |
|---|---|---|---|
| A1 | Verifier #28 | C1 hld-only 残 42 件のうち architecture/acl-qos 領域 ~15 件 | 15 ページ昇格 |
| A2 | Verifier #29 | C1 hld-only 残のうち system/management 領域 ~15 件 | 15 ページ昇格 |
| A3 | Verifier #30 | C1 hld-only 残のうち switching/platform/internals/routing 領域 ~12 件 | 12 ページ昇格 |
| A4 | Writer 配下 | C4 CLI Ref `config buffer*` / `config qos` / `config pfcwd` / `config vnet` / `config warm_restart` (5 ページ) | 5 ページ新規 |
| A5 | Writer 配下 | C4 CLI Ref `show cli pfc` / `pfcwd` / `priority-group` / `queue` / `buffer` / `buffer_pool` / `lldp` / `bfd` / `mgmt-vrf` (9 ページ) | 9 ページ新規 |
| A6 | Writer 配下 | C5 CONFIG_DB `VNET` / `VNET_ROUTE` / `VNET_ROUTE_TUNNEL` / `STATIC_ROUTE` / `VLAN_SUB_INTERFACE` / `NAT_GLOBAL` / `NAT_POOL` / `NAT_BINDINGS` / `STATIC_NAT` / `STATIC_NAPT` (10 ページ) | 10 ページ新規 |
| A7 | Writer 配下 | C5 CONFIG_DB `PBH_TABLE` / `PBH_RULE` / `PBH_HASH` / `PBH_HASH_FIELD` / `PORT_QOS_MAP` / `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` / `MAP_PFC_PRIORITY_TO_QUEUE` / `DHCP_SERVER` / `DHCP_RELAY` / `BGP_GLOBALS_AF` / `LLDP` (11 ページ) | 11 ページ新規 |
| A8 | Writer 配下 | C9 `meta/scripts/gen_coverage.py` + `docs/reference/verification/coverage.md` 自動生成 PR | スクリプト + 1 ページ |

衝突回避:
- A1/A2/A3 は領域分離 (Verifier 系で per-page queue を別領域に分ける)
- A4-A7 は新規ファイル作成のみ。既存ファイルを触らない
- A8 は `meta/scripts/` + `docs/reference/verification/` 新設、他と非干渉

期待される merge 数: ~78 ページ + 1 スクリプト。

### イテレーション B (その次、8 並走)

ターゲット: 深掘り系 (topics 強化 + runbooks)。

| 並走スロット | 担当 | 内容 |
|---|---|---|
| B1 | Topic Writer | C2 topics 02-bgp / 03-vxlan-evpn / 04-vrf-ecmp `setup.md` 強化 (CLI + JSON + show 3 点セット) |
| B2 | Topic Writer | C2 topics 06-l2-vlan-lag / 07-acl-copp-mirror / 08-qos-buffer `setup.md` 強化 |
| B3 | Topic Writer | C2 topics 09-telemetry-snmp / 10-gnmi-openconfig / 11-reboot / 15-security-aaa `setup.md` 強化 |
| B4 | Topic Writer | C3 topics 02-bgp / 06-l2-vlan-lag / 07-acl-copp-mirror / 20-swss-sai-redis `internals.md` 強化 (orchagent / SAI 行番号 + mermaid シーケンス) |
| B5 | Topic Writer | C3 topics 03-vxlan-evpn / 04-vrf-ecmp / 08-qos-buffer / 11-reboot `internals.md` 強化 |
| B6 | Runbook Writer | C7 `reference/runbooks/` 新設 + 5 件 (bgp-down / pfc-storm / warmreboot-trap-loss / fast-reboot-timeout / orchagent-stuck) |
| B7 | Runbook Writer | C7 残り 5-10 件 (vxlan-tunnel-down / lag-flap / nat-conn-table-full / dhcp-relay-fail / sai-asic-crash / ...) |
| B8 | Discrepancy Writer | C8 `_meta/discrepancies/<slug>.md` 個別ページ 39 件のうち代表 10 件 + 上流 Issue 検索リンク |

衝突回避:
- B1-B5 は topics の異なる章を扱う (slug 単位で割当)
- B6-B7 は新規 `runbooks/` ディレクトリ
- B8 は `_meta/discrepancies/` 配下のみ

期待される merge 数: ~50 ページ強化 + 15 ページ新規。

## 4. 当面着手しないもの (Defer)

- C11 area HLD 翻訳調リライト: ボリューム大 (30+) + 読み手要望が薄い。discrepancy が判明している箇所のみピンポイントで C8 内で扱う
- C12 大型 HLD 分割: 既存ページが読みにくいわけではない (mermaid + 章節構成済み)。当面保留
- C6 YANG Ref 未カバー: C5 と内容重複が大きいので C5 完走後に評価
- C10 categories 強化: 読者導線として acceptable な現状。topics 強化 (C2/C3) を優先

## 5. 成功基準

イテレーション A 完走後:
- hld-only ページ: 42 → 0
- CLI Ref カバー率: 40.0% → 52.7% (44 → 58)
- CONFIG_DB Ref カバー率: 30.9% → 41.1% (64 → 85)
- coverage.md ページが mkdocs build に含まれている

イテレーション B 完走後:
- topics 22 章のうち setup.md / internals.md が "show 出力 + コード参照" を含むページ: 0 → 8 以上
- runbooks: 0 → 10+ ページ
- discrepancies 個別ページ: 0 → 10+

## 6. 次にやるべきこと (この PR merge 直後)

1. イテレーション A の A1 (Verifier) を 3 並走で kick — hld-only 42 件の領域別バッチ
2. 並行して A4-A7 (Writer 系 4 並走) を kick — Reference 新規ページ 35 件
3. A8 (coverage 自動生成) を最後に kick — A1-A7 の結果がデータに入る

監視:
- 各サブエージェントが `meta/queue/<slug>.json` を使う
- main 直 push 禁止、PR 経由
- 並走中の `meta/verification-queue.json` 直接編集禁止
