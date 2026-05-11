# 構成再評価 (Devil's Advocate / 反論役・第 2 ラウンド)

- 作成日: 2026-05-11
- 評価対象: main エージェントの「**5 タブ Diátaxis 構造**」提案 (`/tmp/re-proposal-summary.md`)
- 前回レポート: `meta/structure-review-devil.md` (area→archive 案を却下)
- 立場: 反論役。main の自己評価には乗らず、再び徹底批判する。
- 前提実測: `docs/` 配下 .md 657 ファイル、`tags:` を持つ frontmatter は **0 件**、`docs/_meta/discrepancies.md` は 1 ファイルのみ存在 (まだ「ページ群」ではない)、`docs/runbooks/` は **未作成**、`docs/.pages` は各ディレクトリにあるがトップ階層用は未整備。

---

## 結論 (TL;DR)

**採用すべきか: No (大幅修正なしには不可)**。

理由を 1 行に圧縮: **前回 main が出した「破壊」案を引っ込めた代わりに、今度は「足し算」を 5 個増やす案に変質した**。`navigation.tabs` の 5 タブ、新設 `runbooks/` 10〜15 件、Tags プラグイン (= frontmatter 全件更新)、`discrepancies.md` の Reference 昇格、grid cards、Tags 自動横断ビュー — どれも単体では悪くないが、**5 つ全部を同 PR 群でやれば崩壊リスクは前回の archive 案と同等**。「URL を変えていないから安全」という主張は、運用面・コンテンツ面のリスクを過小評価している。

最大の欠陥 3 つ:
1. **Diátaxis 4 → 5 拡張は原則違反**。「Get Started」は Tutorial、「Topics」は Explanation+How-to、「Runbooks」は How-to、「Reference」は Reference、「Subsystems」は Explanation。**How-to が 2 タブに分裂し、Explanation が 2 タブに分裂している**。これは Diátaxis ではなく「Diátaxis 風の何か」であり、フレームワークの権威を借りる根拠を失っている。
2. **`docs/runbooks/` 10〜15 件は粒度未定義の架空コンテンツ**。提案は「BGP UP しない」「VLAN メンバー追加できない」など症状列挙だけで、1 runbook = 1 ページか、1 症状 = 5 ステップ × 5 ページかが未定義。Verifier の裏取りソースが無い (実機障害ログ・support バンドルの蓄積がリポにない)。**書けば憶測ベースの「もっともらしい手順書」になる** — このリポが避けてきた品質ラインを自ら踏み越える。
3. **Tags プラグイン導入 = 657 ページの frontmatter 全件更新**。現状 `tags:` 0 件。Material Tags プラグインは frontmatter `tags: [foo, bar]` が無いと何も生成しない。「3〜4 PR で完結」と書きつつ、657 ファイル × タグ判定の作業量を完全に隠蔽している。前回の「7 割を archive」と移行コストの過小見積もりは構造的に同じ問題。

---

## 1. 新提案の問題点 (12 件)

### Q1. Runbooks 10〜15 件は妥当か → 「粒度未定義」「ソース無し」で不可
提案が列挙する 10 項目「BGP UP しない / VLAN 追加不可 / FEC エラー多発 / Warm Reboot 失敗 / PFC 帯域不足 / DHCP Relay 動かない / Multi-ASIC namespace 不通 / Dual-ToR mux 切替失敗 / SAI failure / Container 起動失敗」のうち、ソースリポ (`.cache/sonic-sources/`) で `swsscommon` テストや `sonic-mgmt` テストケースとして裏取り可能なのは **半分以下**。残りはコミュニティ Slack や issue tracker の話で、このリポの「コード起点で書く」ルールに反する。10 件か 15 件か 50 件かは、対象障害の網羅性ではなく「書きやすそうな数」で決まっている。

### Q2. Reference 配下に discrepancies を昇格するのは性格不一致
Reference は **「製品の現状仕様 (CLI/CONFIG_DB/YANG)」** を引く場所。discrepancies は **「HLD 文書と実装の乖離記録」**。両者は「字引性」しか共通点が無い。読者が `/reference/` を開いた時の期待 (フィールド名・コマンド) と、discrepancy ページ (HLD 誤り指摘) は文脈が違う。**`/verification/` または `/known-issues/` という別タブが本来の置き場**。Reference に混ぜると Reference の信頼性 (= 「ここに書いてある仕様は実機と一致」) を希釈する。

### Q3. Tags プラグイン導入は 657 ページ全件更新
現状 `tags:` を持つ md は 0。タグを後付け一括追加するには (a) area から推論 (b) 手動レビュー (c) LLM 判定 のどれかが必要。(a) は area 構造に依存するので新タブ案と無関係、(b) は数百時間、(c) は前回 Verifier で 200+ ページかけたコストと同等。**「3〜4 PR で完結」は虚偽の見積もり**。

### Q4. navigation.tabs + .pages で 5 タブを実現できる技術的根拠
mkdocs-material の `navigation.tabs` は **トップレベルの nav 項目を tab として表示** する機能。`.pages` (awesome-pages) は **各ディレクトリの並び順** を制御。両者の組み合わせで 5 タブを作るには、`docs/` 直下に 5 個のディレクトリ (またはトップ `.pages` で nav 構造を再定義) が要る。`docs/topics/` `docs/reference/` は既にあるが、`docs/get-started/` `docs/runbooks/` `docs/subsystems/` は **新規ディレクトリ** で、しかも `docs/subsystems/` には `architecture/ routing/ switching/ overlay/ acl-qos/ system/ management/ platform/ internals/ categories/` の **10 dir を物理移動 or symlink** する必要がある。「URL 完全維持」と「Subsystems タブにまとめる」は技術的に両立しない (URL は `/architecture/foo/` のまま、UI 上だけ Subsystems タブ配下に見せたいなら、トップ `.pages` で `Subsystems: [architecture, routing, ...]` のような疑似グルーピングを書くしかなく、これは awesome-pages の標準機能を超える)。**「ナビ階層化のみで実現」は実装可否すら検証されていない**。

### Q5. Topics と Subsystems の重複は前回案と同じ問題
前回反論で指摘した「topics 22 章では area 全 300+ ページを吸収できない」は今回も解決していない。新案では topics と subsystems を **両方残す** ので二次資料と一次資料の二重持ちが固定化する。**どこに書くべきか論争** が PR ごとに発生する。

### Q6. Get Started と Topics の境界が読者に伝わらない
「学習段階」と「実用解説」の差は、書き手側の都合で読者から見えない。例: 「BGP の概念入門」は Get Started か Topics 02-bgp の冒頭か？ 「Dual-ToR 概要」は guides/evaluator か topics 05-dual-tor か？ 現状は両方に書く動機が生まれ、**重複コンテンツ** を誘発する。

### Q7. Diátaxis 4 → 5 拡張は原則違反 (再掲)
Diátaxis 公式 (`diataxis.fr`) は **「4 つ以上に増やすな、4 つ未満に減らすな」** を明示している。5 タブ化はこの権威を借りつつ違反している。「Hick's Law で 7±2 に収めた」と言うが、Diátaxis 公式の主張と Hick's Law を都合よく混ぜている。

### Q8. guides 4 + categories 11 + topics 22 + area 9 を全部維持なら情報重複は残る
新案は 5 タブのうち Get Started に guides を、Topics に topics を、Subsystems に area + categories を「再配置」するだけで、**ページ数は 600+ のまま、コンテンツの重複も解消しない**。「入口の見た目」と「情報重複の有無」は別問題。重複問題の解は「ページの統合 (削除と merge)」しかなく、新案はそれをやらない。

### Q9. Runbooks の粒度未定義 (再掲) は SEO リスクも生む
1 runbook = 1 ページなら 10〜15 ページしかなく、検索流入は薄い。1 ステップ = 1 ページなら 100+ ページに膨らんで保守不能。**粒度を決めずに「とりあえず作る」と SEO・保守の両面で中途半端になる**。

### Q10. `.pages` の保守性低下
Writer (バッチ #1〜#11) は各 area の `.pages` だけ触ればよかった。トップ `.pages` で 5 タブの nav 構造を集中管理すると、新章追加のたびにトップ `.pages` の修正が必要になり、**並走 Writer のマージコンフリクト** が再燃する (前回 §9 の「branch HEAD 共有」「verification-queue 編集レース」の構造的再来)。

### Q11. grid cards (`docs/index.md` 冒頭 5 入口カード化) は美的問題、IA 問題ではない
カードが 5 枚あっても、読者が「Get Started と Topics の違い」を 1 秒で判別できなければ Hick's Law の選択コストはむしろ増える (タブ 14 個から 5 個に減らしても、5 個の意味が曖昧なら選択時間は短縮しない)。

### Q12. `discrepancy-found` ⚠️ バッジ自動表示は技術詳細が未定義
frontmatter `verification: discrepancy-found` を読んで Material のテンプレートで自動表示するには **theme override (overrides/main.html 等)** が必要。現リポは `theme: name: material` 標準テンプレ使用で overrides は未設定。「自動表示」と一言で済ませているが実装工数は数 PR 分。

---

## 2. 提案の根拠の弱さ (3 件)

### R1. Hick's Law (7±2) を nav の選択肢数に適用するのは誤用
Hick's Law (1952) は **均質な選択肢から 1 つを選ぶ** 状況の反応時間モデル。docs サイトのナビは (a) 検索が主導 (`navigation.instant` + Lunr) (b) 階層を深掘りすれば各層は数個ずつ という運用が一般的で、トップ nav の数を 14 → 5 に削ることが体験を改善する根拠は薄い。実際の docs (Kubernetes, AWS, Cisco) はトップ nav 20+ が普通。

### R2. Diátaxis は技術ドキュメントの **1 つの** フレームワークに過ぎない
他に DITA (OASIS) や Microsoft Style Guide IA、Google Developer Documentation Style Guide IA など複数の主流がある。SONiC のような **複数の独立コンポーネント (SWSS/SAI/sonic-mgmt/sonic-buildimage) を抱えるシステムソフトウェア** に Diátaxis が最適である根拠は提示されていない。Linux Kernel docs (`Documentation/`) も、OpenStack docs も Diátaxis を採用していない。SONiC が違うべき理由が無い。

### R3. 「URL を壊すな」で 4 評価が一致 → これは制約であって構造改善の **天井**
4 評価 (A/B/C/D) が URL 維持で一致したのは、**前回 archive 案の SEO 毀損を回避するため**。しかし URL 維持を絶対条件にすると、構造改善は (1) frontmatter 拡張 (2) `.pages` の並べ替え (3) index.md / カードの追加 — の 3 つに限定される。**5 タブ化はこの 3 つの範囲を超えており、URL 維持が嘘になるか、構造改善が見せかけだけになる**。

---

## 3. 代替案 (前回案 Z の発展 + 新規 2 件)

### 案 Z+ (推奨): 前回案 Z + 「読者導線 1 ページ」追加
- 前回 Z: 物理 dir 不変、frontmatter `kind:` タグ、Material Tags、`index.md` 4 段導線
- 追加: `docs/_meta/discrepancies.md` を `/known-issues/` に独立タブ昇格 (Reference に混ぜない)
- 追加: `docs/guides/operator.md` を充実させる (5 タブ案で言う Runbooks の役割を、既存 guides の枠で消化)
- メリット: 5 タブ案の「読み手導線改善」目的を 1 PR で達成し、Diátaxis 偽装も Tags 全件更新も runbooks 新設も避ける
- 移行コスト: **小** (3 PR: index.md 改修 / discrepancies 独立化 / operator guide 強化)

### 案 V: **「何もしない」+ 検索 UX 改善のみ**
- 構造は完全現状維持
- `mkdocs.yml` に `search.suggest` `search.highlight` `search.share` を追加し、`docs/index.md` 冒頭に検索バーを巨大表示
- 「14 セクションが多い」問題を、**ナビではなく検索で解く**
- 根拠: 実 docs サイトの行動分析では nav クリックより検索が主導 (AWS Docs 等で 70%+ が検索流入)
- メリット: コストほぼゼロ、リスクゼロ
- デメリット: 「構造を整えた感」が無く、ステークホルダー (= ユーザー自身) に達成感が薄い

### 案 U: **カードソーティング & ユーザーテスト後に再評価**
- 5 〜 10 名 (社内 / コミュニティ) にカードソーティング (主要 30 〜 50 ページ) を依頼
- 結果を集計し、初めて構造案を決める
- 現状: 4 評価 (A/B/C/D) はすべて **AI による机上評価**。実ユーザーが何に困っているかのデータが 0
- メリット: 構造変更の科学的根拠を得られる
- デメリット: 数週間かかる。だが**前回の archive 案・今回の 5 タブ案を続けて出している現状は、根拠なしのちゃぶ台返しが続いており、データなしに次案を採用するのは無責任**

### 既存資産の選択的廃棄 (main が避けた選択肢)
- 番号付き topics `01-22` の重複ページ (例: 02-bgp 章と routing/bgp-*.md) を **マージして片方を削除** → 物理ページ数を 657 → 500 程度に削減
- 廃棄判断は frontmatter `verification:` を基準: `hld-only` のうち代替 (`code-verified` ページ) が同テーマで存在するものを削除候補
- これは**破壊的だが「足し算ではない構造改善」を真に行う唯一の道**
- main の 2 案 (archive / 5 タブ) はどちらも引き算を避けている。引き算なしに「整理」と言うのは欺瞞

---

## 4. 比較表

| 案 | 入口分かりやすさ | 重複削減 | メンテ性 | URL/SEO | 既存資産活用 | リスク |
|---|---|---|---|---|---|---|
| 今回 main 提案 (5 タブ) | ◯ | × | × (.pages 集中管理) | △ (Subsystems 実装に物理移動) | ◯ | 中〜大 |
| 案 Z+ (前回 Z + α) | ◯ | △ | ◎ | ◎ | ◎ | 小 |
| 案 V (検索 UX のみ) | △ | × | ◎ | ◎ | ◎ | ゼロ |
| 案 U (UX テスト後) | (判定保留) | (保留) | ◎ | ◎ | ◎ | ゼロ (時間コストのみ) |
| 選択的廃棄案 | ◯ | ◎ | ◯ | △ (削除ページの redirect 要) | △ | 中 |

判定: **案 Z+ または案 U が最善**。今回 main 提案は前回 archive 案より「壊れにくい」だけで、解決する問題と作るリスクの収支は marginal。

---

## 5. 結論

### 採用すべきか: **No (大幅修正必須)**

5 タブ案を採用するなら最低限以下を **事前に** 解決すべき:
1. `docs/subsystems/` を作らずに 10 dir を Subsystems タブ配下に見せる技術的方法を mkdocs.yml + .pages で **実証 PoC** すること (口頭仕様だけでは不可)
2. `runbooks/` のソース根拠 (どの sonic-mgmt テストから引くか) と粒度 (ページ数の正確な見積もり) を確定すること
3. Tags プラグイン導入は別 PR で frontmatter 全件更新と同時にやる計画を出すこと (657 ファイルへの一括追加 script レビュー必須)
4. Diátaxis 5 拡張ではなく 4 タブ (Get Started を Tutorial 役、Topics を Explanation 役、Runbooks を How-to 役、Reference を Reference 役) に再整理し、Subsystems は Explanation の subdir に格下げ

### 撤回するなら次の進め方

1. **5 タブ提案を撤回する** ことを `meta/restructure-plan.md` の High セクションに明記
2. **案 Z+ を採用** (1 PR ずつ、3 PR で完結):
   - PR 1: `docs/index.md` を 4 段導線 (guides → categories → topics + area → reference) に書き換え。grid cards 4 枚 (5 ではなく 4)
   - PR 2: `docs/_meta/discrepancies.md` を `/known-issues/index.md` に昇格 + `awesome-pages` トップ `.pages` に追加
   - PR 3: `docs/guides/operator.md` 充実 (障害切り分けの導線追加。runbooks 新設の代わり)
3. **frontmatter `kind:` と Tags プラグイン導入は別フェーズ** (657 ファイル一括更新の覚悟ができてから)
4. **次回構造変更の議論は「カードソーティング結果」を出してから** (案 U)。AI 4 評価の机上案だけで進めるのを止める

---

## 6. メタ批判: 「main エージェントが 2 連続で構造提案を出していること」自体

- 前回 archive 案 (2026-05-11 朝) → 4 評価 → 撤回 → 5 タブ案 (同日) という流れは、main エージェント自身が **構造設計の根拠データ不足** を物語る
- 4 評価 (A/B/C/D) のうち D (本職) が連続で否定的判定を出しているのは、**今は構造変更フェーズではない** という強いシグナル
- 現リポの真のボトルネックは「構造」ではなく「**読者がまだ少ない (= フィードバックゼロ)**」点
- 構造を 2 連続で議論するより、Phase 6 で達成した「discrepancy-found 39 件」を **公開・告知して読者を呼び込み、フィードバックを取る** ことが優先
- 構造案の良し悪しはデータなしには決まらない。今は「動かさない勇気」が必要

---

## 付録: 実測データ

- `find docs/ -name '*.md' | wc -l` = **657**
- `grep -l '^tags:' docs/**/*.md | wc -l` = **0**
- `docs/_meta/discrepancies.md` = 1 ファイル (ページ群ではない)
- `docs/runbooks/` = 存在しない
- `docs/get-started/` = 存在しない
- `docs/subsystems/` = 存在しない
- 既存トップ dir 数 = **14** (`_meta` 含む) / nav 表示対象 = **13**
