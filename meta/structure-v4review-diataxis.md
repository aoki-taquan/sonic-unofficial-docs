# v4 構成の Diátaxis 専門家レビュー

- 作成日: 2026-05-11
- 対象: v4「3 タブ + Reference 内 5 カテゴリ」提案
- 参照: `/tmp/re-proposal-v4.md`, `meta/structure-v3review-diataxis.md`
- 評価観点: Diátaxis 4 象限、Runbooks / Verification の分類、SONiC 非公式ドキュメントの実用 IA

## 結論

v4 は採用可。ただし「純粋 Diátaxis 4 象限」ではなく、「Diátaxis をページ単位の編集規律として使う SONiC 向け 3 タブ IA」と明記するべきである。

v4 の `Topics / Reference / サブシステム` は、Diátaxis の `Tutorials / How-to / Reference / Explanation` に 1:1 対応しない。`Topics` は Explanation と How-to を含む feature hub、`Reference` は仕様 Reference を中心に How-to と trust metadata を抱える lookup hub、`サブシステム` は HLD 由来の Explanation hub である。したがって Diátaxis 整合度は「中」。ページ単位では十分に整合させられるが、タブ単位では混合が残る。

それでも v4 は、v3 より実用 IA として安定している。トップタブを 3 つに減らし、`Library` を `サブシステム` に改名し、Verification の孤島化を避け、Runbooks を復活させる判断は妥当である。特に SONiC の読者が「機能名で読む」「仕様を引く」「実装領域を読む」という探索をすることを考えると、純粋な 4 象限タブより v4 の方が利用者の現実に近い。

採用条件は、`Reference` を「仕様だけの象限」と説明しないことである。v4 の `Reference` は Diátaxis の Reference そのものではなく、lookup hub である。CLI / CONFIG_DB / YANG は純粋 Reference、Runbooks は How-to、Verification は Reference と quality metadata の混合として扱う。この呼び分けを守れば、v4 は Diátaxis 違反ではなく、Diátaxis を複雑な階層に適用した実用的な折衷である。

## v4 タブの Diátaxis 対応

| v4 タブ | 主な読者の問い | Diátaxis 上の位置 | 整合度 | 判定 |
|---|---|---|---|---|
| Topics | 「BGP / VXLAN / QoS などの機能を理解し、設定・運用したい」 | Explanation + How-to、一部 Tutorials | 中 | feature hub として有効。象限名ではない。 |
| Reference | 「仕様、症状、検証状態を引きたい」 | Reference + How-to + quality metadata | 中 | lookup hub として有効。ただし純粋 Reference ではない。 |
| サブシステム | 「HLD 由来の実装領域を深く読みたい」 | Explanation 主体、一部 Reference | 中 | 名称改善により用途が明確。content type ではなく subject taxonomy。 |

v4 の最大の注意点は、`Reference` という名前が Diátaxis の Reference 象限より広い意味で使われていることである。Diátaxis では Reference は、事実・仕様・API・設定キー・コマンドのように、説明や手順ではなく情報を正確に引くための文書形式である。一方 v4 の Reference は、CLI / CONFIG_DB / YANG の仕様に加えて、Runbooks と Verification も含む。そのため「Reference = あらゆる lookup」と再定義している。

この再定義は、上位 IA としては許容できる。ただし編集ルールでは、カテゴリごとの Diátaxis 種別を明記する必要がある。

- `reference/cli/`: Reference
- `reference/config-db/`: Reference
- `reference/yang/`: Reference
- `reference/runbooks/`: How-to
- `reference/verification/discrepancies.md`: Reference
- `reference/verification/coverage.md`: Reference
- `reference/verification/queue.md`: Reference または How-to
- 検証手順・判定手順: How-to
- 検証状態の意味や HLD と実装の関係の説明: Explanation

## Runbooks を Reference 内に置くこと

Runbooks は Diátaxis 上は How-to である。読者は「BGP session が上がらない」「VLAN member を追加したい」「FEC error を調べたい」のような具体的な作業・症状を持ち、手順に従って状態を変える、または原因を絞り込む。これは Reference ではない。

したがって、`Runbooks` を「Reference 象限」として説明するなら Diátaxis 違反である。Runbook は事実表ではなく、状況依存の作業手順であり、順序、分岐、前提条件、確認コマンド、復旧判断を持つ。

一方で、Runbooks を `reference/runbooks/` に物理配置すること自体は、必ずしも Diátaxis 違反ではない。Diátaxis は URL 階層名を厳格に縛るものではなく、文書の機能を分ける枠組みである。v4 が `Reference` を「仕様だけ」ではなく「引くための lookup hub」として定義するなら、症状逆引きである Runbooks を同じ上位タブに置く判断は実用上成立する。

ただし採用時には、次のガードレールが必要である。

1. `reference/runbooks/index.md` で「Runbooks は How-to である」と明記する。
2. 各 Runbook は症状、前提、確認手順、分岐、終了条件、関連 Reference を持つ。
3. CLI / CONFIG_DB / YANG の仕様ページに、Runbook 的な長い手順を混ぜない。
4. Runbook から該当する CLI / CONFIG_DB / YANG / Topics / サブシステムへリンクする。

この条件を満たせば、Reference 内 Runbooks は「Diátaxis 違反」ではなく、「lookup hub 内に How-to カテゴリを置く複合 IA」である。

## Verification の象限

Verification は Diátaxis の第 5 象限ではない。`Validation` や `Quality` を新象限として足すのは推奨しない。Diátaxis は読者の目的と文書形式を分類するが、Verification は「その記述がどの程度信頼できるか」「HLD と実装をどこまで照合したか」という trust / evidence layer であり、すべての象限に横断的にかかる属性である。

ただし Verification 配下の個別ページは、Diátaxis の既存 4 象限に分類できる。

| 内容 | 推奨象限 | 理由 |
|---|---|---|
| HLD と実装の乖離一覧 | Reference | 事実を引くための一覧である。 |
| coverage / status 集計 | Reference | code-verified / hld-only / discrepancy-found の状態表である。 |
| verification queue | Reference | 作業対象の一覧として使うなら Reference。 |
| queue の処理手順 | How-to | 検証作業を進める手順なら How-to。 |
| 検証基準、信頼度ラベルの意味 | Explanation | なぜその状態になるかを説明する。 |
| ページを検証する具体手順 | How-to | 作業者が再現するための手順である。 |

つまり v4 の `reference/verification/` は、「Reference である」と一括判定するより、「trust hub であり、主成分は Reference、一部 How-to / Explanation を含む」と説明するのが正確である。v3 のように独立タブにして Verifier の独自価値を前面化する案も妥当だったが、v4 のように Reference 内カテゴリへ下げる判断も成立する。理由は、Verification の内容が現時点では少なく、独立タブにすると孤島化しやすいからである。

## 3 タブ案と純粋 Diátaxis 4 象限の比較

純粋 Diátaxis のトップ IA は次の形である。

```text
Tutorials
How-to
Reference
Explanation
```

v4 のトップ IA は次の形である。

```text
Topics
Reference
サブシステム
```

| 観点 | 純粋 Diátaxis 4 象限 | v4 3 タブ |
|---|---|---|
| 公式 Diátaxis 整合 | 高い | 中 |
| ページ責務の明確さ | 高い | カテゴリ規律が必要 |
| 機能名からの探索 | 弱くなりやすい | 強い |
| 運用者の症状逆引き | How-to / Runbooks として明確 | Reference 内 Runbooks として実用的 |
| 生成 Reference の扱い | 強い | 強い |
| HLD 派生資産の扱い | Explanation に集約 | サブシステムとして見つけやすい |
| Verification の扱い | Reference / metadata に埋もれやすい | Reference 内カテゴリとして適度に露出 |
| タブ数と認知負荷 | 4 タブ | 3 タブで軽い |
| URL 維持・移行容易性 | 再配置圧が高い | 物理移動が少ない |

純粋 Diátaxis は、執筆・レビュー基準としては最も強い。新規ページを作る時に「これは tutorial か、how-to か、reference か、explanation か」を決めるため、手順と仕様、背景説明と一覧表の混在を防げる。

しかし SONiC 非公式ドキュメントでは、読者は Diátaxis の象限名よりも、機能名、仕様種別、実装領域、検証状態で探す可能性が高い。`BGP`、`VXLAN`、`Warm Reboot`、`Multi-ASIC`、`DASH`、`QoS` のような主題探索を、純粋な `Tutorials / How-to / Reference / Explanation` の 4 タブに分散させると、ユーザーはまず「どの文書形式に入るべきか」を判断しなければならない。

v4 はこの問題を避ける。`Topics` で機能横断の物語を読み、`Reference` で仕様・症状・検証状態を引き、`サブシステム` で HLD 由来の実装詳細を読む。これは Diátaxis の純度では劣るが、SONiC の資産構成と読者行動にはより合っている。

## v3 から見た v4 の評価

v3 は `Topics / Reference / Verification / Library` の 4 タブで、Verification を独立 trust hub として扱った。Diátaxis 専門家レビューでは、これは「採用可」だった。v4 はそこから、Verification を Reference 内カテゴリへ下げ、Library を `サブシステム` に改名し、Runbooks を Reference 内カテゴリとして復活させる。

この変更の評価は次の通りである。

- `Library` から `サブシステム` への改名は改善である。日本語読者にとって、HLD 派生の実装領域を読む場所だと分かりやすい。
- Verification 独立タブの廃止は許容できる。Verifier の独自価値は少し弱まるが、現時点の中身の薄さと孤島化リスクを考えると、Reference 内カテゴリの方が安定する。
- Runbooks 復活は改善である。運用者にとって症状逆引きは重要であり、章末 troubleshooting だけでは入口が弱い。
- `Reference` の意味は広がるため、Diátaxis 用語としては不正確になる。この点は文書内で「lookup hub」と説明して補正する必要がある。

総合すると、v4 は v3 より Diátaxis 純度は少し下がるが、実用 IA としては改善している。特にトップタブ数を 3 に抑え、Runbooks と Verification の両方を残す点は、運用者・評価者・実装読者のバランスがよい。

## 採用条件

v4 を採用するなら、次の条件を満たすべきである。

1. v4 を「厳密 Diátaxis 4 象限」と呼ばない。
2. `Reference` を Diátaxis の Reference 象限そのものではなく、lookup hub と説明する。
3. `reference/runbooks/` は How-to と明記する。
4. `reference/verification/` は trust hub と明記し、主成分は Reference、一部 How-to / Explanation を含むと説明する。
5. CLI / CONFIG_DB / YANG には手順や背景説明を混ぜず、仕様 Reference として維持する。
6. Runbooks には関連 CLI / CONFIG_DB / YANG / Topics / サブシステムへのリンクを必ず持たせる。
7. サブシステムは Explanation 主体とし、仕様表は Reference、手順は Topics または Runbooks へ逃がす。
8. index.md に Tutorials 相当の初回導線を残し、v4 で消える純粋 Tutorial タブを補完する。
9. ページ frontmatter またはレビュー基準で、各ページの `diataxis:` 種別を管理する。

## 推奨判断

採用可。評価は「Diátaxis 部分整合、SONiC 適合性は高い」である。

推奨トップ IA は v4 の `Topics / Reference / サブシステム`。ただし推奨象限は次のように扱う。

- `Topics`: Explanation + How-to の feature hub
- `Reference > CLI / CONFIG_DB / YANG`: Reference
- `Reference > Runbooks`: How-to
- `Reference > Verification`: trust hub。主成分は Reference、一部 How-to / Explanation
- `サブシステム`: Explanation 主体の subject taxonomy

Runbooks を Reference 内に置くことは、Diátaxis の文書形式として見れば不純である。しかし、v4 が Reference を「仕様象限」ではなく「引くための上位入口」と定義するなら、実用上は許容できる。重要なのは、Runbook ページ自体を How-to として書くことであり、URL 階層名ではない。

Verification は Diátaxis の新象限ではない。Reference でない場合の正体は、全象限にかかる trust / evidence metadata である。ページ化された乖離一覧や coverage は Reference、検証手順は How-to、検証状態の意味は Explanation として扱うのが正しい。

最終的に、純粋 Diátaxis 4 象限は理論的には最も整っているが、このリポジトリの現状には抽象的すぎる。SONiC 非公式ドキュメントは、機能名探索、生成 Reference、HLD 派生サブシステム、Verification status という固有資産を持つ。v4 はそれらを 3 タブに収めつつ、ページ単位で Diátaxis を使える。したがって、v4 を採用し、Diátaxis はトップナビ名ではなく編集・レビュー基準として適用するのが最も現実的である。

## 参照

- Diátaxis: https://diataxis.fr/
- The compass: https://diataxis.fr/compass/
- The map: https://diataxis.fr/map/
- Tutorials and how-to guides: https://diataxis.fr/tutorials-how-to/
- Reference and explanation: https://diataxis.fr/reference-explanation/
- Diátaxis in complex hierarchies: https://diataxis.fr/complex-hierarchies/
