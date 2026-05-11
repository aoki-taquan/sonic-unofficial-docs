# 構成 v4 評価レポート（情報設計 / IA 専門家視点・第 4 回 / 評価 B）

- 評価日: 2026-05-11
- 評価者: IA 観点レビューエージェント B（v3 評価で A 判定を出したのと同じ立場）
- 対象: `/tmp/re-proposal-v4.md`（3 タブ + Reference 内 5 カテゴリ）
- 前回レポート: `meta/structure-v3review-ia.md`（v3 を A 判定）

---

## TL;DR

| 案 | グレード | 一行コメント |
|---|---|---|
| 現状（13 タブ） | **D** | 維持 |
| v2（5 タブ） | **A−** | Get Started/Runbooks をコンテンツ薄状態でタブ化したのが弱点 |
| v3（4 タブ + Verification 独立） | **A** | Verification 独立昇格でサイト独自価値を nav に反映 |
| **v4（3 タブ + Reference 内 5 カテゴリ）** | **A（条件付 A+）** | **採用可。** v3 の Verification 独立は捨てたが、Runbooks 復活と Phase 1 工数 30 分が大きな実利。前回 D 評価者の「混ぜるな」指摘も Reference 内サブカテゴリ独立で形式的に整合 |

**結論: v4 採用可。ただし Verification の nav 可視性低下は Home（index.md）ハブで戦略的に補強する条件が付く。**

---

## 1. 3 タブの MECE 性

### 1.1 「動詞 2 種類」軸の妥当性

v4 の核となる思想は読者動詞を「読む」（Topics / サブシステム）と「引く」（Reference）の 2 軸に圧縮した点。これは IA の「Task-based grouping」原則に沿う健全な選択。

| ペア | 排他性 | 評価 |
|---|---|---|
| Topics ⇔ Reference | 「読み物」vs「機械抽出 + 逆引き + メタ」 | ◎ |
| Topics ⇔ サブシステム | **依然として重複あり**（22 章 vs 327 ページ HLD 派生で主題重複） | △ |
| Reference ⇔ サブシステム | Reference は「引く」、サブシステムは「読む（深掘り）」 | ◯ |

**MECE 評価: 2/3 ペアで排他**。v3 で残った Topics⇔Library の重複問題は v4 でも解消されていない（命名「サブシステム」化で読者の期待値整理は進むが、コンテンツの重複は残る）。`related_topics:` + canonical frontmatter による (b)+(d)+(e) 戦略は v3 評価と同じく必要。

### 1.2 Hick's Law

- n=3 → log2(4) = 2.00
- n=4 → log2(5) ≈ 2.32
- 削減効果は v3 比で約 **14%**。3 タブはモバイル横並びの完全安全圏
- 3 タブは「Topic / Reference の 2 軸 + サブシステム」と覚えやすく、Recognition が強い

**判定: 3 タブは IA 上問題なし。むしろ理想に近い。**

### 1.3 命名の Information Scent

| ラベル | 評価 | 備考 |
|---|---|---|
| 📖 Topics | ◎ | 業界標準 |
| 📚 Reference | ◎ | Diátaxis 標準語 |
| 🔧 サブシステム | ◯ | 日本語化で v3「Library」より具体的だが、初訪問者には依然抽象的。「コンポーネント別 HLD」のサブタイトル併記推奨 |

「サブシステム」採用は v3 評価で出した推奨に整合。Information Scent が前回より明確に強化された。

---

## 2. Reference 内 5 カテゴリの IA 妥当性

### 2.1 5 カテゴリの性格分析

| カテゴリ | 引く対象 | 機械生成度 | 信頼性 | 訪問頻度 |
|---|---|---|---|---|
| CLI | コマンド仕様 | 高（ソース抽出） | 高 | 高 |
| CONFIG_DB | スキーマ | 高 | 高 | 中 |
| YANG | モジュール定義 | 高 | 高 | 中 |
| **Runbooks** | **症状** | **低（手書き）** | **中** | **高（運用者）** |
| **Verification** | **メタ状態** | **中（自動集約）** | **メタ情報** | **低（評価者）** |

### 2.2 「引く」軸での同質性検証

**Reference の伝統的定義は「仕様の機械抽出」**（Diátaxis では Reference = information-oriented + neutral）。これに照らすと:

- CLI / CONFIG_DB / YANG = ◎ 完全一致
- Runbooks = △ 「症状 → 手順」の逆引きは Diátaxis では How-to に分類されるべき。Reference に混ぜるのは Diátaxis 厳密派には逸脱
- Verification = △ 「仕様」ではなく「仕様の信頼性メタ」。Reference の性格と異質

**IA 判定**: 5 カテゴリは「読者動詞が引く」で括る括弧としては成立するが、「Reference = 仕様」のメンタルモデルからは Runbooks と Verification がはみ出る。これは v4 提案者も自覚しているはずで、`reference/.pages` でラベル明示することで読者の期待値を整える設計と理解できる。

**条件付き許容**: Reference index に「ここには①仕様 ②運用逆引き ③検証状態 の 3 性格が並ぶ」と明記すれば、読者の混乱は十分回避可能。

### 2.3 5 カテゴリ並列の兄弟粒度

| カテゴリ | ページ数（提案後） | 比率 |
|---|---:|---:|
| CLI | 25 | 13% |
| CONFIG_DB | 66 | 35% |
| YANG | 28 | 15% |
| Runbooks | 10-15 | 6-8% |
| Verification | 3-6 | 2-3% |

最大/最小 ≈ 22 倍。同質コンテンツでは逸脱だが、性格が異なるサブカテゴリ間なので v3 評価と同じく「タブ内サブ粒度の閾値は性格ごと」原則で許容。CLI/CONFIG_DB/YANG の 3 つは粒度が近く（13-35%）、Runbooks/Verification は別性格のメタとして並ぶ、と読める。

---

## 3. Verification を Reference サブカテゴリに置く是非（D 指摘との整合）

### 3.1 前回 D 評価者の指摘の再確認

D は v3 議論で「discrepancy を Reference に混ぜると信頼性希釈」と指摘した。これは v3 で Verification を**独立タブに昇格**する根拠となった。

v4 は Verification を Reference 配下に戻したが、**`reference/verification/` という独立サブディレクトリ**として配置し、CLI/YANG の個別ページには混ぜない設計。

### 3.2 「混ぜる」の二段階解釈

D 指摘の「混ぜる」には 2 つのレベルがある:

| レベル | v4 での状態 | 判定 |
|---|---|---|
| (i) CLI/YANG ページ本文に discrepancy 警告を混入 | **混ぜない**（提案文「CLI/YANG ページには混ぜない、信頼性希釈なし」） | ◎ 整合 |
| (ii) Reference タブ全体の中に Verification を含める | **混ぜる**（サブカテゴリとして） | △ 部分逸脱 |

v4 提案者は (i) を主に意識しており、(ii) は許容範囲と判断している。IA 的には:

- (i) こそが「信頼性希釈」の本丸。ページ本文の権威性は守られる
- (ii) は **Reference index のラベル設計次第で完全回避可能**。「📚 Reference: 仕様・逆引き・検証状態」とサブタイトルを示せば、読者は混合性を予期して訪問する
- D が真に憂慮していたのは (i) の方であり、(ii) は IA 上は問題化しない（Reference 内の独立カテゴリで純度は保てる）

**判定: D 指摘との整合は形式的には保たれる。** ただし v3 で得た「サイト独自価値を nav 1/4 で語る」戦略性は失われる。

### 3.3 nav 可視性低下のリスク

v3: Verification はトップタブ → 初訪問者が必ず目にする
v4: Verification は Reference 内サブカテゴリ → トップタブからは 2 クリック必要

これは IA 上の実質的損失。サイトの独自価値（コミュニティ HLD と実装の機械裏取り）は SONiC 評価者にとって最大の訪問動機だが、v4 ではそれが nav で語られない。

**緩和策（必須条件）**:

- docs/index.md に **「検証ステータス」グリッドカード**を 1 枚配置（discrepancy 件数、code-verified 比率を動的表示）
- `reference/verification/index.md` を hub 化（v4 提案にも明記あり）
- Home → Verification への直接動線を 1 クリックで提供
- これがあれば「nav 可視性低下」は Home の Information Scent で代替可能

**判定: 緩和策込みで Verification の Reference 配下化は許容。Home ハブが必須前提。**

---

## 4. v3 (4 タブ) vs v4 (3 タブ) 採点

### 4.1 軸ごとの優劣

| 軸 | v3 | v4 | 優劣 |
|---|---|---|---|
| タブ数 (Hick's Law) | 4 | **3** | v4 ◎ |
| Verification の nav 可視性 | **独立タブ** | サブカテゴリ | v3 ◎ |
| Runbooks の居場所 | 章末 troubleshooting（発見性低） | **独立サブカテゴリ** | v4 ◎ |
| 命名 Information Scent | Library（弱） | **サブシステム**（中） | v4 ◯ |
| Phase 1 工数 | 3 PR | **1 PR / 30 分** | v4 ◎ |
| 後戻りコスト | 中 | **5 分**（.pages 1 ファイル + 2 サブディレクトリ） | v4 ◎ |
| URL 不変 | ◎ | ◎ | 互角 |
| サイト独自価値の nav 訴求 | **強** | 弱（Home 依存） | v3 ◎ |
| D 評価者「混ぜるな」整合 | 完全（独立タブ） | 形式的（サブ独立） | v3 やや優 |
| MECE | 4/6 排他 | 2/3 排他 | 互角（質的に同じ Topics⇔深掘り問題） |
| 運用者ペルソナ (A 指摘) | △（Runbooks 廃止） | ◎ | v4 ◎ |
| 「24h で 3 案 = 暴走」(D 指摘) | 物理移動あり | **物理移動ゼロ** | v4 ◎ |

### 4.2 総合判定

| 案 | グレード | コメント |
|---|---|---|
| v3 | **A** | Verification 独立がサイト独自価値を nav で語る戦略的勝ち。ただし Runbooks/Onboarding を捨てた |
| **v4** | **A（Home ハブ補強で A+）** | 工数最小・後戻り容易・Runbooks 復活で運用者導線回復・D 指摘の本質（ページ本文混入回避）を維持。代償は Verification の nav 訴求低下 |

**最終判定**: v4 と v3 はトレードオフ関係で**ほぼ等価の A**。決め手は以下の運用判断:

1. **「Verification を nav で語ること」をどれだけ重視するか** → 重視なら v3、Home で代替可なら v4
2. **「Runbooks 不在の運用者導線劣化」をどれだけ重視するか** → 重視なら v4
3. **「Phase 1 工数最小・後戻り容易性」をどれだけ重視するか** → v4 が圧倒

D 評価者が「24h で 3 構造提案 = 暴走」と指摘した点を踏まえると、**v4 の「物理移動ゼロ + 5 分で巻き戻し可能」は実装段階の最大の安全網**であり、ここを評価するなら v4 を採用すべき。

---

## 5. 推奨修正（v4 採用前提・必須補強 4 件）

1. **Home ハブで Verification の Information Scent を担保**（必須）
   - `docs/index.md` に grid card「⚠️ 検証ステータス: discrepancy XX 件 / code-verified XX%」を配置
   - card → `reference/verification/index.md` 直リンク（1 クリック動線）
   - これがないと v3→v4 で失った独自価値訴求が回復しない

2. **Reference index に性格混在の明示**（必須）
   - `reference/index.md` 冒頭に「① 仕様引き (CLI/CONFIG_DB/YANG) ② 運用逆引き (Runbooks) ③ 検証状態 (Verification) の 3 性格が並びます」と明記
   - 読者の期待値を整え、Diátaxis 厳密派の F 指摘との形式的整合を取る

3. **「サブシステム」サブタイトル併記**（推奨）
   - `.pages` で 「🔧 サブシステム（コンポーネント別 HLD 詳細）」と表示
   - Information Scent をさらに強化

4. **canonical + related_topics frontmatter の機械追加**（v3 評価から継続推奨）
   - Topics ⇔ サブシステムの重複問題は v4 でも未解決。同主題ページ群で canonical を 1 つ宣言し、`related_topics:` で双方向誘導

---

## 6. 受け入れ基準（v4 用に更新）

- [x] トップタブが 5 個以下 → 3 タブで達成
- [ ] サイトの独自価値が nav 上で可視化 → **Home grid card 補強が必須**
- [ ] 同一機能のエントリポイント数 (N 値) が 2 以下 → 未達、canonical + related_topics で改善見込み
- [x] mkdocs build --strict 警告 0 → 維持見込み
- [x] URL 不変 → `.pages` 編集 + 2 サブディレクトリ追加のみで達成
- [x] タブラベルが Information Scent を持つ → 「サブシステム」改名で達成
- [x] Onboarding 動線が 3 クリック以内 → Home grid cards 強化で達成
- [x] 後戻り 5 分以内 → 達成（D 指摘「暴走」への直接的回答）
- [x] 運用者ペルソナの逆引き動線 → Runbooks 復活で達成（A 指摘への直接的回答）

---

## 7. 最終結論

**v4 採用可。グレード A。Home ハブ補強で A+。**

- v4 は v3 の Verification 独立を捨てる代わりに、**Runbooks 復活**・**Phase 1 工数 30 分**・**後戻り 5 分**・**「24h 暴走」批判への完全な回答**を獲得した実利重視の案
- D 評価者の「Reference に混ぜるな」指摘は、ページ本文への混入を回避すれば形式的に整合する。サブカテゴリ独立は許容範囲
- 最大の代償は Verification の nav 訴求低下。これは **Home grid card で必ず補強**する条件付き採用
- 移行は単一 PR で完結、後戻り容易。「構造論より本文品質に集中せよ」という D の本質的指摘とも整合
- 推奨次アクション: Phase 1 単一 PR を即実行 → Phase 2-3 を並走 → 本文品質改善（D 指摘）に主リソースを振る
