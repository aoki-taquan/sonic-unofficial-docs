# 構成評価 (Devil's Advocate / 反論役)

- 作成日: 2026-05-11
- 評価対象: main エージェントが提案している「既存 10 area を `archive/` に追放し、`topics/` + `reference/` の 2 軸に絞る」案
- 立場: 反論役（main の自己評価には乗らず、徹底的に批判する）

---

## 結論 (TL;DR)

**main 提案を採用すべきか: No (条件付きでも非推奨)**

理由を 1 行に圧縮すると: **600+ ページの 7 割を一晩で「archive」というラベルに押し込めば、SEO・被リンク・Verifier が積み上げた `code-verified` / `discrepancy-found` の信用、`awesome-pages` 自動 nav が動くという運用上の安定、そのすべてを同時に毀損する。** 2 軸化のメリット（読み手の入口が単純化される）は、`topics/` の章 index と「discrepancy 一覧」ページを **追加するだけ** で 8 割以上を達成できる。破壊的構造変更でなく、`restructure-plan.md` の High セクションを実行するのが正解。

main 提案の最大欠陥 3 つ:
1. **`reference` 167 ページ + `topics` 143 ページの 310 ページしか「表」に残らない**。残り 300+ の HLD 移植は `archive/` というラベルが付くだけで読み手は触らなくなる。実装と一致確認まで終わった `code-verified` 資産が即「過去のメモ」扱いになる。
2. **URL が壊れる**。area→archive へのディレクトリ移動は `/architecture/foo/` → `/archive/architecture/foo/` 級の path 変化を伴い、外部からの参照（issue、社内 wiki、検索流入）が全滅する。MkDocs に redirects プラグインを入れていない以上、404 の山ができる。
3. **`topics/` 22 章は完成しすぎていて、構造の主軸として固定するには硬すぎる**。`01-overview` ... `22-reference-index` の番号は並べ替えが難しく、新領域 (例: gNOI、SAI-RPC、AI 関連) が出るたびに番号体系を壊す or 末尾に積むしかない。

推奨する代替案: **`restructure-plan.md` の High を実行 + Diátaxis 風のラベル（Concept / Guide / Reference / Internals）を `frontmatter` の `kind:` でタグ付けし、Material の Tags プラグインで横断ビューを足す**。物理ディレクトリは触らない。

---

## 1. main 提案「area を archive 化、topics + reference の 2 軸」の問題点 (12 件)

### P1. SEO / 被リンクの即時毀損
`docs/architecture/` 配下 41 ページ、`docs/routing/` 配下 51 ページ等は、site_url (`https://aoki-taquan.github.io/sonic-unofficial-docs/`) 配下で半年以上のインデックス実績がある。`archive/` プレフィックスを付けた瞬間、Google の「path 含む URL シグナル」も検索流入導線もリセットされる。MkDocs Material 標準では redirect は出ない。

### P2. Verifier の成果が見えなくなる
`hld-only: 0 件` 達成・39 件の `discrepancy-found`・~290 件の `code-verified` という、このリポの「他の SONiC HLD 寄せ集めサイトには無い独自価値」が、`archive/` に押し込まれると一覧不能になる。むしろ Verifier 成果は **トップに昇格** すべき（例: `/verification/` という新セクション）。

### P3. `topics/` 22 章で代替できない
topics の合計 143 ページは「読み物」として再構成された二次資料。`routing/` 51 + `system/` 71 など area 配下の HLD 詳細を完全には吸収していない。topics ですべて済むという前提は、章ごとの粒度（6 ページ平均）を見れば成立しない。例: `02-bgp` 章は 6 ページ程度だが、`routing/` 配下 BGP 系は 20+ ページ存在し、SRv6 / VRRP / BMP / BFD などの深い HLD は topics に入っていない。

### P4. 章番号 `01-22` 固定の硬直性
slug に番号を埋めた瞬間、追加・削除・並べ替えが破壊的になる。`13-dash-smartswitch` の前に新章を入れたければ全番号を打ち直すか、`12.5-` のような汚いハックを許すしかない。`awesome-pages` の `.pages` で順序を決め、slug 自体は番号無しが本来正しい。

### P5. 「読み物」と「reference」の境界が定義不能
`docs/architecture/sonic-generic-hash.md` は HLD 起源だが、ハッシュ機能の設定方法と SAI 属性まで書いてある。これは reference か concept か？「2 軸」に押し込もうとすると毎ページ判定論争が発生する。実態はスペクトラム。

### P6. トラブルシュート・運用手順の置き場がなくなる
topics/reference の 2 軸では「障害時の切り分け」「warm-reboot 失敗時の調査」など How-to が居場所を失う。Diátaxis フレームワークでは Tutorial / How-to / Reference / Explanation の 4 象限に分けるのが定説で、2 軸はその半分しかカバーしない。

### P7. `guides/` 5 ページの消失
beginner / developer / evaluator / operator というロール別入口は、新規読者の最大の入口になり得る。これを `topics/` に統合すると、ロール軸とトピック軸が混在してかえって迷う。

### P8. `categories/` 11 ページの再価値化が止まる
categories は area 横断クラスタ（dual-tor / smartswitch / dash / bgp-evpn 等）の「テーマ別入口」として既に存在する。これこそが「分かりづらい」問題の本来の解決策で、archive 化すると逆走する。

### P9. `internals/` 12 ページの誤分類リスク
SWSS / sairedis / orchagent 内部実装は reference ではないが、topics の読み物章にも収まりが悪い。「2 軸」だと結局 topics に押し込むことになり、上級者向け資料が初心者向け章の中に紛れる。

### P10. mkdocs.yml と `.pages` の運用ノウハウ破棄
`awesome-pages` で各ディレクトリの `.pages` を編集することで Writer が nav に触らず安全に追記できるという既存ルール (CLAUDE.md §5, mkdocs.yml 末尾コメント) が、2 軸前提の固定 nav に置き換わると崩壊する。バッチ Writer の並走運用 (#1〜#11) を支えてきた基盤を破壊する。

### P11. `meta/queue/<area>-<slug>.json` の slug が崩壊
per-page queue ファイル名は area 名を含む。`docs/architecture/foo.md` → `docs/archive/architecture/foo.md` に動かすと queue 側のインデックス、`aggregate_queue.py`、`meta/verification-queue.json` 互換性、CI scripts が一斉に壊れる。移行コストが見積もられていない。

### P12. 「足し算しただけ」の批判は実は妥当だが、引き算が解ではない
14 セクションが多いのは事実。だが解は「7 割を捨てる」ではなく「**入口を 1 枚増やす**」ことである。トップに「読み手別ガイド (guides) → 横断テーマ (categories) → 詳細 HLD (area) → 字引 (reference)」の 4 段階導線を明示する README/index.md 改修で十分。

---

## 2. 代替案 (3 種類)

### 案 X: **Diátaxis 4 軸 (Tutorial / How-to / Reference / Explanation)**
- 物理 dir: `getting-started/` `howto/` `reference/` `explanation/`
- area は `explanation/` 配下に吸収（`explanation/routing/...`）
- メリット: 業界標準フレームワーク。読み手の意図 (学ぶ/解決する/調べる/理解する) と 1:1
- デメリット: 600+ ページの分類作業が必要、URL 全面変更、areas との対応付けが曖昧なページが多発
- 移行コスト: **超大** (人手で全 600 ページ judge、1 人日 × 数週間相当)

### 案 Y: **5 軸 (Concepts / Setup / Operations / Reference / Internals)**
- 物理 dir: 上記 5 つ
- topics は `concepts/` へ、guides は `setup/` `operations/` へ分岐、internals は維持、reference は維持
- メリット: 役割が明確、運用者・開発者・新規評価者の 3 ペルソナと対応
- デメリット: area→concepts の移動で大規模 URL 変更、operations と setup の境界論争
- 移行コスト: **大** (URL redirect 必須、`.pages` 全書き直し)

### 案 Z (推奨): **物理ディレクトリ不変 + frontmatter `kind:` タグ + Material Tags プラグイン**
- 既存 14 dir はそのまま
- frontmatter に `kind: concept | howto | reference | internals | testplan` を追記（既に `verification` フィールド運用ノウハウあり）
- `mkdocs.yml` に `plugins: - tags` を追加し、`/tags/concept/` `/tags/howto/` などの自動横断ビューを生成
- トップ `index.md` を「読み手別 (guides) → 横断テーマ (categories) → 詳細 HLD (area) → 字引 (reference)」の 4 段導線に書き換え
- メリット: **URL 不変、SEO 維持、awesome-pages 運用維持、Verifier 成果も `verification` タグで横断可視化、機械処理しやすい**
- デメリット: 物理構造の「2 軸」的単純さは得られない（だが本当に必要なのは「見た目の入口」であって物理構造ではない）
- 移行コスト: **小〜中** (frontmatter 一括追加 script + プラグイン導入 + index.md 改修。1 PR 群で完結)

### 案 W: **完全フラット + タグベース**
- 全 600+ ページを `docs/pages/` 直下にフラット配置し、すべてタグで分類
- メリット: 「area の境界論争」を完全消去
- デメリット: ファイル名衝突、URL 全変更、`awesome-pages` 不要だが mkdocs nav が爆発、編集者が探しにくい
- 移行コスト: **特大、非推奨**

---

## 3. 比較表 (5 軸評価)

| 案 | 入口の分かりやすさ | 情報重複の少なさ | メンテ性 | 検索性 (SEO含む) | 既存資産活用度 |
|---|---|---|---|---|---|
| main 提案 (archive + 2 軸) | ◯ (単純) | △ (archive 内で重複は残る) | × (`.pages` 運用崩壊) | × (URL 全変更、SEO 毀損) | × (Verifier 成果が埋没) |
| 案 X Diátaxis | ◎ | ◯ | △ | × (URL 全変更) | △ (再分類が必要) |
| 案 Y 5 軸 | ◯ | ◯ | △ | × (URL 大幅変更) | △ |
| **案 Z タグ (推奨)** | ◯ (index.md 改修で対応) | ◯ (タグ横断で可視化) | ◎ (現状運用維持) | ◎ (URL 不変) | ◎ (全資産そのまま) |
| 案 W フラット | × | △ | × | × | × |

判定: **案 Z が 5 軸中 4 軸で最高評価**。main 提案は「入口の分かりやすさ」以外で軒並み最低。

---

## 4. 「実は現状のままが正解かもしれない」可能性

### 14 セクションは本当に多すぎるのか？
- mkdocs Material の navigation.tabs はトップに横並びで 14 個出すと確かにスクロールが必要。
- ただし `navigation.sections` も有効なので、tabs を絞って 2 段目に sections を出す UI 調整だけで「多い」印象は解決する。物理構造は無罪。

### guides + topics + area の三層は冗長か？
- guides = ロール別入口 (5)、topics = テーマ別読み物 (22 章)、area = HLD 詳細 (10) は **役割が違う**。冗長ではなく多層案内。
- 問題は「3 層の関係性が index.md に書かれていない」こと。書けば解決。

### 「足し算しただけ」批判への反論
- 確かにバッチ #1〜#11 で 290 ページ、Verifier #1〜#27 で 200+ ページの足し算をしてきた。
- だが各 area 内では `.pages` で並び順を整え、`code-verified` / `discrepancy-found` のタグ付けまで完了している。**足し算が無秩序だったわけではない**。
- 必要なのは「外から見える導線の足し算」(index.md 改修、タグ横断ビュー、discrepancy 一覧) であり、構造の引き算ではない。

---

## 5. 推奨アクション (優先度順)

1. **main 提案 (area→archive) を却下** する
2. `restructure-plan.md` の High セクションを実行
   - 10 area `index.md` に概要 + 検証分布 + ページ一覧
   - `.pages` を意味順に並べ替え (URL 不変)
   - CONFIG_DB ↔ CLI ↔ HLD 相互リンク追加
3. 案 Z を追加実装
   - frontmatter `kind:` 追記 (一括 script)
   - `mkdocs.yml` に Tags プラグイン追加
   - `docs/index.md` を 4 段導線 (guides → categories → area → reference) に改修
4. 39 件の `discrepancy-found` 専用一覧ページを `/discrepancies/` に作成 (このリポの最大価値の可視化)
5. 番号付き topics (`01-22`) は番号を `.pages` 側に移し、slug から番号を剥がす (URL 後方互換のため symlink or redirect が必要なら別 PR)

---

## 付録: 参照した既存メタファイル

- `meta/restructure-plan.md` (現状サマリと既存改善計画。本レポートは High セクションの実行を強く支持)
- `meta/categories-proposal.md` (categories の既存案)
- `meta/personas-guide-proposal.md` (guides 既存案)
- `meta/topics-plan-*.md` (topics の 3 系統 plan)
- `mkdocs.yml` (`awesome-pages` 運用、Writer は nav を触らないルール)
- `CLAUDE.md` §5 (メタファイルの役割)、§10 (現状スナップショット)
