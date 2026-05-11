# v4 構成評価レポート（Codex 第三者視点）

- 作成日: 2026-05-11
- 評価対象: `/tmp/re-proposal-v4.md` の「3 タブ + Reference 内 5 カテゴリ」案、および本 checkout の現行構成
- 立場: 前回レポート `meta/structure-v3review-third.md` の指摘に対する再評価

## 結論

**v4 は条件付きで採用可。** v3 よりも実装リスクが低く、前回指摘した「タブ増殖」「Verification の孤島化」「Runbooks 廃止による運用者動線の劣化」をかなり現実的に畳んでいる。3 タブへ戻し、Reference 内に CLI / CONFIG_DB / YANG / Runbooks / Verification を並べる判断は、サイト全体の情報量に対して過剰な分類を避ける案として妥当である。

ただし、v4 を「最終 IA」として大きく実装するのではなく、**小さい構造変更 + 本文品質改善の開始条件**として採用すべきである。v4 の勝ち筋は 3 タブそのものではない。Search-first Hub、症状逆引き、Verified Pathways、乖離の運用影響説明が本文とリンクで機能して初めて価値が出る。ここを作らないまま `reference/verification/` と `reference/runbooks/` だけを増やすと、v3 で懸念した「品質台帳の孤島化」が Reference 配下で再発する。

また、本 checkout では v4 実装はまだ確認できない。`docs/.pages` は `guides`、`topics`、9 area、`reference`、`categories` が横並びの従来構成であり、`docs/reference/.pages` も CLI / CONFIG_DB / YANG の 3 カテゴリのみである。`docs/reference/runbooks/` と `docs/reference/verification/` は存在せず、`docs/_meta/discrepancies.md` はまだ `_meta` 配下にある。したがって本レポートは、提案としての v4 への採否と、現行 checkout に対する実装ギャップを分けて扱う。

## 1. 前回指摘への反映

### Verified Pathways の核を昇格できたか

v4 は v3 の「Verification 独立タブ」を取り下げ、Reference 内カテゴリとして `reference/verification/` を置く。これは一見すると前回の「Verified Pathways を昇格せよ」から後退して見えるが、設計意図としては妥協可能である。Verification は読者が単独で読む章というより、「このページはどこまで裏取り済みか」「HLD と実装の差は何か」を引くための参照情報だからである。

ただし条件がある。`reference/verification/index.md` が単なる統計ページや `discrepancies.md` へのリンク集なら、昇格にはならない。必要なのは、主要クラスタごとに次をつなぐ Verified Pathways である。

- 機能説明: Topics またはサブシステムの解説ページ
- 操作入口: CLI reference と CONFIG_DB / YANG reference
- 検証状態: `code-verified` / `discrepancy-found` / `hld-only`
- 乖離判断: その差分が運用・設定・障害調査にどう効くか
- 次の確認: 実機で見るコマンド、該当コード、未確認事項

現行 corpus には `verification:` frontmatter が広く入り、確認時点で `code-verified` は 401 件、`discrepancy-found` は 39 件、`hld-only` は 42 件ある。この資産は v4 の核になり得る。一方で、今の `docs/_meta/discrepancies.md` は `_meta` に閉じており、一般読者の動線から見えにくい。v4 でここを `reference/verification/` に移すこと自体は採用してよいが、移動だけでは不足である。

### Search-first Hub を受け止めたか

v4 は `docs/index.md` をハブ化し、検索と Verification 統計バナーを置くとしている。これは前回指摘への正しい反応である。Get Started を独立タブ化せず index に統合する点も、タブ数を抑える判断として妥当である。

しかし、Search-first Hub は「カードがあるトップページ」ではない。600 ページ規模のサイトで必要なのは、検索語・症状・作業・乖離から最短で既存ページへ入れる編集済み導線である。現行 `docs/index.md` は読み手別ガイドと大分類リンクが中心で、BGP / VXLAN / VLAN-LAG / Warm Reboot / gNMI / FEC のような実検索語から入る構造にはなっていない。

v4 の hub は次を満たす必要がある。

- 「BGP neighbor が上がらない」「VLAN に疎通しない」「FEC エラー」「Warm Reboot 失敗」「gNMI 設定」など症状・作業語を入口にする。
- 各入口から Topics、CLI、CONFIG_DB、YANG、Runbook、Verification へ分岐する。
- `discrepancy-found` があるクラスタでは、最初から注意喚起と影響範囲を見せる。
- `hld-only` のページは、読者が実装済み事実と誤認しないようにする。

この条件を満たすなら、v4 は Search-first Hub を受け止めている。満たさないなら、3 タブ化しても前回指摘は未解決のままである。

### 構造より本文品質を受け止めたか

v4 は「Phase 1 構造 30 分 + Phase 2 以降 本文品質に全振り」と明記している。この反省は正しい。24 時間で複数構造案が出ている状況では、これ以上 IA の完成度を追うより、読者が実際に解決したい問いに答える本文へ移るべきである。

ただし、Phase 2 以降という表現は弱い。本文品質は Phase 1 の後ではなく、v4 採用条件そのものに入れるべきである。特に `docs/guides/operator.md` はすでに「障害別の逆引き導線が不足」「runbook 形式のページがない」と明記している。これは構造の美観ではなく、実利用の欠損である。

優先すべき本文改善は次である。

- 主要 5 クラスタ: BGP / VLAN-LAG / FEC-optics / Warm Reboot / gNMI-OpenConfig
- 症状逆引き: Runbooks 10-15 件のうち、まず 5 件を手で厚く作る
- 乖離影響: `discrepancy-found` 39 件のうち、運用影響が大きいものを先に説明する
- 未裏取り警告: `hld-only` 42 件が実装事実として読まれないようにする
- 操作完遂性: 確認、変更、保存、rollback、再起動影響まで本文に入れる

## 2. v4 の構造で検索・症状・乖離は機能するか

### 検索

機能する可能性は高い。Reference に CLI / CONFIG_DB / YANG が集約済みで、既存 reference は `code-verified` の機械抽出ベースとして強い。ここに Runbooks と Verification を足す設計は、検索から来た読者が「コマンド」「設定テーブル」「モデル」「症状」「裏取り状態」を同じ大分類内で引けるため、情報設計として自然である。

ただし、Reference index が今のような長大なページ一覧のままだと検索入口としては弱い。`docs/reference/index.md` は CLI / CONFIG_DB / YANG の一覧が中心で、作業語や症状語のまとめがない。v4 では `reference/index.md` を 5 カテゴリの索引に作り替え、各カテゴリの役割を明確にする必要がある。

### 症状

v4 で最も改善した点は Runbooks の復活である。v3 の「Runbooks 廃止、章末 troubleshooting へ吸収」は、運用者が症状名から探す動線を弱める懸念があった。v4 が `reference/runbooks/` を置く判断は、この問題を正しく受け止めている。

一方で、Runbooks を Reference 配下に置くと、トップタブとしての視認性は下がる。これを補うには、`docs/index.md` と `reference/index.md` から症状カードを直接出す必要がある。Runbook の中身も、単なるリンク集では不十分である。最低限、症状、最初に見るコマンド、正常値、よくある原因、CONFIG_DB / YANG の確認点、関連 discrepancy、rollback または安全な中断条件まで必要である。

つまり、v4 の構造は症状起点に向いているが、機能するかは Runbook 本文の密度で決まる。

### 乖離

乖離の扱いは v4 で改善している。D 指摘の「discrepancy を Reference に混ぜるな」に対して、CLI / CONFIG_DB / YANG の各ページへ直接混ぜず、Reference 内の独立カテゴリに分ける設計は妥当である。仕様参照ページの信頼性を薄めず、裏取り状態を別の軸として扱える。

ただし、`reference/verification/` が Reference 内にあることで、トップレベルの存在感は v3 より弱くなる。この弱点は index hub と各ページ末尾のリンクブロックで補うべきである。`discrepancy-found` ページから `reference/verification/discrepancies.md` へ戻れること、逆に discrepancy 一覧から該当 Topics / サブシステム / Reference へ戻れることが必須である。

乖離は一覧化だけでは読者価値にならない。必要なのは「この HLD 記述は現行実装ではどう違い、どの操作判断を変えるべきか」である。v4 はその置き場を作るが、本文を書かなければ解決しない。

## 3. 構造より本文品質へ切り替えるべきか

**切り替えるべきである。ただし v4 の Phase 1 は並行で実施してよい。**

理由は、v4 の構造変更が小さいからである。`docs/.pages` の 3 タブ化、`reference/.pages` の 5 カテゴリ化、`docs/index.md` のハブ化、`_meta/discrepancies.md` の移動は、後戻り可能な範囲に収まっている。これを止めて本文監査だけに入るより、v4 の薄い骨格を入れて、本文品質改善の入口を作るほうが効率的である。

ただし、構造 PR を連続で増やすのは避けるべきである。v4 採用後の作業比率は、構造 20%、本文 80% に寄せるのが妥当である。具体的には、構造変更は 1 PR で止め、直後の PR から主要クラスタの Runbook と discrepancy 影響説明へ移る。

特に次の順序を推奨する。

1. v4 Phase 1 を 1 PR で実施する。ただし `guides/` 削除は、index に同等以上の導線が入るまで遅らせてもよい。
2. `reference/runbooks/` は 10-15 件を一気に薄く作らず、まず BGP / VLAN / FEC / Warm Reboot / gNMI の 5 件を濃く作る。
3. `reference/verification/index.md` は統計ではなく、主要クラスタ別 Verified Pathways を置く。
4. `discrepancy-found` 39 件から運用影響の大きいものを選び、本文側にも「この乖離が何を変えるか」を追記する。
5. その後に coverage / queue の自動生成、関連リンクの機械追加を行う。

## 4. v4 採用可否

判定は **条件付き採用**。

採用してよい点:

- トップレベルを 3 タブへ戻し、構造の過剰設計を抑える。
- Library を「サブシステム」に改名し、日本語サイトの読者語彙へ寄せる。
- Runbooks を Reference 配下に復活させ、症状起点の入口を残す。
- Verification を Reference 内の独立カテゴリにし、CLI / CONFIG_DB / YANG の仕様参照と混ぜない。
- 物理移動を最小化し、後戻り可能な Phase 1 にする。

採用条件:

- `docs/index.md` は Search-first Hub として、検索語・症状・作業・検証状態から入れる内容にする。
- `reference/index.md` は 5 カテゴリの役割を明示し、長大な一覧ページから入口ページへ変える。
- `reference/verification/index.md` は統計中心ではなく、主要クラスタ別 Verified Pathways を持つ。
- `reference/runbooks/` は薄い雛形量産を避け、少数の実用 runbook から始める。
- v4 構造 PR の次は、本文品質 PR を必ず優先する。

採用しない場合のリスクは、v3 の 4 タブ案に戻って Verification の存在感は上がるが、Runbooks と Search-first Hub の扱いが再び揺れることである。v4 は、構造議論を終わらせて本文へ移るための落とし所として優れている。

## 5. 推奨次行動

1. v4 Phase 1 を小さく実装する。対象は `docs/.pages`、`reference/.pages`、`docs/index.md`、`reference/index.md`、`reference/verification/`、`reference/runbooks/` の最小骨格に限定する。
2. `guides/` 削除は急がない。index hub が読み手別入口、症状入口、検証入口を同等以上に担えることを確認してから削除する。
3. 最初の本文 PR は BGP を対象にする。`show bgp`、`config bgp`、`BGP_NEIGHBOR`、YANG、該当 Topics / routing ページ、discrepancy を 1 本の pathway にする。
4. 次に VLAN-LAG、FEC-optics、Warm Reboot、gNMI-OpenConfig を同じ型で作る。
5. 5 クラスタで型が固まってから、coverage / queue の自動生成と全体 metadata 展開を行う。

v4 の評価で重要なのは、タブ数の正しさではなく、構造変更が本文品質改善を始めるための摩擦を下げるかである。その意味で、v4 は採用してよい。ただし、これ以上の構造再提案は打ち止めにし、次の主作業は Runbooks と Verified Pathways の本文化に移すべきである。
