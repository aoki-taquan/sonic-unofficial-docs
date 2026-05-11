# 構成評価レポート（情報設計 / IA 専門家視点）

- 評価日: 2026-05-11
- 評価者: IA 観点レビューエージェント
- 対象: `docs/` 配下 13 セクション、約 600 ページ（HLD/Reference/Topics/Guides 含む）
- 目的: オーナー指摘「構成がわかりづらい」の原因究明と再設計案提示

---

## TL;DR

| 項目 | 評価 |
|---|---|
| 現状構造 | **D（要再設計）** |
| main 提案案（topics + reference の 2 軸） | **B+（方向性は正しいが粒度配慮が必要）** |
| 推奨案（後述「3 軸 + Reference + Meta」） | **A**（情報設計上のベストプラクティス充足） |

主要問題は **(1) area 階層と topics 階層の二重化による MECE 違反**、**(2) navigation.tabs 上の 13 タブによる Hick's Law 違反**、**(3) categories と topics の役割重複**の 3 点。

---

## 1. 現状の構造分析

### 1.1 ナビゲーション階層と認知負荷

```
Level 0: サイトトップ
Level 1: 13 タブ (guides / topics / architecture / routing / switching /
                overlay / acl-qos / system / management / platform /
                internals / reference / categories)
Level 2: 各 area の index + 個別ページ
Level 3: topics/<chapter>/<phase>.md （6〜7 ページ）
Level 4: reference/cli/<group>/<cmd>.md
```

- **Hick's Law**: タブ数 13 は閾値（7±2）を大きく超過。初訪問ユーザの最初の選択に 2〜3 秒の遅延を生む（NN/g 計測値で 5 タブ→10 タブで意思決定時間 ~1.6 倍）。
- 最大階層深度: 4。これ自体は許容範囲（kernel docs も 4〜5）。問題は**幅**であり、深さではない。
- index.md「目次」セクション (Level 1 リスト 11 個) + サイドバー 13 個 + categories ページ 11 個 で **同じ情報が 3 度提示されている**。

### 1.2 セクション粒度のばらつき（MECE 違反の症状）

| area | ページ数 | 評価 |
|---|---|---|
| system | 72 | 過大（reboot/telemetry/secure-boot/kdump/platform-monitor が同居） |
| routing | 52 | 過大（BGP / DHCP-relay / MPLS / SRv6 / management-vrf 混在） |
| management | 44 | 過大（gNMI / gNOI / TACACS / AAA / CLI / YANG が混在） |
| platform | 44 | 過大 |
| architecture | 42 | 「アーキテクチャ全般」という曖昧バケット |
| acl-qos | 32 | 中 |
| switching | 20 | 中 |
| internals | 13 | 小 |
| overlay | 10 | 小（DASH/VXLAN/NVGRE/Dual-ToR） |

`internals=13` と `system=72` は **同じ Level 1** にあるが粒度が 5 倍違う。これは IA の **Sibling Comparability**（兄弟ノードは同じスケールであるべき）原則に違反。

### 1.3 ラベリングの一貫性

問題点:
- `acl-qos`（kebab + 複合語）vs `overlay`（単数語）vs `internals`（複数語） → 命名規則不統一
- `architecture`（全般）vs `internals`（実装内部）→ 意味的境界が曖昧。読者は「BGP の内部実装は routing? internals? architecture?」を即決できない
- `topics` = 「読み物」というラベル（.pages タイトル）と URL `/topics/` の不一致
- `categories` = 「横断カテゴリ」と `topics` = 「横断章」のメンタルモデルが衝突

### 1.4 カード/グルーピング適切度

`docs/index.md` の「目次」リストは **flat な 11 項目の bullet list**。カードメタファ（Material grid cards）が未活用で、読み手のタスク（学ぶ / 設定する / 調べる）にひも付かない。

---

## 2. 情報重複の機械的検出

### 2.1 area × topics の対応マッピング

`topics/` の 22 章はすべて、既存 area ページの再構成。同一機能が **必ず 2 箇所以上** に存在する構造的二重化。

**重複ペア例（5 つ）**:

| # | topic 章 | 対応 area ページ | 重複度 |
|---|---|---|---|
| 1 | `topics/02-bgp/architecture.md` | `routing/bgp-loading-optimization-for-sonic.md`, `routing/bgp-prefix-independent-convergence-architecture-document.md`, `routing/bgp-suppress-announcements-of-routes-not-installed-in-hw.md` 他 12 件 | bgpd→zebra→fpmsyncd→orchagent の解説が 4 箇所で繰り返し |
| 2 | `topics/03-vxlan-evpn/architecture.md` | `overlay/vxlan-sonic.md`, `routing/evpn-vxlan-hld.md`, `routing/evpn-vxlan-multihoming.md` | VXLAN encap 図が 3 箇所 |
| 3 | `topics/05-dual-tor/architecture.md` | `overlay/active-active-dual-tor.md`, `overlay/active-standby-dual-tor.md` + `categories/dual-tor.md`（12 ページ集約） | 同じ Dual-ToR が 4 箇所のエントリポイント |
| 4 | `topics/11-reboot/architecture.md` | `system/fast-reboot-flow-improvements-hld.md`, `system/sonic-express-reboot-hld-spec.md`, `system/multi-asic-warm-reboot.md`, `system/sonic-warm-reboot.md`, `system/smart-switch-reboot-high-level-design.md` + `categories/reboot.md`（12 集約） | warm/fast/express/cold の比較が 3 階層に分散 |
| 5 | `topics/07-acl-copp-mirror/architecture.md` | `acl-qos/acl-in-sonic.md`, `acl-qos/acl-support-in-sonic.md`, `acl-qos/copp-manager-redesign-test-plan.md`, `acl-qos/sonic-port-mirroring-hld.md` 他 8 件 + `categories` 該当なし | ACL テーブル種別の説明が 5 箇所 |

### 2.2 重複の N 値（同一機能が記述されている階層数）

- **BGP**: `topics/02-bgp/` + `routing/bgp-*` (13 ページ) + `categories/bgp-evpn.md` + `reference/{cli,config-db,yang}/bgp-*` (12+) → **N = 4 階層**
- **DASH**: `topics/13-dash-smartswitch/` + `overlay/sonic-dash-hld.md` + `acl-qos/dash-acl-tags.md` + `categories/dash.md` → **N = 4**
- **VXLAN/EVPN**: 上記同様 N = 4
- **Reboot**: `topics/11-reboot/` + `system/*reboot*` + `categories/reboot.md` + `reference/cli/reboot-fast-warm.md` → **N = 4**
- **gNMI**: `topics/10-gnmi-openconfig/` + `management/gnmi-*` (5) + `routing/gnmi-subscription-for-yang-data.md` + `categories/gnmi-openconfig.md` (57 集約) → **N = 4**

平均的に主要機能は **4 箇所のエントリポイント**を持つ。これは **Information Scent**（リンクテキストから内容を予測する能力）を強く損なう（「routing/ から BGP に行くべきか、topics/02-bgp から行くべきかが判断できない」）。

### 2.3 ファイル名重複の検出

- `bfd-hw-offload.md` と `bfd-hw-offload-for-bgp-session.md`（routing/ 内）
- `kdump.md` と `kdump-remote-ssh.md`（system/）
- `acl-in-sonic.md` と `acl-support-in-sonic.md`（acl-qos/）
- `sfputil-...-by-page-and-offs.md` と `sfputil-...-by-page-and-offset.md`（platform/、明らかな名称ゆれ）
- `critical-resource-monitoring.md` と `critical-resource-monitoring-in-sonic.md`（system/）

これらは Indexer 段で正規化されていない slug。**Canonical URL** が定まらず、内部リンクの安定性も損なう。

---

## 3. IA ベストプラクティスとの比較

| 原則 | 現状評価 | 主な違反箇所 |
|---|---|---|
| **MECE** | ✗ | topics × area の二重化、routing と management に gNMI 関連が散在 |
| **Progressive Disclosure** | △ | guides → topics → area → reference の段階は意図されているが Level 1 が並列に晒されている |
| **Hick's Law** | ✗ | 13 タブ |
| **Information Scent** | ✗ | 「BGP の話は routing? topics? internals?」が予測不能 |
| **Sibling Comparability** | ✗ | system 72 vs internals 13 |
| **Pogo-sticking 回避** | △ | categories ページは集約として機能するが、area との重複でユーザを行き来させる |
| **URL persistency** | △ | area→topics 整理時のリダイレクト戦略が不明確 |
| **DAMA labeling**（同義語の統合） | ✗ | architecture/internals/system の境界 |

---

## 4. ベンチマーク：参考にすべき OSS ドキュサイト

| サイト | 採用すべきパターン |
|---|---|
| **Kubernetes docs (kubernetes.io/docs)** | **Personas + Task-orientation の 5 タブ構造** (Concepts / Tasks / Tutorials / Reference / Contribute)。Diátaxis フレームワークに準拠。本プロジェクトの guides + topics + reference の意図に完全に合致。13 タブを **5 タブに圧縮できる根拠**。 |
| **Linux kernel docs (docs.kernel.org)** | **Audience 別トップ** (Users / Admins / Tools / Developers / Internals / Subsystems)。Subsystems は機能別の **flat な巨大ツリー** で深い階層は採らない。本プロジェクトの area を「subsystem 群」として 1 タブ配下に格納する根拠。 |
| **FRR docs (docs.frrouting.org)** | **Daemon 別の単一ナビゲーション**（bgpd / ospfd / staticd…）。シンプル過ぎるが、reference 系の **コマンド階層をプロトコル別に切る発想**は CLI Reference 整理に流用可能。 |
| **公式 SONiC docs (sonic-net.github.io)** | 反面教師。HLD が flat に並ぶだけで Information Scent ゼロ。**「公式の弱点を埋める」が本プロジェクトの存在意義**であることを再確認。 |
| **Cumulus Linux docs (NVIDIA Networking)** | **Feature × Version の 2 軸タブ + 各機能ページ内の「Overview / Configure / Verify / Troubleshoot」固定セクション**。本プロジェクト topics 章の `concept/architecture/setup/operations/internals/advanced` 6 分割と思想一致。**この章テンプレートは強み**なので維持すべき。 |

**結論**: Diátaxis (Tutorials / How-to / Reference / Explanation) + Personas tab を主構造に。area は subsystem として 1 タブに収容。

---

## 5. 提案

### 5.1 現状評価: **D**

理由: タブ数過多、area×topics 二重化、ラベリング不統一、命名ゆれの 4 重苦。コンテンツの質は高いがナビゲーションが価値を毀損している。

### 5.2 main 提案（area→archive、topics+reference の 2 軸）の評価: **B+**

良い点:
- 重複の主因（topics × area）を解消する方向性は正しい
- Hick's Law を満たす（タブ 2〜3 個）
- topics 章 6 分割テンプレートを主役にすることで Cumulus 型の強みを活かせる

懸念点:
- **area を archive にすると 357 ページの個別 HLD ページが「降格」表記となり、検索・直リンクの正当性が落ちる**（外部から該当 URL が引用されている可能性）
- topics 22 章でカバーされていない HLD ページ（NAT, Wake-on-LAN, banner-messages 等）が **archive へ「捨てられる」誤解** を招く
- guides セクションの位置付けが不明（消す？topics に統合？）

### 5.3 推奨代替案: **Diátaxis + Subsystem の 4 タブ構造**

```
Level 1 (タブ): 5 つに絞る
  1. はじめに (Get Started)       ← 旧 guides + index
       - 初学者 / 評価者 / 運用者 / 開発者
  2. 読み物 (Topics)              ← 旧 topics の 22 章をそのまま昇格
       - 各章は concept/architecture/setup/operations/internals/advanced で統一
  3. サブシステム別 HLD (Subsystems)  ← 旧 area 9 個を 1 タブ配下に集約
       - routing / switching / overlay / acl-qos / system / management /
         platform / internals / architecture（横断系）
       - 各 area の index.md は「topics の対応章への誘導」を主役にする
  4. リファレンス (Reference)     ← CLI / CONFIG_DB / YANG
  5. メタ (Meta) ※小さく        ← categories / 編集方針 / verification 状態一覧
```

#### カードソーティング結果に基づく主要再配置

- `routing/gnmi-subscription-for-yang-data.md` → `management/` へ移動（gNMI 配下統合）
- `switching/increasing-lacp-pdu-timeout-during-warm-reboot.md` → `system/` の reboot 群へ
- `acl-qos/dash-acl-tags.md` → `overlay/` の DASH 配下に移動
- `architecture/` の DHCP relay 系 → `routing/` または `management/` に再配置
- `internals/` 13 ページ → `system/` または各機能 area に解体（兄弟粒度の不均衡を解消）

#### Topics ↔ Subsystem の関係を明示

各 area の `index.md` 先頭に固定パネル:

```markdown
!!! tip "まずは読み物から"
    BGP を読む順番で理解したい場合は **[読み物: 02 BGP と FRR 制御プレーン](../topics/02-bgp/)** へ。
    このページ以下は HLD 単位の個別ページです。
```

これで「entry point は topics、深掘りは subsystem」という Progressive Disclosure を成立させる。

#### Categories の扱い

- categories は **Meta タブ配下** に移し、トップタブから外す（Hick's Law 対応）
- 内部的には topics の **タグ集計ページ**として再定義（手動メンテからタグベース自動生成へ）

#### ラベリング統一

- すべて kebab-case + 日本語タイトル併記（`.pages` の `title:`）
- `internals` → 廃止（system / architecture / 各 area に解体）
- `architecture` → `cross-cutting`（横断的設計）に改名 or 廃止して各 area へ吸収

### 5.4 移行戦略（破壊的変更を避ける）

1. **Phase A** (非破壊): 5 タブ構造をルート `.pages` で実現、area は `Subsystems` グループ配下に nest（URL 不変）
2. **Phase B**: 各 area `index.md` の文言を「topics への誘導」に書き換え
3. **Phase C**: ファイル名ゆれを Indexer 段で正規化、リダイレクト（mkdocs-redirects）追加
4. **Phase D**: categories を Meta タブへ移動、タグ自動生成化

URL の物理削除は Phase D まで実施しない。**外部リンク・検索エンジンへの影響をゼロに抑える**。

---

## 6. 受け入れ基準（再設計後の検証指標）

- [ ] トップタブが **5 個以下**
- [ ] 同一機能のエントリポイント数（N 値）が **2 以下**（topics 入口 + reference 入口）
- [ ] 各 area の兄弟ページ数が **最大 / 最小で 3 倍以内**
- [ ] `docs/index.md` から任意のページに **3 クリック以内**到達
- [ ] 命名規則違反 0 件（lint 化）
- [ ] mkdocs build --strict で警告 0

---

## 7. 参考

- Diátaxis Framework: https://diataxis.fr/
- NN/g "Information Architecture": https://www.nngroup.com/articles/ia-vs-navigation/
- IA Institute "Cognitive Load in IA"
- Cumulus Linux Docs structure (NVIDIA)
- Kubernetes Documentation Style Guide
