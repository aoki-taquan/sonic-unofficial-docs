# v3 構成の Diátaxis 専門家レビュー

- 作成日: 2026-05-11
- 対象: main の v3「4 タブ + Verification ハブ」提案
- 参照: `/tmp/re-proposal-v3.md`, `meta/structure-rereview-diataxis.md`
- 評価観点: Diátaxis 4 象限、SONiC 非公式ドキュメントの読者ニーズ、Verifier の独自価値

## 結論

v3 は、前回の 5 タブ案より Diátaxis との衝突が小さい。`Get Started` と `Runbooks` を独立タブから外し、上位入口を 4 つに絞った点は改善である。特に `Subsystems` 相当を `Library` にまとめ、`Reference` と `Verification` を分離した判断は、読者にとって「仕様を引く」と「裏取り状況を判断する」を混同しにくい。

ただし、v3 を「厳密な Diátaxis 4 象限」と呼ぶのは正確ではない。v3 の 4 タブは、Diátaxis の 4 象限そのものではなく、SONiC ドキュメント運用に合わせた実用 IA である。`Topics` は Explanation と How-to を含み、`Library` は Explanation の深掘りと一部 Reference 的な実装詳細を含む。`Verification` は Diátaxis の第 5 象限ではなく、content type を横断する quality / trust / evidence のメタ導線である。

推奨は、v3 を採用可とする。ただし説明上は「Diátaxis 準拠」ではなく「Diátaxis をページ分類ルールとして使う SONiC 向け 4 入口 IA」と呼ぶべきである。トップナビは v3 の `Topics / Reference / Verification / Library` を維持し、各ページの執筆・レビュー基準では Diátaxis の `Tutorials / How-to / Reference / Explanation` を使う。この二層構造が、SONiC の規模、生成 Reference、HLD 派生 Library、Verifier の独自価値を最も無理なく両立する。

## v3 タブの Diátaxis 対応

| v3 タブ | 主な読者の問い | Diátaxis 上の位置 | 整合度 | 判定 |
|---|---|---|---|---|
| Topics | 「この機能を理解・設定・運用したい」 | Explanation + How-to、一部 Tutorials | 中 | 機能単位の入口として有効。ただし Diátaxis 象限そのものではない。 |
| Reference | 「仕様、フィールド、コマンドを引きたい」 | Reference | 高 | 最も純粋に Diátaxis と整合する。 |
| Verification | 「どこまで裏取り済みか、乖離は何か」 | Reference + How-to + Explanation を横断する品質メタ情報 | 中 | 独立タブは妥当。ただし新象限ではない。 |
| Library | 「HLD 由来の実装詳細を深く読みたい」 | Explanation 主体、一部 Reference | 中 | 深掘り説明として有効。subject taxonomy であり象限名ではない。 |

前回の 5 タブ案では、`Topics` と `Subsystems` がどちらも主題分類であり、`Runbooks` と `Get Started` が Diátaxis 象限に近い一方で、上位ナビ全体としては分類軸が混在していた。v3 はその混在を完全には解消していないが、タブ数を絞り、用途が明確な `Verification` を独立させたことで、実用上の認知負荷は下がっている。

## Verification の位置づけ

`Verification` は Diátaxis の 4 象限に直接は収まらない。理由は、Diátaxis が「読者がその瞬間に必要としている documentation form」を分類する枠組みであるのに対し、Verification は「その記述をどの程度信頼できるか」「HLD と実装の照合状態はどうか」という evidence layer だからである。

Verification 配下の想定ページは、ページごとに Diátaxis 上の性格が変わる。

| Verification 内の内容 | Diátaxis 上の扱い | コメント |
|---|---|---|
| `discrepancies.md` | Reference | HLD と実装の乖離一覧は、作業中に引く事実表である。 |
| `coverage.md` | Reference | code-verified / hld-only / discrepancy-found の統計・一覧は factual reference である。 |
| `queue.md` | Reference + How-to | 優先度キューは一覧としては Reference、検証作業の進め方を含めるなら How-to になる。 |
| 検証方法・判定基準 | How-to | 「このページをどう検証するか」は作業手順である。 |
| 乖離が起きる背景、HLD と実装の関係 | Explanation | 構造的理由や設計過程を説明するなら Explanation である。 |

したがって、`Verification` を新象限 `Validation` または `Quality` として Diátaxis に追加するのは推奨しない。これは Diátaxis の拡張ではなく、品質保証・証拠・信頼性のための横断ファセットである。新象限と呼ぶと、Diátaxis の「4 つの読者ニーズ」を崩し、他のページも `quality` と `reference` のどちらに置くべきか曖昧になる。

一方で、トップタブとして `Verification` を置くこと自体は妥当である。SONiC 非公式ドキュメントの差別化要因は、単なる HLD 翻訳や整理ではなく、`hld-only`、`code-verified`、`discrepancy-found` を明示している点にある。この情報は、読者の導線上で隠すよりも独立入口にした方がよい。結論として、`Verification` は「Diátaxis の第 5 象限」ではなく、「Diátaxis の外側にある trust hub」として採用するのが正確である。

## Library の位置づけ

`Library` は Diátaxis では主に Explanation に属する。HLD 派生ページ、実装背景、設計意図、daemon 間の責務、Redis DB / SAI / orchagent の関係を読む場であれば、「なぜそうなっているか」「どのように構成されているか」を理解するための説明である。

ただし `Library` には Reference 的なページも混ざり得る。たとえば object、table、field、enum、API、設定キーを事実として列挙するページは Reference である。開発者が「この subsystem を変更するにはどうするか」を知るための手順ページなら How-to である。つまり `Library` は content type ではなく subject taxonomy であり、前回の `Subsystems` と同じ性質を持つ。

v3 で `Library` を採用するなら、次の編集ルールが必要である。

- HLD の設計背景、構成、責務分界は `Library` に置いてよい。
- field 定義、CLI、CONFIG_DB、YANG、一覧表は `Reference` に寄せる。
- 変更手順、検証手順、障害調査手順は `Topics` の `setup` / `operations` / `troubleshooting` に寄せる。
- `Library` ページには関連する `Topics` と `Reference` へのリンクを必ず持たせる。

このルールを守るなら、`Library` は厳密 Diátaxis の Explanation 相当として機能する。ただしタブ名は読者ニーズではなく、SONiC の HLD 資産を束ねる編集上の名前である。

## Topics の位置づけ

`Topics` は v3 の中で最も Diátaxis 純度が低い。`concept.md` は Explanation、`setup.md` と `operations.md` は How-to、`troubleshooting` は How-to / runbook、`architecture.md` と `internals.md` は Explanation または Reference である。章全体を `Topics` と呼ぶと、「理解したい」「設定したい」「運用したい」という異なる読者状態を 1 つのタブにまとめることになる。

それでも SONiC では `Topics` に実用的な価値がある。運用者や評価者は、まず BGP、VXLAN、QoS、Warm Reboot、gNMI のような機能名で入ることが多い。純粋な Diátaxis タブにすると、読者は「BGP の概念は Explanation、設定は How-to、CLI は Reference、HLD は Explanation > Library」と分散して探す必要がある。大規模ネットワーク OS のドキュメントでは、この分散は検索性を下げる可能性がある。

したがって `Topics` は、「Diátaxis 象限」ではなく「feature hub」として扱うべきである。章内のページ単位では Diátaxis を厳密に適用し、上位タブでは読者の主題探索を優先する。この折衷は、公式 Diátaxis の complex hierarchies と矛盾しない。重要なのは、ページ単位で reader need を混ぜないことである。

## 厳密 Diátaxis 4 象限との比較

厳密 Diátaxis のトップ IA は次の形になる。

```text
Tutorials
How-to
Reference
Explanation
```

v3 のトップ IA は次の形である。

```text
Topics
Reference
Verification
Library
```

両者の強みと弱みは明確に異なる。

| 観点 | 厳密 Diátaxis 4 象限 | v3 4 タブ |
|---|---|---|
| Diátaxis 公式整合 | 高い | 中程度 |
| 初学者の学習導線 | Tutorials を明示できる | index.md の Get Started に依存する |
| 運用者の作業導線 | How-to / Runbook を明示できる | Topics 内の setup / operations / troubleshooting に依存する |
| 機能名からの探索 | 弱くなりやすい | 強い |
| 生成 Reference の扱い | 強い | 強い |
| HLD 派生資産の扱い | Explanation 配下で整理 | Library として前面化できる |
| Verifier の独自価値 | Reference 内に埋もれやすい | Verification タブで明確に出せる |
| URL 維持・移行容易性 | 再配置圧が高い | 物理構造維持と相性がよい |

純粋 Diátaxis は、執筆ガバナンスには強い。新規ページを作るときに「これは tutorial か、how-to か、reference か、explanation か」を決めさせるため、ページの責務が明確になる。特に runbook と reference の混同、概念説明と手順の混同を防げる。

一方で SONiC の読者は、常に Diátaxis の問いで入るとは限らない。むしろ「BGP」「VXLAN」「Multi-ASIC」「DASH」「QoS」「Warm Reboot」のような機能・実装領域名で入る場面が多い。さらにこのリポジトリは HLD 由来の大きな Library と、機械生成 Reference と、Verification queue を持つ。これらは純 Diátaxis の 4 タブだけに押し込むと、読者の実際の探索モデルから遠ざかる。

結論として、SONiC には v3 の方が向いている。ただし、v3 を採用する場合でも Diátaxis を捨てるべきではない。上位 IA は v3、ページ設計とレビュー基準は Diátaxis、という役割分担が最も現実的である。

## 新象限 Validation / Quality の妥当性

新象限 `Validation` または `Quality` を Diátaxis に追加する案は、概念的には魅力があるが推奨しない。Diátaxis は、documentation の種類を「読者の目的」と「内容の機能」で分ける。`Quality` は読者の目的ではなく、すべての documentation form に対する属性である。

たとえば、次のすべてに quality state は存在する。

- Tutorial が現行環境で再現できるか。
- How-to が実装で検証済みか。
- Reference がコード生成・手動確認のどちらか。
- Explanation が HLD のみか、コードと照合済みか。

つまり `Quality` は第 5 象限ではなく、各ページに付与される metadata である。`hld-only`、`code-verified`、`discrepancy-found` は、Diátaxis の外側で全象限にかかる verification status と見る方がよい。

ただし、SONiC 非公式ドキュメントでは、この metadata が重要すぎるため、独立タブで可視化する価値がある。これは「IA 上のタブ」と「Diátaxis 上の象限」を分ければ矛盾しない。`Verification` はトップタブとして妥当だが、公式 Diátaxis の拡張としては扱わない、というのが推奨である。

## 採用条件

v3 を採用する場合、次の条件を満たすべきである。

1. v3 を「厳密 Diátaxis」と表現しない。
2. `Verification` を第 5 象限ではなく、trust hub / evidence hub と明記する。
3. `Topics` 内のページ種別を `concept`、`setup`、`operations`、`troubleshooting`、`architecture`、`internals` で維持し、ページ単位の Diátaxis 純度を守る。
4. `Reference` には仕様・事実・フィールド・生成物を置き、長い背景説明や作業手順を混ぜない。
5. `Library` は HLD 深掘り・設計説明を主目的にし、仕様表は `Reference`、作業手順は `Topics` へ逃がす。
6. `related_topics:` または同等の機械的相互リンクで、`Topics`、`Library`、`Reference`、`Verification` の分断を補う。
7. index.md には Tutorials 相当の初回導線を残し、純 Diátaxis で失われる beginner path を補完する。

この条件を満たせば、v3 は Diátaxis の原則を実務上利用しながら、SONiC 固有の探索・検証・HLD 資産を上位 IA に反映できる。

## 推奨判断

採用可。評価は「Diátaxis 部分整合、SONiC 適合性は高い」である。

厳密な Diátaxis 4 象限をトップタブにする案は、理論上は最も整っている。しかし SONiC 非公式ドキュメントの現状では、機能名からの探索、HLD 派生 Library、生成 Reference、Verification status という 4 つの実資産が強く、純粋な `Tutorials / How-to / Reference / Explanation` だけでは利用者の入口が抽象的になりすぎる。

v3 は Diátaxis を上位ナビそのものとしては採用していない。その代わり、上位ナビを `Topics / Reference / Verification / Library` という SONiC 向けの実用入口にし、Diátaxis をページ設計・レビュー・執筆ルールに下ろして使う構成である。この方針は、前回の 5 タブ案より正確で、移行コストも低く、Verifier の独自価値も見せやすい。

最終推奨は次の通り。

- トップタブ: v3 の `Topics / Reference / Verification / Library` を採用する。
- 推奨象限: `Verification` は新象限ではなく、全象限を横断する trust hub とする。
- Diátaxis 適用単位: タブではなくページ単位、特に `topics/*/{concept,setup,operations,troubleshooting,architecture,internals}.md` の責務分離に適用する。
- 呼称: 「Diátaxis 厳密準拠」ではなく「Diátaxis を内部規律にした SONiC 向け 4 タブ IA」とする。

## 参照

- Diátaxis: https://diataxis.fr/
- The compass: https://diataxis.fr/compass/
- The map: https://diataxis.fr/map/
- Tutorials and how-to guides: https://diataxis.fr/tutorials-how-to/
- Reference and explanation: https://diataxis.fr/reference-explanation/
- Diátaxis in complex hierarchies: https://diataxis.fr/complex-hierarchies/
