# 構成 v4 評価 (Devil's Advocate / 反論役・第 4 ラウンド)

- 作成日: 2026-05-11
- 評価対象: `/tmp/re-proposal-v4.md` (3 タブ + Reference 内 5 カテゴリ案)
- 前回レポート: `meta/structure-v3review-devil.md` (4 タブ案を「No、大幅修正必須」と判定し案 W = 構造変更ゼロ + 本文品質を推奨)
- 立場: 反論役。main の自己評価には乗らず徹底批判する。
- 実測前提 (2026-05-11):
  - 直近 24h 内に main が出した構造提案 = v1 (archive)・v2 (5 タブ)・v3 (4 タブ)・v4 (3 タブ) の **4 回目**
  - `docs/_meta/discrepancies.md` への被リンク = `docs/topics/22-reference-index/` 配下 6 箇所
  - `docs/topics/` 22 章中 `troubleshooting.md` を持つ章 = 0、`operations.md` 保有 = 21
  - frontmatter `related_topics:` 保有 md = 0 件
  - 累計 merge ページ = ~455、verification ステータス完備、`hld-only` = 0 件

---

## 結論 (TL;DR)

**採用すべきか: No (構造変更そのものを 1 週間停止し案 W に戻すべき)**。

v4 は v3 の批判 (タブ過多・Runbooks 廃止劣化・命名英語) に表面的に答えたが、**前回 D の本丸 = 「24h で 3 案は暴走、構造変更ゼロ + 本文品質に切替」をスルーした**。タブを 1 個削っただけの 4 回目の提案であり、main の自己防衛能力低下 (= 「構造を動かしたい衝動」が判断を覆い続ける状態) を一段悪化させた。最大欠陥:

1. **Verification を Reference 配下に置くのは D 初回主張 (「Reference に discrepancy を混ぜるな」) と直接矛盾する**。「カテゴリで分けたから希釈しない」は理屈倒れ。
2. **Runbooks を「引く」と分類して Reference 配下に同居させるのは Diátaxis の How-to (= タスク指向 = 動詞「やる」) を Reference (= 情報指向 = 動詞「引く」) と混同**。`/tmp/re-proposal-v4.md` 自身が「読む / 引く」の 2 動詞しか立てないため、How-to が居場所を失った結果の押し込みである。
3. **「Phase 1 = 30 分 / 1 PR」は虚偽見積もり**。実作業を分解すると最低 5 種類 (.pages 階層化 / reference 内 .pages 新設 / guides 内容を index 統合 / `_meta/discrepancies` 移動 + redirect + 6 箇所リンク修正 / `reference/runbooks/` `reference/verification/` のスタブ index 作成) で、`mkdocs --strict` を通すデバッグ込みで 2-4h は固い。前回 v2/v3 と同じ「タブ数だけ見て簡単」と錯覚する症状の再発。

以下、問題点 10 件 + 個別質問への回答。

---

## 1. v4 の問題点 (10 件以上)

### P1. Verification を Reference 配下に置くことは D 初回主張と矛盾する

v3 評価時、D は「discrepancy-found を Reference (CLI/CONFIG_DB/YANG) 配下に混ぜるな = 既存リファレンスの信頼性が希釈される」と主張した。v4 提案表の D 行は **「Reference 内に独立カテゴリ `verification/` を立てるから信頼性希釈なし」** と書くが、これは:

- 物理的に `reference/verification/` は `reference/cli/` `reference/config-db/` `reference/yang/` と同じ親配下に居る
- mkdocs nav 上は同じ「Reference タブを開いた時のサイドバー」に並列表示される
- 読者の目線では「Reference を引いたら verification も同列に見えた」となり、希釈は構造的に発生

「独立カテゴリ」なる隔壁は **`.pages` 上のラベルだけ** で、URL 階層・nav 並び・サイドバー視覚的距離は隣接。D 初回指摘 (「Reference に混ぜるな」) は「サブディレクトリ深度を 1 つ足せば回避できる」とは言っていない。**指摘の文字面だけ撫でて本質を回避した形式的応答**。

真の対応は (a) `/known-issues/` のような **トップレベル独立ページ** で `nav` には項目を立てない、または (b) verification は外部観測 (CI バッジ等) として `docs/` 配下に出さない、のいずれか。v4 は「Reference 内カテゴリ」と称して D の指摘を吸収したと自称するが、構造は v3 の「Reference 配下サブツリー」と本質的に同じ。

### P2. Runbooks を「引く」対象とする分類は Diátaxis 違反

v4 §思想は読者の動詞を「読む / 引く」の 2 種類とし、Runbooks を「症状を引く」に分類する。これは **Diátaxis 4 象限の How-to (= タスク指向、手順を実行する、動詞は「やる / 直す」) を Reference (= 情報指向、動詞は「引く」) に潰し込んだ** ことを意味する。

- 症状逆引きは **入口** は引くだが、**出口** は「BGP が UP しない時、設定差分を確認し、neighbor を bounce し、log を tail する」という **手順実行** に至る
- 手順実行は Reference (= 動かない/動かさない一次情報) と性格が違う。読者は Reference を「読む途中で離脱して別タブで動かす」ことはあっても、Runbooks は「読みながら自分のターミナルで打つ」
- v3 評価で D は「Diátaxis 厳密 4 象限」を直接強要していないが、How-to を Reference に同居させる構造は **後で必ず分離要求が出る** (フィードバック反映時、読者が「手順だけまとめてほしい」と言うため)

v4 §評価者指摘対応表 F 行で「実用 IA として『Diátaxis 風』と明示」と書いて逃げているが、**「Diátaxis 風」と明示すれば How-to を Reference に潰せる訳ではない**。これは命名の弥縫策。

### P3. 「Phase 1 = 30 分 / 1 PR」は虚偽見積もり

§Phase 移行表は Phase 1 を「`docs/.pages` 3 タブ階層化、`reference/.pages` 5 カテゴリ定義、`docs/index.md` ハブ化、guides 内容を index に統合し guides 削除、`_meta/discrepancies.md` を `reference/verification/discrepancies.md` に移動 (redirects 追加)」を **30 分 / 1 PR** と見積もる。分解すると:

| サブタスク | 実工数下限 | 備考 |
|---|---|---|
| `docs/.pages` 3 タブ階層化 | 10 分 | PoC 未実施、`awesome-pages` の挙動確認が必要 |
| `reference/.pages` 5 カテゴリ定義 | 5 分 | 新規 |
| `docs/index.md` ハブ化 (grid cards + Verification 統計バナー + 検索) | 30-60 分 | 「Verification 統計バナー」は何を表示するか未定義、データソース未指定 |
| guides 5 ファイル (beginner/developer/evaluator/operator/index) を index に統合 | 60-120 分 | ペルソナ 4 種 × 章推奨 = 20+ リンクの再配置、文章圧縮 |
| `_meta/discrepancies.md` を移動 + 6 箇所のリンク修正 + redirects 設定 | 30-45 分 | v3 評価 Q8 で D が既に指摘。`mkdocs-redirects` プラグイン未導入なら導入も必要 |
| `reference/runbooks/index.md` `reference/verification/index.md` スタブ作成 | 15 分 | Phase 1 で空 dir のままだと nav が空ノードを指して `--strict` で落ちる |
| `mkdocs build --strict` デバッグ | 30-60 分 | broken link、nav エラー、redirect 動作確認 |
| PR レビュー・rebase | 15-30 分 | |
| **合計下限** | **3.5h** | **見積もり 30 分の 7 倍** |

「30 分」は **作業手順のリスト長で計算した**ように見える (= タスク数 5 個 × 6 分)。実際の mkdocs IA 変更はリンク・redirect・PoC・CI 確認で必ず数時間規模。前回 v2 で D が指摘した「Tags 657 ファイル一括追加は数日仕事を 3 PR と称した過小評価」と同じ症状。

### P4. 4 回目の構造提案を出した事実そのものが、main の自己防衛能力低下を示す

タイムライン:
- 2026-05-11 朝: v1 (archive 案) → 4 評価で否定 → 撤回
- 2026-05-11 昼: v2 (5 タブ案) → 6 評価で否定 → 撤回
- 2026-05-11 夕: v3 (4 タブ案) → 6 評価で否定 (D は「24h で 3 案は暴走、構造変更ゼロを推奨」) → 撤回
- 2026-05-11 夜 (今): v4 (3 タブ案) ← いま評価中

**前回 D の本丸主張 = 「構造変更を一切やめる」をスルーして 4 案目を出した**。これは:

- AI 評価ループに自分自身が嵌っており、停止判断 (= 構造変更を中止する判断) が下せない状態
- 「6 評価のうち 5 が賛成」を理由に進めるが、その 5 評価者も同じ main エージェントが立てた評価役であり、**多数決の母集団が自家中毒している**
- 真に独立した評価軸 = 読者 / 実装者 / GitHub Issue 報告者 のフィードバックがゼロのまま、内部評価だけで 4 案を出している

「ユーザーが v4 を要求した = だから出した」という防御線は成立しない。ユーザーが要求できるのは「あなたの判断結果を見せろ」までで、「構造を変えろ」と命令している訳ではない。**「ユーザーが要求しているから」を理由に構造変更を継続することは、main の自己防衛能力 (= やらない判断) の不在を示す**。前回 D の警告 (§6 メタ批判) は完全に黙殺された。

### P5. 「6 視点で再評価し賛成 5/不採用 1」の母集団バイアス

§冒頭で「v3 を 6 視点で再評価し賛成 5/不採用 1」と書くが、その 6 視点は:
- v3 評価レポートを書いた A/B/C/D/E/F の評価者群
- 全員が main エージェントが生成したペルソナまたは反論役

つまり **賛成 5 = 自家評価の 5 票**。前回 D が「AI 評価ループだけで構造変更を進めるのを止めろ」と書いた直後に、その 6 票の AI 評価で「採用」と称している。**メタ的に皮肉**。

さらに不採用 1 = D (反論役) のみが構造変更そのものを否定している。v4 はその 1 票を「Phase 1 工数 30 分」「物理移動ゼロ」と表面対応で吸収したと称するが、上記 P3 で示した通り工数は虚偽、P1 で示した通り混在問題は未解決。**「賛成 5/不採用 1」と数えること自体が、不採用 1 の主張内容を質的に評価せず数で押し切る運用**。

### P6. 「物理移動ゼロ」と称しつつ `_meta/discrepancies.md` を `reference/verification/discrepancies.md` に移動する自己矛盾

§Phase 1 で「`_meta/discrepancies.md` を `reference/verification/discrepancies.md` に移動 (redirects 追加)」と明記。一方 §差分表で v4 は「物理構造 (URL 維持、既存を一切動かさない)」と謳う。

- `_meta/discrepancies.md` を移動 = 物理移動 1 件
- URL `/(_meta|meta)/discrepancies/` → `/reference/verification/discrepancies/` = URL 変更
- redirect で繋ぐと言うが、redirect ≠ URL 維持。SEO 上は新 URL 評価がリセット、検索順位下落リスク

「物理移動ゼロ」と「discrepancies.md 移動」は同一提案内で矛盾している。前回 v3 評価で D が指摘した URL 維持原則違反 (Q8) を **同じ提案内で再現**。

### P7. `reference/runbooks/` 10-15 件作成は前回否定された「ソース無しの架空 runbooks」と同じ問題

§Phase 2 で `reference/runbooks/` 10-15 件 (BGP UP しない / VLAN メンバー追加 / FEC エラー / Warm Reboot 失敗 / DHCP Relay 動かない 等) を並走 4-6h で作成する。これは:

- v2 評価時に D が「ソース無しの架空 runbooks は HLD 引用主義に反する」と否定した内容そのもの
- v3 で「Topics 章末 troubleshooting サブページに統合」と回避を試みた (D が Q6 で否定)
- v4 で「Reference 配下に独立カテゴリで復活」 ← **v2 案に回帰**

つまり v4 の Runbooks 案は **v2 のリトライ**。Runbooks 1 件あたり「コマンド出力例・ログ例・回避策」を実機検証なしに書くなら、現リポの方針 (引用元コミット + 検証ステータス frontmatter) と相性が悪い。`verification: code-verified` のステータスを Runbooks にどう付けるか未定義のまま 10-15 件着手は、Phase 6 で確立した品質基準を緩める。

### P8. 「Verification 統計バナー」のデータソース未定義

§Phase 1 内 `docs/index.md` ハブ化に「Verification 統計バナー」と書くが:

- 統計の中身: `code-verified` 件数 / `discrepancy-found` 件数 / カバー率 ? — 未定義
- データソース: 各ページ frontmatter を mkdocs hook で集計 ? `meta/queue/*.json` 集約 ? — 未定義
- 更新頻度: build 時自動再計算 ? 手動 ? — 未定義
- 実装言語: mkdocs-macros プラグイン (未導入) ? Python hook ? — 未定義

v3 評価 Q10 で D が指摘した「coverage.md / queue.md 自動生成スクリプト未実装」と全く同じ問題。「Phase 1 で実施」と書きながら **実装スクリプトの設計すら無い**。

### P9. 「Library → サブシステム改名」の日本語化は IA 上の議論を片付けない

v4 は B 評価者の「Library を日本語化」を採用したと称する。しかし:

- 「サブシステム」という語は SONiC コンテキストでは曖昧 (syncd / orchagent / portsyncd 等の daemon を指す既存用語と被る)
- 現状 `docs/architecture/` `docs/routing/` 等は **機能領域 (functional area)** であり、技術用語の「サブシステム」とは粒度が違う
- 「サブシステム」と呼ぶことで読者に「daemon 単位の章」と誤認させるリスク

命名は「Library」のままの方が「ライブラリ = 参照集」の暗喩で実態に近い。**日本語化を採用すること自体が表面対応**で、命名の語義整合性は検討されていない。

### P10. 「後戻り 5 分で可能」の根拠が薄い

§D 評価者対応行で「物理移動ゼロ、`docs/.pages` 1 ファイル + reference/ に 2 サブディレクトリのみ。後戻り 5 分で可能」と書く。しかし実際の後戻り工数:

- `docs/.pages` を revert: 1 分
- `reference/runbooks/` `reference/verification/` 削除: 1 分
- `_meta/discrepancies.md` 移動の revert + redirect 削除 + 6 箇所のリンク再修正: 10-20 分
- guides 削除の revert (5 ファイル復元 + index.md 再修正): 15-30 分
- `docs/index.md` ハブ化 (grid cards + 統計バナー) の revert: 10-15 分
- mkdocs build 再確認: 5-10 分
- **合計**: 40-80 分

「5 分」は `docs/.pages` 1 ファイル分だけを数えており、Phase 1 で実施する他の 4 種類の変更を無視。前回 v3 評価で D が指摘した「タブ数だけ見てシンプル」と同じパターン。

### P11. Phase 2-4 並走工数の合算

§Phase 移行表は工数を Phase 別に並べるが、合算すると:

- Phase 1: 30 分 (実態 3-4h、P3 参照)
- Phase 2: 4-6h (runbooks 10-15 件)
- Phase 3: 2-4h (coverage/queue 自動生成 + related_topics 機械追加)
- Phase 4: 「数日〜」(本文品質改善)

合計 **8-14h + 数日**。「Phase 1 構造 (30 分) + Phase 2 以降 本文品質に全振り」と D 対応行に書くが、Phase 2/3 は構造作業 (Runbooks 新設 + 自動生成スクリプト) であり本文品質ではない。**「30 分で構造完了、後は本文」は虚偽の枠組み**。

### P12. `related_topics:` 機械追加が Phase 3 に温存されている

§Phase 3 に「Topics⇔サブシステム の `related_topics:` frontmatter 機械追加」と書く。これは前回 v2 で D が Tags プラグイン批判で否定し、v3 で `related_topics:` に名前を変えて再提案、D が Q2 で「判定ロジック未定義」と否定した内容。**v4 で名前そのまま Phase 3 に温存**。

判定ロジック (どの area ページが章 03 に該当するか) は依然未定義。「並走 2-4h」と見積もるが、~140 Topics ページ × 平均 5-15 関連 = 700-2100 リンクの判定を 2-4h で機械化できる根拠ゼロ。**3 回連続で同じ過小見積もりが提案されている**。

---

## 2. 質問への直接回答

### Q-D-1. Verification を Reference 内に置くと、D 初回の「Reference に混ぜるな」と矛盾しないか

**矛盾する** (P1 詳述)。「カテゴリで分けたから希釈しない」は `.pages` ラベル上の隔壁に過ぎず、URL 階層・nav 並び・サイドバー視覚距離・読者の心理的近接度は v3 案と同じ。D 初回主張は「Reference の信頼性を守るために discrepancy を視覚的・構造的に Reference から離せ」であり、サブディレクトリ深度 +1 では離れていない。

真に整合する選択肢は:
- (a) `/known-issues/discrepancies/` のような **トップレベル独立ページ** (nav には出さず、index.md からのリンクのみ)
- (b) discrepancy 情報を frontmatter `verification: discrepancy-found` だけにとどめ、専用ハブを作らない
- (c) Verification は外部 (GitHub Project / CI バッジ) で管理し `docs/` には出さない

v4 はいずれも採用していない。

### Q-D-2. Runbooks を Reference 配下にするのは「症状逆引きは情報引きである」の解釈、これは妥当か

**妥当でない** (P2 詳述)。症状逆引きの動詞は **入口 = 引く、出口 = やる**。Diátaxis では明確に How-to (タスク指向) と Reference (情報指向) を分けており、両者を混在させると:
- 読者の期待コンテキスト切替コストが上がる (Reference を読む頭から、コマンドを打つ頭へ)
- 1 ページ内に「Reference 風の表」と「How-to 風の手順」が混在し、書き手も粒度を維持しづらい
- 検索結果で症状ページが CLI ページと並ぶと、「どちらが正解か」読者が判定する負担が増える

v4 が「読む / 引く」の 2 動詞だけを立てたために How-to の居場所がなくなり、Reference に押し込んだ。**動詞分類が 2 つでは Diátaxis を表現できない**ことを示す。3 動詞 (読む / 引く / やる) に増やせば Runbooks は独立タブまたは独立ディレクトリになり、v2 案に近づく。

### Q-D-3. 「Phase 1 が 30 分」は虚偽見積もりではないか

**虚偽** (P3 詳述)。実工数下限 3.5h。「30 分」は作業項目を列挙して 1 項目 6 分で割った数値遊びに見える。mkdocs IA 変更で 30 分で完了するのは「`.pages` 1 ファイルだけを書き換える」ような最小単位のみ。v4 Phase 1 は最低 5 種類の変更 + redirect 設定 + `mkdocs --strict` デバッグを含むため数時間スケール。

### Q-D-4. 既に 4 案出している事実が問題、ユーザーが要求している = main の自己防衛能力低下では

**その通り** (P4 詳述)。前回 D が「24h で 3 案 = 暴走」「構造変更を 1 週間停止せよ」と明示主張したが、v4 はそれを完全黙殺して 4 案目を出した。「ユーザーが要求した」は防御線にならない:
- ユーザーが要求しているのは「v4 案の判断結果」であり、「構造を変えろ」ではない
- main は「v4 を出さずに『前回 D の主張通り構造変更を停止します』と返答する」自由があった
- それを選ばず 4 案目を出した = **「動かしたい衝動」が「停止すべき判断」を覆い続けている**

これは設計者の自己防衛能力 (= やらない判断、stop の判断) の機能不全。Phase 6 で 455 ページの品質を積み上げた main と同じエージェントが、構造変更フェーズに入ると 4 連続で同種提案を出している事実は、**ドメイン (本文 vs 構造) によって判断品質が大きく違う**ことを示す。本文ドメインで磨いた信頼を構造ドメインで使い回すべきではない。

### Q-D-5. 構造変更を一切やめてコンテンツに集中する案 W の再提案

**強く再提案する**。具体的に:

#### 案 W' (v4 評価版・前回案 W の精緻化)

**構造変更 = ゼロ**。`docs/.pages` も `docs/index.md` も `_meta/discrepancies.md` も触らない。代わりに次の 3 PR を 1 週間で出す:

1. **discrepancy-found 39 件の検証根拠強化** (1 PR ~5 ファイル × 6-8 PR)
   - 各ページに「該当 sonic-buildimage commit ハッシュ」「テスト失敗の再現コマンド」「回避策または upstream Issue 番号」を追記
   - frontmatter `verified_at: 2026-05-XX` を追加し最新性を示す
   - これは前回 v3 評価 §3 案 W で D が提案した内容そのもの

2. **Topics 22 章 `operations.md` の運用観点拡充** (1 PR ~3 章 × 7 PR)
   - 現状 `operations.md` は薄い (各章 100-200 行) 。運用者目線の「監視メトリクス」「変更時のチェックリスト」「ロールバック手順」を追記
   - 1 章 +200 行目安、22 章で +4400 行の本文増。これは「ソース無し runbooks 新設」と違い、既存ページの深堀りで HLD 引用主義に整合

3. **categories 10 件 + 横断索引強化** (1 PR)
   - 各 categories ページに `updated_at:` `verification:` frontmatter を追加
   - categories index に「最終更新降順」「verification ステータス別」のテーブルを mkdocs-macros または手書きで追加 (構造変更ではなく既存ページの強化)

#### 「構造変更を 1 週間停止する」運用ルール

- 2026-05-11〜18 は構造提案 PR を出さない (`docs/.pages` / `mkdocs.yml` の nav 関連 / ディレクトリ移動 を含む PR を main に merge しない)
- 同期間に Phase 6 で公開済の 455 ページに対し **読者フィードバック取得** を試みる (SNS 告知、GitHub Discussions 開設、コミュニティへの URL 共有)
- 1 週間後に「フィードバック有無 + 本文品質改善の進捗」を見てから構造を議論する

#### v4 を「採用しない」ことのリスク評価

| 観点 | v4 採用 | 案 W' 採用 |
|---|---|---|
| Phase 1 工数 | 実態 3-4h (虚偽 30 分) | 0 (構造変更なし) |
| 後戻りコスト | 40-80 分 (P10) | 0 |
| 本文品質向上 | Phase 4 以降 (実質遅延) | 即着手 |
| 自己評価ループ脱出 | できない (v5 / v6 のリスク) | できる (構造議論停止) |
| URL/SEO リスク | 中 (P6) | ゼロ |
| 読者導線 | 多少改善 (3 タブ) | 不変 |
| 母集団バイアス露呈 | 賛成 5/反対 1 を押し切る前例 | 反論役の主張を採用する前例 |

**案 W' は v4 採用より全項目で優位または同等**。唯一「読者導線が多少改善」のみ v4 に分があるが、その効果は読者フィードバック取得前には測定不能。

---

## 3. 採用判定

### v4 採用すべきか: **No (構造変更そのものを 1 週間停止し案 W' を採用すべき)**

v4 を採用するなら最低限以下を **事前に** 解決する必要:
1. Verification を Reference 配下から外し、`/known-issues/` 等の独立ページに格下げ (P1)
2. Runbooks を Reference から外す。または「読む/引く/やる」の 3 動詞分類に切替 (P2)
3. Phase 1 工数を実測ベースで再算出 (最低 3.5h、P3)
4. `Verification 統計バナー` のデータソースと実装手段を明示 (P8)
5. `related_topics:` の判定ロジックを PoC で動かして見せる (P12)
6. 「物理移動ゼロ」と `_meta/discrepancies.md` 移動の矛盾を解消 (P6)
7. 「賛成 5/不採用 1」の母集団バイアスをユーザーに明示し、外部評価を取る (P5)

これらを満たさず採用するなら、v5 / v6 が今夜中にさらに提案される可能性が高い。**今が停止判断の最後のタイミング**。

### 提案する次行動

1. **v4 提案を撤回する** (main が自発的に「採用しない」と決める)
2. **構造変更停止期間 (2026-05-11〜18) を設ける** (`CLAUDE.md` に明記)
3. **案 W' (本文品質 3 PR 系列) に切替** (詳細は §Q-D-5)
4. **1 週間後に再評価** (フィードバック有無 + 本文品質進捗を見て構造を議論)
5. **AI による構造評価ループを停止** (前回 D §6 既指摘、v4 でも未対応)

---

## 4. メタ批判: 「24h で 4 案」の異常さの再警告

前回 v3 評価で D は「24h で 3 案」を異常と指摘した。v4 で **4 案目** に到達。指摘内容が **採用されないまま** 同じパターンが続いている。これは:

- main エージェントの自己修正能力が「構造変更ドメイン」で機能していない
- 評価役 (A〜F) の多数決で進める運用が、母集団バイアスを内包している
- 「ユーザーが要求した」を防御線に構造提案を再生産する構造が、main 内部にロックインしている

このまま放置すると 2026-05-12 朝に v5 が出る可能性が現実的にある。**今 v4 を撤回することは、未来の v5/v6/v7 を 1 度に止める唯一の手段**。

---

## 付録: 実測データ (2026-05-11、v3 評価から再確認)

- 直近 24h 内の構造提案 = v1/v2/v3/v4 の 4 案 (今回 v4 を含む)
- `docs/_meta/discrepancies.md` 被リンク = `docs/topics/22-reference-index/` 配下 6 箇所 (v3 評価時から変動なし)
- `docs/topics/` 22 章中 `troubleshooting.md` 保有 = 0、`operations.md` 保有 = 21
- frontmatter `related_topics:` 保有 md = 0 件
- 累計 merge ページ = ~455、`hld-only` = 0 件、verification ステータス完備
- v3 評価で D が推奨した案 W (構造変更ゼロ + 本文品質) は **未着手**
- v4 提案で Phase 1 = 30 分と見積もるが、実工数分解で 3.5h 下限 (P3)
