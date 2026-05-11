# v3 構成評価レポート（Codex 第三者視点）

- 作成日: 2026-05-11
- 評価対象: `/tmp/re-proposal-v3.md` の「4 タブ + Verification ハブ」案、および本 checkout の現行構成
- 立場: 前回レポート `meta/structure-rereview-third.md` の指摘に対する再評価

## 結論

**v3 は「修正して段階採用」が妥当。** 前回の「5 タブは採用しない」「Search-first Hub + Verified Pathways を優先する」という指摘は、v3 提案にかなり反映されている。特に、discrepancy を Reference に混ぜず Verification として独立させた点は、Verified Pathways の中核を正しく拾っている。

ただし、採用条件は残る。v3 は依然として構造変更が主で、HLD 派生ページの本文品質、症状起点の診断、設定変更の完遂手順、実装乖離の影響判断までは解いていない。600+ ページのサイトで本当に効くのは、トップタブの見た目より「検索・外部流入・任意ページから、検証済みの次ページへ戻れること」である。

また重要な確認事項として、本 checkout の `origin/main` / `chore/codex-v3-third` では v3 実装はまだ確認できない。`docs/.pages` は 14 項目のまま、`docs/verification/` は存在せず、`docs/index.md` も grid cards hub ではなく従来の読み手別リンク一覧である。したがって本レポートは、提案としての v3 への評価と、現行 checkout に対する実装ギャップの指摘を分けて扱う。

## 1. 前回指摘への反映

### Verification 独立タブ

これは前回の Verified Pathways 提案を受けた改善と評価できる。

前回は `_meta/discrepancies.md` を単なる裏方の品質メモではなく、このドキュメントの独自価値として見える場所へ上げるべきだと指摘した。v3 は `verification/` を独立タブにし、`discrepancies.md`、`coverage.md`、`queue.md` を置く設計なので、単なる Reference の一部ではなく「この記述はどこまで裏取り済みか」を読む入口になる。

この判断は正しい。特に現行 corpus では `verification:` frontmatter がすでに広く存在し、`code-verified`、`discrepancy-found`、`hld-only` がページ単位で付いている。これをトップレベルの体験に昇格するのは、プロジェクトの差別化要素を UI に反映する施策である。

ただし、独立タブだけでは Verified Pathways には届かない。必要なのは一覧ではなく、主要クラスタごとに「読む順」「確認コマンド」「CONFIG_DB / YANG / CLI reference」「discrepancy の影響」をつなぐ経路である。`coverage.md` と `queue.md` が統計表に寄りすぎると、評価者向けの品質台帳にはなるが、運用者が問題解決に使う導線にはならない。

### Search-first Hub

v3 提案は `docs/index.md` を grid cards hub にすると明記しており、前回の Search-first Hub 指摘を受けている。Get Started タブを廃止して index に統合する判断も、トップタブの増殖を避ける点では妥当である。

一方、現行 checkout の `docs/index.md` はまだ grid cards ではない。読み手別ガイドへの箇条書き、SONiC の概要、目次リンクが中心で、検索語・症状・作業・検証状態から入る hub にはなっていない。

Search-first Hub と呼べるには、少なくとも次が必要である。

- BGP / VXLAN / VLAN-LAG / Warm Reboot / gNMI / FEC など、検索されやすい入口をカード化する。
- 各カードで Topics、Reference、Library、Verification のどこへ進むかを最初から分ける。
- 「症状から探す」「設定から探す」「仕様名から探す」「実装乖離から探す」を同じトップページで受ける。
- hub 自体を薄い目次ではなく、既存ページを読む順番の編集済み導線にする。

つまり、v3 の設計意図は正しいが、実装判定は `docs/index.md` の本文を見て行うべきで、単にカードが並んだだけでは不足する。

### まだ残る盲点

残る最大の盲点は、`related_topics:` と 4 タブだけで `topics` と HLD area の重複を解けると見ている点である。

`related_topics:` frontmatter は、Tags プラグインより軽く、前回指摘した「機能追加コストの過小評価」を避ける良い代替である。しかし、metadata はリンクの材料であって、読者の問いに答える文章ではない。BGP のページ群を例にすると、読者は「BGP の仕組みを読む」「設定する」「neighbor が上がらない原因を調べる」「HLD と現行実装の差分を見る」を行き来する。これを frontmatter だけで解決するには、自動生成されるリンクブロックの設計と、各ページ本文の役割分担が必要になる。

また、runbooks を独立タブ化しない判断はタブ数削減としては正しいが、Topics 章末の troubleshooting サブページへ統合するだけだと、症状起点の入口が埋もれる可能性がある。Search-first Hub から troubleshooting へ直接入れる設計を併用しないと、前回指摘した「Solve」の価値が弱くなる。

## 2. 構造 vs コンテンツの優先順位

v3 でも作業の中心は構造工事である。

- `docs/.pages` を 4 タブへ変更する。
- `_meta/discrepancies.md` を `verification/` へ移動する。
- `coverage.md` / `queue.md` を生成する。
- `docs/index.md` を hub 化する。
- `guides/` を index へ統合して削除する。
- 既存ページへ `related_topics:` を機械追加する。

これらは必要な整理だが、コンテンツ品質の根本問題は残る。前回レポートで述べた通り、根本問題は構造 40%、コンテンツ 60% である。HLD 翻訳・再構成のままのページは、読者が実機で何を確認し、どの設定を変え、どのリスクを疑うべきかを最後まで案内しない。

特に優先すべき監査対象は次である。

- `verification: hld-only` のページ。現行 checkout ではまだ 42 件ある。
- `verification: discrepancy-found` のページ。現行 checkout では 39 件あり、乖離の運用影響が本文上で十分に判断できるか確認が必要。
- Topics の `operations.md` と `setup.md`。コマンド列、確認結果、rollback、再起動影響まで含むかを見る。
- 主要 5 クラスタ、BGP / VLAN-LAG / FEC-optics / Warm Reboot / gNMI-OpenConfig。ここが薄いまま構造を変えても、実利用での満足度は上がりにくい。

したがって、構造工事の前に大規模な全ページ監査を完了する必要まではないが、少なくとも v3 PR 1 の前後で「主要クラスタだけのコンテンツ監査」を挟むべきである。そうしないと、Verification タブは品質改善の入口ではなく、未消化の課題一覧を見せるだけになる。

## 3. v3 採用可否

判定は **修正して採用**。

採用してよい点:

- トップレベルを 4 タブに抑える。
- Verification を独立タブにする。
- discrepancy を Reference に混ぜない。
- Get Started をタブ化せず、index hub に統合する。
- Tags プラグインを前提にせず、軽い frontmatter で相互誘導する。
- runbooks を空の新設タブとして量産しない。

修正が必要な点:

- `docs/index.md` hub は、単なるカード目次ではなく「検索語・症状・作業・検証状態」から既存ページへ入る編集済み導線にする。
- Verification は統計一覧だけでなく、主要クラスタ別の Verified Pathways を持つ。
- `related_topics:` は追加して終わりではなく、ページ末尾に「読む / 引く / 疑う」のリンクブロックを生成する前提で設計する。
- `guides/` 削除は急がない。index に統合した後、同等以上の導線が確認できてから削除する。
- v3 の構造 PR と並行して、主要クラスタのコンテンツ監査 PR を必ず入れる。

撤回すべきではない。v2 の 5 タブ案より明確に前進しており、前回指摘の多くを吸収している。ただし、これを「完成形の IA」として一括採用すると、また構造だけが先行する。v3 は最終構造ではなく、コンテンツ監査を走らせるための足場として扱うのがよい。

## 4. 推奨次行動

1. まず現行 main に v3 実装が入っているかを確認する。本 checkout では未確認であり、`docs/.pages`、`docs/index.md`、`docs/verification/` に提案との差分が残っている。
2. v3 PR 1 は Verification 独立化に絞る。`discrepancies.md`、`coverage.md`、`queue.md` の生成とリンク切れ検証までを完了条件にする。
3. v3 PR 2 は index hub 化に絞る。カード数を増やすより、BGP / VLAN-LAG / FEC-optics / Warm Reboot / gNMI-OpenConfig の 5 経路を手で編集する。
4. v3 PR 3 は `related_topics:` の機械追加ではなく、まず 5 クラスタで「読む / 引く / 疑う」リンクブロックの仕様を固める。
5. その後に `guides/` 削除と全体 metadata 展開を行う。

この順序なら、構造変更がコンテンツ品質改善を隠すのではなく、逆に未監査ページを発見しやすくする。v3 の価値は、タブを 4 個にすること自体ではなく、検証状態を読者の行動経路に組み込むことにある。
