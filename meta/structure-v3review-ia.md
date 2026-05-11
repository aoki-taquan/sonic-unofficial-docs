# 構成 v3 再評価レポート（情報設計 / IA 専門家視点・第 3 回）

- 再評価日: 2026-05-11
- 評価者: IA 観点レビューエージェント B
- 対象: main 提案 v3「4 タブ + Verification ハブ」（`/tmp/re-proposal-v3.md`）
- 前回（v2 5 タブ案）レポート: `meta/structure-rereview-ia.md`（A− / A）
- 前々回（13 タブ現状）レポート: `meta/structure-review-ia.md`（D）

---

## TL;DR

| 案 | グレード | 一行コメント |
|---|---|---|
| 現状（13 タブ） | **D** | 維持 |
| v2（5 タブ: Get Started / Topics / Runbooks / Reference / Subsystems） | **A−** | 前回判定維持。Get Started タブで Information Scent 確保、Runbooks 新設で運用導線 |
| **v3（4 タブ: Topics / Reference / Verification / Library）** | **A** | **採用可。** Verification 独立昇格は本サイト固有の独自価値を最大化。Get Started 廃止は index.md grid cards で代替可能。タブ数削減で Hick's Law 強化 |
| 私の推奨（v3 + Get Started 軽量化救済 + Verification 中身の厚み増し） | **A+ (条件付)** | v3 採用前提で 2 点の補強 |

**結論: v3 を採用すべき。** v2 比で 2 点改善している:

1. **Verification 独立タブ** = 本サイトの「コミュニティ HLD と実装の乖離を機械裏取り」という**唯一無二の独自価値**を nav の 1/4 に昇格させた。これは「Onboarding tutorial」より戦略的に正しい
2. **タブ数 5→4** = Hick's Law 上の最適点に近づいた（4 タブはモバイル横並びに無理がない上限）

v2 で評価した「Get Started 独立の必然性」は、`docs/index.md` の grid cards 強化で代替可能と判断を改める。Onboarding は Tab で背負わず Home で背負うのが本来正しい IA。

---

## 1. IA 原則チェック

### 1.1 MECE 性（Topics / Reference / Verification / Library が排他か）

| ペア | 排他性 | 評価 |
|---|---|---|
| Topics ⇔ Reference | 「読み物」vs「機械抽出仕様」で完全に異なる | ◎ |
| Topics ⇔ Verification | Topics は機能理解、Verification は HLD↔実装差分のメタ情報 | ◎ |
| Topics ⇔ Library | **重複あり**（22 章 Topics と 327 ページ HLD 派生の主題が同じ機能を扱う） | △ |
| Reference ⇔ Verification | Reference は仕様引き、Verification は「その仕様が実装と合っているか」のメタ | ◎ |
| Reference ⇔ Library | Reference は機械抽出（CLI/CONFIG_DB/YANG）、Library は手書き HLD 解説 | ◯ |
| Verification ⇔ Library | Verification はステータス横串、Library はページ単位の本文 | ◎ |

**MECE 評価: 5/6 ペアで排他**。残る 1 ペア（Topics ⇔ Library）は v3 でも未解決だが、`related_topics:` frontmatter での機械相互誘導で**読者から見ての境界判断**は緩和される。「学ぶなら Topics、深掘るなら Library」という性格分けが明示されれば許容範囲。

### 1.2 Hick's Law（4 タブ vs 5 タブ）

- Hick's Law: 選択肢が増えると意思決定時間は **log(n+1)** で増加
- n=5 → log2(6) ≈ 2.58
- n=4 → log2(5) ≈ 2.32
- 削減効果は約 **10%**。劇的ではないが、モバイル横並び表示の上限（多くのテーマで 4-5）に近づく安全マージンとして意味がある
- **判定: v3 の 4 タブは v2 の 5 タブよりわずかに優位**。MIT-HCI 系の経験則では「4 ± 1 がトップナビの最適」とされ、v3 はその中央値

### 1.3 命名一貫性

| ラベル | 評価 | 備考 |
|---|---|---|
| 📖 Topics | ◎ | 業界標準。Kubernetes / Cilium / Istio が同名採用 |
| 📚 Reference | ◎ | Diátaxis 公式語。揺らぎなし |
| ⚠️ Verification | ◯ | やや専門用語。読者は「検証 / 裏取り」と認識する必要あり。日本語表示「検証ステータス」推奨 |
| 🔧 Library | △ | **要検討**。"Library" は一般的すぎて中身が想像しづらい。v2 の「Subsystems」「HLD 詳細」のほうが Information Scent が強い |

**命名修正提案**: 
- Library → **「HLD ライブラリ」** または **「サブシステム」** に変更。"Library" 単独は SaaS 系ドキュメントで「コンポーネントギャラリー」「コード片集」を指すことが多く、SONiC 文脈では混乱を招く

絵文字は ◎ 統一感ある。ただし `navigation.tabs` の絵文字は OS フォントに依存（Linux/Windows で表示差）。本文用 `:material-*:` アイコンに置き換える方が安全（任意）。

### 1.4 兄弟粒度のバランス

| タブ | ページ数 | 比率 |
|---|---:|---:|
| Topics | 143 | 22% |
| Reference | 166 | 25% |
| Verification | 3 | 0.5% |
| Library | 327 | 51% |

- **最大/最小 = 327/3 ≈ 109 倍**。前回受け入れ基準「3 倍以内」を大きく逸脱
- しかし**この比率は本質的に正しい**:
  - Verification はステータスのメタビューであって本文ではない。3 ページで足りるのが正常
  - Library は HLD 派生 327 ページの集約場所であって肥大化は不可避
- **「兄弟粒度 3 倍以内」原則は同質コンテンツに適用するもので、性格の違うタブ間で適用するのは誤り**。判定基準を「タブ内のサブ兄弟」に下ろすべき
  - Topics タブ内: 22 章で粒度ほぼ均一 → OK
  - Library タブ内: area 9 系列で 10〜72 ページ = 7 倍 → △（system 過大は別 PR で）
  - Reference タブ内: cli/config-db/yang で構造化済 → OK
  - Verification タブ内: 3 ページで均一 → OK

**結論: タブ間粒度の不均衡は構造的に必然で問題なし**。タブ内粒度はおおむね健全。

---

## 2. 「Verification タブ」昇格の妥当性

### 2.1 独立タブの正当性

- 前回（v2）レビューでも「discrepancies.md を Reference 最上段に置く」を推奨したが、D 評価者が**「Reference に混ぜると信頼性希釈」**と指摘した点は IA 的に妥当
- Reference は「ここに書かれている = 仕様」というメンタルモデル。discrepancy（=仕様が信用できない箇所）を混ぜると Reference 全体の権威性が薄まる
- **独立タブ化は IA の「ラベルの純度を保つ」原則に整合**

### 2.2 「3 ページしかなくて薄すぎないか」問題

提案中身: `discrepancies.md` / `coverage.md` / `queue.md`

- ページ数では 3 だが、内容は**全 600 ページの横串メタ集約**。実質的な情報量は本文 100 ページ相当
- 類例: 
  - Linux kernel docs の `Reporting issues` セクション（数ページだが独立扱い）
  - Rust の `Stability` ページ群（少数ページで重大度高）
  - npm の `Security Advisories` タブ（独立タブ、ページ数少）
- **「薄すぎる」のはページ数ではなく「読者が訪れる頻度 × 訪れたときの満足度」で評価すべき**
  - SONiC 評価者にとって discrepancy 一覧は最も価値の高いコンテンツの一つ
  - 「コミュニティ版 SONiC を本番採用検討中」のペルソナはまず discrepancy を確認する
  - 訪問頻度は低いが満足度は極端に高い = **タブ昇格の正当事例**

### 2.3 nav の 1/4 を占める価値

- 4 タブ中 1 つが Verification = 「このサイトの存在理由の 1/4 はメタ品質保証である」というメッセージ
- これは**競合ドキュメントとの差別化**として戦略的に正しい
  - 公式 SONiC docs にはない
  - ベンダー版 NOS docs にもない
  - 「AI が機械裏取りした非公式ドキュメント」というポジショニングを nav が体現

**判定: Reference サブセクションでは弱い。独立タブで正解。**

### 2.4 補強提案（中身の厚み増し）

3 ページのまま放置すると「タブを開いたら少なくて拍子抜け」体験になり得る。以下を追加推奨:

- `verification/by-area.md`: area 別の coverage マトリックス（routing 95%, dash 60% など）
- `verification/methodology.md`: 「どう機械裏取りしているか」の方法論
- `verification/changelog.md`: 直近 30 日で昇格したページ一覧（"動いている感"を出す）

これで 6 ページ。タブとしての存在感が安定する。

---

## 3. Topics ⇔ Library 重複の対策

### 3.1 `related_topics:` frontmatter の効果

**部分的に解決する**:

- ◯ ページ単位の双方向リンクは確実に貼れる
- ◯ 機械追加可能（slug マッチ or LLM 判定でバッチ処理）
- △ 「同じ機能の Topics と Library を両方読む必要があるか」の疑問は残る
- × 「重複そのものを減らす」効果はない

### 3.2 IA 観点の「重複ページ群」の正解

選択肢:

| 戦略 | 効果 | コスト | 適用可否 |
|---|---|---|---|
| (a) **完全統合**（Topics に Library を吸収） | 重複消滅 | 327 ページ書き直し | 非現実的 |
| (b) **役割分離宣言**（Topics=入門/設定、Library=HLD 詳細） | 読者の判断負担減 | nav 説明 + frontmatter | **採用推奨** |
| (c) **タグ統合ビュー**（タグページで両者を横串） | 発見性向上 | Tags プラグイン + 全ページ tag 付与 | 別フェーズ |
| (d) **canonical 指定**（同主題の代表ページを 1 つ宣言） | SEO/検索改善 | frontmatter 1 行 | 低コスト・推奨 |
| (e) related_topics 機械相互誘導（v3 提案） | 双方向動線確保 | LLM バッチ 1 回 | **採用推奨** |

**正解は (b)+(d)+(e) の組み合わせ**。v3 は (e) を採用しており方向性は正しいが、(b) と (d) を追加することで真の解決に近づく:

- (b) Topics タブ index に「Topics は機能を学ぶための章立てです。HLD 仕様の完全な引用は Library を参照してください」と明記
- (d) 同主題ページ群で `canonical: topics/02-bgp/concept.md` のような frontmatter を入れ、検索エンジンと内部リンク優先度を制御

`related_topics:` 単独では不十分だが、3 点セットで「重複は許容しつつ読者を迷わせない IA」になる。

---

## 4. v2 (5 タブ) vs v3 (4 タブ) 採点

| 案 | グレード | 主たる強み | 主たる弱み |
|---|---|---|---|
| v2 (5 タブ: Get Started + Topics + Runbooks + Reference + Subsystems) | **A−** | Onboarding 動線 (Get Started) と運用動線 (Runbooks) の独立タブ化 | タブ数 5 でモバイル厳しめ、Verification の独自価値が埋没 |
| **v3 (4 タブ: Topics + Reference + Verification + Library)** | **A** | Verification 独立で独自価値最大化、4 タブで Hick's Law 改善、URL 不変、移行 3 PR | Get Started タブ消失で初訪問動線が index.md 依存、Library 命名が弱い、Runbooks の居場所が Topics 章末で発見性低下 |
| v3 + 補強（推奨） | **A+ (条件付)** | (a) Library → サブシステムへ改名、(b) Verification に方法論/changelog 追加、(c) Topics⇔Library に canonical 追加、(d) index.md grid cards で Onboarding 救済 | なし（条件達成時） |

### 4.1 v2 → v3 の損益

**得たもの**:
- Verification 独立昇格 = サイトの独自価値が nav で可視化 (+++)
- タブ数 4 化 = Hick's Law / モバイル / 視認性 (+)
- Tags プラグイン取り下げ = 段階導入リスク回避 (+)

**失ったもの**:
- Get Started タブ消失 = 初訪問者の Information Scent (--)
  - **緩和策**: docs/index.md の grid cards 強化で代替可能
- Runbooks タブ消失 = 運用者「症状から逆引き」動線 (-)
  - **緩和策**: Topics 章末 troubleshooting + Verification の discrepancy で部分代替
  - **残課題**: 章をまたいだ症状検索（"BGP UP しない"）は Topics 章内に隠れるため検索プラグイン依存度が上がる

### 4.2 v3 採用判定

- 得たもの (Verification 独立) >> 失ったもの (Get Started/Runbooks タブ消失) と評価
- 理由: Get Started/Runbooks は **コンテンツが充実してから独立タブ化すべき**だった。現状 guides 6 ファイル / runbooks 0 ファイルでタブを立てるのは「空のタブ」リスクが高い。v3 は「実体のあるコンテンツのみタブ化」で IA 原則に忠実
- v3 を採用、補強 (4.0 の (a)(b)(c)(d)) を別 PR で追加

---

## 5. 微修正提案（v3 採用前提）

1. **Library → 「サブシステム」（日本語）** または **"Subsystems"（英語）** に改名。"Library" は意味曖昧
2. **タブ日本語表示**を `.pages` の `title:` で統一
   - 📖 Topics → 「読み物」
   - 📚 Reference → 「リファレンス」
   - ⚠️ Verification → 「検証ステータス」
   - 🔧 Library → 「サブシステム」
3. **Verification タブを 6 ページに増強**（by-area / methodology / changelog 追加）
4. **Topics タブ index に役割宣言**を 1 段落追加（重複問題への読者ガイダンス）
5. **canonical frontmatter 導入**を `related_topics:` と同時に機械処理
6. **docs/index.md の grid cards** で Get Started 機能を補完（4 ペルソナカード: 初学者/評価者/運用者/開発者）
7. **Runbooks の発見性補強**: Topics 章末 troubleshooting に統合する方針は維持しつつ、`verification/` または `docs/index.md` から "症状逆引きインデックス" ページを 1 枚作成
8. **絵文字依存の検討**: タブの絵文字は OS フォント差で表示変動。`material/icons` への置換を将来検討

---

## 6. 受け入れ基準（更新）

- [x] トップタブが 5 個以下 → 4 タブで達成
- [x] サイトの独自価値が nav 上で可視化 → Verification 独立で達成
- [ ] 同一機能のエントリポイント数 (N 値) が 2 以下 → 未達、`related_topics:` + canonical で改善見込み
- [x] mkdocs build --strict 警告 0 → 維持
- [x] URL 不変 → `.pages` 編集のみで達成
- [ ] タブラベルが Information Scent を持つ → Library 改名で達成
- [ ] Onboarding 動線が 3 クリック以内 → index.md grid cards 強化で達成

---

## 7. 最終結論

**v3 採用。グレード A。補強 4 点追加で A+ 到達可能。**

- v3 の最大の発明は **Verification 独立タブ昇格**。これは v2 で見落とした「サイトの独自価値を nav で語る」IA 戦略
- Get Started/Runbooks タブ消失は損失だが、コンテンツ実体が薄い段階で先行タブ化していた v2 のほうが本来は不健全だった
- 移行 3 PR の構成は妥当。PR 1 (nav 4 タブ化) → PR 2 (index.md grid cards) → PR 3 (related_topics 機械追加) の順で漸進実装
- 推奨補強: (a) Library 改名、(b) Verification 3→6 ページ化、(c) canonical frontmatter、(d) 症状逆引きインデックス 1 枚

次のアクションは v3 提案の 3 PR をそのまま着手 + 上記補強を PR 4 として並走、で OK。
