# 構成 v3 再評価 (Devil's Advocate / 反論役・第 3 ラウンド)

- 作成日: 2026-05-11
- 評価対象: `/tmp/re-proposal-v3.md` (4 タブ + Verification ハブ案)
- 前回レポート: `meta/structure-rereview-devil.md` (5 タブ案を「No、大幅修正必要」と判定)
- 立場: 反論役。main の自己評価には乗らず、徹底批判する。
- 前提実測 (2026-05-11):
  - `docs/topics/` 22 章中、`operations.md` を持つ章 = **21** (`01-overview` のみ非保有)。`troubleshooting.md` を持つ章 = **0**
  - `docs/_meta/discrepancies.md` への被リンク = `docs/topics/22-reference-index/` 配下 3 ファイルから計 **6 箇所**
  - `docs/categories/` = 10 ファイル + index
  - `docs/guides/` = beginner / developer / evaluator / operator / index の 5 ファイル
  - `mkdocs.yml` で `navigation.tabs` は既に有効、`overrides:` 未設定
  - `docs/.pages` (トップ用) = 未確認 (PoC 未実施)
  - frontmatter `related_topics:` を持つ md = **0 件** (現状)

---

## 結論 (TL;DR)

**採用すべきか: No (大幅修正必須)**。

v2 (5 タブ) を否定したのは正しかったが、v3 は **「5 タブから 1 タブ削っただけの再配置案」** であり、本質的に同じ欠陥を抱える。最大の問題は次の 3 つ:

1. **Verification タブ 3 ページで 1/4 の上部 nav 面積を占有するのは費用対効果が悪い**。discrepancies.md は 1 ページ、coverage.md / queue.md は **未着手 (= 自動生成スクリプトすら無い)**。実体 3 ページのために、Topics 22 章・Reference 166 ページ・Library 327 ページと **対等な視覚的重み** を与えるのは IA の重大な歪み。
2. **`related_topics:` frontmatter 機械追加は 600+ ページ規模で「メンテ持続性ゼロ」**。前回 v2 の Tags プラグイン批判 (657 ファイル一括更新は虚偽の見積もり) を、名前を `related_topics:` に変えただけで再提案している。新章追加・章名変更・slug rename 時の全件追従コストが設計に含まれていない。
3. **「足し算ではなく引き算」と main は主張するが、実態は「Get Started 廃止 (-1)・Verification 新設 (+1)・Library 改称 (±0)」で純減ゼロ**。Topics と Library の重複ページ問題 (前回 D が指摘した 02-bgp 章 ⇔ `routing/bgp-*` の二重持ち) は v3 でも未解決。`related_topics:` の双方向リンクは **重複の固定化** であり解消ではない。

---

## 1. v3 の問題点 (12 件)

### Q1. Verification タブ 3 ページで 1/4 を占有する価値があるか → ない

提案する Verification タブの中身:

- `verification/discrepancies.md` — 既存 `_meta/discrepancies.md` の移動
- `verification/coverage.md` — **未作成**。自動生成と謳うが生成スクリプトは設計のみ
- `verification/queue.md` — **未作成**。`meta/queue/*.json` を集計するスクリプトは存在するが、`docs/` 配下に出力する仕組みは未実装

つまり Verification タブは **実体 1 ページ + 未着手 2 ページ** で、トップ nav の 25% を消費する。比較対象:

- Topics タブ: 22 章 / 143 ページ
- Reference タブ: 166 ページ
- Library タブ: 9 area / 327 ページ

**1 タブ = 1 ページ (実質)** は IA として明らかに不均衡。`navigation.tabs` の各 tab は同列に並ぶため、視覚的に「Topics と同じ重み」を読者に与えるが、内容量は 1/100 以下。`/known-issues/` のような **ページ単独昇格** で十分で、タブ昇格は overkill。

### Q2. `related_topics:` frontmatter 600+ ページ機械追加のメンテ持続性

提案 PR 3 で「Topics 章 ↔ 該当 area ページの双方向追加」と書くが:

- 22 章 × 平均 6 サブページ (concept/setup/operations/architecture/internals/index 等) = **~140 Topics ページ**
- 9 area × 平均 36 ページ = **~327 Library ページ**
- 想定リンク数: Topics 1 章あたり 5〜15 area ページが関連 → 双方向で **~3000 リンク**

このうち:

- 1 章追加ごとに `related_topics:` を ~10 ページ書き換え必要
- 1 area ページ rename (slug 変更) ごとに該当 `related_topics:` を全件 grep して書き換え必要
- 自動生成スクリプトが書ければ良いが、`related` の判定 (どの area ページが章 03 に該当するか) は **意味判定**。LLM 経由かルールベースか手動かが未定義

前回 v2 で Tags プラグインを「657 ファイル更新は虚偽の見積もり」と否定したが、v3 の `related_topics:` は **判定ロジックが Tags より複雑** (Tags は 1 ページ 1 タグ集合だが、related は 1 ページ N 個の他ページ参照)。**前回の批判を解決していない**。

### Q3. guides 削除で初学者導線が消える

v3 は「guides を index.md に統合 → guides 削除」と書くが、現状の `docs/guides/`:

- `beginner.md` — SONiC を初めて触る読者向けの章順案内
- `evaluator.md` — 製品評価担当者向け
- `operator.md` — 運用者向け
- `developer.md` — 開発者向け
- `index.md` — 4 ペルソナのハブ

これらは **ペルソナ別の章選択ガイド** であり、index.md の grid cards (= タブ別) では代替できない。grid cards は「Topics / Reference / Verification / Library」の **構造別** 入口で、「初学者は何から読むか」のペルソナ別導線とは軸が違う。

具体例: 「BGP を初めて学ぶ運用者」は `guides/operator.md` から「Topics 02-bgp の concept → setup → operations の順」と誘導される。v3 では index.md の Topics カードをクリック → 22 章一覧 → 自力で 02-bgp を選ぶ必要があり、**Hick's Law の選択コストはむしろ増える**。

ペルソナ導線を index.md に圧縮するには **index.md が肥大化** (現状簡素な 1 画面 → 5 ペルソナ × 5 章推奨で 25 リンク以上) し、grid cards との両立は構造的に困難。

### Q4. Topics と Library の重複は `related_topics:` だけでは解消しない

`related_topics:` は **「両方読め」と読者に促すだけで重複そのものは残す**。具体的に:

- `topics/02-bgp/concept.md` の冒頭 200 行と `routing/bgp-overview.md` の冒頭 200 行は **記述内容が ~70% 重複** (前回 D が grep で確認済)
- v3 案では両方を維持し、frontmatter で相互リンクするだけ
- 結果: Google 検索で「sonic bgp」を打つと両ページが上位に並び、**どちらが正かを読者が判定** することになる
- これは「重複の固定化」であり「重複の解消」ではない

真の解は (a) 一方を **redirect** で他方に統合 (b) 役割を明確に分離 (Topics = 読み物 / Library = HLD 一次資料) してコンテンツを実際に書き分ける、のいずれか。v3 はどちらもやらず frontmatter リンクで誤魔化す。

### Q5. categories を Library 末尾に置くと埋もれる

`docs/categories/` は 10 件 (bgp-evpn, container-build, dash, dual-tor, gnmi-openconfig, mib-snmp, multi-asic, reboot, sai-extensions, smartswitch)。これは **横断的にまとまった良質な索引** で、現状トップ nav に独立して見える。

v3 では Library タブ配下の末尾 (`architecture / routing / switching / overlay / acl-qos / system / management / platform / internals / categories` の 10 番目) に押し込める。Library タブを展開しないと見えず、展開しても 9 area の後に来るため **読者が辿り着く前に離脱**。

categories の真の役割は「Topics と Library を横断する第三の索引」であり、Library 配下の 1 dir 扱いは性格不一致。

### Q6. Topics 章末 troubleshooting サブページは現状 0 章が持っている

実測: `docs/topics/` 22 章のうち `troubleshooting.md` を持つ章 = **0**。代わりに 21 章が `operations.md` を持つ。

v3 は「runbooks タブ廃止 → Topics 章内 troubleshooting サブページに統合」と書くが:

- 22 章すべてに新規 `troubleshooting.md` を書く必要 → 前回 v2 で否定した「ソース無しの架空 runbooks」と同じ問題
- もしくは既存 `operations.md` を `troubleshooting.md` に改称 → URL 変更 = SEO 毀損 + 既存被リンク (前回 v2 でも避けた制約)
- もしくは `operations.md` に troubleshooting 節を追記 → これは v3 案の「サブページ」と矛盾

**「v2 で否定した runbooks 新設コストを、Topics 章内に分散して隠蔽した」だけ**。総作業量は変わらない。

### Q7. `navigation.tabs` 4 タブの深さ制約

`mkdocs-material` の `navigation.tabs` は **トップレベル nav 項目を tab 化** する。`navigation.sections` と併用時:

- tab 1 (Topics) 配下: 22 章 → section として展開 → 各章配下にページ
- tab 4 (Library) 配下: 9 area + categories → section として展開 → 各 area 配下にページ

ここで問題: Library タブ配下の **2 階層目** (architecture / routing 等) が左サイドバーで section 表示されるが、**Topics タブ配下の章 (22 個)** も同じ section 表示。階層深度が tab によって不揃い (Topics は 2 階層、Library は 3 階層) で、サイドバー UX が不安定。

PoC が無いまま「navigation.tabs で 4 タブ実装可能」と断定しているのは前回 v2 と同じ過ち。Library 配下の 10 dir を「Library タブの子」として nav 階層化する `.pages` 記法は **awesome-pages 標準機能を超える** 可能性が高い (前回 v2 §Q4 で指摘済、v3 でも検証されていない)。

### Q8. `_meta/discrepancies.md` → `verification/discrepancies.md` 移動で既存リンク 6 箇所が切れる

実測:

```
docs/topics/22-reference-index/index.md:41:        ../../_meta/discrepancies.md
docs/topics/22-reference-index/concept.md:46:       docs/_meta/discrepancies.md
docs/topics/22-reference-index/quality-gaps.md:12:  docs/_meta/discrepancies.md
docs/topics/22-reference-index/quality-gaps.md:17:  ../../_meta/discrepancies.md
docs/topics/22-reference-index/quality-gaps.md:24:  ../../_meta/discrepancies.md
docs/topics/22-reference-index/quality-gaps.md:53:  ../../_meta/discrepancies.md
```

v3 PR 1 で移動するなら **同 PR でこの 6 箇所を書き換え必須**。mkdocs `--strict` で broken link 検出されるため CI 落ち確実。提案文には触れられていない。さらに、外部から `/_meta/discrepancies/` URL を踏んだ読者は 404 を見る (redirect 設定なし)。「URL 完全維持」原則を v3 自身が破っている。

### Q9. 「5 タブ → 4 タブ = 引き算」は虚偽

詳細:

| 軸 | v2 (5 タブ) | v3 (4 タブ) | 差 |
|---|---|---|---|
| Get Started タブ | あり | なし (index.md に統合) | -1 |
| Topics タブ | あり | あり | 0 |
| Runbooks タブ | あり | なし (Topics 章内に統合) | -1 |
| Reference タブ | あり | あり | 0 |
| Verification タブ | なし (Reference 配下) | あり (新設) | +1 |
| Subsystems / Library タブ | あり | あり (改称) | 0 |

純差: -1 -1 +1 = **-1 タブ** (5 → 4)。

しかし新規作業量で見ると:

- Get Started 廃止 = guides 5 ファイルを index.md に統合する書き直し作業
- Runbooks 廃止 = Topics 22 章に troubleshooting サブページを書く作業 (Q6 参照)
- Verification 新設 = coverage.md / queue.md の自動生成スクリプト実装 + 既存 _meta 移動 + リンク修正

**「引き算」ではなく「再配置 + 新規作業 3 種類」**。タブ数だけ見て「シンプルになった」と称するのは欺瞞。

### Q10. coverage.md / queue.md 自動生成スクリプトの実装コストが見積もりに含まれない

提案 PR 1 で「`coverage.md` / `queue.md` 自動生成」と書くが:

- coverage.md: 各 area で `code-verified / discrepancy-found / hld-only` の比率を集計 → 既存スクリプトなし
- queue.md: `meta/queue/<area>-<slug>.json` を読んで未着手項目を一覧 → 既存 `meta/aggregate_queue.py` はあるが出力先が `docs/` ではない
- 両者とも CI で再生成しないと陳腐化 → GitHub Actions workflow 追加必要

PR 1 のスコープが「verification/ 新設 + 移動 + nav 階層化」と書かれているが、**実態は 3 つのスクリプト + 1 つの workflow**。3 PR で完結とする見積もりは Tags の時と同じ過小評価。

### Q11. index.md 冒頭 grid cards は 4 タブ + Verification Hub で 5 カード必要

`docs/index.md` 冒頭セクションに「4 タブ + Verification Hub カード」と書く (提案 §物理構造)。

「4 タブ」だけならカード 4 枚で良いが、Verification Hub を **追加で** カード化するなら 5 枚。タブとカードの数が一致せず、読者は「Verification はタブとカード両方にあるが、Topics は片方だけ」と混乱する。

または Verification をカードから外すと、Hub の昇格意義が薄れる (タブはあるが冒頭で目立たない)。**設計矛盾**。

### Q12. `related_topics:` frontmatter 機械追加 PR 3 のレビュー負荷

PR 3 で 600+ ファイルの frontmatter に `related_topics:` を一括追加するなら、PR の diff は **600+ ファイル × 数行**。これを 1 PR でレビューするのは現実的でない (前回 v2 の Tags 全件更新と同じ問題)。

分割するなら area 別に 10 PR 程度に分けるべきだが、その分 main の作業継続コストが膨らみ、「3 PR で完結」は虚偽。

---

## 2. v3 を採用すべきでない理由

### R1. 「5 タブ → 4 タブで足し算ではなく引き算」は実態に反する (Q9 詳述)

v3 が誇る「タブ数削減」は数字遊びで、新規作業量は v2 と同程度かそれ以上。「Verification 新設 + 各章 troubleshooting + index.md 統合 + related_topics 全件追加」の 4 種類の新規作業が同時並行で必要。

### R2. v3 は前回 D が指摘した本質的な問題 (Topics ⇔ Library 重複) に対応していない

前回 D は「重複ページを統合 (削除と merge) しないと真の整理にはならない」と主張した。v3 は frontmatter リンクで「重複の固定化」をするだけ。**main は引き算を 2 連続で避けている**。

### R3. main エージェントが構造提案を 3 連続で出すこと自体が異常

- v1 (archive 案、2026-05-11 朝) → 否定 → 撤回
- v2 (5 タブ案、同日) → D 否定 → 撤回
- v3 (4 タブ案、同日) ← いま評価中

**24 時間で 3 案** は構造設計の根拠データ不足を物語る。AI 評価だけで構造変更を進めるのを止め、**読者フィードバックを取る** ことが先。

### R4. Verification タブの独立は「自己満足」で読者価値が不明

discrepancy-found ページは 39 件あり貴重だが、それを「タブ昇格 = サイト全体の 1/4 の重み」で扱うのは **書き手側の達成感** であり、読者の主たる入口ではない。読者の主たる入口は「BGP を学びたい」「sonic-cli コマンドを引きたい」であり、「HLD と実装の乖離一覧を見たい」は二次的な需要。トップ nav 1/4 を割く根拠が薄い。

### R5. URL 維持原則を Verification 移動で自ら破っている (Q8)

`/_meta/discrepancies/` → `/verification/discrepancies/` は URL 変更。v3 自身が掲げる「URL 完全維持」原則の最初の例外をこの提案自身で作っている。原則破りなら他にも壊しても良い理屈になり、設計の骨が抜ける。

---

## 3. 代替案

### 案 W (推奨): **構造を変えず本文品質を上げる**

前回 D の主張を継承。具体的に:

- discrepancy-found 39 件のページに **詳細な検証コード参照** を追記 (該当 sonic-buildimage commit、テスト失敗例、回避策)
- Topics 22 章の `operations.md` を **既存運用ノートとして拡充** (現状の `operations.md` は記述薄め、運用観点の追加で価値倍増)
- categories 10 件のページに **更新日と検証ステータス** を frontmatter で明示

これは構造変更を **ゼロ** にし、各ページの中身の品質を上げる。3 連続の構造提案で疲弊した main の判断力を回復させる。

### 案 X: **完成度ベースの軸で再分類**

タブを (a) 構造別 (Topics / Reference / Library) でなく (b) **完成度別** (Verified / In Progress / Stub) で切る。

- Verified タブ: `verification: code-verified` の全ページ (現在 ~300 ページ)
- Discrepancy タブ: `verification: discrepancy-found` (39 件)
- Reference タブ: CLI / CONFIG_DB / YANG (166 ページ)

読者の問い「これは信用していいのか?」に直接答える。Diátaxis から脱却し、SONiC docs 独自の軸を立てる。

### 案 Y: **機能完成度ベースで再分類**

Topics 章を「機能の SONiC 内実装完成度」で並べる:

- Production-ready: BGP / VLAN / ACL / QoS …
- Beta: DASH / SmartSwitch HA / SRv6 …
- Experimental: P4-PINS / VOQ / Dual-ToR …

読者の問い「これは production で使えるか?」に直接答える。番号順 (01-22) より読者価値が高い。

### 案 Z (前回提案再録): **何もしない + 検索 UX 改善**

`mkdocs.yml` に `search.suggest` `search.share` を追加し、`docs/index.md` 冒頭に検索バー誘導を強化。構造ゼロ変更でリスクゼロ。

---

## 4. 比較表

| 案 | 入口分かりやすさ | 重複削減 | メンテ性 | URL/SEO | 既存資産活用 | リスク | 読者価値 |
|---|---|---|---|---|---|---|---|
| v3 (4 タブ) | △ (Verification 過剰) | × (related で固定化) | × (related 全件追従) | × (_meta 移動) | ◯ | 中 | △ |
| 案 W (本文品質) | (変化なし) | △ (将来統合余地) | ◎ | ◎ | ◎ | ゼロ | ◎ |
| 案 X (完成度軸) | ◎ (信用度問い) | ◎ (Stub 削除誘発) | ◯ | △ (再分類で URL 影響) | ◯ | 中 | ◎ |
| 案 Y (機能完成度) | ◯ | △ | ◯ | ◯ | ◯ | 小 | ◯ |
| 案 Z (検索 UX) | △ | × | ◎ | ◎ | ◎ | ゼロ | △ |

判定: **案 W が最善**。3 連続の構造提案を止め、本文品質に注力。

---

## 5. 結論

### 採用すべきか: **No (大幅修正必須)**

v3 を採用するなら最低限以下を **事前に** 解決すべき:

1. Verification タブを **タブではなく `/known-issues/` 単独ページ昇格** に格下げ。タブ 1/4 専有を取り消す。
2. `related_topics:` 機械追加の **実装スクリプトを先に PoC で動かして見せる** こと。Topics 章 ⇔ area ページの判定ロジックを口頭仕様だけで進めるのは前回 v2 の Tags と同じ過ち。
3. guides 削除は撤回。**Get Started タブ復活 (= v2 の 5 タブに戻る) または guides を維持** の二択。「index.md に統合」はペルソナ導線を失う。
4. Topics 章末 troubleshooting サブページは **既存 `operations.md` を活用して新規作成を避ける** こと。22 章 × 新規ページは「ソース無しの架空 runbooks」と同じ問題。
5. `_meta/discrepancies.md` 移動は既存 6 箇所のリンク修正を同 PR で実施 + redirect ルール追加。

### 撤回するなら次の進め方

1. **v3 提案を撤回** し、構造変更の議論を 1 週間停止
2. **案 W を採用** (本文品質向上):
   - discrepancy-found 39 件に検証コード参照追記 (1 PR ~5 ファイル × 数 PR)
   - Topics 22 章 `operations.md` 拡充 (1 PR ~3 章)
   - categories 10 件に更新日 frontmatter 追加 (1 PR)
3. **次回構造変更は読者フィードバック取得後** (Phase 6 で公開した discrepancy-found 39 件を SNS/コミュニティに告知 → 1 週間のアクセスログ・フィードバックを取る)
4. **AI による机上評価だけで構造変更を進める運用を停止する** (前回レポート §6 で既に指摘)

---

## 6. メタ批判: 「24 時間で 3 案」の異常さ

- 2026-05-11 朝: v1 (archive 案) → 4 評価 → 否定 → 撤回
- 2026-05-11 昼: v2 (5 タブ案) → 6 評価 → 否定 → 撤回
- 2026-05-11 夕: v3 (4 タブ案) ← いま評価中

**1 日 3 提案は構造設計者として未熟か、または「動かしたい衝動」が強すぎる**。Phase 6 で 455 ページの品質を積み上げた成果と、その上に乗せる構造案の準備期間は **桁違いに不均衡**。Phase 6 の準備に数ヶ月かけたなら、構造変更の準備にも同等の時間 (実ユーザー調査・PoC・段階的検証) をかけるべき。

現リポの真のボトルネックは前回も指摘した通り「読者フィードバックゼロ」。**動かさない勇気と、データ取得への投資** が次の一歩。

---

## 付録: 実測データ (2026-05-11)

- `docs/topics/[0-9]*/` = 22 章
- `find docs/topics -name 'operations.md' | wc -l` = **21** (`01-overview` のみ非保有)
- `find docs/topics -name 'troubleshooting.md' | wc -l` = **0**
- `docs/_meta/discrepancies.md` への被リンク = **6 箇所** (全て `docs/topics/22-reference-index/` 配下)
- `docs/categories/` = 10 ファイル + index
- `docs/guides/` = 5 ファイル (beginner / developer / evaluator / operator / index)
- `mkdocs.yml`: `navigation.tabs` 有効 / `theme.custom_dir` (overrides) 未設定
- frontmatter `related_topics:` 保有 md = **0 件**
- 累計 merge ページ数 = ~455
