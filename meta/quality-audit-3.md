# 品質改善サンプリング監査（round 3）

- 実施日: 2026-05-11
- 対象: イテレーション C (PR #903-910) で merge されたコンテンツ
  - Topics setup 強化 4 PR (#904/905/906/907): 19 章 / +3178 行
  - Topics internals 強化 1 PR (#910): 22 章 / +1689 行
  - reference/runbooks/ 新設 1 PR (#909): 症状逆引き 15 件
  - discrepancy 個別ページ 10 件深掘り 1 PR (#908)
  合計約 66 件のページ強化・新設
- サンプル数: 15 件
  - setup 強化 4 章 (S1-S4)
  - internals 強化 4 章 (I1-I4)
  - Runbook 4 件 (R1-R4)
  - discrepancy 深掘り 3 件 (D1-D3)
- 評価者: AI (Claude / batch #6)

## 1. サンプル

### Topics setup 強化 (4)

| # | パス | 行数 |
|---|------|------|
| S1 | `docs/topics/02-bgp/setup.md` | 243 |
| S2 | `docs/topics/03-vxlan-evpn/setup.md` | 255 |
| S3 | `docs/topics/07-acl-copp-mirror/setup.md` | 298 |
| S4 | `docs/topics/10-gnmi-openconfig/setup.md` | 218 |

### Topics internals 強化 (4)

| # | パス | 行数 |
|---|------|------|
| I1 | `docs/topics/02-bgp/internals.md` | 47 |
| I2 | `docs/topics/03-vxlan-evpn/internals.md` | 107 |
| I3 | `docs/topics/08-qos-buffer/internals.md` | 150 |
| I4 | `docs/topics/12-multi-asic-voq/internals.md` | 107 |

### Runbook (4)

| # | パス |
|---|------|
| R1 | `docs/reference/runbooks/bgp-session-down.md` |
| R2 | `docs/reference/runbooks/pfc-bandwidth.md` |
| R3 | `docs/reference/runbooks/dualtor-mux.md` |
| R4 | `docs/reference/runbooks/sai-failure.md` |

### discrepancy 深掘り (3)

| # | パス |
|---|------|
| D1 | `docs/internals/l3-scaling-and-performance-enhancements.md` |
| D2 | `docs/architecture/error-handling-framework-in-sonic.md` |
| D3 | `docs/system/warmboot-manager-hld.md` |

## 2. 評価軸（5 段階）

- A. 情報密度（重複・水増しが少ないか）
- B. 実用性（読み手が次にとる行動が明確か）
- C. 正確性（コード・スキーマ・引用が現行 master と一致するか）
- D. 読みやすさ（見出し・表・コードブロックの構造）
- E. HLD 翻訳調解消（受動表現の連鎖・原文の直訳臭の不在）

## 3. 評価結果

| ID | A | B | C | D | E | 平均 | 備考 |
|----|---|---|---|---|---|------|------|
| S1 (bgp/setup) | 5 | 5 | 5 | 5 | 5 | 5.00 | 3 シナリオ × (CLI / JSON / show) の三段で完結。CONFIG_DB のキー形式 `default\|10.0.0.0` も正確 |
| S2 (vxlan-evpn/setup) | 5 | 5 | 5 | 5 | 5 | 5.00 | `ctx.fail()` 由来のエラーメッセージ表が秀逸。削除順序「add の逆順」の明文化が実用 |
| S3 (acl-copp-mirror/setup) | 5 | 5 | 5 | 5 | 5 | 5.00 | `acl_loader/main.py` の `AclLoaderException` 文字列を 12 件抜粋、コード照合済 |
| S4 (gnmi-openconfig/setup) | 4 | 5 | 5 | 4 | 5 | 4.60 | gNMI/gNOI/gNSI の 3 ロール分けは丁寧。やや章数多めで密度がわずかに散る |
| I1 (bgp/internals) | 3 | 3 | 4 | 4 | 5 | 3.80 | 47 行と短い。orchagent/fpmsyncd の責務表はあるが、SAI 属性表は欠落 |
| I2 (vxlan-evpn/internals) | 4 | 4 | 5 | 5 | 5 | 4.60 | EVPN Type 表と orchagent の責務分担が明快 |
| I3 (qos-buffer/internals) | 5 | 5 | 5 | 5 | 5 | 5.00 | データフロー・SAI 属性表・Redis テーブル参照表・既知制約の四段が完備。round 3 の最高峰 |
| I4 (multi-asic-voq/internals) | 4 | 5 | 5 | 5 | 5 | 4.80 | `sources: []` で空、frontmatter 未充足だが本文は密。-0.5 で済む |
| R1 (bgp-session-down) | 5 | 5 | 5 | 5 | 5 | 5.00 | 「状態 ↔ 原因」マトリクスと `sonic-db-cli` 切り分けコマンドが揃う。frrcfgd template path も具体 |
| R2 (pfc-bandwidth) | 5 | 5 | 5 | 5 | 5 | 5.00 | Rx/Tx PFC counter の意味解釈が読み手を救う |
| R3 (dualtor-mux) | 4 | 5 | 5 | 5 | 5 | 4.80 | linkmgrd / HW / state-db 三層の整合確認が実用。YANG 欄が空のままなのは元々無いため許容 |
| R4 (sai-failure) | 5 | 5 | 5 | 5 | 5 | 5.00 | CRM 閾値・SAI status code → 対処の連結が筋良し |
| D1 (l3-scaling) | 5 | 5 | 5 | 5 | 5 | 5.00 | 行番号 + コード抜粋 + 影響 + 回避策コマンド + GitHub PR の 5 要素 |
| D2 (error-handling) | 5 | 5 | 5 | 5 | 5 | 5.00 | `SWSS_RC_*` enum のみ採用・`ERROR_DB` 未実装の明示で読み手の誤解を強力に防止 |
| D3 (warmboot-manager) | 4 | 5 | 5 | 5 | 5 | 4.80 | Google 提案 daemon 未マージの結論が明快。深掘りセクション内の repo 行番号引用がやや少ない |

**平均: 4.84 / 5.0** （15 件、計 75 軸）

## 4. 引用された実コード行番号 spot check

| 引用元 | 主張 | 実機照合 | 結果 |
|--------|------|----------|------|
| S2 vxlan/setup | `sonic-utilities/config/vxlan.py` `ctx.fail("VTEP already configured.")` | L45 で完全一致 | OK |
| S3 acl/setup | `sonic-utilities/acl_loader/main.py` `AclLoaderException("Session %s does not exist")` | L380 完全一致 / `Table {} does not exist` L522 完全一致 / `Unknown rule action` L506 完全一致 | OK |
| I3 qos/internals | `orchagent/bufferorch.cpp` / `orchagent/pfcwdorch.cpp` / `orchagent/qosorch.cpp` の path 主張 | 3 path とも `.cache/sonic-sources/sonic-swss/orchagent/` 配下に実在 | OK |
| I4 voq/internals | `orchagent/fabricportsorch.cpp` の `FabricPortsOrch` 責務主張 | path 実在 | OK |
| D1 l3-scaling | `sonic-buildimage/files/image_config/sysctl/90-sonic.conf` L21-L26 の sysctl 6 行 | L21-L26 完全一致 (v4/v6 共通で 1024/2048/4096) | OK |

参考: D1 が `routeorch.cpp` L41 と明示している RouteOrch コンストラクタの実位置は L40 開始。1 行ずれだが内容は一致しており、引用としての信頼性は維持。

5/5 spot check pass。round 2 の 5/5 と同水準で、コード裏取りは堅牢。

## 5. round 1 / 2 / 3 比較トレンド

| round | 平均 | サンプル | 主な強み | 主な弱み |
|-------|------|----------|----------|----------|
| 1 | 4.60 | 10 | Operations chapter の 7 ステップ運用シナリオ | discrepancy が「乖離 1 行」で終わる、Reference が CONFIG_DB schema dump 寄り |
| 2 | 4.83 | 10 | Verifier の昇格判断、Reference batch B の YANG/CLI 連結 | 一部 verification frontmatter が `meta` のまま昇格漏れ |
| 3 | **4.84** | 15 | setup の (CLI / JSON / show) 三段化、Runbook の症状逆引き、discrepancy の (行番号 + 影響 + コマンド + Issue) 五段 | internals が章により行数バラつき (47 行 ↔ 150 行)、I1 と I4 の frontmatter `sources` 空欄 |

**主要トレンド**:

- 平均値は 4.60 → 4.83 → 4.84 と高止まり。漸近域に達しており、平均値だけでは更なる伸びを観測しづらい
- ばらつきは round 2 の 4.4-5.0（幅 0.6）から round 3 の 3.8-5.0（幅 1.2）に拡大。**章ごとの非対称性**が顕在化
- 5.0 ページの比率は round 2 で 4/10、round 3 で 9/15 と増加（55% → 60%）
- 3.0 台が 1 件 (I1 BGP/internals 3.80)。下振れの原因が明確（行数不足・SAI 属性表欠落）でリカバリ容易

## 6. 「6 イテレーション目」(イテレーション D) の罠 / 次に何が必要か

### A. 罠（過去 5 イテレーションで実害が出た or 出始めている兆候）

1. **internals 章の行数ばらつき**: I1 (47 行) と I3 (150 行) の落差が読み手の期待値を裏切る。同じディレクトリ階層に「読みごたえ章」と「触り程度章」が混在。**全 22 章を 100-180 行帯にレンジ整形**する均し作業が要る
2. **frontmatter の `sources: []` 残存**: I4 など、本文は密だが frontmatter が空。verifier batch で frontmatter 充足判定を入れていないため、コンテンツ進化に metadata が追いついていない
3. **setup の (CLI / JSON / show) 三段固定化のリスク**: テンプレ化が進んだ結果、章間で記述の「型」が揃いすぎ、シナリオ固有の差分が薄まる懸念。例えば SAA / DASH / SmartSwitch ではこの三段に乗らない (controller-driven、live REST 経由) ため、章ごとに型を分岐させるべき
4. **Runbook の YANG 列空欄**: dualtor-mux / sai-failure 等で YANG 列が `[]`。本当に YANG が無いのか、調べていないだけかが区別できない。Runbook frontmatter に `yang_searched: true/false` を入れて意図的空欄を明示すべき
5. **discrepancy 深掘りの均質化**: D1/D2 は満点だが D3 は GitHub Issue/PR 引用がやや薄い。残り 7 件 (今回未サンプル) の品質ばらつきが懸念

### B. 次イテレーション (D) で着手すべき項目

優先度順:

1. **internals 章の行数均し** (高): 22 章中 4 章をサンプルしたうち I1 が 47 行と outlier。残り 18 章で同様の不足章を洗い出し +100 行帯まで補強
2. **frontmatter linter** (高): `meta/scripts/` 配下に `sources:` 空チェック + verification の整合性 (`code-verified` なのに sources が無いと FAIL) を入れる
3. **Runbook 追加 15 件** (中): 現在 15 件だが、未カバー領域 = telemetry/SNMP、gNMI subscribe、syncd 起動失敗の原因別、warm-reboot ロールバック、Y-cable firmware mismatch、PINS gRPC 切断、CRM threshold 越え別 (FDB/Route/Nexthop/ACL の 4 種) など。**もう 1 batch 15 件追加で計 30 件** が現実的目標
4. **discrepancy 深掘り残 (低)**: 残 7 件を確認して D1/D2 水準まで底上げ
5. **scenario の「型」分岐** (中): controller-driven 系 (DASH/SmartSwitch/PINS) と CLI-first 系 (BGP/VXLAN/ACL) で setup の章立てを意図的に変える。テンプレ依存の硬直化を予防

### C. 構造論争を再開する必要があるか

**結論: 不要。コンテンツで満たせる**。

理由:

- round 1 で挙がった構造課題 (Topics と Reference の境界、area frontmatter の使い分け) は Topics × 22 章のサブ構造 (`concept` / `setup` / `operations` / `internals` / `advanced`) と Reference × 4 種 (`cli` / `config-db` / `yang` / `runbooks`) で **実質的に役割分担が確立**
- round 3 で追加された `reference/runbooks/` は構造変更ではなく**症状逆引きという新しい入口を Reference 内に増設**しただけで、既存階層を壊していない。これは Diataxis でいう "How-to guide" の追加に相当し、Topics の operations.md と棲み分けできている
- 残課題はすべて「コンテンツの均し」「frontmatter 整合性」「verification の運用」であり、ディレクトリ階層 / sidebar nav の再編は要らない
- 過去 (`structure-rereview-*.md` 5 本) で議論された案 (persona-driven / Diataxis / IA 主導) のいずれも「現状コンテンツが densify したら不要になる」と round 2 で結論済み。round 3 の結果はその判断を追認

## 7. 結論

- 平均 4.84 / 5.0 は round 2 とほぼ同率で**高位安定**
- コード行番号引用は 5/5 pass、`ctx.fail()` / `AclLoaderException` の実エラー文字列の正確な抽出が裏取り強度を担保
- イテレーション D は「不足章 (主に internals) の均し + frontmatter linter + Runbook +15 件 + discrepancy 深掘り残 7 件」の 4 つに集中すべき
- 構造論争の再開は不要、コンテンツ均しで十分対応可能
