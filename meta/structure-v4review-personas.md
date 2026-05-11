# 構成 v4 評価レポート (ペルソナ動線 / 評価 A / 第 4 ラウンド)

- 作成日: 2026-05-11
- 評価者: 再評価エージェント A (ペルソナ動線視点、v4 回)
- 評価対象: `/tmp/re-proposal-v4.md` (3 タブ + Reference 内 5 カテゴリ)
- 前回 (v3 評価): `meta/structure-v3review-personas.md` で v3 を条件付き Yes (4 条件併走必須) と判定

---

## TL;DR

| 観点 | 評価 |
|---|---|
| v4 (3 タブ + Reference 内 5 カテゴリ) の採否 | **Yes (採用推奨、v3 より明確に優位)** |
| v3 (4 タブ + Verification 独立) との比較 | **総合で v4 > v3**。主因は (a) Runbooks 復活で P2 運用者の構造的劣化を解消、(b) 「サブシステム」改名で第三タブの正体が明瞭化、(c) Phase 1 工数 1 PR/30 分で着手障壁が消える |
| 残る要改善点 | 3 点 (Reference 5 カテゴリの内部 IA、Verification と Runbooks の境界線、`docs/index.md` ハブ実装の品質依存) |

---

## 1. v4 提案の構造的差分 (v3 → v4)

| 軸 | v3 (4 タブ + Verification ハブ) | v4 (3 タブ + Reference 内 5 カテゴリ) | 差分評価 |
|---|---|---|---|
| タブ数 | 4 | **3** | ◯ Hick's Law でさらに圧縮、トップ認知負荷が軽い |
| Verification | 独立タブ | **Reference 内カテゴリ** (verification/) | △/◯ 独自価値の昇格性は下がるが、孤島化リスクが消える。「引く」対象として CLI/CONFIG_DB と同列に並ぶのは正しい IA |
| Runbooks | 廃止 → 章末 troubleshooting | **Reference 内カテゴリで復活** | **◎** v3 で P2 が構造的劣化した最大の弱点を解消 |
| 第三タブ命名 | Library | **「サブシステム」** | ◎ 日本語化で初学者にも意味が通る。「ライブラリ」よりは「下位機構の集合」感が出る |
| Phase 1 工数 | 3 PR (Topics 章末 troubleshooting 22 件 + Verification タブ + index.md + related_topics 自動化) | **1 PR / 30 分** (`docs/.pages` + `reference/.pages` + `docs/index.md` + 2 サブディレクトリ追加 + redirects) | ◎ 着手障壁が劇的に低下。後戻り 5 分で可能なので「先に出して検証」できる |

**本質**: v3 の「Verification 独立タブで独自価値を昇格」は思想として正しかったが、(a) 孤島化リスク、(b) Runbooks 廃止のロス、の 2 つを抱えた。v4 は **「読者の動詞は『読む』と『引く』の 2 種類」** という第一原理に立ち戻り、CLI/CONFIG_DB/YANG/Runbooks/Verification を「引く」の 5 兄弟として Reference 内に並列配置することで両問題を一括解消。さらに「サブシステム」改名でナビ上の動詞 3 種 (読む:Topics / 引く:Reference / 深く読む:サブシステム) を 1:1 対応させた。

これは v2/v3 の試行錯誤を経て初めて到達できた IA で、構造提案として最も収まりが良い。

---

## 2. 5 ペルソナ × 主要質問で v4 動線テスト

スコア: ◎ (2 クリック以内、迷いなし) / ◯ (3 クリック、軽い迷い) / △ (4+ クリック or タブ判定で迷う) / × (到達不能 / 未整備)

### P1 初学者

| 質問 | v4 動線 | v3 | v4 | コメント |
|---|---|---|---|---|
| Q1-a「SONiC とは」 | docs/index.md ヒーロー → Topics → 01-overview | ◎ | ◎ | 同等 |
| Q1-b「config どこ」 | index.md → Reference → CONFIG_DB | ◯ | ◯ | 同等 (Reference 内に 5 カテゴリあるので一瞬迷うが、ラベルが日本語 + 直感的) |
| Q1-c「Redis/SAI とは」 | Topics → 20-swss-sai-redis | ◎ | ◎ | 同等 |
| Q1-d「VM 動かす」 | index.md → Topics → 21-lab-vs-developer | ◯ | ◯ | 同等 |
| Q1-e「サブシステムって何？」 | サブシステムタブをホバー / クリック | - | ◯ | **新規**: 「サブシステム」というラベルは初学者でも意味が推測可能。「Library」より良い |

→ **P1 は v3 と同等以上**。3 タブに圧縮されたことで最初の画面の選択肢が減り、Hick's Law 的に微改善。「サブシステム」改名は地味だが効く。

### P2 運用者

| 質問 | v4 動線 | v3 | v4 | コメント |
|---|---|---|---|---|
| Q2-a「BGP UP しない」 | Reference → Runbooks → bgp-not-established | ◯ | **◎** | **大幅改善**。Runbooks 復活で症状逆引きが直撃 |
| Q2-b「VLAN メンバ追加」 | Reference → CLI → config-vlan | ◎ | ◎ | 同等 |
| Q2-c「FEC エラー多発」 | Reference → Runbooks → fec-errors | △ | **◎** | **大幅改善**。v3 で「どの章の troubleshooting に置くか不明」だった章横断症状が Runbooks フラット一覧で解決 |
| Q2-d「show techsupport」 | Reference → Runbooks → techsupport-collection | △ | **◎** | **大幅改善**。同上 |
| Q2-e「save → reload 順序」 | Reference → Runbooks → config-reload-order or Topics → 11-reboot | ◯ | ◎ | 改善 |

→ **P2 で v4 最大の勝利**。v3 評価で「P2 運用者は構造的に劣化 (−1)」と判定した最大の弱点が完全に解消。「症状」から「Reference → Runbooks」という直線動線が成立し、章選定の 1 クッションが消える。これは v4 採用の決定打。

### P3 開発者

| 質問 | v4 動線 | v3 | v4 | コメント |
|---|---|---|---|---|
| Q3-a「fpmsyncd と orchagent 分界」 | Topics → 02-bgp + サブシステム → routing/architecture | ◯ | ◯ | 同等 |
| Q3-b「新 CONFIG_DB + YANG」 | Reference → CONFIG_DB / YANG + サブシステム → management | △ | △ | 横断 how-to 欠落は未解決 |
| Q3-c「SAI extension 追加」 | サブシステム → categories/sai-extensions | △ | △ | 同等 |
| Q3-d「ZMQ producer/consumer」 | サブシステム → internals | ◯ | ◯ | 同等 |
| Q3-e「HLD は信用できるか」 | Reference → Verification → discrepancies | ◎ | ◯ | **微劣化**。v3 ではトップタブで Verification が前面に出ていたが、v4 では Reference 内 1 カテゴリ。能動的に Reference を開く前提が必要 |

→ **P3 は ±0 ないし微劣化 (−0.5)**。Q3-e で v3 が持っていた「Verification 独立タブの前面性」が薄まる。ただし `docs/index.md` ハブに「裏取り済 X% / 乖離 Y 件」のバナーを置けば回復可能で、v4 提案にもそのように記載されている (`index.md` に Verification 統計バナー)。実装次第で同等まで戻せる。

### P4 評価者

| 質問 | v4 動線 | v3 | v4 | コメント |
|---|---|---|---|---|
| Q4-a「sonic-vs で BGP」 | index.md ロールカード → Topics → 02-bgp/setup | ◯ | ◯ | 同等 |
| Q4-b「Dual ToR」 | Topics → 05-dual-tor | ◎ | ◎ | 同等 |
| Q4-c「EVPN VXLAN 2 leaf」 | Topics → 03-vxlan-evpn | ◯ | ◯ | 同等 |
| Q4-d「fast-reboot 時間」 | Topics → 11-reboot + サブシステム → system | △ | △ | 同等 |
| Q4-e「この OSS は信用できるか」 | index.md バナー → Reference → Verification → coverage | ◎ | ◯ | **微劣化**、ただし index.md バナーがあれば実用上◎相当 |

→ **P4 も P3 と同様、Verification の前面性低下で −0.5**。ただし `docs/index.md` ハブに統計バナー (coverage 円グラフのサムネ等) を置く前提なら回復。P4 は「採用判断材料が欲しい」ので、トップに統計が見えれば Reference 内深さは問題にならない。

### P5 経営判断者

| 質問 | v4 動線 |
|---|---|
| Q5「SONiC OSS の成熟度」 | index.md バナー → Reference → Verification → coverage |

→ **v3 → v4 で同等**。P5 は本リポのスコープ外と冒頭明示するのは前回同様。index.md にバナーを置けば「タブ越しに 1 階層深い」程度の差で、実用上は問題なし。

### 動線テスト総括 (v4)

| ペルソナ | v3 | v4 | 改善度 |
|---|---|---|---|
| P1 初学者 | 同等 | 同等 + α | **+0.5 (3 タブ圧縮 + サブシステム改名)** |
| P2 運用者 | 改善中 (構造的劣位あり) | 改善大 | **+1.5 (Runbooks 復活が決定打)** |
| P3 開発者 | 改善中+ (Verification 前面) | 改善中 (index バナー必須) | **−0.5 (index バナー実装次第で回復)** |
| P4 評価者 | 改善大 (Verification 前面) | 改善中 (index バナー必須) | **−0.5 (同上)** |
| P5 経営判断 | scope 外明示 + coverage | 同等 | **±0** |

**ネット**: +1.0 / 5 ペルソナ。P2 の大幅改善が P3/P4 の微劣化を上回り、v3 より総合で明確に上回る。さらに **v3 で必須だった 4 併走条件のうち最重量の「Topics 22 章 × troubleshooting + 横断 index」が不要になる** ことで、実装現実性で v4 が圧勝。

---

## 3. v4 の盲点 (タスク §3)

### 3.1 Reference 内 5 カテゴリ (CLI / CONFIG_DB / YANG / Runbooks / Verification) の内部 IA は耐えるか？

**条件付き Yes**。

- **強み**: 「引く」という動詞で 5 兄弟が一貫している。読者が Reference タブを開いた時点で目的が「何かを索引で引く」と明確になっており、5 カテゴリのどれを選ぶかは目的次第 (コマンドなら CLI、症状なら Runbooks、信頼性なら Verification)
- **懸念 1 (動詞の微妙な違い)**: CLI / CONFIG_DB / YANG は「仕様を引く」、Runbooks は「症状を引く」、Verification は「状態を引く」。同じ Reference でも目的のメタが異なる。読者によっては「Runbooks は Topics か Reference か」で迷う可能性
  - **緩和**: `reference/.pages` の表示順を「仕様 (CLI/CONFIG_DB/YANG)」「症状 (Runbooks)」「状態 (Verification)」とグルーピングし、`reference/index.md` で 3 グループの目的別カードを出す
- **懸念 2 (Verification の能動性低下)**: P3/P4 評価で見たように、Verification の前面性は v3 比で下がる。**`docs/index.md` のハブに統計バナーを置くのは必須**であり、v4 提案にも記載されているがレビュー段で実装品質を確認しないと孤島化する
- **結論**: Reference 内 5 カテゴリは IA としては成立する。ただし (a) `reference/index.md` のグルーピング表示、(b) `docs/index.md` の Verification 統計バナー、の 2 点は必須セットで実装すること。

### 3.2 Runbooks 復活で v3 評価の主要懸念は本当に消えるか？

**Yes、完全に消える**。

- v3 評価 §3.1 で指摘した「Topics 章末 troubleshooting は Runbooks の代替にならない (章横断症状が救えない)」問題は、Runbooks を Reference 内にフラット復活させることで構造的に解決
- **副次効果**: Topics 22 章全てに troubleshooting.md を新設する Phase 1 大型作業 (v3 評価で 1 週間と見積もり) が **不要**。代わりに Reference/runbooks/ に 10-15 件の症状逆引きを新設するだけで済む (v4 提案の Phase 2、並走 4-6h)
- **メンテ持続性**: Runbooks は症状ベース (BGP UP しない / VLAN メンバー追加 / FEC エラー / Warm Reboot 失敗 / DHCP Relay 動かない 等) でフラットなので、章構造のメンテに引きずられない。新症状が出たら 1 ファイル追加するだけ
- **結論**: v4 の Runbooks 復活は v3 評価の最大の懸念を解決し、かつ実装工数を 1/10 以下に圧縮する。**v4 採用の決定的根拠**。

### 3.3 「サブシステム」改名は読者に届くか？

**Yes、改善**。

- 「Library」は技術文書文脈では「ライブラリ (依存パッケージ)」と誤読される可能性があった (実態は HLD 派生詳細群)
- 「サブシステム」は SONiC の内部構造 (SWSS / SyncD / orchagent / portsyncd 等のサブシステム群) を読み解く章という意味で正確
- ただし「Topics と サブシステム の違い」は読者に説明が必要。`docs/index.md` で「機能横断の物語 = Topics」「内部機構の深堀り = サブシステム」と明示すれば解消
- **微懸念**: カタカナ語の長さ (8 文字) で nav 横幅を食う。3 タブ目だけ長いとモバイル表示で折り返しの可能性
- **結論**: 改名は妥当。`docs/index.md` で動詞 (読む / 引く / 深く読む) 対応を明示すること。

### 3.4 Phase 1 工数 1 PR / 30 分は本当に現実的か？

**Yes、現実的**。

- 物理移動が `_meta/discrepancies.md` → `reference/verification/discrepancies.md` の 1 ファイルだけ
- 新規ファイル: `reference/runbooks/index.md`、`reference/verification/index.md`、`reference/verification/discrepancies.md` (移動先) の 3 つ
- 編集: `docs/.pages` (新設 or 更新)、`reference/.pages` (新設 or 更新)、`docs/index.md` (ハブ強化)、`guides/*` 削除 + redirects
- mkdocs redirects plugin で URL 互換性を担保すれば後戻り 5 分は実現可能
- **比較**: v3 評価で Phase 1 を「3 PR / 1-2 週間」と見積もっていたのに対し、v4 は **1 PR / 30 分**。ROI が劇的に高い

---

## 4. v4 採用可否 (タスク §4)

### 結論: **Yes (採用推奨、v3 より明確に優位)**

v4 は v3 より総合 +1.0 ペルソナで明確に上回る。特に:

1. **P2 運用者の構造的劣化を解消** (v3 評価最大の懸念)
2. **Phase 1 工数を 1/10 以下に圧縮** (1-2 週間 → 30 分)
3. **「読む / 引く / 深く読む」の動詞 3 軸で IA が一貫**

v3 で必須だった 4 併走条件のうち、Topics 22 章 × troubleshooting は **不要** になる。残る必須条件は以下 2 点に縮減:

1. **`docs/index.md` をロール別 grid cards + 直近おすすめ章 3 つ + Verification 統計バナー の真のランディングに再設計** (P1/P3/P4 補償)
2. **`reference/index.md` で 5 カテゴリを「仕様 / 症状 / 状態」3 グループで提示** (Reference 内 IA の混乱回避)

この 2 点は Phase 1 (1 PR / 30 分) に含めて実装可能で、v3 採用時に必要だった「1 週間以上のリソース確保」が不要。**即座に着手して問題ない**。

### v3 からの乗り換え推奨度

- **乗り換える**: 即座 (Phase 1 で 30 分着手 → Phase 2 で並走 4-6h)
- **v3 で留まる理由**: 無し。v3 から v4 への移行は v3 で必要だった大型作業 (Topics 章末 troubleshooting 22 件) を不要化するため、v3 着手前に v4 にスイッチするのが純利益

main エージェントの現状リソース (Phase 6 完了、455 ページ merge 済、自動化基盤稼働) を見るに、**v4 は今週中に Phase 1 + Phase 2 まで実装可能**。

---

## 5. 残課題 (Phase 2 以降)

### v4 採用後の残課題

- **Reference/Runbooks の初期 10-15 件選定**: P2 質問例 (BGP not established / VLAN member add / FEC errors / Warm Reboot 失敗 / DHCP Relay / techsupport collection / config reload order / container restart loop / core dump 解析 / fast-reboot 失敗 / interface down / route missing / DUT 接続喪失 / counter 異常 / log rotation) を優先実装
- **`docs/index.md` Verification 統計バナー の自動生成**: Verifier 集計から coverage 円グラフ thumbnail を mermaid で render。Phase 3 のスクリプト化と連動
- **`related_topics:` frontmatter 機械追加** (v3 評価の §3.2): v4 でも有効。Topics ⇔ サブシステム の双方向リンクは引き続き必要
- **P3 開発者向け横断 how-to** (Q3-b/Q3-c): v2/v3/v4 全てで未解決。`topics/23-developer-howto/` 新設で対応

### v4 提案の盲点で本評価が発見した点

- **Reference 5 カテゴリの動詞混在 (§3.1)**: `reference/index.md` でグルーピング表示を必須化
- **「サブシステム」が nav 横幅を食う (§3.3)**: モバイル表示確認、必要なら「サブシステム」より短い候補 (例: 「機構」) も比較検討
- **Verification の前面性低下 (P3/P4 −0.5)**: `docs/index.md` バナー実装品質に依存。レビュー段で「バナーがバニラ HTML テキストだけ」だと孤島化リスク

---

## 6. 前回 (v3 評価) からの自己訂正

v3 評価 §4 で「v3 採用推奨、ただし 4 併走条件 (Topics 22 章 troubleshooting / index.md ハブ / related_topics 自動化 / Verification バッジ + coverage グラフ) が必須」と判定したが、**条件 1 (Topics 22 章 troubleshooting) は Runbooks 独立カテゴリで構造的に置換可能** という見落としがあった。v3 評価時点では「Runbooks を廃止する以上、Topics 章末で補うしかない」と思考停止していたが、v4 が示した「Reference 内に Runbooks 復活」という選択肢で完全に解決される。

**結論訂正**: v3 採用推奨を v4 採用推奨に上書きする。v3 → v4 への移行コストは負 (v3 で必要だった大型作業を回避するため、トータルでマイナス工数)。

---

## 7. 採用後の推奨タイムライン

| 時期 | 作業 | 主担当 |
|---|---|---|
| 即日 | Phase 1: `docs/.pages` + `reference/.pages` + `docs/index.md` + `reference/index.md` + `reference/runbooks/index.md` + `reference/verification/{index,discrepancies}.md` + redirects + guides 削除 | 1 サブエージェント / 30 分 |
| 1-2 日 | Phase 2: `reference/runbooks/` 10-15 件作成 (BGP UP しない 等の優先症状) | 並走 2-3 サブエージェント / 4-6h |
| 1 週間 | Phase 3: `reference/verification/coverage.md` + `queue.md` 自動生成スクリプト、index.md 統計バナー連動 | 1 サブエージェント / 2-4h |
| 並走 | Phase 4: `related_topics:` 機械追加 + CI warn、Topics ⇔ サブシステム 相互誘導 | 並走 |

---

## 8. 評価サマリ

**v4 採用可否**: **Yes (推奨)**
**v3 比改善点**: P2 運用者の構造的劣化解消、Phase 1 工数 1/10 以下、動詞 3 軸 IA の一貫性、「サブシステム」改名の意味明瞭化
**残課題**: `docs/index.md` ハブの実装品質、`reference/index.md` のグルーピング表示、Verification 前面性の補償 (バナー実装)、開発者向け横断 how-to の欠落 (v2/v3 から継続)
