# 構成 v3 再々評価 — ラディカル簡素化視点

主エージェントが 6 視点評価を経て収束させた **v3「4 タブ + Verification ハブ」** を、ラディカル簡素化視点 (案 C / 前回 3 タブ推奨) から再評価する。

前提資料:
- `/tmp/re-proposal-v3.md` (v3 提案本文)
- `meta/structure-rereview-radical.md` (前回 3 タブ案レポート)

---

## 0. v3 の要点（再掲）

- **4 タブ**: 📖 Topics / 📚 Reference / ⚠️ Verification / 🔧 Library
- v2 (5 タブ) から Get Started タブ廃止 (index.md 統合)、Runbooks タブ廃止 (Topics 章末統合)
- **discrepancy を Reference に混ぜず、Verification 専用タブで昇格**
- Tags プラグイン取り下げ、`related_topics:` frontmatter で Topics ↔ Library 機械相互誘導
- URL 完全維持、`docs/.pages` の論理ナビのみ変更
- 移行 3 PR

前回ラディカル案との差分:
- 前回案: 3 タブ (Topics / Reference / Subsystems)、Verification は無し or Reference 内
- v3: 4 タブ、Verification を独立タブで昇格、Subsystems を Library にリネーム

---

## 1. v3 は十分シンプルか

### 1.1 「4 タブも多い、3 で十分」と主張する根拠

| 根拠 | 詳細 |
|------|------|
| Hick's Law | 4 → 3 で選択肢が 25% 減。タブ間の「自分は今どこ？」迷いが減る |
| デファクト事例 | Stripe 4 ブロック / Tailwind 0 タブ / Astro 3 タブ / Cloudflare 1 タブ。**4 タブは技術 docs 上位 25% タイの多さ** |
| Verification の物量 | 想定 3 ページ (discrepancies / coverage / queue)。**1 タブを 3 ページに割く費用対効果が低い** |
| 認知コスト | 「Topics 読み物」「Library 詳細読み物」の境界は依然曖昧で、4 タブにしてもこの本質問題は未解決 |
| メンテコスト | タブを増やすほど `.pages` 階層・index.md カード・mkdocs.yml 設定の整合性メンテが増える |

### 1.2 Verification を独立タブ化するメリット vs デメリット

**メリット**:
- Verifier ロールの独自価値 (hld-only / code-verified / discrepancy-found) を**プロジェクトの顔として打ち出せる**
- 「公式 HLD と実装の乖離を裏取りする」という本プロジェクトのユニーク・セリング・ポイントが上部ナビに常時露出
- D 視点 (反論評価) の「discrepancy を Reference に混ぜるな」指摘に正面回答
- discrepancy-found ページが 40 件 + 今後増加、coverage.md の俯瞰ビューと合わせれば実質「読み物」として成立

**デメリット**:
- **1 タブあたりのページ数が極端に偏る** (Topics 143 / Reference 166 / Library 327 / Verification 3)。タブの粒度が不均衡
- 初回読者の 95% は Verification タブをクリックしない (運用者・実装者が中心読者で、品質メタ情報は二次関心)
- 同じ情報は index.md の「⚠️ 実装と乖離している箇所」カード 1 枚で到達可能 → タブを 1 つ割く必然性が弱い
- mkdocs-material のタブはモバイルでドロワー化されるため、4 タブと 3 タブで実装複雑度は実質同じだが、**読者の認知地図は確実に肥大化**

**判定**: Verification の昇格は方向性として正しいが、**「独立タブ」は過剰**。`index.md` 冒頭の Hub セクション + Reference タブ末尾の `reference/verification/` セクションで同等の価値が出せる。

---

## 2. 3 タブ案 (Topics / Reference / Library) 再提示

### 2.1 構造

```yaml
nav:
  - index.md                          # Hub: grid cards 7-8 枚
  - "📖 Topics": topics
  - "📚 Reference":
      - reference/cli
      - reference/config-db
      - reference/yang
      - reference/verification        # ← discrepancies / coverage / queue をここに
  - "🔧 Library":
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

### 2.2 Verification の扱い — 3 つの選択肢比較

| 案 | 位置 | 長所 | 短所 |
|----|------|------|------|
| **A: index.md Hub 内** | `docs/index.md` の grid card 2 枚 ("⚠️ 実装と乖離している箇所" / "✅ Verifier 検証済みカバレッジ") | 1 クリック導線、タブ消費ゼロ | 深い階層から戻る導線が弱い |
| **B: Reference タブ末尾** | `docs/reference/verification/{discrepancies,coverage,queue}.md` | 「仕様引き」と「仕様と実装の乖離」が隣接 = 論理的に妥当、タブ消費ゼロ | D 視点「Reference に混ぜるな」と衝突 |
| **C: Library 末尾** | `docs/library/verification/` | HLD 派生詳細と並ぶ | discrepancy は HLD 派生でなくメタ情報、ミスマッチ |

**推奨**: **A + B 併用**。index.md Hub に常時露出するカード 2 枚を置き、実体は Reference 末尾の `reference/verification/` に置く。「Reference に混ぜるな」の指摘は **discrepancy を CLI / YANG ページに混ぜるな** と解釈し、独立セクション化すれば指摘は満たせる。タブを増やす理由にはならない。

### 2.3 検索中心で nav を最小化する考え方

- mkdocs-material 検索は 656 ページ全文インデックス済 + 日本語 separator 対応。**3 文字で着地可能**
- ナビは「**検索キーワードを持っていない初回読者の入口**」と割り切り、最小化
- 詳細は sidebar (`navigation.sections`) で折り畳み、タブは大カテゴリのみ
- `index.md` を grid cards 化することで、検索を使えない読者も 1 クリックで主要導線に到達

---

## 3. v3 採用の妥当性

### 3.1 4 タブで「足し算終了」と言えるか

**部分的に Yes、本質的に No**。

| 軸 | 評価 |
|----|------|
| v2 (5 タブ) からの削減 | Get Started 廃止 + Runbooks 廃止 = 2 タブ削減。**確実に前進** |
| v2 ⇄ v3 の品質改善 | discrepancy の扱い改善、Tags 廃止で実装コスト減、`related_topics:` で機械相互誘導。**設計品質は向上** |
| ラディカル視点での最小性 | **4 タブはまだ過剰**。Verification の 3 ページに専用タブを与える費用対効果が悪い |
| 「足し算終了」宣言の正当性 | Verification タブを足したことで「引き算しきっていない」状態 |

v3 は v2 から大きく改善されたが、**「タブを増やしてでも独自価値を見せたい」というプロダクト視点が混ざっており、UX 最小化視点では未到達**。

### 3.2 v3 を採用するなら何が残るか / 何が削れたか

**削れたもの (v2 比)**:
- Get Started タブ (中身薄かった)
- Runbooks タブ (新設 10-15 ページのためにタブを割く過剰さ)
- Tags プラグイン (実装コスト 3-4 PR の虚偽申告)

**残ったもの (依然解決していない問題)**:
- **Topics ⇔ Library の境界曖昧さ** — v3 は `related_topics:` frontmatter で誘導するが、frontmatter は読者から不可視。読者は依然「BGP の挙動は topics/02-bgp と library/routing/ のどっち？」で迷う
- **Verification タブの偏った粒度** — 3 ページに 1 タブ
- **タブの装飾性** — 絵文字 4 つ並ぶことで「最小性」ではなく「整理感の演出」が前面に出る

---

## 4. 結論

### 4.1 v3 採用すべきか

**条件付き Yes、最良案ではない**。

- v3 は v2 (5 タブ) より明確に良い。Verification 昇格・Tags 廃止・Runbooks 統合は正解
- ただし**「もっと圧縮できる」**: Verification を index.md Hub + Reference 末尾セクションに格納すれば 3 タブで完結
- v3 の最大の正当化は「Verifier ロールの独自価値を上部ナビに常時露出させたい」というプロダクト戦略。これを優先するなら v3、UX 最小化を優先するなら 3 タブ

### 4.2 最良の構成 (再提案)

```
タブ数: 3 (📖 Topics / 📚 Reference / 🔧 Library)
Verification: index.md Hub カード 2 枚 + reference/verification/ セクション
Hub: docs/index.md を grid cards 8 枚化
  - "SONiC とは"
  - "BGP を理解する" (Topics 入口)
  - "症状から逆引き" (Topics 末尾 troubleshooting)
  - "CLI を引く" (Reference)
  - "YANG を引く" (Reference)
  - "HLD 派生詳細" (Library)
  - "⚠️ 実装と乖離している箇所" (Reference/verification)
  - "✅ Verifier 検証済みカバレッジ" (Reference/verification)
URL: 完全維持 (docs/_meta/discrepancies → docs/reference/verification/discrepancies へリダイレクト 1 行)
related_topics: frontmatter で Topics ↔ Library 双方向誘導 (v3 のこの部分は採用)
mkdocs-material: navigation.tabs.sticky 有効化
移行: 3 PR (Hub 刷新 / .pages 3 タブ化 / frontmatter 追加)
```

### 4.3 比較サマリ

| 軸 | v2 (5 タブ) | v3 (4 タブ) | 推奨 (3 タブ) |
|----|-------------|-------------|----------------|
| タブ数 | 5 | 4 | **3** |
| Hick's Law | 弱 | 中 | **強** |
| Verification 独自価値露出 | 弱 (Reference 内) | **強 (独立タブ)** | 中 (Hub カード + Reference 末尾) |
| 実装コスト | 大 (Tags 含む) | 中 | **小** |
| Topics ⇔ Library 境界 | 未解決 | 未解決 (frontmatter で誤魔化し) | 未解決 (本質問題、3 タブでも解けない) |
| 移行 PR 数 | 5+ | 3 | **3** |
| デファクト追従度 (技術 docs) | 低 | 中 | **高** |

---

## 5. 結論ワンライナー

**v3 は採用可だが、Verification 独立タブを取り下げた 3 タブ案がより最適**。Verification の独自価値は「タブ」ではなく「index.md Hub の常時露出 + Reference 末尾の独立セクション」で同等以上に表現でき、Hick's Law とデファクト技術 docs 慣行により忠実。v3 で「足し算終了」と宣言するより、もう一段引き算した 3 タブを最終形にすべき。
