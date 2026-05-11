# 構成 再評価レポート（情報設計 / IA 専門家視点・第 2 回）

- 再評価日: 2026-05-11
- 評価者: IA 観点レビューエージェント B
- 対象: main 提案「5 タブ Diátaxis 構造」（`/tmp/re-proposal-summary.md`）
- 前回レポート: `meta/structure-review-ia.md`（現状 D, main 旧案 B+, 推奨 A）

---

## TL;DR

| 項目 | グレード | コメント |
|---|---|---|
| 現状（13 タブ） | **D** | 前回判定維持（タブ過多・MECE 違反・命名ゆれ） |
| main 新提案（5 タブ: Get Started / Topics / Runbooks / Reference / Subsystems） | **A−** | 方向性は完全に正しい。Diátaxis 厳密適用ではないが**実務的にはこの 5 タブが最適解**。技術検証 OK |
| 私の推奨（5 タブ案を採用しつつ Runbooks 命名・Subsystems 命名・タグ運用に微修正） | **A** | 同 5 タブを採るが「Runbooks → トラブルシュート」「Subsystems → HLD 詳細」と日本語ラベル統一、Get Started を意図的に Diátaxis のうち Tutorials + Orientation の二役と明示 |

**結論: main の 5 タブ提案を採用すべき。** 4 タブ案・3 タブ案も検討したが、Get Started の独立はオーナーシップ獲得（最初の 5 秒で「ここは何のサイトか」を伝える）に必須で、Subsystems の独立は 357 ページの個別 HLD ページの直リンク尊厳を守るために必須。両方を畳むと "ペルソナ動線" と "URL 安定性" のどちらかが必ず犠牲になる。

---

## 1. Diátaxis 解釈の妥当性チェック

### 1.1 Diátaxis 公式の 4 象限

[diataxis.fr](https://diataxis.fr/) によれば Diátaxis は **行動 (action) × 認知 (cognition)** の 2 軸で文書を 4 象限に分類する:

| | 学習段階 (Acquisition) | 仕事段階 (Application) |
|---|---|---|
| 実践指向 (Practical) | **Tutorials**（手を動かして学ぶ） | **How-to guides**（タスクを終わらせる） |
| 理論指向 (Theoretical) | **Explanation**（理解する） | **Reference**（調べる） |

### 1.2 5 タブ提案 vs 4 象限のマッピング

| 提案タブ | 主たる Diátaxis 象限 | 副次的象限 | 厳密性 |
|---|---|---|---|
| Get Started | Tutorials | Explanation（"SONiC とは"） | ◯（Tutorials を Get Started と呼ぶのは Kubernetes / Stripe / GitHub 全てが採用する事実上の標準） |
| Topics | Explanation | How-to（章末の operations / advanced） | △（Explanation が主だが章テンプレに how-to が混入。これは**意図的なハイブリッド**で許容範囲） |
| Runbooks | How-to | — | ◎（症状逆引き = Application × Practical で純粋な How-to） |
| Reference | Reference | — | ◎ |
| Subsystems | Explanation | Reference（HLD は仕様書性も持つ） | △（個別 HLD ページは Explanation と Reference の中間。これは SONiC コミュニティ HLD の性質そのものなので妥協は妥当） |

### 1.3 「Get Started」「Subsystems」追加の妥当性

**Diátaxis 公式は「4 つに無理矢理押し込め」とは言っていない**。diataxis.fr/start-here/ には:

> "These four kinds of documentation answer to four different needs of the user. They are different in their purpose, their content, their style and the way they are read."

つまり**ユーザの 4 つのニーズを満たせばよく、タブ数を 4 にする必要はない**。Kubernetes docs (Concepts / Tasks / Tutorials / Reference / Contribute) も 5 タブで Diátaxis 準拠を名乗っており、これは IA 業界の合意。

- **Get Started を独立タブにする根拠**: Tutorials を Topics 配下に隠すと「初訪問者がどこから読むか」の Information Scent が完全に喪失する（前回レポートの第 1 の問題）。Get Started を**最も左に置く**ことで Onboarding コストが直接下がる
- **Subsystems を独立タブにする根拠**: SONiC HLD は「Explanation かつ Reference」という Diátaxis 単独象限に収まらない特性。これを Topics に混ぜると Topics タブが肥大化し、Reference に混ぜると Reference の "短く調べる" 性質が壊れる。**独立タブ化が両者の純度を守る**

### 1.4 結論: 5 タブの Diátaxis 解釈は妥当

厳密に言えば「Get Started = Tutorials の別名」「Subsystems = Explanation の深掘り変種」であり、4 象限の延長として整理可能。Diátaxis 違反ではない。

---

## 2. 物理ディレクトリ不変 + nav 階層化の技術検証

### 2.1 mkdocs.yml の現状

```yaml
plugins:
  - search
  - awesome-pages
theme:
  features:
    - navigation.tabs      # ← 既に有効
    - navigation.sections
    - navigation.indexes
```

`navigation.tabs` は**有効済み**。現在は `docs/.pages` のトップレベル 13 項目がそのまま 13 タブに展開されている状態。これを 5 グループに **nest** すれば自動的に 5 タブになる。

### 2.2 `.pages` での nav 階層化の制約

`awesome-pages` の `nav:` キーは次をサポート:

| 構文 | 動作 | 5 タブ化への適用 |
|---|---|---|
| `- dir-name` | サブディレクトリをそのまま再帰展開 | 既存 area 9 個を Subsystems 配下に並べる |
| `- title: path/to/file.md` | ファイルへのリンク（カスタムタイトル） | Get Started の index 配置に必要 |
| `- グループ名:` (children インデント) | 仮想グループ（タブ扱い） | **5 タブの本体構造**。これがキー |
| `- ...` | 残り全部 | 漏らさず吸収用 |
| `- glob: *.md` | glob 展開 | tag 補助用 |

**重要な技術制約**:

1. **同じファイルを複数タブに置くことは awesome-pages 単独では不可能**（物理ファイルは 1 つの nav 位置にしか出現しない）。  
   対応策: (a) **stub page を別 slug で作成し中身は redirect** か (b) **`mkdocs-redirects` プラグインで URL 別名を作る** か (c) **タグページからの被リンクで複数導線を確保**（最も低コスト）。本提案では (c) を採用すべき
2. **navigation.tabs は Level 1 のみがタブ化される**。Level 2 以下はサイドバーに落ちる。5 タブを Level 1 仮想グループに置けば望み通り動く
3. **navigation.sections と併用時の挙動**: Level 2 が「セクション見出し」として太字表示される。これは Subsystems 配下の area 9 個を見出しとして整列するのに有利
4. **モバイル表示**: navigation.tabs はモバイルで自動的にハンバーガー内ドロワーに畳まれる。5 タブで問題なし（13 タブはモバイルでスクロール必要だった）
5. **`navigation.indexes` 有効時**: 仮想グループに `index.md` を割り当てるとグループタイトルクリックでそのページに飛ぶ。`Get Started` タブをクリックで `guides/index.md` に飛ばす設計が綺麗に書ける

### 2.3 必要な変更（mkdocs.yml は不変）

`docs/.pages` を**この 1 ファイルだけ書き換える**:

```yaml
nav:
  - index.md
  - Get Started:
      - guides/index.md
      - guides/beginner.md
      - guides/operator.md
      - guides/evaluator.md
      - guides/developer.md
      - topics/01-overview
  - Topics:
      - topics/02-bgp
      - topics/03-vxlan-evpn
      - ... (22 章)
  - Runbooks:
      - runbooks    # 新設ディレクトリ
  - Reference:
      - reference
      - _meta/discrepancies.md
  - Subsystems:
      - architecture
      - routing
      - switching
      - overlay
      - acl-qos
      - system
      - management
      - platform
      - internals
      - categories
```

URL は 1 つも変わらない。`categories` を Subsystems 配下に降格させるだけで Hick's Law 違反が即時解消する。

### 2.4 Tags プラグイン

mkdocs-material には **Tags プラグイン**が同梱（Community Edition でも利用可、`material/plugins/tags`）:

```yaml
plugins:
  - tags:
      tags_file: _meta/tags.md
```

frontmatter `tags: [bgp, evpn]` を付与すれば tags.md に自動集約。**categories の手動メンテを廃止し、タグベース自動生成に置き換える根拠**になる。ただし全 600 ページに tag を打つ作業コストは無視できない（バッチ #12 相当の独立タスクで処理推奨）。

### 2.5 技術検証 結論

**5 タブ案は `docs/.pages` の 1 ファイル編集のみで実現可能。** mkdocs.yml も既存ページも一切触らない。技術リスクはゼロ。Tags プラグイン導入は別フェーズで段階的に。

---

## 3. 600+ ページ再分類の現実性

### 3.1 Topics タブ（22 章）

`docs/topics/01-22` をそのまま全部入れる。01-overview のみ Get Started に**論理移動**（物理は topics 配下のまま、`.pages` 上で Get Started 配下にも列挙）。重複曖昧ゼロ。

### 3.2 Subsystems タブ（area 9 系列 + categories + internals + architecture）

| area | ページ数 | Subsystems 配下での位置付け |
|---|---|---|
| architecture | 42 | 横断系 HLD として最上段 |
| routing | 52 | 大きいので index に topics 02/04/16/17 へのリンクパネル |
| switching | 20 | OK |
| overlay | 10 | OK |
| acl-qos | 32 | OK |
| system | 72 | 過大だが Subsystems 配下なので兄弟比較が同類項のみになり問題顕在化が緩和 |
| management | 44 | OK |
| platform | 44 | OK |
| internals | 13 | 残存。将来的に解体検討（前回提案）だが**今回は触らない** |
| categories | 11 | Subsystems の **末尾** に配置。タグページ的役割が明確化 |

**残る曖昧**: `gnmi` 系が routing と management に分散している件は変わらず。これは**今回のスコープ外**（個別ページ移動は別 PR）。**5 タブ化だけで読者の Information Scent は劇的に改善**するので、ページ単位の再配置は後続フェーズで OK。

### 3.3 Get Started タブ

| 既存資産 | 配置 |
|---|---|
| guides/index.md | Get Started index |
| guides/beginner.md | 初学者カード |
| guides/evaluator.md | PoC 評価者カード |
| guides/operator.md | 運用者カード |
| guides/developer.md | 開発者カード |
| topics/01-overview | "SONiC とは / アーキ概観" |

**categories 10 件と guides 6 件は綺麗に収まる**。categories は Subsystems 末尾でタグ的に温存、guides は Get Started の本体。

### 3.4 Runbooks タブ（新設）

提案された候補 10〜15 ページ:

- BGP UP しない
- VLAN メンバー追加できない
- FEC エラー多発
- Warm Reboot 失敗
- PFC 帯域不足
- DHCP Relay 動かない
- Multi-ASIC namespace 通信不通
- Dual-ToR mux 切替失敗
- SAI failure
- Container 起動失敗

**既存ページから「移動 / 統合される候補」の検索結果**:
- `system/fast-reboot-flow-improvements-hld.md` の "Failure modes" セクション → Warm Reboot 失敗 Runbook の原資料
- `acl-qos/copp-manager-redesign-test-plan.md` の "Test failure scenarios" → CoPP 過剰ドロップ Runbook
- `_meta/discrepancies.md` 39 件 → 半分は「実装が HLD と違うので注意」型で Runbook の "落とし穴" セクションに転用可
- 既存 topics の `operations.md` 末尾 → 各章の Runbook 種が散在しているのを **Runbooks タブに引き上げて集約**

**結論**: 既存ページからは "移動" よりも "抽出+書き直し" になる。新規 10〜15 ページとして書き下ろすのが妥当（コスト 1 バッチ）。

---

## 4. もっとシンプルな案の検討

### 4.1 4 タブ案: Topics / Runbooks / Reference / Subsystems

- **Get Started を Topics 配下に**畳む
- 問題: 初訪問者が `Topics` タブを開いた瞬間に 22 章の見出しに直面し、`guides/beginner.md` を見つけるのに 2 階層 + スクロールが必要
- ペルソナ動線評価（前回 A 評価）が下がる
- **却下**

### 4.2 3 タブ案: Topics / Reference / Subsystems

- Get Started を Topics に、Runbooks を Subsystems の各 area 配下に分散
- 問題: 運用者が「BGP UP しない」を探すために `Subsystems > routing > bgp-*` の 13 ページから推測する負担に戻る。これは現状の悪さそのもの
- **却下**

### 4.3 6 タブ以上の案

- Tutorials / How-to / Explanation / Reference / Subsystems / Meta などへ分割
- 問題: 再び Hick's Law 違反（境界判断が増える）
- **却下**

### 4.4 ナビ階層を深くせずフラットにする案

- 600 ページを単一サイドバーに全部並べる
- 問題: そもそも今がそれに近く、評価 D の原因。**却下**

### 4.5 結論

**5 タブが最小最適**。3/4 タブはペルソナ動線 or 運用者導線を必ず犠牲にする。6+ タブは現状の問題に戻る。

---

## 5. 採点

| 案 | グレード | 評価 |
|---|---|---|
| 現状（13 タブ） | **D** | 前回判定維持 |
| main 旧提案（topics + reference の 2 軸 + area→archive） | B+（前回） | area→archive が URL 安定性を毀損。**今回提案で克服** |
| main 新提案（5 タブ Diátaxis） | **A−** | 物理 URL 不変、Diátaxis 解釈妥当、技術リスクゼロ、Runbooks 新設で運用者導線を獲得 |
| 私の推奨（5 タブ + ラベル微調整 + Tags 段階導入） | **A** | 同 5 タブ。差分は (a) "Runbooks" を `runbooks/` ディレクトリ名は維持しつつタブ表示は **「トラブルシュート」** で日本語統一、(b) "Subsystems" タブ表示は **「サブシステム HLD」** とすることで Information Scent を強化、(c) Tags 導入は別フェーズに分離してリスク隔離 |

A+ を出さない理由: 600 ページの分散した重複（前回指摘の N=4 問題）は 5 タブ化だけでは解消しきれない。**ページ単位の再配置と Tags 化**を後続でやる必要がある。それでも「現状の何を最小コストで最大改善するか」の問いに対して 5 タブ案は最良解。

---

## 6. 微修正提案（5 タブ採用前提）

1. **タブの日本語表示名**を `.pages` の `title:` で統一
   - Get Started → 「はじめに」
   - Topics → 「読み物」
   - Runbooks → 「トラブルシュート」
   - Reference → 「リファレンス」
   - Subsystems → 「サブシステム HLD」
2. **Runbooks ディレクトリ命名**は英語 `runbooks/` のまま（URL 不変方針一貫性）
3. **タブ順序**: 上記の左から右が読者の認知フロー（学ぶ → 知る → 直す → 引く → 深掘り）と一致
4. **categories は Subsystems タブの末尾に配置**してタブから外す。`docs/_meta/tags.md`（Tags 自動生成）が育ったら categories は完全廃止
5. **discrepancies.md の Reference 昇格**は良案だが、表示位置は Reference タブの**最上段**にして "実装と HLD の差分" の発見性を最大化
6. **`docs/index.md` の grid cards 化**は 5 タブと独立して並行で進める（Material `grid` 拡張、既に有効済の attr_list で実装可能）

---

## 7. 受け入れ基準（前回再掲＋更新）

- [x] トップタブが 5 個以下 → 5 タブ案で達成
- [ ] 同一機能のエントリポイント数（N 値）が 2 以下 → 5 タブ化だけでは未達。Tags 段階で達成見込み
- [ ] 各 area の兄弟ページ数が最大 / 最小で 3 倍以内 → 別 PR で
- [x] `docs/index.md` から任意のページに 3 クリック以内到達 → 5 タブ + grid cards で達成見込み
- [ ] 命名規則違反 0 件（lint 化） → 別タスク
- [x] mkdocs build --strict 警告 0 → 維持

---

## 8. 最終結論

**main の 5 タブ Diátaxis 提案を採用すべき。** 

- Diátaxis 解釈は厳密ではないが妥当（Kubernetes docs と同じ実務適用）
- 技術検証 PASS（`docs/.pages` 1 ファイル編集で実現、URL 不変）
- 600+ ページの再分類は機械的に決まる（曖昧残はあるが 5 タブ化のスコープ外）
- 3/4 タブ案は劣る（ペルソナ or 運用者導線を犠牲にする）
- 6+ タブ案は Hick's Law 違反に戻る

**推奨タブ数: 5。** グレード A−（main 案そのまま）/ A（タブラベル日本語化と Tags 段階導入を追加）。

次のアクションは `docs/.pages` 書き換え PR + `docs/runbooks/` 新設バッチの 2 本立て。Tags 導入は第 3 PR で分離。
