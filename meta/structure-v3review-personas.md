# 構成 v3 評価レポート (ペルソナ動線 / 第 3 ラウンド)

- 作成日: 2026-05-11
- 評価者: 再評価エージェント A (ペルソナ動線視点、v3 回)
- 評価対象: main の **v3 提案「4 タブ + Verification ハブ」** (`/tmp/re-proposal-v3.md`)
- 前回 (第 2 ラウンド): `meta/structure-rereview-personas.md` (5 タブ案を条件付き Yes と判定)

---

## TL;DR

| 観点 | 評価 |
|---|---|
| v3 (4 タブ + Verification) の採否 | **条件付き Yes (推奨、ただし v2 より僅差で上回る程度)** |
| v2 (5 タブ) との比較 | **総合で v3 > v2**。主因は (a) Verification 独立による独自価値の昇格、(b) タブ数削減で初期認知負荷低下、(c) `related_topics:` 機械相互誘導の明文化 |
| 残る要改善点 | 4 点 (Runbooks 廃止リスク・Get Started 廃止リスク・`related_topics:` 自動化の実装現実性・Verification タブの読者到達率) |

---

## 1. v3 提案の構造的差分 (v2 → v3)

| 軸 | v2 (5 タブ) | v3 (4 タブ + Verification ハブ) | 差分評価 |
|---|---|---|---|
| Get Started タブ | 独立 (guides 昇格) | 廃止 → `docs/index.md` に統合 | **△** 入口の単純化と引換に、ロール別カードがトップ画面 1 回 scroll 必要 |
| Runbooks タブ | 独立 (10〜15 件新設) | 廃止 → Topics 章末 `troubleshooting.md` サブページ | **△** 症状逆引きと機能別読み物のメンタルモデル混在 |
| Subsystems → Library | `Subsystems` 命名 | `Library` 命名 | ◯ 「下位システム」より「資料集」の語感で実態に合う |
| Verification | Reference 配下に discrepancy 昇格 | **独立タブ**。`coverage.md` / `queue.md` / `discrepancies.md` 集約 | **◎** このリポの独自価値が前面化 |
| Tags プラグイン | 導入 (3〜4 PR) | 取り下げ → `related_topics:` frontmatter | ◎ 実装コスト削減、構造 vs 横断の混乱回避 |
| Topics ⇔ Library 重複対策 | 言及あるが手段不明 | `related_topics:` で機械的双方向リンク | ◎ 前回懸念 (§3.2) への明示的対策 |

**本質**: v3 は「タブ数を 5→4 に削減した代わりに、Verification を専用タブで昇格 (5 タブ目に相当)」という等価変換。Tab 数だけ見れば 5→4 だが、ナビ上の独立エリアは依然 5 つ (Topics / Reference / Verification / Library / Hub セクション)。**真のメリットは「読者が見たいものごとに 4 つのタブで意図 1:1 になる」点**で、Hick's Law 的な選択肢圧縮には貢献している。

---

## 2. 5 ペルソナ × 主要質問で v3 動線テスト

スコア: ◎ (2 クリック以内、迷いなし) / ◯ (3 クリック、軽い迷い) / △ (4+ クリック or タブ判定で迷う) / × (到達不能 / 未整備)

### P1 初学者

| 質問 | v3 動線 | v2 | v3 | コメント |
|---|---|---|---|---|
| Q1-a「SONiC とは」 | docs/index.md ヒーロー → topics/01-overview | ◎ | ◎ | index.md カードに「初学者はここから」 |
| Q1-b「config どこ」 | index.md → reference/config-db/ | ◯ | ◯ | Get Started 廃止で 1 クッション少ない。ただしロール別カードを index.md に置く前提 |
| Q1-c「Redis/SAI とは」 | Topics → 20-swss-sai-redis | ◎ | ◎ | 同等 |
| Q1-d「VM 動かす」 | index.md → topics/21-lab-vs-developer | ◯ | ◯ | evaluator.md は index に統合される |

→ **P1 は v2 と同等**。Get Started 廃止のロスは index.md ヒーロー / grid cards 実装次第。ヒーローが薄ければ v2 のほうが入口明示性で上。**v3 で同等を担保するには `docs/index.md` を真の「ロール別 + 直近のおすすめ」ランディングにする実装が前提**。

### P2 運用者

| 質問 | v3 動線 | v2 | v3 | コメント |
|---|---|---|---|---|
| Q2-a「BGP UP しない」 | Topics → 02-bgp → troubleshooting.md | ◎ | ◯ | troubleshooting サブページが各章にゼロ件 (現状確認済)。**全章への新設が必要**。読者は「BGP の運用なら 02-bgp」と直感できるので動線自体は△以上 |
| Q2-b「VLAN メンバ追加」 | Reference → cli/config-vlan | ◎ | ◎ | 同等 |
| Q2-c「FEC エラー多発」 | Topics → 14-platform-port-optics → troubleshooting | ◯ | △ | 「Topics 章のどこに FEC があるか」判断に 1 クッション必要。Runbooks 独立タブのほうが症状逆引き直撃 |
| Q2-d「show techsupport」 | Topics → 11-reboot or system 配下を彷徨う | ◎ | △ | techsupport は章横断トピック。Topics 章末 troubleshooting に分散すると **「どの章に techsupport runbook があるか」が見つからない** |
| Q2-e「save → reload 順序」 | Topics → 11-reboot → operations or troubleshooting | ◎ | ◯ | 11-reboot で直撃可能 |

→ **P2 で v3 の最大の弱点が露呈**。「症状」から逆引きする運用者にとって、Topics は「機能ツリー」なので章選定で 1 クッション増える。**Topics 章末 troubleshooting だけでは Q2-c, Q2-d のような章横断症状は救えない**。Verification タブの discrepancy 一覧も「症状逆引き」とは方向が違う。
**ただし**: Topics 各章末 troubleshooting.md が揃えば P2 は ◯ 評価で落ち着く。v2 の Runbooks ◎ には届かない構造的劣位。

### P3 開発者

| 質問 | v3 動線 | v2 | v3 | コメント |
|---|---|---|---|---|
| Q3-a「fpmsyncd と orchagent 分界」 | Topics → 02-bgp/architecture + 20-swss-sai-redis | ◯ | ◯ | 同等 |
| Q3-b「新 CONFIG_DB + YANG」 | Reference → config-db/yang + Library → management | △ | △ | 横断 how-to 欠落、v3 でも未解決 |
| Q3-c「SAI extension 追加」 | Library → categories/sai-extensions | △ | △ | 同等の薄さ |
| Q3-d「ZMQ producer/consumer」 | Library → internals | ◯ | ◯ | 同等 |
| Q3-e「HLD は信用できるか」 | **Verification → discrepancies.md** | △ | **◎** | **v3 で大幅改善**。開発者が実装前に「公式 HLD と実装の差」を判断できる |

→ **P3 は v3 で 1 軸 (Q3-e) 改善**。Verification タブ独立により、開発者が「HLD を当てにする前に乖離を見る」動線が確立される。これは v3 の最大の独自貢献。

### P4 評価者

| 質問 | v3 動線 | v2 | v3 | コメント |
|---|---|---|---|---|
| Q4-a「sonic-vs で BGP」 | index.md ロールカード → Topics 02-bgp/setup | ◯ | ◯ | Get Started 廃止で同等 |
| Q4-b「Dual ToR」 | Topics → 05-dual-tor | ◎ | ◎ | 同等 |
| Q4-c「EVPN VXLAN 2 leaf」 | Topics → 03-vxlan-evpn | ◯ | ◯ | 同等。コンテンツ問題は変わらず |
| Q4-d「fast-reboot 時間」 | Topics → 11-reboot + Library → system | △ | △ | 同等 |
| Q4-e「この OSS は信用できるか」 | **Verification → coverage.md** | × | **◎** | **新規**。評価者が「裏取り済 N%」を一目で見られる |

→ **P4 も Q4-e で v3 が明確に上回る**。評価者ペルソナにとって `coverage.md` (verification ステータス統計) は「OSS 採用判断材料」として有効。

### P5 経営判断者

| 質問 | v3 動線 |
|---|---|
| Q5「SONiC OSS の成熟度」 | **Verification → coverage.md** で hld-only / code-verified / discrepancy-found の比率を一望 |

→ **v3 で初めて P5 の入口が構造化**。v2 では Reference 配下に埋もれていた。`coverage.md` を読み物 (グラフ含む) として整備すれば P5 が直撃する。**ただし P5 は本リポのスコープ外と冒頭で明示すべき**。

### 動線テスト総括

| ペルソナ | v2 | v3 | 改善度 |
|---|---|---|---|
| P1 初学者 | 改善大 | 同等 | **±0 (index.md 実装次第)** |
| P2 運用者 | 改善大 | 改善中 | **−1 (Runbooks 廃止の構造的劣化)** |
| P3 開発者 | 改善中 | 改善中+ | **+1 (Verification で HLD 信頼性可視化)** |
| P4 評価者 | 改善中 | 改善大 | **+1 (coverage.md で OSS 評価材料)** |
| P5 経営判断 | スコープ外明示なし | スコープ外明示 + coverage 提供 | **+1** |

**ネット**: +2 / 5 ペルソナ。v3 は v2 より総合で僅差で上回る。ただし P2 (運用者) は構造的に劣化するため、Topics 章末 troubleshooting の充実が必須条件。

---

## 3. v3 の盲点 (タスク §3)

### 3.1 Topics 章末「troubleshooting サブページ」は本当に runbooks の代替か？

**部分的に No**。

- **現状確認 (本評価時)**: 22 章中、troubleshooting.md を持つ章は **0 件**。全章新設が必要。`operations.md` に運用情報は集約されているが、症状逆引きの形式ではない。
- **構造的問題 1 (章横断症状)**: `techsupport` / `core dump` / `container restart loop` / `config save → reload 順序` のような章横断症状は、どの章の troubleshooting に置くか判断不能。読者も「どの章を見れば」と迷う。Runbooks 独立タブならフラットな症状一覧で逆引き可能。
- **構造的問題 2 (検索性)**: 4 タブ全文検索で「BGP not established」は引けるが、Topics 章末に埋もれると **タイトル一覧画面 (Verification の discrepancies のような) が存在しない**。運用者が「何の症状に対応 runbook があるか」を俯瞰できない。
- **緩和策**:
  - 各 Topics 章末 troubleshooting.md を **必須化** (テンプレ・Indexer 自動生成枠)
  - Topics 配下に **横断 `troubleshooting-index.md`** を 1 ページ置き、症状 → 章へのフラットな逆引きリストを Indexer で自動生成 (frontmatter `symptoms:` を集約)
  - `troubleshooting-index.md` を Topics タブの 1 番目に固定し、運用者の入口にする
- **結論**: troubleshooting サブページのみでは Runbooks の代替にならない。**横断 troubleshooting-index.md を併設して初めて代替成立**。

### 3.2 `related_topics:` frontmatter の機械追加は実装可能か？ メンテ持続性は？

**実装は可能、ただしメンテ持続性に課題**。

- **実装案 (Indexer 拡張)**:
  1. `topics/<NN-area>/index.md` の frontmatter に `linked_areas: [routing, switching]` を手動で記述 (22 章のみ、メンテ可能)
  2. Indexer が `topics/<NN>/` ↔ `area/*` を `linked_areas` から逆引きし、`related_topics:` を `area/` 各ページに **追記** (上書きはしない、人手記述は保持)
  3. mkdocs プラグインまたは Jinja マクロで `related_topics` を「関連」セクションに自動 render
- **メンテ持続性**:
  - 新ページ追加時に `related_topics:` が空でも自動補完されるならゼロメンテ
  - **問題**: area ページの主題が複数章にまたがるとき (例: BGP loading optimization は 02-bgp と 11-reboot 両方) 自動推定が難しい。frontmatter にキーワード or タグを別途持つか、ファイルパス heuristic に頼る
  - **メンテ負担**: 22 章の `linked_areas:` は変動が少ないため、月 1 〜半年に 1 回見直しで足りる。低負担
- **代替案**: タグプラグイン (v2 で取り下げた案) のほうが自動分類精度は上だが、構造 vs 横断の混乱があるため取り下げ判断は妥当
- **結論**: **実装可能で持続性も低負担**。ただし「複数章リンク」「自動推定不能ケース」は手動補完を許容する設計が必須。Indexer に CI で「`related_topics:` が空の area ページ N 件」を warn 出力させると放置を防げる。

### 3.3 Verification タブの中身 (coverage.md / queue.md) は本当に読者に届くか？

**Yes (P3 / P4 / P5)、No (P1 / P2)**。

- **届く読者**: 開発者 / 評価者 / 経営判断者は「HLD と実装の乖離」「裏取り進捗」を判断材料にする。Verification タブを能動的に開く動機がある。
- **届かない読者**: 初学者は Verification の存在自体を意識しない。運用者は「動く / 動かない」が関心事で discrepancy には興味薄い (運用者にとって「これは未検証」より「これで直る」のほうが価値高い)。
- **必須要件**:
  - **`coverage.md`**: グラフ (mermaid pie / bar) で「全 N ページ中、code-verified X%, hld-only Y%, discrepancy-found Z%」を 1 画面で。area 別 / topic 別の breakdown も。**自動生成必須** (Verifier 集計スクリプトから render)
  - **`queue.md`**: per-page queue (`meta/queue/*.json`) を集約した「裏取り懸念点」一覧。読者が「自分が読んでいるページに疑問があるか」を逆引きできるよう、ページ slug でソート
  - **`discrepancies.md`**: 既存の `_meta/discrepancies.md` を移動。各 discrepancy にバッジ + 該当ページへのリンク
- **各ページからの導線**: 各ページの frontmatter `verification:` から、ページ上部に ⚠️ バッジを表示し、クリックで Verification タブの該当 entry へ jump。これがないと Verification タブは「能動的に開いた人だけ届く」孤島になる
- **結論**: 中身設計次第。**バッジ自動表示と coverage.md グラフ化を必須セットにすれば届く**。それ単体だと P3 / P4 / P5 限定。

### 3.4 guides 削除で初学者は迷わないか？

**条件付き No**。

- **削除しても迷わない条件**:
  - `docs/index.md` 冒頭に **ロール別 grid cards** (Beginner / Operator / Developer / Evaluator) を必ず配置
  - 各カードから直接 Topics 章 or Reference セクションへ deep link
  - 1st viewport に収まる (scroll 不要)
- **迷うケース**:
  - index.md が「リポ説明 → カード」の順だと初学者は説明を読み飛ばしてカードに到達できない
  - カードが薄いリンク集 (現 guides/beginner.md 相当) だと「結局どこを読めば」が同じ
- **比較**: 現 `guides/beginner.md` は薄いリンク集 (5 リンク程度) なので、削除して index.md に統合する痛みは小さい。**ただし統合時に「ロール別 + 直近のおすすめ章 3 つ」程度の中身を持たせること必須**
- **結論**: index.md の実装品質次第。**雑に削除すると初学者が迷う**。実装時にレビュー必須。

---

## 4. v3 採用可否 (タスク §4)

### 結論: **条件付き Yes (採用推奨)**

v3 は v2 より総合 +2 ペルソナで僅差で上回る。特に Verification タブ独立により P3 / P4 / P5 の独自価値昇格は v2 で実現できなかった構造改善。Tab 数削減 (5→4) も Hick's Law 的に妥当。

ただし以下 4 条件の併走が必須:

1. **Topics 22 章全てに troubleshooting.md を新設 + Topics 配下に横断 troubleshooting-index.md を Indexer 自動生成** (P2 運用者の Runbooks 廃止ロスを構造的に埋める)
2. **`docs/index.md` をロール別 grid cards + 直近おすすめ章 3 つの真のランディングに再設計** (Get Started 廃止のロス補償)
3. **`related_topics:` frontmatter 機械追加 + 各ページ「関連」セクション自動 render + CI で空 frontmatter warn** (Topics ⇔ Library 重複の機械的解消)
4. **Verification タブの coverage.md グラフ化 + 各ページ verification バッジ自動表示 + バッジクリックで該当 entry に jump** (Verification 独立タブを孤島にしない)

条件 1, 4 は **同時実装でないと v3 を採用するメリットが半減**する。PR 1 (`verification/` 新設) と PR 4 (新設、Topics troubleshooting 一括) を併走必須。

### v2 から v3 への乗り換え推奨度

- **乗り換える**: 上記 4 条件を Phase 1 (1〜2 週間) で揃えられる場合
- **v2 で留まる**: 条件 1 (22 章 × troubleshooting + 横断 index) が 4 週間以上かかる見込みの場合。中途半端な v3 (Verification タブだけ独立、Topics 章末 troubleshooting 未整備) は v2 より劣化する

main エージェントの現状リソース (Phase 6 完了、455 ページ merge 済、自動化基盤稼働) を見るに、**条件 1〜4 は 1 週間で揃えられる見込み**。よって **v3 採用を推奨**。

---

## 5. 残課題 (Phase 2 以降)

- **P3 開発者向け横断 how-to の欠落** (Q3-b / Q3-c) は v2 / v3 ともに未解決。`topics/23-developer-howto/` のような開発者専用章新設で対応
- **Verification タブの ML 的な信頼度スコア**: 単純な hld-only / code-verified の 3 値だけでなく「裏取り深度」を数値化できれば P3 / P4 にさらに有用
- **ペルソナ P5 経営判断者向けサマリー**: `coverage.md` トップに「Executive Summary」セクションを 3〜5 行で

---

## 6. 前回 (v2 評価) からの自己訂正

第 2 ラウンド §3.1 で「5 タブ固定、4 圧縮メリットなし」と判定したが、**v3 提案で Verification 独立タブが 5 タブ目相当を担うことで、見かけ 4 タブでも実質 5 軸を維持できる**ことを見落としていた。Tab 上部の選択肢は 4 個に圧縮しつつ独自価値 (Verification) は昇格、というのは v2 時点の自分のフレームでは思いつかなかった解。

**結論訂正**: 4 タブ + Hub セクション (Verification 独立) は 5 タブより優れている。v2 推奨を v3 推奨に上書きする。
