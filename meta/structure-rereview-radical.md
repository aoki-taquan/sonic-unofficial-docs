# 構成再評価 — ラディカル簡素化視点

主エージェントの「5 タブ Diátaxis 案」を、**「もっと圧縮できないか」「ナビ最小が UX に効く」** という視点で再評価する。

## 0. 現状の物量（前提）

| 領域 | ページ数 |
|------|----------|
| `docs/topics/` (22 章) | 143 |
| `docs/<area>/` (architecture, routing, switching, overlay, acl-qos, system, management, platform, internals, categories) | 340 |
| `docs/reference/` (CLI / CONFIG_DB / YANG) | 167 |
| `docs/guides/` | 5 |
| `docs/_meta/` | 1 (discrepancies) |
| **合計** | **656** |

5 タブ案では「Subsystems」タブが 340 ページを吸う最大ブロックになる。**この 340 ページが topics の 143 と本当に別物として読者に提示されるべきか** が最大の論点。

## 1. ラディカル案の比較

### 案 X: 2 タブ案 — "Read" + "Reference"

- **Read**: topics + areas + guides + runbooks すべて読み物として 1 タブ
- **Reference**: CLI / CONFIG_DB / YANG / discrepancies

**長所**:
- Hick's Law 究極：選択肢が 2 つしかない。迷いゼロ
- 「リファレンスを引きに来た」 vs 「読み物を読みに来た」のメンタルモードは実際には 2 つに収斂する（Stripe / Linear / Tailwind の docs もこの粒度）
- 既存 URL 完全保持。`docs/.pages` の nav grouping だけで実装可能
- mkdocs-material の検索が強力で、「2 タブ × 全文検索」で目的達成可能

**短所**:
- Read タブ内で 488 ページが 1 つの sidebar に並ぶ。サブグループ化必須（section index で吸収可能）
- 「運用者の症状逆引き runbook」 vs 「概念説明 topic」 vs 「HLD 派生詳細 area」が同列に並ぶことで、運用者は迷う可能性
- "Get Started" 入口の弱体化（index.md カードで補完）

### 案 Y: 3 タブ案 — "Topics" + "Reference" + "Subsystems"

- **Topics**: 既存 `docs/topics/` + 新 runbooks + guides を併合
- **Reference**: CLI/CONFIG_DB/YANG/discrepancies
- **Subsystems**: 既存 area (architecture, routing, ...) をそのまま

**長所**:
- 5 → 3 で十分簡素化。Get Started は Topics の冒頭 (01-overview) で吸収、Runbooks は Topics の章末「トラブルシュート」セクションで吸収
- 「読み物 (Topics)」 vs 「深掘り (Subsystems)」の区別は、Stripe の "Guides" vs "API" と類似で読者は受け入れやすい
- area ディレクトリ温存で URL 完全不変

**短所**:
- Topics と Subsystems の境界が依然曖昧（読者は「BGP の挙動」が topics/02-bgp と routing/ のどちらに書かれているか分からない）
- 3 タブでも「どこに何が」が直感的でない

### 案 Z: タブ廃止案 — トップ index.md 集約 + sidebar のみ

- `navigation.tabs` 無効化
- `docs/index.md` を「目的別カード 8〜10 枚」のランディングに刷新（"SONiC とは" / "BGP を理解する" / "症状から探す" / "CLI を引く" / "YANG を引く" / "HLD 派生詳細" / "実装と乖離している箇所" / "Verifier ステータス一覧"）
- 二次階層は sidebar (`navigation.sections`) のみ
- 全文検索が主導線

**長所**:
- もっとも minimal。**Stripe docs / Tailwind docs / Linear docs / Astro docs はこの形** に近い（タブを使わず、トップで目的別カード + sidebar）
- 「IA を設計する」コストがゼロ。既存ディレクトリそのまま
- 「タブを増やす vs 減らす」の議論が無くなる
- mkdocs-material の検索 (with suggestions) は十分強力で、知っているキーワードがあれば 2 キー打鍵で着地できる

**短所**:
- 全体俯瞰の手がかりが index.md カードと sidebar しかない（タブの「上位カテゴリ」シグナルがない）
- Material の `navigation.tabs` を捨てるのは見た目の重厚感を失う
- 656 ページが sidebar 1 つに展開されるので `navigation.sections` で折り畳み必須

### 案 W: 全部 topics 統合案

- area ディレクトリを廃止（または symlink で URL 維持）
- 既存 `docs/routing/bgp-evpn-l3vpn.md` を `docs/topics/02-bgp/internals-evpn-l3vpn.md` などに論理的に紐付け
- topics の各章に「内部実装 / HLD 派生詳細」サブセクションを設け、area の 340 ページをそこに吸い込む

**長所**:
- 論理的に最も clean。「BGP を知りたい」 → topics/02-bgp に行けば概要から HLD 派生詳細まですべてある
- 物理 area ディレクトリ廃止で `docs/` 構造が drastically 簡素化

**短所**:
- **既存 340 URL を全部リダイレクトする必要**。mkdocs-redirects プラグイン必須、移行コスト最大
- topics の 22 章に綺麗に分類できない area ページがある（categories, internals, _meta はどの章にも属さない）
- バッチ Writer の運用ルール大幅変更（既存の `docs/<area>/<slug>` 規約が崩壊）
- メリットが「概念的に綺麗」だけで、読者の UX に直接効くかは不明

## 2. mkdocs-material 検索の威力

- material の build-in search は lunr ベース + 日本語形態素対応 (separator) で、3 文字打てば候補が出る
- 既存 656 ページが全文インデックス済み
- **「ナビをどう切るか」より「検索でどう着地するか」が重要** という考え方は妥当
- ただし「SONiC ってそもそも何？」と来た読者は検索キーワードを持っていない。**ランディング（index.md）の質** が検索を使えない読者の生命線

## 3. 「ナビ最小」サイト事例

| サイト | nav 構造 |
|--------|----------|
| Stripe Docs | トップに「Get started / Products / APIs / Support」の 4 ブロック、内側は sidebar のみ |
| Tailwind CSS | タブなし、左 sidebar のみ、トップは grid cards |
| Linear Docs | タブなし、サイドバーのみ |
| Astro Docs | 上部 tabs は「Learn / Reference / Integrations」3 つ |
| Cloudflare Developers | "Products" の 1 タブ + sidebar |
| Kubernetes Docs | 5 タブ (Documentation / Blog / Training / Partners / Community) だが、Docs 内は sidebar |

**傾向**: 技術 docs は **2〜3 タブ + 強力な sidebar + 検索** がデファクト。5 タブはやや多い側。

## 4. 「主エージェントの 5 タブ案」の本質的な問題

1. **Subsystems タブが 340 ページの巨大袋になる**。「読み物」 (topics) と「深掘り」 (subsystems) の境界が読者に伝わらず、結局検索で着地して終わる → タブ分離の意味が薄い
2. **Get Started タブの中身が薄い** (guides 5 + topics/01-overview の 6 ページ程度)。1 タブを割く費用対効果が低い
3. **Runbooks タブを「新設 10〜15 ページ」のために設けるのは過剰**。topics の各章末「トラブルシュート」節 or `docs/topics/00-runbooks/` の 1 ディレクトリで吸収可能
4. **タブが多いほど読者は「正しいタブに居るか」を確認する認知コストを払う**。Diátaxis 4 象限を厳密にやるなら 4、運用者導線を加えて 5、と段階的に増えたが、SONiC のような技術トピック中心ドキュメントには Diátaxis を 1:1 で適用しなくてよい

## 5. 推奨

**案 Y (3 タブ) を基本とし、案 Z (タブ廃止) との折衷を推奨**。

具体的には:

1. **タブは 3 つ — "Topics" / "Reference" / "Subsystems"**
   - "Get Started" は Topics の冒頭 `01-overview` で吸収。タブを割かない
   - "Runbooks" は `docs/topics/00-troubleshooting/` 新設 1 ディレクトリで吸収。タブを割かない
2. **`docs/index.md` を grid cards 化**（案 Z の核を採用）
   - "SONiC とは" / "BGP を理解する" / "症状から逆引き" / "CLI を引く" / "YANG を引く" / "実装と乖離している箇所" / "Verifier 検証済みページ" の 7 カード
   - 検索使えない初回読者の入口を厚くする
3. **既存 URL は完全保持**。物理ディレクトリ不変、`docs/.pages` の nav grouping だけで 3 タブを実装
4. **mkdocs-material `navigation.tabs.sticky` を有効化**して、深い階層からでも 3 タブが常時見える
5. **Tags プラグインで categories を補完**（"discrepancy-found"、"warm-reboot 関連" など横断タグ）

## 6. 主エージェント 5 タブ案を採用すべきか

**No — もっと圧縮できる**。

5 タブ案は「Diátaxis を全タブに対応付けたい」というアカデミックな整合性が透けて見える。実際の読者は:

- 「読み物を読みたい」 → Topics / Subsystems / Get Started のどれを見るか毎回迷う
- 「症状から逆引きしたい」 → タブを増やすより index.md の grid cards から 1 クリック導線のほうが速い
- 「リファレンスを引きたい」 → Reference タブで OK（ここは全案一致）

→ **3 タブで十分。5 タブは安全策で本質的問題（Subsystems と Topics の境界曖昧さ）を解決していない**。

## 7. URL 不変制約は緩めるべきか

**緩めるべきでない**。

- 656 ページに対する mkdocs-redirects のメンテコストは合わない
- 既存 PR 履歴・gh-pages 履歴・外部からのリンクを破壊する
- 案 W (全部 topics 統合) は論理的に綺麗だが、URL 移動コストに見合うリターンが無い
- 「物理ディレクトリ = URL」「論理ナビ = `docs/.pages`」の分離原則を守る。**論理ナビは何度でも作り直せるが、URL は不可逆**

例外: 個別ページの slug rename が必要な場合は mkdocs-redirects でリダイレクト 1 行追加、これは local optimisation として OK。

## 8. 実装順序

1. `docs/index.md` を grid cards 7 枚に書き換え（PR 1 つ）
2. `mkdocs.yml` に `navigation.tabs` + `navigation.tabs.sticky` + `navigation.sections` 追加
3. `docs/.pages` で 3 タブ階層 (Topics / Reference / Subsystems) を定義
4. `docs/topics/00-troubleshooting/` 新設 + 10〜15 ページ追加（既存 backlog から）
5. mkdocs-material Tags プラグイン有効化、discrepancy-found に ⚠️ バッジ

→ 3 PR で完了。URL 変更ゼロ。Reviewer の負荷も最小。

## 9. 結論サマリ

| 項目 | 推奨 |
|------|------|
| タブ数 | **3** (Topics / Reference / Subsystems) |
| 5 タブ案採用 | **No — もっと圧縮** |
| Get Started タブ | 廃止、Topics 冒頭で吸収 |
| Runbooks タブ | 廃止、`docs/topics/00-troubleshooting/` で吸収 |
| URL 移動 | しない、物理ディレクトリ完全保持 |
| index.md | grid cards 7 枚ランディング化 |
| ナビ哲学 | 「タブは最小、sidebar と検索で深掘り、index.md で入口を厚く」 |
