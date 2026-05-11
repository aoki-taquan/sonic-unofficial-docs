# 構成評価レポート（読み手ペルソナ動線視点）

- 作成日: 2026-05-11
- 評価対象: `docs/` 配下の現行構成、および main メンバ提案「area を archive 化し topics + reference の 2 軸に絞る」案
- 評価視点: 読み手ペルソナによる導線（クリック数 / 迷いポイント / 重複ページの判別コスト）

## 評価サマリ

| 案 | 3 段階評価 | 一言で |
|---|---|---|
| 現状（area 9 系列 + topics 22 章 + reference + guides + categories） | C（迷う） | 同じ機能が `topics/02-bgp/` と `routing/` と `categories/bgp-evpn.md` の 3 か所にあり、どれが正なのか読み手が判断できない。入口が「目次の繰り返し」になっており、第 2 階層まで降りて初めて中身を判別できる |
| 提案（area を archive、topics + reference 2 軸） | B+（マシ、ただし条件付き） | 重複の判断コストは大幅に減る。ただし topics 22 章でカバーされていない HLD 派生ページ（300+ 件）を archive に押し込めると、検索ヒットしても「archive」ラベルで信用されないリスクがある |
| 自己提案（**topics + reference + archive、ただし guides を topics に統合 / categories を廃止 / archive はファセット検索専用と明示**） | A-（推奨） | 2 軸の単純さを保ちながら、archive を「過去ログ」ではなく「裏取り済み HLD ライブラリ」として再定義することで信頼性を維持する |

**推奨**: 提案案を基線に、guides 廃止 + categories 廃止 + archive のラベル戦略明確化を加えた自己提案案を採用。

---

## 1. ペルソナ定義

### P1: 初学者（ネットワークエンジニア、SONiC は未経験）

- ゴール: SONiC が何で、どう設定して、どう動くかの全体像を 1 時間で把握したい
- 典型的な質問:
  - Q1-a. 「SONiC ってそもそも何？ Linux なの？ NOS なの？」
  - Q1-b. 「コンフィグはどこに書くの？ Cisco IOS みたいに running-config があるの？」
  - Q1-c. 「Redis や SAI って何のためにあるの？」
  - Q1-d. 「とりあえず VM で動かしてみたい」

### P2: 運用者（既存 SONiC 環境、トラブル時の引きが多い）

- ゴール: 障害発生時に該当 CLI / CONFIG_DB テーブル / 関連 HLD に最短で辿り着きたい
- 典型的な質問:
  - Q2-a. 「BGP セッションが Established にならない」
  - Q2-b. 「VLAN メンバーを追加する CLI と CONFIG_DB スキーマ」
  - Q2-c. 「FEC エラーが多発する、どのカウンタを見ればいい？」
  - Q2-d. 「`show techsupport` で何が取れるのか」
  - Q2-e. 「設定変更を save してから reload までの順序」

### P3: 開発者（拡張機能追加、orchagent / SAI を読みたい）

- ゴール: 既存実装の責任分界を読み、自分のパッチがどこに入るべきかを判断したい
- 典型的な質問:
  - Q3-a. 「fpmsyncd と orchagent の責任分界」
  - Q3-b. 「新しい CONFIG_DB テーブルを足したい、YANG はどう書く」
  - Q3-c. 「SAI extension を追加する手順」
  - Q3-d. 「PRC や ZMQ producer/consumer のスキーマ」

### P4: 評価者（ラボで bring-up、設定例 + 検証手順が欲しい）

- ゴール: 仮想 SONiC で典型機能を動かし、想定通り動くか確認したい
- 典型的な質問:
  - Q4-a. 「sonic-vs を起動して BGP セッションを上げる手順」
  - Q4-b. 「Dual ToR を 2 台で組む構成例」
  - Q4-c. 「EVPN VXLAN を 2 leaf で組む最小構成」
  - Q4-d. 「ベンチマーク観点での fast-reboot 時間」

### P5: 経営判断者（採用可否、他 NOS との比較）

- ゴール: 採用判断材料（成熟度、ハード対応、運用しやすさ、コミュニティ）を 30 分で把握
- 典型的な質問:
  - Q5-a. 「どのベンダー ASIC が対応している？」
  - Q5-b. 「商用 NOS と比べて何が足りない / 優れる？」
  - Q5-c. 「商用版 SONiC（NVIDIA / Edgecore / Cisco）との違い」

---

## 2. 現状構造でのナビ動線評価

### P1 初学者

- **Q1-a「SONiC って何」**: `index.md` 冒頭 → 「SONiC とは」セクションに 1 段落、その下が「目次」。1 クリックで answer に到達するが、その先「Linux ベース」「コンテナ」「Redis」と単語が並ぶだけで、各単語の解説への lin がない。読み手は次に `architecture/` か `topics/01-overview/` か `topics/20-swss-sai-redis/` か迷う（**3 候補で 1 つも default になっていない**）。実測 2-3 クリックで「正しい入口」に到達するのに 2 回戻る。
- **Q1-b「コンフィグどこに書く」**: 入口は `guides/beginner.md`、そこから `management/sonic-nos-configuration-methods.md` に飛ぶ。さらに CONFIG_DB / YANG / CLI / gNMI の対比が必要だが、ページ間で互いに参照しておらず読み手が自力で行き来する。**ペルソナ完遂までに 4-5 クリック + 2 回の戻り**。
- **Q1-d「VM 動かす」**: `topics/21-lab-vs-developer/` と `architecture/steps-to-bring-up-sonic-vs.md` の 2 か所に解説がある。`guides/evaluator.md` からはどちらにも案内があるが、章立てが違うため**読み比べないと「同じ話か」が分からない**。

最大の問題: **同じ問いに対する正解ページが 3 系列（topics / area / guides）に分散し、読み手が「どれを開けばよいか」を最初の 30 秒で判定できない**。

### P2 運用者

- **Q2-a「BGP が UP しない」**: 入口は guides/operator.md。reading path は 20 個のリンクが番号付きで並ぶ「リスト」で、「BGP が UP しない」という質問に直接答えるエントリがない（`guides/operator.md` の末尾に「不足コンテンツ注記」として『障害別の逆引き導線が不足』と自白している）。読み手は `reference/cli/show-bgp.md` → `reference/cli/config-bgp.md` → `topics/02-bgp/operations.md` → `routing/` 配下のどれかを順に開く。**最低 4 クリック、しかも逆引き辞書がないので「これで全部見たか」が分からない**。
- **Q2-b「VLAN 追加 CLI」**: `reference/cli/config-vlan.md` に直行できれば 2 クリック。ただし入口が `index.md` → `reference/` → `cli/` → `config-vlan.md` で、検索（サイドバー）依存。検索すると `topics/06-l2-vlan-lag/setup.md`、`switching/` 配下、`reference/config-db/vlan.md` も同時にヒットして判別コスト高。
- **Q2-c「FEC エラー多発」**: 該当ページは `platform/fec-flr-support-in-sonic.md` だが、運用者の guides からも topics からも直接リンクされていない。**カテゴリ「FEC」「カウンタ」「光モジュール」を横断するページがない**。

最大の問題: **「症状 → 確認 CLI → 設定変更 → 関連 HLD」の逆引き runbook が存在せず、reference / topics / area の 3 軸を読み手が手動で結合させる必要がある**。

### P3 開発者

- **Q3-a「fpmsyncd と orchagent の責任分界」**: `topics/02-bgp/architecture.md` と `topics/20-swss-sai-redis/architecture.md` 両方を読む必要がある。これは topics 章立てなので比較的良いが、対応する `internals/` 配下、`routing/bgp-loading-optimization-for-sonic.md` も読まないと最新の ring buffer 経路が分からず、結局 area 横断が要る。
- **Q3-b「新 CONFIG_DB テーブル + YANG」**: `reference/config-db/index.md` と `reference/yang/index.md` を行き来。`management/` 配下に分散している YANG の検証フロー HLD を探す必要があるが、入口が無いに等しい。
- **Q3-c「SAI extension 追加」**: `categories/sai-extensions.md` がまさにこの目的のはずだが、入口が `index.md` から 3 階下にあり、しかも `categories` の存在自体が `index.md` のトップに書かれていない（目次の末尾「外」にある）。

最大の問題: **categories と topics と area が併存しており、開発者向けの「責任分界」「拡張手順」が 3 系列のどこに正本があるか不明**。

### P4 評価者

- **Q4-a「sonic-vs で BGP」**: `guides/evaluator.md` から `architecture/steps-to-bring-up-sonic-vs.md` へ。BGP 起動はそこから `topics/02-bgp/setup.md` か `routing/` のどれかへ。setup.md は概念中心で「コマンド列を貼ればコピペで動く」レベルの手順ではない（HLD ベースの再構成のため）。**3 クリックでページに到達はするが、ゴールは達成できない**。
- **Q4-b「Dual ToR 2 台」**: `topics/05-dual-tor/` 章は充実。これは現状構成の数少ない成功例。

最大の問題: **「動くサンプル」が文書全体で意図的に弱い（ペルソナの想定外）。評価者向け Quick-Start ページが 1 枚もない**。

### P5 経営判断者

- **Q5-a「対応 ASIC」**: 該当ページなし。`platform/` 配下の HLD 派生ページに分散。
- **Q5-b「商用との比較」**: スコープ外（CLAUDE.md「8. 既知のスコープ外」に明記）。

最大の問題: **このペルソナはそもそも対象外と宣言されており、構成評価の対象から外して良い**。判断材料として『P5 を切ることを明示する 1 ページ』があると判断者を迷わせなくて済む。

### 現状の構造的問題（ペルソナ横断）

1. **3 系列重複**: topics / area / categories のどれが正本か明示されていない。`topics` は「読み物」で章立て、`area` は「HLD 派生 reference」、`categories` は「横断インデックス」と立て付けが違うが、読み手にこの区別が伝わるラベリングがされていない。
2. **トップ目次の冗長**: `index.md` の目次に area 9 個 + topics + guides + reference + categories の 12 項目が並列に並ぶ。最重要の 2 項目（topics / reference）が他と同じ列で埋もれる。
3. **guides の役割が曖昧**: guides/operator.md は「reference へのリスト」になっており、本文が薄い。runbook でも navigator でもなく中途半端。
4. **categories はトップから 3 段下**: SAI 拡張、SmartSwitch 等の横断的関心は categories ページに集約されているが、入口が遠い。

---

## 3. 提案案（area を archive 化、topics + reference の 2 軸）の評価

### 改善されるケース

- **P1 Q1-a / P1 Q1-b**: 入口候補が「topics / reference」の 2 つに絞られ、`topics/01-overview/` を default 入口にできれば 1 クリックで正解に着く
- **P3 Q3-a**: topics 章が「BGP → 責任分界」を含むので、area `routing/` 配下を archive 化しても辿る経路は短くなる
- **目次の認知負荷**: 12 項目 → 3-4 項目（topics, reference, guides, archive）に減少
- **3 系列重複が解消**: topics が「読み物」、reference が「ピンポイント引き」、archive が「HLD 派生詳細」と立て付けが明確になる

### 改善されないケース

- **P2 Q2-a (BGP が UP しない)**: 逆引き runbook 自体が存在しないので構造を変えても解決しない。runbook ページの新規作成が別途必要
- **P4 Q4-a (BGP コピペ手順)**: 同上。「動くサンプル」の不在は構造問題ではなくコンテンツ問題

### 悪化するケース

- **archive 内検索ヒット時の不信感**: 検索結果に `archive/routing/bgp-loading-optimization-for-sonic.md` が出てきたとき、ユーザは「archive＝古い／非推奨」と直感的に解釈する。実際は code-verified された最新の HLD 派生ページなのに、ラベルで信用を落とす
- **P2 Q2-c (FEC)**: topics でカバーされていない HLD 派生ページ（FEC, link training, sub-port, sFlow など）に到達するには archive を能動的に掘る必要があり、現状より導線が深くなる
- **P3 Q3-c (SAI extension)**: categories ページが消えるなら横断インデックスが失われ、SAI 拡張系 9 ページを横断する手段が消える

### 提案案への総合評価

3 軸 → 2 軸の単純化はペルソナ全体に好影響だが、**「archive」というラベルの心理的負荷**と**categories の処遇**を解決しないと、現状より体感が悪化するペルソナ（特に P2、P3）が出る。

---

## 4. 自己提案案（推奨）

### 案: **`topics` + `reference` + `library` の 3 軸 / `guides` 廃止 / `categories` 廃止**

#### 構成

```
docs/
  index.md                      # 「3 つの入口」を視覚的に対比、ペルソナ別案内は廃止
  topics/                       # 22 章（既存、読み物中心、各章 6 ページ程度）
  reference/                    # CLI / CONFIG_DB / YANG（既存）
  library/                      # ← 現 area 9 系列を全部移設（archive ではなく library と命名）
    routing/  switching/  overlay/  acl-qos/
    system/   management/  platform/  internals/
    architecture/
  runbooks/                     # ← 新設、P2 運用者の逆引き専用（後続バッチで埋める枠だけ作る）
```

#### 主要な変更点

1. **`area` → `library/<area>/` に移動**: 提案案と同じく archive 化するが、**ラベルを `library` に変える**ことで「廃止された資料」ではなく「機能別の HLD ライブラリ」と読ませる。検索ヒット時の信頼を維持
2. **`guides/` を廃止**: 現状の guides は薄いリンク集にすぎず、`topics/01-overview/` と `runbooks/` で代替可能。ペルソナ別案内は `index.md` 1 ページに集約
3. **`categories/` を廃止し、frontmatter `tags:` ベースの mkdocs-material tag plugin に置換**: 11 個の categories ページは手動メンテで陳腐化する。tag ベースなら frontmatter だけで自動生成
4. **`runbooks/` を新設**: 「BGP が上がらない」「FEC 多発」「config save 後の reload 手順」など、症状 → 確認 → 対処 → 関連 HLD の 4 段構成で書く。P2 と P4 の最大の不満を構造的に解決
5. **`index.md` を「3 つの入口」に圧縮**:
   - 「読みたい」 → topics
   - 「引きたい」 → reference + runbooks
   - 「深く調べたい」 → library

#### ペルソナ別効果

| ペルソナ | 現状 | 提案案 | 自己提案案 |
|---|---|---|---|
| P1 初学者 | 3 候補で迷う | topics 一択で OK | topics 一択 + index で「読みたい」明示 |
| P2 運用者 | 逆引きなし | 逆引きなし（構造のみ改善） | runbooks/ で逆引き |
| P3 開発者 | categories 入口遠い | categories 消失 | library + tag で代替、topics の internals 章で責任分界 |
| P4 評価者 | quick-start なし | quick-start なし | runbooks/quick-start-*.md で対処 |
| P5 経営判断者 | 対象外 | 対象外 | 対象外（index に明示） |

### 自己提案案の弱点

- `runbooks/` を新設しても中身を書くバッチが別途必要。構造だけ用意してもコンテンツが追いつかなければ「空の枠」になる
- `library/` 命名がプロジェクトオーナーの直感に合わない可能性。`reference/` と意味が被って見えるリスク
- mkdocs-material の tag plugin は Insiders 版に一部機能が限定される

### 補強案（オプション）

- A. `library/` ではなく `details/`（詳細）にして「topics の裏付け資料」感を強める
- B. `runbooks/` を先行して 5-10 ページだけ用意し、効果を測る
- C. `categories/` は当面残し、`tags:` ベース置換が動いてから廃止する段階移行

---

## 5. 最終推奨

**Phase A（即実施）**:
- `area 9 系列` → `library/` に移設し、`index.md` を「topics / reference / library」の 3 入口に圧縮
- `guides/` を廃止（pricing path は `topics/01-overview/` と `index.md` のペルソナ案内に統合）
- `categories/` は当面残し、tag plugin への置換は Phase B

**Phase B（後続バッチ）**:
- `runbooks/` を新設し、症状逆引き 10 本（BGP up しない、FEC 多発、config save→reload、warm-reboot 影響範囲、Dual ToR フェイルオーバ確認、show techsupport の使い方、syslog 設定、L2 ループ調査、CPU/mem/disk 確認、telemetry 確認）を書く
- frontmatter `tags:` を全ページに付与し、tag plugin で `categories/` を置換、`categories/` 削除

**Phase C（仕上げ）**:
- `index.md` 冒頭に「このドキュメントは何で、何ではないか（P5 経営判断者向け宣言）」を 1 段落
- `topics/01-overview/` を Q1-a の正解ページとして再構成

この 3 段階で、現状の C 評価 → A- 評価に到達可能と判断する。提案案（B+）に対しても明確に上振れする。
