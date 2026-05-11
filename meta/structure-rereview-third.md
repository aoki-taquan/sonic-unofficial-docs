# 構成再評価レポート（Codex 第三者視点）

- 作成日: 2026-05-11
- 評価対象: main の「5 タブ Diátaxis 構造」再提案
- 立場: main の自己評価・既存 reviewer の結論から独立した第三者評価

## 結論

**5 タブ案は、そのまま採用しない。** ただし「トップタブを 5 個前後に絞る」「Runbooks を入口として作る」「HLD 詳細を Subsystems として一段下げる」という方向は採用価値がある。

採用を止める理由は、5 タブという見た目の整理が、実際には次の 4 つをまだ解いていないため。

1. `topics` / HLD area / `categories` / `reference` の重複は、タブ名を変えても検索結果とページ本文では残る。
2. `docs/.pages` だけで 600+ ページの意味的ナビを制御し続けると、PR 増加に比例して手動 nav が運用負債になる。
3. Tags プラグインや badge 自動表示は、現行 `mkdocs.yml` には入っていない機能で、提案内の実装難度が過小評価されている。
4. 根本問題は構造だけではなく、ページ本文が HLD 再構成のまま「運用で使える答え」になっていない点にある。

推奨は **「Search-first Hub + Verified Pathways」**。物理ディレクトリと URL は維持し、トップ nav の整理より先に、検索・症状・検証状態を束ねる小さな hub を作る。詳細は後述する。

## 1. 現状俯瞰

### ページ数

依頼にあった `find docs -name "*.md" | wc -l` は、この実行環境では `find` コマンド自体が存在せず失敗した。そのため同等の `rg --files docs -g '*.md' | wc -l` で確認した。

結果は **657 Markdown ページ**。

主要セクション別の内訳:

| セクション | ページ数 | 位置づけ |
|---|---:|---|
| `docs/reference/` | 167 | CLI / CONFIG_DB / YANG |
| `docs/topics/` | 143 | 22 章の読み物 |
| `docs/system/` | 72 | HLD 派生詳細 |
| `docs/routing/` | 52 | HLD 派生詳細 |
| `docs/management/` | 44 | HLD 派生詳細 |
| `docs/platform/` | 44 | HLD 派生詳細 |
| `docs/architecture/` | 42 | HLD 派生詳細 |
| `docs/acl-qos/` | 32 | HLD 派生詳細 |
| `docs/switching/` | 20 | HLD 派生詳細 |
| `docs/internals/` | 13 | HLD 派生詳細 |
| `docs/categories/` | 11 | 手動横断カテゴリ |
| `docs/overlay/` | 10 | HLD 派生詳細 |
| `docs/guides/` | 5 | 読者別導線 |
| `docs/_meta/` | 1 | discrepancy 一覧 |

HLD 系 area、つまり `architecture/routing/switching/overlay/acl-qos/system/management/platform/internals` は合計 **329 ページ**。この 329 ページをどう見せるかが、構造評価の中心になる。

### 既存 5 系統の重複度

ここでの 5 系統は、現状の主要な情報軸として次を指す。

- `topics/`
- HLD area: `architecture/routing/switching/overlay/acl-qos/system/management/platform/internals`
- `reference/`
- `categories/`
- `_meta/`

重複はかなり高い。特に BGP、EVPN/VXLAN、Dual-ToR、Reboot、gNMI/OpenConfig、DASH、SAI failure、FEC などは、最低でも `topics`、area、`reference`、`categories` の 3-4 系統に顔を出す。

ただし、これは単純な「同じ内容の重複」ではない。役割が違う重複も混ざっている。

- `topics`: 読み順を作る章立て。
- HLD area: HLD 単位の詳細と検証ステータス。
- `reference`: CLI / CONFIG_DB / YANG の字引。
- `categories`: 手動で作られた横断テーマ索引。
- `_meta/discrepancies.md`: 実装乖離の価値ある一覧。

問題は、**役割の違いが UI 上で明示されず、検索結果でも区別できない**こと。重複そのものより、「どれが最初に読む正本か」が分からないことが本質。

### `mkdocs.yml` と `docs/.pages`

`mkdocs.yml` はすでに `navigation.tabs` を有効化している。つまり main 提案の「tabs を有効化」は新規施策ではなく、現状でも有効。

プラグインは `search` と `awesome-pages` のみ。提案にある Material Tags プラグイン、redirect、badge 自動表示に相当する仕組みは現状入っていない。

`docs/.pages` は現在:

```yaml
nav:
  - index.md
  - guides
  - topics
  - architecture
  - routing
  - switching
  - overlay
  - acl-qos
  - system
  - management
  - platform
  - internals
  - reference
  - categories
```

現状の第 1 階層は 14 項目。5 タブ案はこの過密を下げる点では妥当だが、`docs/.pages` に巨大な論理階層を押し込む設計になるなら、今度は `.pages` が単一障害点になる。

## 2. 5 タブ案の盲点

### 盲点 1: Tags / badge 自動表示が「低コスト施策」ではない

提案には「mkdocs-material Tags プラグインで categories を補完」「discrepancy-found ページに badge を自動表示」とあるが、現状の `mkdocs.yml` には tags プラグインがない。frontmatter にも `tags:` や `kind:` は標準化されていない。主に存在するのは `area:` と `verification:`。

つまり tags 施策は、設定を 1 行足せば終わる話ではない。

- 657 ページへタグ語彙を付ける分類作業が必要。
- `categories/` 11 ページをタグへ置換するなら、既存カテゴリとの対応表が必要。
- `verification: discrepancy-found` を badge 化するにはテンプレート、theme override、または markdown preprocessor が必要。
- Material の tags 機能はバージョンや edition の差で挙動が変わる可能性があり、`mkdocs build --strict` だけではユーザが期待する UI まで保証できない。

5 タブ案は「物理ディレクトリ完全維持なので低コスト」と言うが、tags と badge を成果物の中核に置くなら、実装・タグ設計・CI 検証のコストを別に見積もるべき。

### 盲点 2: クリック感はタブ数だけでは決まらない

5 タブにすれば最初の選択肢は減る。しかし実際のユーザは、タブをクリックしたあとに次の問題へ当たる。

例:

- `Topics` を開くと、番号付き 22 章が並ぶ。BGP や VXLAN は分かるが、FEC、SAI failure、show techsupport、gNOI、P4RT などの入口は即座に判断しづらい。
- `Subsystems` を開くと、結局 `architecture/routing/system/management/platform/...` の area 群に戻る。現状の 9 area が 1 タブ下に移動するだけで、area 間の境界問題は残る。
- `Runbooks` は 10-15 ページ新設予定だが、最初の PR では空に近い枠になりやすい。ユーザは期待してクリックし、薄いページに失望する可能性がある。
- `Reference` は 167 ページあり、CLI / CONFIG_DB / YANG を知らない読者には深い。症状起点の運用者はここだけでは完遂できない。

つまり 5 タブは「入口の見た目」を改善するが、「クリック後に正しいページへ着く匂い」は別問題。現行の `guides/operator.md` が自分で認めている通り、運用者には「BGP が上がらない」「VLAN が疎通しない」から入る逆引きが必要で、これはタブではなくページ本文の品質問題。

### 盲点 3: `.pages` 中心の nav は PR 増加で壊れやすい

現状は各 area の `.pages` が 10-72 ページの手動順序を持っている。これはすでに大きい。5 タブ案ではさらに root `docs/.pages` で論理タブを作り、各ディレクトリの `.pages` で内部順を維持することになる。

この運用には次のリスクがある。

- 新規ページ追加時に、どのタブのどの順序へ入れるかを writer が判断できない。
- 複数 PR が同時に `.pages` を触ると conflict が増える。
- `runbooks/` を増やすほど「症状別」「機能別」「重要度順」のどれで並べるかが揺れる。
- categories を tags へ寄せる途中で、手動カテゴリとタグ一覧が二重管理になる。

`.pages` は「局所的な並び順」には強いが、657 ページの意味的 IA を管理する台帳としては弱い。5 タブ案は URL を守る代わりに、nav の複雑さを `.pages` に移しているだけの面がある。

## 3. 独自代替案: Search-first Hub + Verified Pathways

既存案との違いは、**物理ディレクトリやタブを主戦場にしない**こと。600+ ページのサイトで、ユーザは最終的に nav だけでなく検索・リンク・外部流入で入ってくる。ならば「どのディレクトリに置くか」より、「入ってきたページから次にどこへ進むか」を設計する。

### 提案構造

トップタブは最小限にする。

1. **Start**: SONiC 概要、対象読者、最短の読み順。
2. **Solve**: 症状・作業・確認観点から入る hub。runbook そのものではなく、最初は gateway として作る。
3. **Learn**: 既存 `topics/`。
4. **Look Up**: 既存 `reference/` と `_meta/discrepancies.md`。
5. **Deep Dive**: HLD area 329 ページと categories。

main の 5 タブと似て見えるが、肝は `Solve` の作り方である。`Runbooks` をいきなり 10-15 本の新規本文として作らない。まず **症状別 hub** を作り、既存ページを組み合わせた「検証済み経路」を示す。

例:

```text
Solve / BGP セッションが上がらない
  1. まず見る CLI: show bgp, show ip route, show interfaces
  2. CONFIG_DB: BGP_NEIGHBOR, DEVICE_METADATA
  3. 読む順: topics/02-bgp/operations → reference/cli/show-bgp → routing/bgp-...
  4. 注意: discrepancy-found 関連がある場合は明示
  5. 実装差分: _meta/discrepancies.md の該当箇所
```

この方式なら、初期 PR で薄い runbook 本文を量産しなくてよい。既存 657 ページを活かし、足りないところだけが明確になる。

### 既存 600+ ページの活用方法

- HLD area 329 ページは `Deep Dive` として維持する。降格ではなく「出典と検証の層」として扱う。
- `topics/` 143 ページは `Learn` として維持する。章番号の硬直性は後回し。
- `reference/` 167 ページは `Look Up` の主役にする。
- `categories/` 11 ページは廃止せず、当面は `Deep Dive` 内の「手動 curated collections」として残す。タグ自動化が実証できた後に置換する。
- `_meta/discrepancies.md` は `Look Up` から必ず見える場所へ上げる。これはこのプロジェクトの差別化要素。

### 目から鱗の提案: すべての主要ページに「次に開く 3 枚」を機械生成する

構造変更より効果が大きいのは、各ページ末尾の固定ブロックを自動生成することだと考える。

各ページに次の 3 リンクを置く。

1. **読む**: 対応する `topics` ページ。
2. **引く**: 対応する CLI / CONFIG_DB / YANG reference。
3. **疑う**: `discrepancy-found` または検証ステータス一覧。

例: `routing/bgp-loading-optimization-for-sonic.md` なら、末尾に `topics/02-bgp/architecture.md`、`reference/cli/show-bgp.md`、`reference/config-db/bgp-neighbor.md`、関連 discrepancy を出す。

これは navigation を上から再設計するのではなく、**どこから入っても同じ導線へ復帰できる mesh を作る**案である。600+ ページのサイトでは、トップページの美しさよりこの復帰導線のほうが実利用で効く。

実装は frontmatter に `topic: bgp`、`cli_refs: [...]`、`config_db_refs: [...]` のような軽い metadata を足し、CI でリンク切れを検出する。いきなり全ページではなく、BGP / Reboot / gNMI / FEC / Dual-ToR の 5 クラスタから始めればよい。

## 4. 本当の問題は構造かコンテンツか

結論: **根本問題は構造 40%、コンテンツ 60%。**

構造が悪いのは事実。14 タブは多いし、`topics` と area と `categories` の役割説明も弱い。だが、構造を 5 タブにしても、ページ本文が HLD 翻訳・HLD 要約のままなら「ユーザの仕事」は終わらない。

特に弱いのは次の 3 種類のコンテンツ。

1. **症状起点の診断**: BGP が上がらない、FEC が増える、Warm Reboot が失敗する、VLAN が疎通しない、container が起動しない、など。
2. **設定変更の一連手順**: 確認、変更、保存、rollback、再起動影響、検証コマンド。
3. **現行実装との差分の読み方**: `discrepancy-found` は価値が高いが、今は読む人が自分で影響判断する必要がある。

優先すべき作業は、構造変更そのものより次。

1. `Solve` hub を 5 本だけ作る。BGP、VLAN/LAG、FEC/optics、Warm Reboot、gNMI/OpenConfig。
2. 各 hub から CLI / CONFIG_DB / topics / HLD / discrepancy へつなぐ。
3. 既存ページ末尾に「読む / 引く / 疑う」の 3 リンクを入れる metadata 設計を始める。
4. その結果として足りない本文だけを runbook 化する。
5. 最後に top nav を 5 タブへ整える。

この順序なら、空白埋めの Runbooks を作らず、既存 657 ページを即座に活用できる。

## 5. main 5 タブ案への採否

評価は **条件付き B-**。

採用してよい部分:

- 14 項目のトップ nav を 5 個前後へ落とす。
- `Runbooks` 相当の運用者入口を作る。
- HLD area を `Subsystems` として一段下げる。
- `docs/index.md` を入口カード化する。

採用しない部分:

- Runbooks を最初から 10-15 本の新規ページとして埋める。
- Tags プラグインを categories 置換の前提にする。
- discrepancy badge 自動化を低コスト施策として扱う。
- `.pages` だけで全 IA を管理する。
- 5 タブを揃えるために、薄いページや空の枠を作る。

## 6. 推奨ロードマップ

### Phase 1: 構造変更なしで hub を作る

- `docs/solve/` または `docs/runbooks/` を作る場合でも、最初は「本文型 runbook」ではなく「既存ページへの診断 gateway」にする。
- 5 本だけに絞る: BGP、VLAN/LAG、FEC/optics、Warm Reboot、gNMI/OpenConfig。
- `docs/_meta/discrepancies.md` を Reference または Look Up から明示リンクする。

### Phase 2: ページ間 mesh を作る

- frontmatter に `topic_group`、`cli_refs`、`config_db_refs`、`related_hlds` を段階的に追加。
- 各ページ末尾に「読む / 引く / 疑う」リンクを生成する。
- CI で metadata のリンク切れを検出する。

### Phase 3: top nav を 5 タブへ整理する

- `Start`
- `Solve`
- `Learn`
- `Look Up`
- `Deep Dive`

この時点で 5 タブ化する。先にタブだけ変えるより、クリック後の満足度が高い。

### Phase 4: Tags 自動化は実証後に採用

- 既存 `categories/` を残したまま、数クラスタで tags を試す。
- `mkdocs build --strict` だけでなく、生成ページと検索結果の見え方を確認する。
- 問題なければ `categories/` を tags へ移す。

## 7. 最終判断

main の 5 タブ案は、現状の「入口が多すぎる」問題には効く。しかし、このプロジェクトの本当の価値は、HLD を大量に集めたことではなく、実装差分と reference を横断して読めることにある。5 タブ案はその価値をまだ十分に前面化できていない。

したがって、最初にやるべきは「美しい 5 タブ」ではなく、**ユーザの問いから既存資産へ最短で戻す hub と mesh** である。構造はその後に整えればよい。
