# Diátaxis 専門家視点の再評価

- 作成日: 2026-05-11
- 対象: main の「5 タブ Diátaxis 構造」再提案
- 参照: `/tmp/re-proposal-summary.md`
- 評価基準: Diátaxis 公式サイトの 4 象限、compass、map、complex hierarchies

## 結論

5 タブ案は、読者の入口を増やし、運用者向け runbook と reference を前面に出す点では有効である。ただし Diátaxis 公式原則への整合度は「部分整合」に留まる。理由は、Diátaxis が documentation type を「読者のその瞬間のニーズ」で分けるのに対し、5 タブ案は `Topics` と `Subsystems` で主題別・実装領域別の分類を上位タブに混ぜているためである。

公式 Diátaxis は 4 つの distinct needs と documentation forms、すなわち tutorials / how-to guides / technical reference / explanation を中心に構造化する。compass では action/cognition と acquisition/application の 2 軸で判定する。map では「Can you teach me to...?」「How do I...?」「What is...?」「Why...?」という問いの違いが、読者期待と執筆スタイルを分けると説明されている。

したがって、厳密に Diátaxis を採用するなら、トップレベルは次の 4 タブにするべきである。

1. Tutorials
2. How-to
3. Reference
4. Explanation

機能ファミリー、HLD 派生、subsystem、persona は、4 象限の内側に置く二次分類として扱う。SONiC の規模では単純な 4 箱だけでは不足するが、Diátaxis 公式の complex hierarchies は、巨大ドキュメントでも 4 種の目的を保ったまま、その内側に topic area や user type の階層を足せるとしている。問題は複雑性そのものではなく、異なる documentation form を同じページや同じ上位タブで混ぜることである。

## 公式 Diátaxis の判定軸

Diátaxis の 4 象限は、ページの主目的を次のように分ける。

| 象限 | 読者状態 | 内容の性質 | 読者の問い | SONiC での典型例 |
|---|---|---|---|---|
| Tutorials | 学習中、技能獲得 | 実用、手順 | 教えてほしい | 30 分ラボ、初回 bring-up、評価チュートリアル |
| How-to guides | 仕事中、技能適用 | 実用、手順 | どうすればよいか | BGP 障害調査、VLAN 追加、Warm reboot 手順 |
| Reference | 仕事中、技能適用 | 認知、事実 | 何であるか | CLI、CONFIG_DB、YANG、field 定義、差分一覧 |
| Explanation | 学習中、技能獲得 | 認知、理解 | なぜそうか | SONiC アーキテクチャ、SWSS/SAI/Redis の概念、HLD の背景 |

重要なのは「初心者向けか上級者向けか」ではない。Tutorials と How-to はどちらも手順を含むが、tutorial は学習体験、how-to は仕事上の目的達成に責務がある。Reference と Explanation はどちらも理論的知識を扱うが、reference は作業中に引く事実、explanation は作業から離れて理解を深める文章である。

## 5 タブ案の整合性チェック

| 5 タブ | 対応する Diátaxis 象限 | 評価 | コメント |
|---|---|---|---|
| Get Started | Tutorials + 一部 Explanation | 条件付きで整合 | 「最初に何を読めばよいか」という入口は妥当。ただし `topics/01-overview/` の概念解説を混ぜすぎると tutorial ではなく explanation になる。 |
| Topics | Explanation + How-to | 不整合 | `concept.md` と `setup.md` / `operations.md` を同じ上位タブに並べるなら、タブ自体が読者の状態を表さない。Diátaxis では目的の異なる form を分けるべき。 |
| Runbooks | How-to guides | 整合 | 症状逆引き、障害調査、変更作業は how-to として強い。SONiC で最も不足している読者導線でもある。 |
| Reference | Reference | 整合 | CLI / CONFIG_DB / YANG / discrepancies は reference として明確。解説や手順を混ぜず、事実と仕様に寄せるべき。 |
| Subsystems | Explanation + Reference + 開発者向け探索 | 不明瞭 | HLD 詳細や実装深掘りは explanation になり得るが、subsystem という分類は Diátaxis の象限ではない。実装領域別 taxonomy であり、上位タブに置くと目的分類を崩す。 |

### Subsystems の位置づけ

`Subsystems` は Diátaxis の第 5 象限ではない。内容が HLD の背景、設計判断、内部構造の理解なら Explanation に属する。API、DB schema、CLI field、SAI object の事実列挙なら Reference に属する。開発者が「この subsystem を直したい」という作業手順なら How-to に属する。

つまり `Subsystems` は content type ではなく subject taxonomy である。採用するなら `Explanation > Subsystems` または `Reference > Subsystems` の下位分類にする。トップタブ化は、Diátaxis というより DITA 的な subject map / component map に近い。

### Topics の混在

`Topics` が `concept.md`、`setup.md`、`operations.md`、`architecture.md`、`internals.md` をまとめる構成は、現実的な章立てとしては分かりやすい。しかし Diátaxis 的には、`concept.md` は Explanation、`setup.md` と `operations.md` は How-to、`architecture.md` と `internals.md` は Explanation または Reference に分かれる。

同じ機能章の中に複数象限のページを持つこと自体は許容できる。問題は、上位タブ名 `Topics` が reader need を示さず、「機能について読みたい」という曖昧な目的に戻してしまう点である。Diátaxis を前面に出すなら、`Topics` は Explanation の別名としてのみ使うべきで、How-to を含めない方がよい。

### Get Started と Topics の境界

`Get Started` は Tutorials として成立する。ただし「SONiC とは」「全体像」「PoC 評価動線」を一つのタブに置く場合、学習手順と概念導入が混ざりやすい。

Diátaxis 的な境界は次の通りである。

- Tutorials: 読者に実際に操作させ、成功体験まで導く。例: VS 起動、管理 IP 設定、VLAN/BGP 最小確認。
- Explanation: SONiC の設計、DB、SAI、SwSS、container 構成を理解させる。例: 「SONiC の設定反映モデルとは何か」。

したがって `Get Started` は `guides/evaluator.md` や beginner path のような tutorial 入口に絞り、概念 overview は Explanation 側に置く方が純度が高い。

## Diátaxis 純粋な 4 タブ案

推奨するトップレベル IA は次である。

```text
Home
  Tutorials
    Beginner
    Evaluator lab
    Developer first contribution
    Operator first maintenance task
  How-to
    Runbooks
    Setup and configuration
    Operations
    Migration and upgrade
    Developer workflows
  Reference
    CLI
    CONFIG_DB
    YANG
    Discrepancies
    Generated indexes
  Explanation
    Concepts
    Architecture
    Subsystems
    Internals
    Topic families
```

既存資産の対応は次の通り。

| 既存資産 | 推奨配置 | 理由 |
|---|---|---|
| `docs/guides/` | Tutorials | beginner / operator / developer / evaluator の reading path は学習導線として再編集できる。 |
| `docs/topics/*/concept.md` | Explanation | 機能ファミリーの理解、背景、用語、関係性を扱う。 |
| `docs/topics/*/setup.md` | How-to | 設定・導入という具体的な作業目的に向く。 |
| `docs/topics/*/operations.md` | How-to | 確認、運用、障害切り分けは仕事中の action。 |
| `docs/topics/*/architecture.md` | Explanation | 設計の理解、内部構造、なぜそうなっているかを扱う。 |
| `docs/topics/*/internals.md` | Explanation または Reference | 背景説明なら Explanation、object / table / daemon の事実列挙なら Reference。 |
| `docs/runbooks/` | How-to | 症状・目的から手順へ進むため、Diátaxis と最も整合する。 |
| `docs/architecture/`、`docs/routing/`、`docs/switching/`、`docs/overlay/`、`docs/acl-qos/`、`docs/system/`、`docs/management/`、`docs/platform/`、`docs/internals/` | Explanation > Subsystems / Topic families | HLD 派生詳細や設計背景の読み物として整理する。事実表は Reference へ分離する。 |
| `docs/reference/` | Reference | CLI / CONFIG_DB / YANG は機械・仕様・フィールドの記述であり、作業中に引く資料。 |
| `docs/_meta/discrepancies.md` 相当 | Reference | 乖離一覧は評価判断に使う事実情報。必要なら Explanation 側から「なぜ乖離が起きるか」へリンクする。 |

## ページ単位の制約

Diátaxis は、単一ページが単一の読者ニーズに応えることを強く求める。厳密には「ページが 1 象限」になるように設計し、別象限の内容はリンクで逃がすのがよい。

現状の `topics` は、章単位では混在しているが、ページ名で `concept` / `setup` / `operations` / `architecture` / `internals` に分かれている。この分割は Diátaxis 化に有利である。一方で、各ページ本文の中で「概念説明、手順、CLI reference、HLD 詳細」を同時に展開している場合は再編集が必要になる。

推奨ルールは次。

- `concept.md`: 背景、用語、なぜ、関係性に限定する。操作手順は置かない。
- `setup.md`: 目的、前提、手順、確認、rollback に限定する。長い設計説明は `concept.md` / `architecture.md` へリンクする。
- `operations.md`: 運用上の判断、確認順、障害時の次アクションに限定する。field 定義は reference へリンクする。
- `architecture.md`: 設計判断、データフロー、責務分界を説明する。CLI 一覧や DB schema 表は reference へリンクする。
- `internals.md`: 読者が「理解したい」のか「引きたい」のかで Explanation / Reference に振り分ける。両方あるならページを割る。

## SONiC への適合性

Diátaxis は SONiC に向いている。理由は、SONiC の読者ニーズが明確に 4 つへ分かれるためである。

- 初学者・評価者は、最小構成を成功させる Tutorials を必要とする。
- 運用者は、障害調査と変更作業の How-to / Runbook を必要とする。
- 実運用者と開発者は、CLI / CONFIG_DB / YANG / discrepancies の Reference を必要とする。
- 開発者、上級運用者、評価者は、SwSS / SAI / Redis / HLD の Explanation を必要とする。

ただし SONiC は巨大で、機能領域、実装コンポーネント、読者ペルソナ、生成リファレンスが交差する。Diátaxis だけで全分類軸を表現しようとすると、`Topics` や `Subsystems` のような第 5 分類を作りたくなる。この場合でも、公式が述べる通り Diátaxis は「4 箱へすべて押し込む図」ではなく、4 つのニーズで内容を構造化する approach と見るべきである。

実務上は、トップは 4 象限、内側に `routing`、`switching`、`platform`、`management`、`internals` などの subject taxonomy を置くのがよい。これなら SONiC の規模と Diátaxis の原則を両立できる。

## Diátaxis 以外の選択肢

Diátaxis 以外を採るなら、次が候補になる。

| フレームワーク | 向く領域 | SONiC での使いどころ | 注意点 |
|---|---|---|---|
| DITA | 大規模・再利用・topic type・条件付き出力 | HLD、CLI、CONFIG_DB、YANG、release ごとの差分管理 | 導入コストが高い。MkDocs 中心の軽量運用とは相性調整が必要。 |
| Information Mapping | 業務手順、policy、process、chunking | Runbook、障害調査、変更手順、運用 SOP | 概念理解や開発者向け HLD 説明には単独では弱い。 |
| IBM task/concept/reference 型 | DITA より軽量な topic typing | `concept/setup/reference` の既存分割と相性がよい | Tutorial と How-to の違いが Diátaxis ほど明確でない。 |
| Persona / journey based IA | 読者別入口 | 初学者、運用者、開発者、評価者の landing page | トップ分類にすると、同じ reference を複数 persona に重複配置しがち。 |

推奨は、上位 IA に Diátaxis、下位分類に subject taxonomy、運用 runbook には Information Mapping の粒度、生成・再利用が必要な reference には DITA 的な metadata を使う混合方式である。トップナビゲーションだけは Diátaxis の 4 象限に寄せ、内部運用で別フレームワークの利点を取り込むのが最も現実的である。

## 推奨判断

main の 5 タブ案をそのまま「Diátaxis 構造」と呼ぶのは避けるべきである。実用 IA としては悪くないが、Diátaxis 公式原則に照らすと `Topics` と `Subsystems` が混在軸であり、第 5 象限のように見える。

採用するなら、名称を「5 入口の実用 IA」とし、Diátaxis 準拠とは言わない方が正確である。Diátaxis 準拠を明示するなら、トップタブは `Tutorials / How-to / Reference / Explanation` の 4 つに戻し、`Runbooks` は How-to の最重要サブセクション、`Subsystems` は Explanation または Reference の subject taxonomy、`Topics` は Explanation 内の機能ファミリーとして扱う。

優先度は次の通り。

1. `Runbooks` を How-to として新設する。これは 5 タブ案でも 4 タブ案でも価値が高い。
2. `Reference` を独立タブとして維持し、CLI / CONFIG_DB / YANG / discrepancies を混ぜずに置く。
3. `Topics` 配下のページを `concept` / `setup` / `operations` ごとに Diátaxis 象限へ明示分類する。
4. `Subsystems` はトップタブにせず、Explanation の下位分類として扱う。
5. `Get Started` は Tutorials に改名するか、少なくとも tutorial 以外の概念解説を Explanation へ逃がす。

## 参照

- Diátaxis: https://diataxis.fr/
- The compass: https://diataxis.fr/compass/
- The map: https://diataxis.fr/map/
- Tutorials and how-to guides: https://diataxis.fr/tutorials-how-to/
- How-to guides: https://diataxis.fr/how-to-guides/
- Reference and explanation: https://diataxis.fr/reference-explanation/
- Explanation: https://diataxis.fr/explanation/
- Diátaxis in complex hierarchies: https://diataxis.fr/complex-hierarchies/
