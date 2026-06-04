---
title: 品質監査ガイド（quality-audit-N シリーズ運用ルール）
area: meta
verification: meta
last_verified: 2026-05-12
sources: []
---

# 品質監査ガイド（quality-audit-N シリーズ運用ルール）

`meta/quality-audit-1.md` 〜 `meta/quality-audit-NN.md` の **6 軸 5 点満点サンプリング監査** を継続実施するための運用ルールをここに集約する。新規 round を起票する監査ロールは本ドキュメントを参照し、各軸の評価基準のブレを最小化すること。

## 0. 評価軸（6 軸 5 点満点）

| # | 軸 | 通常ページの基準（要旨） |
|---|----|--------------------------|
| 1 | 構成 | 見出し階層 / セクション分割 / 導入 → 詳細 → 引用元の流れ |
| 2 | 裏取り | code-verified 度合い / evidence コメントの密度 / SHA 固定 |
| 3 | 引用 | frontmatter `sources[]` / 本文脚注 / 「引用元」セクションの整備 |
| 4 | 関連性 | `related.config_db` / `related.cli` / `related.yang` の網羅性と妥当性 |
| 5 | 可読性 | 用語統一 / glossary 整合 / 図表の有効性 / 1 ページの分量バランス |
| 6 | 完結性 | 機能の網羅性 / ops-hint / troubleshooting / 読み手が次に取れる行動 |

## 1. ページ種別による軸の読み替え

通常ページに対して上記基準をそのまま適用すると、特定ページ種別が構造的に低評価へ張り付く問題があり、これまでの round で実害が観測されている。本プロジェクトでは以下の読み替えを **formal なルール** として採用する。

### 1.1 `page_kind: chapter-index`（章扉）

22 章の扉ページ (`docs/topics/NN-slug/index.md`)。配下ページへのリンク集が本体。

- **N/A 化する軸**: 軸 2 (裏取り) / 軸 6 (完結性)
- **維持する軸**: 軸 1 / 3 / 4 / 5
- **理由**: 章扉は個別主張を持たないため evidence は不要、また「機能としての完結」も求めない
- 集計時は N/A 軸を除いた平均で 5 点換算する

詳細は `meta/templates/SCHEMA.md` の `page_kind` セクションを参照。

### 1.2 `verification: discrepancy-found` ページ

HLD と実装に差分があるページ。

- **読み替える軸**: 軸 6 (完結性) → **「乖離説明の構造的整理が出来ているか」**
- 他の軸 (1〜5) は通常ページと同じ基準
- 評価サブ項目は `meta/templates/SCHEMA.md` の「`discrepancy-found` ページの軸 6 評価基準」セクションを参照（monitor タグ妥当性 / 「実装との乖離」セクションの構造化 / 裏取り evidence / 読み手への next-action の 4 サブ項目）
- **理由**: 実装が未着手 / 進化済み / 廃止済みのため「機能としての完結」を本文で書きようがなく、通常基準では構造的に 4 点天井になる。代わりに「読み手に乖離を有益な形で渡せているか」で評価する

### 1.3 `verification: stub` / `meta` ページ

監査対象外（サンプリングで引いた場合は再抽選または N/A 評価）。

## 2. `discrepancy-found` 監査時のチェックリスト

新規 round で `discrepancy-found` ページをサンプリングに引いた場合、軸 6 評価は以下のチェックリストで行う:

- [ ] frontmatter `monitor:` が 4 値 (`not_implemented` / `evolved_beyond_hld` / `partially_implemented` / `deprecated`) のいずれかで、本文の乖離パターンと整合している
- [ ] 「実装との乖離」「現行実装との乖離」「HLD と実装の乖離」見出しのセクションが存在し、HLD 側の主張 / 現行 master の状態 / 差分のインパクトの 3 点が読み分けられる
- [ ] 「実装が存在しない」「別名で実装されている」等の判定根拠が evidence コメント（`source:` / `excerpt:` / `reasoning:`）で埋め込まれている
- [ ] 読み手が現行 master でこの HLD をどう取り扱うべきかの next-action が明示されている

4 項目すべて満たすと軸 6 = 5 点。1 つ欠けると 4 点、2 つ欠けると 3 点、それ以下も同様に下げる。

## 3. round 集計時の表記

quality-audit-N.md の冒頭サマリには、本ガイドの読み替えを適用したことを明記する。例:

> `verification: discrepancy-found` ページの軸 6 は `meta/quality-audit-guide.md` および `meta/templates/SCHEMA.md` の規定に従い「乖離説明の整理度」で評価した。

過去 round（round 17 以前）は通常基準で評価されており、`discrepancy-found` ページが軸 6 = 4 点で天井に当たっていた。round 18 以降は本ガイドの読み替えを適用する。

## 3.2. score 0 phantom entry の取り扱い（formal）

母集団平均を計算する側 (`meta/scripts/gen_index_banner.py` / `meta/scripts/gen_snapshot.py`) は、抽出した score が **ぴったり 0.00** だった場合は **phantom entry とみなして除外** する。理由:

- 本プロジェクトの実 audit は round 1 以降すべて 9.0+/10 もしくは 4.5+/5 帯域に収まっており、母集団平均が 0.00 になることは構造的に起こらない
- 0.00 のマッチが発生する主因は次の 3 種で、いずれも分布平均として無効:
    1. 未集計セル（評価表のテンプレが残ったままで実値が入っていない）が 0 として展開された結果
    2. 軸サブ集計（重み 0、サブ軸 0 個、N/A 件数 0 等の説明的数値）への誤マッチ
    3. round 番号間違いや draft 状態のファイルが集計対象に混入したケース
- これらが母集団に注入されると **score distribution skew by zero injection** が発生し、平均が（例: 4.97 ± 0.005 帯域から）1〜2 点台へ急落するなど真値から大きく乖離する

aggregation 側のガードに加え、audit ファイル執筆側でも以下を守ること:

- `総平均` 行に **未確定値や 0.00 を書かない**。集計中の round は `総平均: —` または行自体を省略する
- 「軸別 0 件」「重み 0」等の説明的数値は本文中で `0 件` `重み 0` のように単位付きで書き、`平均` `総平均` 等の集計キーワードに 0.00 を隣接させない
- weighted random round の重み係数 0 を扱う場合は `weight: 0` のような明示形式に揃え、`/5` 単位の score 値と混在しないようにする

## 3.1. サンプリング戦略（奇偶交互運用、round 28 で確立）

round 28 以降、サンプリング方式を round 番号のパリティで機械的に決定する:

| パリティ | サンプリング | 目的 |
|---------|------------|------|
| **奇数 round** | **random 12**（`find docs -name '*.md' \| shuf -n 12`） | 母集団 unbiased estimator、構造的偏り検知 |
| **偶数 round** | **stratified 12**（cv 6 / rv 2 / df 2 / ci 1 / meta 1） | サブセット軸別平均の安定監視 |

stratified の比率は `quality-audit-27.md` §1 の抽出シェルを参照。stratified round では母集団重み補正後の期待値を生サンプル平均と並記し、続く random round の生サンプル平均との乖離を測ることで stratified scheme の mature 度を継続検証する（乖離 0.05 以下で mature）。

round 28 で round 27 (stratified, 4.941) と round 28 (random, 4.94) の乖離が 0.001 と確認され、stratified scheme は mature 判定済み。

## 4. サブ軸定義（軸 5 / 軸 6、round 35 から正式運用）

audit round 32 の改善提言を受け、軸 5 (可読性) と軸 6 (完結性) を 3 つのサブ軸に分割して評価する運用を round 33・round 34 で 2 round 試行し、stratified / random 両サブシリーズで母集団真値 4.97 → 4.98 帯域押し上げに寄与することを確認した。これを受け **round 35 以降は正式運用** とする。

### 4.0 運用ルール（formal）

以下を本プロジェクトの formal なルールとして固定する:

1. **サブ軸 5 点満点**: 各サブ軸 (5a / 5b / 5c / 6a / 6b / 6c) は通常軸と同様の 5 点満点で評価する（0.5 段刻み可、round 33 から導入の細評価を継続）
2. **軸スコア = サブ軸平均**: 軸 5 / 軸 6 のスコアは、適用可能なサブ軸の **単純平均** とする（小数第 2 位四捨五入）。サブ軸が全部 5 点なら軸スコアも 5.00、(5, 4, 5) なら 4.67
3. **N/A はサブ軸単位で適用可**: 単一サブ軸が当該ページに構造的に該当しない場合（例: 設定が存在しない overlay 概念ページの 6a、図表が不要な極短ページの 5c）は当該サブ軸を N/A とし、残りのサブ軸の平均で軸スコアを算出する。軸単位で全サブ軸が N/A になる場合のみ軸自体を N/A とする
4. **round 32 以前との互換**: round 32 以前の audit はサブ軸を持たない軸単位評価が引き続き有効。サブ軸方式は **前向き運用** とし、既存 audit ファイルは遡及修正しない
5. **新規 audit ファイル**: round 35 以降の `meta/quality-audit-N.md` は `meta/templates/quality-audit-page.md` を雛形とし、サブ軸内訳を必ず併記する

### 4.1 軸 5 (可読性) サブ軸

| サブ軸 | 名称 | 評価対象 |
|--------|------|---------|
| **5a** | 章立て / 流れ | 見出し階層の妥当性、導入 → 詳細 → 引用元の論理的順序、セクション分割の粒度、読み進めるリズム |
| **5b** | 日本語の自然さ | 用語統一（glossary 整合）、助詞・語尾のブレ、機械翻訳調の不自然さ、専門用語の和訳一貫性 |
| **5c** | mermaid / 表の有無と質 | 図表が必要な箇所への配置、mermaid のラベル明確さ、表ヘッダの妥当性、PNG 等スコープ外形式を使っていないこと |

### 4.2 軸 6 (完結性) サブ軸

| サブ軸 | 名称 | 評価対象 |
|--------|------|---------|
| **6a** | 設定例の有無 | CLI / config_db JSON / YANG payload など実際の設定スニペットが提示されているか、最小例と典型例の網羅 |
| **6b** | 制限事項の有無 | 既知の制限・スケール上限・未サポート機能・前提条件（プラットフォーム依存等）の明示 |
| **6c** | トラブルシュート / 確認コマンドの有無 | `show` 系コマンド、ログ確認ポイント、debug の足がかり、典型エラーと対処の整理 |

### 4.3 集計表記

サブ軸を適用した round (round 33 以降) では、各ページの評価表に軸スコアと並んで `(5a/5b/5c)` `(6a/6b/6c)` の内訳を必ず併記する。例:

> 軸 5: 4.67 (5a=5, 5b=4, 5c=5) / 軸 6: 4.00 (6a=5, 6b=3, 6c=4)

N/A を含む場合の例:

> 軸 5: 4.50 (5a=5, 5b=4, 5c=N/A) / 軸 6: 4.50 (6a=5, 6b=4, 6c=N/A)

`page_kind: chapter-index` の軸 6 は引き続き軸単位で N/A とし、サブ軸も評価しない。`verification: discrepancy-found` ページの軸 6 は §1.2 / §2 の「乖離説明の整理度」基準を優先し、サブ軸 6a-6c は副次情報として併記のみ可（軸スコアの算出には用いない）。

### 4.4 テンプレ

新規 round の audit ファイルは `meta/templates/quality-audit-page.md` を雛形として使用する。サブ軸 5a-c / 6a-c の評価表セクションが定義済み。

### 4.6 snapshot 集計ページの評価仕様（round 46 で確定、formal）

`docs/_meta/snapshot.md` をはじめとする `meta/scripts/gen_snapshot.py` 系の **自動生成集計ページ** は通常ページの評価軸をそのまま当てると構造的に低評価へ張り付くため、本節を formal ルールとして固定する。round 46 以降の audit ですべての snapshot 集計ページ抽出に本節を適用する。

**対象ページ**:

- `docs/_meta/snapshot.md`（メイン集計、`gen_snapshot.py` 生成）
- 同 generator から派生する `coverage.md` / `discrepancies.md` / `sitemap.md` 等の auto-generated 集計ページ（frontmatter `verification: meta` かつ生成元が `meta/scripts/gen_snapshot.py` を含むもの）

**評価方針**:

1. **ページ種別**: `verification: meta` の **auto-generated 集計ページ** として扱う。`page_kind: chapter-index` とは別カテゴリで、`page_kind` 未指定でも本節の評価対象とする
2. **内容鮮度のみ評価**（6 軸のうち 5/6 サブセット使用 = 軸 2/3/6 は N/A、軸 1/4/5 のみ評価）の **簡易評価モード**:
    - **軸 1 (構成)**: generator 出力構造の妥当性（H2 セクション分割が `verification 分布` / `area 別件数` / `discrepancy 偏在` 等の集計単位ごとに区切られているか）
    - **軸 2 (裏取り)**: **N/A**（auto-generated のため引用元は generator スクリプト自体、本文では sources 不要）
    - **軸 3 (引用)**: **N/A**（同上、引用機構は generator 内に閉じる）
    - **軸 4 (関連性)**: xref 完備度（`related.*` / `_no_related` 明示、または本文内で `coverage.md` / `sitemap.md` 等の派生集計ページへのリンクが揃っているか）
    - **軸 5 (可読性)**: 表組み・mermaid figure の評価（サブ軸 5a/5b/5c 適用可）
    - **軸 6 (完結性)**: **N/A**（運用ページではないため設定例・制限・トラブルシュートを書きようがない）
3. **内容鮮度の追加スコア（軸 1 内で適用）**:
    - `last_verified` が **当日（audit 実施日と同じ）** なら 軸 1 = 5.00（満点）
    - それ以外は **30 日経過ごとに -0.1 減点**（小数第 2 位で四捨五入、`(audit_date - last_verified).days // 30 * 0.1` を 5.00 から減算、下限 1.00）
    - 計算例: `last_verified: 2026-04-12` で audit 実施日 `2026-05-12` の場合、30 日経過で軸 1 = 4.90
4. **各 metric の妥当性は本 lint で検証する前提**: snapshot 内に記載される verification 分布件数 / area 別件数等の数値そのものの正確性は audit の評価対象外。`python3 meta/scripts/gen_snapshot.py --check` が pass している（CI green）ことを前提とし、audit では数値の正確性ではなく **構造・xref・鮮度** のみ評価する
5. **集計表記**: 評価表には軸 2/3/6 = N/A と明記し、軸 1 の鮮度減点があれば備考に書く。例:

```
[snapshot]  軸 1: 5.00 / 軸 2: N/A / 軸 3: N/A / 軸 4: 5.00 / 軸 5: 5.00 (5a=5, 5b=N/A, 5c=5) / 軸 6: N/A  平均: 5.00
[snapshot (last_verified 30 日経過)]  軸 1: 4.90 / 軸 2-3: N/A / 軸 4: 5.00 / 軸 5: 5.00 / 軸 6: N/A  平均: 4.97 ※ 鮮度 -0.1
```

**理由**: snapshot 集計ページは内容の正確性が generator 出力に依存するため、audit でテキスト評価しても発見できる問題は本 lint で先に検出可能。audit ではむしろ **「鮮度（最新の状態を反映しているか）」「読み手が他の集計ページへ辿れるか（xref）」「構造（generator が壊れた出力をしていないか）」** の 3 点に絞ることで、評価の再現性と効率性を両立する。

### 4.5 snapshot 参照運用（round 46 以降の formal）

audit round の前後で `docs/_meta/snapshot.md` を必ず参照すること。リポジトリ全体の verification 分布・area 別件数・discrepancy 件数を 1 ページに集約した自動生成サマリで、サンプリング設計と母集団傾向の把握に不可欠。

- **監査前**: `docs/_meta/snapshot.md` を確認し、全体傾向（verification 分布 / area 別件数 / discrepancy 偏在）を把握してからサンプリングに入る。stratified round の比率調整や random round の代表性検証は本ページの最新値を元に行う
- **監査後**: `python3 meta/scripts/gen_snapshot.py` を実行して snapshot を再生成し、当該 round の merge による分布変動を最新化する。CI 連携は `--check` で drift 検出可
- 監査ファイル冒頭サマリには、参照した snapshot の `last_verified` 日付を明記することを推奨する（再現性のため）

## 5. `discrepancy-found` subtype 別評価基準

`verification: discrepancy-found` ページは `monitor:` の subtype によって軸 6 (完結性) の読み替え方が異なる。§1.2 / §2 の「乖離説明の整理度」基準を主軸としつつ、サブ軸 6a-6c の判定は以下の subtype 別ルールで行う。サブ軸スコアを軸 6 の集計に反映する round では本節を優先する。

### 5.1 `monitor: not_implemented`（finalized: §5.4 確定ルール）

HLD が提案段階で master に対応コードが無いため、通常の「設定例 / 制限 / 確認コマンド」は本来存在しない。本サブシリーズの最終運用ルールは §5.4 で確定済み。サブ軸 6a / 6b / 6c はすべて N/A とし、軸 6 = 5.00（満点）として集計する。詳細は §5.4 を参照。

### 5.2 `monitor: partially_implemented`

HLD のうち一部のみ取り込まれ、残りが欠落している状態。サブ軸 6a-6c は**通常評価**を行うが、軸 6b に追加要件を課す。

| サブ軸 | 評価 |
|--------|------|
| **6a** 設定例 | 実装済み部分の CLI / config_db / YANG payload が示されているか（通常評価） |
| **6b** 制限事項 | 通常評価に加え、**「実装済 / 未実装 の境界明示」が追加要件**。どこまでが動き、どこから先が HLD 提案のみで動かないかをユーザが識別できる記述が必須。境界が曖昧なら 6b は最大 3 点止まり |
| **6c** 確認コマンド | 実装済み部分の `show` 系 / debug 手順が示されているか（通常評価） |

### 5.3 `monitor: evolved_beyond_hld`

機能は存在するが HLD と名前・構造・経路が異なる状態。サブ軸 6a-6c は**通常評価**を行うが、軸 6b に追加要件を課す。

| サブ軸 | 評価 |
|--------|------|
| **6a** 設定例 | 現在の実装名（テーブル名 / 引数 / コマンド）に基づく設定例が示されているか（通常評価） |
| **6b** 制限事項 | 通常評価に加え、**「HLD と実装の差分」を含めることが要件**。HLD 時点の名称・構造と現行実装の対応関係（旧 → 新の rename 表など）を含む記述が必須。差分記述が無いなら 6b は最大 3 点止まり |
| **6c** 確認コマンド | 現行実装に対応した `show` 系 / debug 手順が示されているか（通常評価） |

### 5.4 `monitor: not_implemented` 確定ルール（finalized）

`monitor: not_implemented` ページの軸 6 評価は本節を **formal な確定ルール** として運用する。本ルールは §5.1 の暫定運用（6b / 6c 平均）を置き換える最終仕様であり、round 46 以降のすべての audit で本節を優先適用する。

**確定ルール本体**:

1. **軸 6 全体を N/A 扱いとし、満点 5.00 を付与する**。サブ軸 6a / 6b / 6c はすべて N/A とし、軸 6 のスコア算出にサブ軸を用いない（サブ軸平均ではなく一律 5.00 を付与する）
2. ただし以下 2 点が本文に含まれていることを **前提条件** とする:
    - **未実装である旨の明示**: HLD が提案段階に留まる / master にコードが無い / 採用見送り等、読み手に「現状では動作しない」と伝わる記述
    - **代替手段の有無の明示**: 後発の代替機能・関連 HLD・回避策の有無（「現時点で代替実装は無い」と明示する場合も可）
3. **前提条件を満たさない場合の減点**: 上記 2 点のいずれかでも欠けている場合、軸 6 は **5.00 → 4.5 へ 0.5 減点** する（両方欠けても 4.5 で止め、それ以下には下げない。N/A 扱いの構造上、通常評価への切替は行わない）
4. **audit 時の記載方法**: 評価表には軸 6 = 5.00 と記載し、サブ軸内訳には `6a=N/A, 6b=N/A, 6c=N/A` と明記する。減点ケース（4.5）の場合も同様にサブ軸は N/A 表記とし、減点理由を備考に書く

集計表記例:

```
[not_implemented, 前提条件 OK]  軸 6: 5.00 (6a=N/A, 6b=N/A, 6c=N/A)
[not_implemented, 代替言及なし] 軸 6: 4.50 (6a=N/A, 6b=N/A, 6c=N/A) ※ 代替手段の有無が本文に無く -0.5
```

### 5.4a `monitor: deprecated`

HLD 方針自体が廃止され、後発別機能に置き換えられた状態。サブ軸 6a-6c は**全て N/A**とし、代わりに以下のみを評価する。

| 項目 | 評価 |
|------|------|
| 代替機能リンク | 「本 HLD は X に置き換えられている」「migration-to-Y で置換」等の**代替機能への内部リンク（または明示的なページ参照）が有るかのみ**を評価。リンク有りなら軸 6 = 5、リンク無し（廃止のみ言及）なら軸 6 = 2、廃止である旨すら明示されていないなら軸 6 = 1 |

軸 6 にはサブ軸内訳を併記せず、`(deprecated: link-ok)` / `(deprecated: no-link)` 等のラベルで記載する。

### 5.5 集計表記例

```
[not_implemented]      軸 6: 5.00 (6a=N/A, 6b=N/A, 6c=N/A)  ※ §5.4 確定ルール
[partially_implemented] 軸 6: 4.00 (6a=5, 6b=3, 6c=4)  ※ 境界明示が弱く 6b 減点
[evolved_beyond_hld]    軸 6: 3.67 (6a=4, 6b=3, 6c=4)  ※ 旧 → 新差分の記述不足で 6b 減点
[deprecated]            軸 6: 5.00 (deprecated: link-ok)
```

## 6. weighted random sampling 規約（round 51 から試行）

### 6.0 背景

奇偶交互運用（§3.1）で random サブシリーズは母集団 unbiased estimator として運用してきたが、`find docs -name '*.md' | shuf -n 12` 方式は **全件等確率抽出** のため、件数の多い `code-verified` (~586 件 / 66%) が常に 7-9 件を占め、件数の少ない `discrepancy-found` (~75-82 件 / ~9%) や `runbook-verified` (~27 件 / 3%) は **0 件抽出が頻発**する。round 47 では df 0 件抽出となり、同日付の `quality-audit-47-discrepancy-mini.md` で別途指名 audit を起こす二重運用が発生した。

stratified（§3.1 偶数 round）は逆に固定比 (cv 6 / rv 2 / df 2 / ci 1 / meta 1) で再現性が高い反面、**母集団真値の unbiased estimator にはならない**（df をオーバーサンプリング、cv をアンダーサンプリング）。

両者の良いとこ取りとして **weighted random sampling**（重み付き無作為抽出）を round 51 から random サブシリーズに導入する。母集団全体から抽出する点で random の unbiased 性を維持しつつ、verification 種別ごとに重みを変えて少数派サブセットの抽出機会を確保する。

### 6.1 重み定義（formal）

各ページ `p` の抽出重み `w(p)` を verification 種別ごとに固定する:

| verification | 重み `w` | 理由 |
|--------------|---------|------|
| `code-verified` (cv) | **0.7** | 主力サブセット、ある程度の代表性は確保するが純等確率より圧縮 |
| `runbook-verified` (rv) | **0.05** | 件数最少、過小評価で抽出 0 が常態化を防ぐため等確率より増 |
| `discrepancy-found` (df) | **0.15** | df subtype 別評価のため毎 round 1-2 件抽出を期待 |
| `meta` (chapter-index / split-child / snapshot 集計含む) | **0.05** | meta は site root / snapshot.md 等の構造評価対象 |
| `meta` (chapter-index 単独カウント = ci) | **0.05** | 22 章の扉、毎 round 0-1 件期待 |

`page_kind: chapter-index` のページは ci バケット、それ以外の `verification: meta` は meta バケット。`verification: stub` は監査対象外（§1.3）のため重み 0。

### 6.2 抽出手順

```python
import random
weights_per_bucket = {"cv": 0.7, "rv": 0.05, "df": 0.15, "ci": 0.05, "meta": 0.05}
# 各ページ p の重み = weights_per_bucket[bucket(p)] / count(bucket(p))
# → バケット全体に重み w が割り当てられ、バケット内は等確率
random.seed(round_number)
sample = random.choices(pages, weights=weights, k=12)
# 重複は除外し、サンプル数が 12 に満たない場合は重複なしで再抽選
```

重みは **バケット全体に割り当て、バケット内ページは等確率**。具体的には個別ページ重み = `weights_per_bucket[bucket(p)] / count(bucket(p))`。

### 6.3 期待される抽出分布（n=12）

母集団 ~880 件、cv 586 / rv 27 / df 75 / ci 22 / meta 174 を仮定すると、期待値は cv 8.4 / rv 0.6 / df 1.8 / ci 0.6 / meta 0.6。**df は毎 round 1-2 件抽出が期待**でき、round 47 で発生した df 0 件抽出 → 別途指名 audit 起票という二重運用を解消できる。

純等確率（`shuf -n 12`）の期待値 cv 8.0 / rv 0.37 / df 1.02 / ci 0.30 / meta 2.37 と比較すると、weighted random は **rv +0.23 / df +0.78 / ci +0.30** で少数派を底上げ、meta を -1.77 圧縮。

### 6.4 平均算出時の重み補正

weighted random で抽出した round 平均は **生サンプル平均** と **母集団重み補正後の期待値** を併記する。重み補正後期待値は各ページ評価を母集団内バケット比率で再重み付けして算出する:

```
weighted_mean = Σ (score_i × population_ratio[bucket_i] / sample_ratio[bucket_i]) / 12
```

`population_ratio` は母集団内のバケット比率、`sample_ratio` は本 round サンプル内のバケット比率。stratified の重み補正と同じ要領で、生サンプルは少数派を強調しているため生平均から母集団真値推定へ補正する。

### 6.5 試行 round と mature 判定

- **round 51 で初試行**（奇数 round = random サブシリーズに導入）
- **round 53 / 55** で継続観測、**round 57** で random サブシリーズの真値帯域（4.98 ± 0.01）に **±0.005 以内で収束**すれば mature 判定
- mature 判定後は **奇数 round = weighted random 12** を formal 運用（§3.1 を改訂）
- mature 未達の場合は重み係数を再調整（cv 0.7 → 0.75 への押し戻し等）、round 59 で再判定

### 6.6 stratified との関係

stratified（偶数 round）は **固定比 sampling** として継続、weighted random（奇数 round 試行）は **可変比 sampling** として並走。両者の真値推定が一致することで母集団真値の信頼区間が縮小する。

## 7. 関連ドキュメント

- `meta/templates/SCHEMA.md`: frontmatter スキーマ全体および `page_kind` / `monitor` の定義
- `meta/prompts/reviewer.md`: Reviewer ロールの自動チェック
- `docs/reference/verification/discrepancy-index.md`: `discrepancy-found` ページの自動生成一覧（軸 6 読み替えの注記あり）
- `meta/scripts/gen_discrepancy_index.py`: 上記一覧の生成スクリプト
