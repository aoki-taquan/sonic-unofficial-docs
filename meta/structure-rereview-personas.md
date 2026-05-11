# 構成再評価レポート (ペルソナ動線 / 第 2 ラウンド)

- 作成日: 2026-05-11
- 評価者: 再評価エージェント A (ペルソナ動線視点)
- 評価対象: main エージェントの **「5 タブ Diátaxis 構造」最新提案** (`/tmp/re-proposal-summary.md`)
- 前回 (第 1 ラウンド) の自己提案: `meta/structure-review-personas.md` (`topics` + `reference` + `library` + `runbooks` の 3〜4 軸)

---

## TL;DR

| 観点 | 評価 |
|---|---|
| 5 タブ提案の採否 | **条件付き Yes (推奨)** |
| 自己の前回提案との優劣 | **5 タブ提案 > 前回自己提案**。主因は (a) URL 完全維持、(b) `library` 命名問題の回避、(c) IA レビューと整合 |
| 残る要改善点 | 3 点 (後述「改善余地」) |

main の 5 タブ案は、4 評価 (A: 自分 / B: IA / D: 反論役) の要求を **同時に満たす最小工事案** であり、前回自分が出した `library + runbooks` 案より優れている。

---

## 1. 前回自己提案と新提案の差分

| 項目 | 前回 (自分) | 新提案 (main) |
|---|---|---|
| 軸数 | 3〜4 (topics / reference / library / runbooks) | 5 タブ (Get Started / Topics / Runbooks / Reference / Subsystems) |
| area 配下の扱い | `library/` に物理移動 (URL 変更) | **Subsystems タブ配下に置くだけで URL は不変** |
| `guides/` | 廃止 (index に統合) | `Get Started` タブに昇格、温存 |
| `categories/` | 廃止 → tag plugin | tag プラグインで補完、明示的な廃止指定なし |
| runbooks | 新設 (10 本) | 新設 (10〜15 本)、内容例も同等 |
| discrepancy-found | 言及なし | `Reference` 配下に昇格 + `⚠️` バッジ自動表示 |
| 移行コスト | area 全移動で大 (queue・SEO・CI 影響) | nav 階層化のみ、3〜4 PR |

**差分の本質**: 前回案は「物理ディレクトリを動かす」前提だったが、新提案は「物理は不変、`navigation.tabs` と `.pages` で **見た目だけ** 再構成する」。これは Devil's Advocate の P1 (SEO 毀損) / P10 (`.pages` 運用崩壊) / P11 (queue slug 崩壊) をすべて回避する。前回の自分はここを軽視していた。

---

## 2. 5 ペルソナ × 主要質問で動線テスト

評価方法: 新 5 タブ構造 (Get Started / Topics / Runbooks / Reference / Subsystems) で、各質問が何クリックで到達するか / 迷うかを採点。
スコア: ◎ (2 クリック以内、迷いなし) / ◯ (3 クリック、軽い迷い) / △ (4+ クリック or タブ判定で迷う) / × (到達不能)。

### P1 初学者

| 質問 | 動線 | 現状 | 新提案 | コメント |
|---|---|---|---|---|
| Q1-a「SONiC とは」 | Get Started → 01-overview | △ | ◎ | Get Started 入口で `01-overview` を default 表示にできる |
| Q1-b「config どこ」 | Get Started → beginner.md → reference | × | ◯ | Get Started の中で beginner.md がランディングになる |
| Q1-c「Redis/SAI とは」 | Topics → 20-swss-sai-redis | △ | ◎ | Topics タブの存在が明示されるので一発 |
| Q1-d「VM 動かす」 | Get Started → evaluator.md → topics/21 | △ | ◯ | 同じ話が evaluator と topics/21 にあるが Get Started 経由で一本化される |

→ **P1 は 5 タブで明確に改善**。Get Started を「入口を 1 つにまとめる役」として機能させる効果が大きい。

### P2 運用者

| 質問 | 動線 | 新提案 | コメント |
|---|---|---|---|
| Q2-a「BGP UP しない」 | Runbooks → bgp-not-established | ◎ | **新設 Runbooks が直撃**。前回最大の不満を構造的に解決 |
| Q2-b「VLAN メンバ追加」 | Reference → cli/config-vlan | ◎ | Reference タブで CLI が独立、迷いなし |
| Q2-c「FEC エラー多発」 | Runbooks → fec-error / Reference → counters | ◯ | Runbooks に「FEC」項目があれば◎、なければ Subsystems/platform 経由で△ |
| Q2-d「show techsupport」 | Runbooks → techsupport / Reference → cli | ◯ | Runbooks の必須項目に含めること |
| Q2-e「save → reload 順序」 | Runbooks → config-save-reload | ◎ | これも Runbooks 必須 |

→ **P2 で最大の効果**。Runbooks タブの存在が構造的解決になっている。**ただし** Runbooks のコンテンツが揃わない限り「空のタブ」になるリスク (後述)。

### P3 開発者

| 質問 | 動線 | 新提案 | コメント |
|---|---|---|---|
| Q3-a「fpmsyncd と orchagent の責任分界」 | Topics → 02-bgp/architecture + 20-swss-sai-redis | ◯ | Topics タブで一本化 |
| Q3-b「新 CONFIG_DB + YANG」 | Reference → config-db/yang + Subsystems → management | △ | 横断 how-to が無く、Subsystems と Reference を行き来 |
| Q3-c「SAI extension 追加」 | Subsystems → categories/sai-extensions (categories は Meta 配下) | △ | Get Started でも Subsystems でも入口が薄い |
| Q3-d「ZMQ producer/consumer」 | Subsystems → internals | ◯ | internals が Subsystems 配下に整理される |

→ **P3 は改善が中程度**。Subsystems タブで「開発者向け深掘り」の位置付けが明確になるのは良いが、**Q3-b / Q3-c は依然として「横断 how-to」が欠落**。runbooks/ に開発者向け how-to (例: `add-config-db-table.md`) を入れるか、Topics の中に開発者専用章を追加すべき。

### P4 評価者

| 質問 | 動線 | 新提案 | コメント |
|---|---|---|---|
| Q4-a「sonic-vs で BGP」 | Get Started → evaluator.md → Topics → 02-bgp/setup | ◯ | Get Started で evaluator が前面化 |
| Q4-b「Dual ToR」 | Topics → 05-dual-tor | ◎ | 既存の好例 |
| Q4-c「EVPN VXLAN 2 leaf」 | Topics → 03-vxlan-evpn | ◯ | setup.md がコピペ手順でない問題は残る |
| Q4-d「fast-reboot 時間」 | Topics → 11-reboot + Subsystems → system | △ | ベンチマーク数値そのものはコンテンツ不在 |

→ **構造としては P4 も改善**。残る不満は「動くサンプルの薄さ」というコンテンツ問題で、構造変更では解決しない (前回と同じ結論)。

### P5 経営判断者

スコープ外。Get Started 冒頭に「P5 は対象外」を明示すれば判断者を迷わせない。新提案は明示していないので追記が必要。

### 動線テストの総括

- 新提案で **明確に改善**: P1 (全質問)、P2 (全質問、ただし Runbooks 内容次第)、P4 (動線のみ)
- **改善が中程度**: P3 (横断 how-to は別途必要)
- **未対応**: P5 のスコープ明示

---

## 3. 新提案の妥当性検証 (タスク §3)

### 3.1 タブ 5 個は本当に 7±2 範囲内か？ 4 個に圧縮できないか

**Yes、5 は範囲内。ただし 4 に圧縮可能で、しかも 4 の方が望ましい局面がある**。

- Miller's Law (7±2) 観点: 5 タブは安全圏。Cumulus / Arista / Cisco の docs はトップが 4〜6 タブで揃っている。
- 圧縮候補: **`Runbooks` を `Topics` 配下に吸収** すれば 4 タブ (Get Started / Topics / Reference / Subsystems)。ただし Runbooks は「症状逆引き」というメンタルモデルが Topics の「機能別読み物」と直交するので、別タブのほうが認知負荷は低い。
- もう 1 つの圧縮候補: **`Get Started` を index.md カードに吸収** して 4 タブ化。これは賛成しない。Get Started はトップタブにあることで「最初に読むべき場所」が明示される効果が大きく、index.md カードだけだと既存読者がスルーする。
- **結論**: 5 で固定。4 に圧縮するメリットはない。

### 3.2 Topics と Subsystems の役割分離は読者に明確か？ 同じ機能が両方にあるのは前回と同じ問題では？

**部分的に未解決**。

- **理屈上の分離**: Topics = 章立ての「読み物」(concept → architecture → setup → operations → internals → advanced の 6 ページテンプレ)。Subsystems = HLD 派生の「個別ページ群」 (例: `routing/bgp-loading-optimization-for-sonic.md`)。
- **読者の体感**: BGP を調べたい読み手は Topics/02-bgp に行き、深掘りしたければ Subsystems/routing/bgp* を見る、という Progressive Disclosure が成立する **ように見える**。
- **しかし**: Subsystems の各 area `index.md` で「まずは Topics/02-bgp へ」というクロスリンクを **必ず張る** ことを強制しないと、読者は Subsystems から入った瞬間に Topics の存在を知らないまま深掘りに突入する。
- **対策の必須化**:
  - IA レビューが提案した「area index 先頭に Topics への誘導パネル」を 5 タブ提案でも採用すべき
  - Subsystems タブの上に「これは Topics の深掘り版です」というセクション説明を入れる
  - frontmatter `related_topics:` を追加し、Subsystems の各ページから対応 Topics 章へ自動リンク

**結論**: 構造的には分離可能。**ただし「相互誘導の自動化」を併走しないと前回と同じ「3 系列重複の判別不能」問題が再発する**。これは 5 タブ案の最大のリスク。

### 3.3 runbooks のコンテンツ 10-15 件は本当に妥当か？

**初期は妥当、長期は不足**。

- **比較対象**: Cumulus Linux Docs の Troubleshooting セクションは ~40 ページ。Arista EOS Knowledge Base は数百件。
- **このリポの規模 (600+ ページ)** に対し 10〜15 件は「症状逆引きの代表例」止まり。例えば `BGP up しない` は 1 ページに収まらない (next-hop / TCP 接続 / config 反映タイミング / FRR 起動順 / namespace で派生)。
- **段階移行案**:
  - Phase 1 (即時): 10〜15 ページ。提案案でカバー (BGP, VLAN, FEC, Warm Reboot, PFC, DHCP Relay, Multi-ASIC, Dual-ToR, SAI failure, Container)。これで P2 ペルソナの「不満ゼロ」ではないが「最大不満は解消」される。
  - Phase 2 (3 ヶ月後): 30 ページ規模へ拡張。`discrepancy-found` 39 件を runbook に変換する作業を Verifier の継続バッチで実施。
- **結論**: 提案の 10〜15 件は **MVP として妥当**、ただし「これで完成ではない」ことを `runbooks/index.md` に明示。

### 3.4 Get Started タブに guides + 01-overview を入れるのは適切か？

**Yes、適切**。

- 現状 `guides/` 5 ページ (beginner / developer / evaluator / operator + index) は薄いリンク集で、入口が遠い。
- `topics/01-overview/` は「SONiC とは」の正解ページ候補だが、Topics タブの 1 章目に埋もれる。
- Get Started タブに両方を集約することで:
  - ロール別入口 (beginner / developer / evaluator / operator) が前面化 → P1, P3, P4 が直撃
  - 01-overview が「最初の 1 ページ」として明示される → P1 Q1-a 解決
- **微調整**: Get Started タブの index は **`01-overview` を直接表示** (リダイレクト) する、または「短縮版 overview + ロール別カード」のランディングにする。`guides/index.md` を流用する形が無難。

### 3.5 discrepancy-found ページの「Reference 配下に昇格」は本当に正解か？

**部分的に Yes、ただし専用タブ化または Get Started 内昇格も検討すべき**。

- **Reference 配下に置く論理**: Reference は「機械抽出された事実」のタブ。discrepancy も「事実 (HLD と実装の乖離)」なので親和性はある。
- **しかし違和感**: discrepancy-found ページは「Reference 引きたい」読者ではなく「**この HLD は信用していいか？**」と判断したい読者が見るもの。これは判断材料であって Reference の引きではない。
- **検討すべき代替**:
  - 案 α: **Get Started タブ内に「ドキュメント信頼性」セクション** を作り、`discrepancies` 一覧を置く。読者が「これは公式 HLD と異なる」と知ったうえで Topics / Subsystems を読み始められる。
  - 案 β: **Meta タブを 6 個目として追加** (IA レビュー案)。`categories` + `discrepancies` + `verification 状態一覧` を集約。Hick's Law 範囲 (5→6) を 1 つだけ越えるが許容範囲。
  - 案 γ: 提案通り Reference 配下。`Reference > Discrepancies` というメニュー位置。
- **推奨**: 案 β (Meta タブ追加)。ただし優先度は低く、Phase 2 で対応。Phase 1 は提案通り Reference 配下で OK。Verifier 成果は ⚠️ バッジで全ページに表示されるので、入口が Reference でも実害は小さい。

---

## 4. 自分の前回提案 vs 新提案の決着

### 比較表

| 評価軸 | 前回自己提案 (library + runbooks) | 新提案 (5 タブ、URL 不変) |
|---|---|---|
| ペルソナ動線改善 | ◯ (3 軸化 + runbooks) | ◎ (5 軸で意図 1:1) |
| URL / SEO 維持 | × (`area` → `library` で全変更) | ◎ (完全維持) |
| awesome-pages 運用維持 | △ (大幅再構成) | ◎ (`.pages` 階層化のみ) |
| `meta/queue/` 互換性 | × (slug 名に area 含むため崩壊) | ◎ (物理パス不変) |
| guides の扱い | 廃止 (リスクあり) | Get Started に昇格 (理にかなう) |
| categories の扱い | 廃止 → tag plugin | tag plugin で補完、判断保留 |
| discrepancy 可視化 | 言及なし | ⚠️ バッジ自動表示 + Reference 昇格 |
| 反論役 (Devil) の P1〜P12 | 半数解決 (P1, P10, P11 は未解決) | ほぼ全て解決 (P3 = topics で吸収しきれない問題のみ残る) |
| IA レビューの A 評価案 | 部分一致 | ほぼ完全一致 |
| 移行コスト | 大 (10+ PR、redirect 必須) | 小 (3〜4 PR、URL 不変) |

### 決着

**新提案 (5 タブ) を採用すべき**。前回の自己提案は明確に劣る。

理由 (重要順):
1. **URL 完全維持**: 前回の自己提案は `area` を `library/` に物理移動する前提だったが、これは Devil's Advocate の P1 (SEO 毀損) を直撃する。新提案は `.pages` のみで階層化するため URL 変更ゼロ。これだけで前回案より優れる。
2. **`library` 命名の心理的負荷を回避**: 前回案で `archive` を `library` に名前変更したが、これは結局「同じ問題の言い換え」だった。新提案は `Subsystems` という機能的ラベルで、命名論争が起きない。
3. **IA / Devil の両レビューと整合**: 5 タブ案は IA レビューの推奨案 (5.3 節) と一致し、Devil の P1/P10/P11 (URL・運用・queue) を回避する。前回案は Devil 観点で △ だった。
4. **既存資産の最大活用**: guides 5 ページ、categories 11 ページ、topics 22 章、area 9 系列、reference 167 ページ、すべてが新提案でそのまま生きる。前回案は guides / categories を廃止する分、既存資産の損失があった。

**前回案が勝っていた点** (公平のため):
- 「3 軸の単純さ」: 前回案は 3〜4 軸、新案は 5 タブで、見た目の単純さは前回が上。ただしこれは些末。

---

## 5. 改善余地 (3 点)

新提案を採用するうえで必ず併走させたい改善点。優先度順。

### 改善 1 (必須): Topics ↔ Subsystems の相互誘導を機械化

- 各 Subsystems area `index.md` 先頭に Topics 対応章への誘導パネル (IA レビュー 5.3 で既出) を **テンプレ化** し、Indexer が自動挿入する仕組みを作る
- frontmatter `related_topics:` フィールドを SCHEMA に追加し、Reference / Subsystems ページから対応 Topics 章へリンク自動生成
- これがないと 5 タブ案でも「3 系列重複の判別不能」問題が再発する (本評価§3.2)

### 改善 2 (高): Runbooks の段階拡張と P3 開発者向け how-to の追加

- Phase 1 で 10〜15 件は妥当だが、`runbooks/index.md` に「これは MVP、Phase 2 で 30 件規模へ拡張」と明示
- 開発者向け how-to (例: `add-config-db-table.md`, `add-yang-module.md`, `add-sai-extension.md`) を Runbooks か Topics 内に追加し、P3 ペルソナ Q3-b / Q3-c を構造的に解決

### 改善 3 (中): Meta タブの追加 (6 個目) を Phase 2 で検討

- discrepancy-found 一覧、categories、verification 状態統計などを集約する Meta タブを Phase 2 で追加
- Hick's Law 範囲 (5→6) を 1 つ超えるが、このリポの独自価値 (`code-verified` / `discrepancy-found`) の可視化に有効
- Phase 1 では提案通り Reference 配下で良い

---

## 6. 最終推奨 (再評価エージェント A の結論)

**Yes (条件付き) — 5 タブ提案を採用する**

条件:
1. Phase 1 で `Topics ↔ Subsystems` の相互誘導を `related_topics:` frontmatter + Indexer 自動挿入で機械化する
2. Phase 1 で Runbooks 10〜15 件を実コンテンツとして埋める (空タブを残さない)
3. Phase 2 で Meta タブ追加と Runbooks 拡張を検討

前回の自己提案 (`library + runbooks`) は撤回する。URL 不変・既存資産活用・他レビュー視点との整合のすべてで新提案が上回る。
