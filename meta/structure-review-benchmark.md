# 構成評価レポート: 他 OSS / 商用 NOS docs ベンチマーク

作成日: 2026-05-11
対象: `sonic-unofficial-docs`（MkDocs Material、約 455 ページ）
目的: プロジェクトオーナーから「構成がわかりづらい」と指摘を受けたため、他の代表的なドキュメントサイトと比較し、IA（Information Architecture）面の差分を洗い出す。

---

## 1. 比較対象サイト

WebFetch で実際に閲覧したサイト:

| サイト | URL | 種別 |
|---|---|---|
| 公式 SONiC | `sonic-net.github.io/SONiC/` | OSS NOS（リダイレクト/Wiki 中心、IA ほぼ無し） |
| FRRouting | `docs.frrouting.org` | OSS Control Plane（Sphinx / RTD） |
| NVIDIA Cumulus Linux | `docs.nvidia.com/networking-ethernet-software/cumulus-linux/` | 商用 NOS |
| Arista EOS | `arista.com/en/support/product-documentation` | 商用 NOS |
| Linux kernel | `docs.kernel.org` | 巨大 OSS プロジェクト |
| Kubernetes | `kubernetes.io/docs/home/` | 複雑分散システムの IA 模範例 |

---

## 2. 各サイトの構成サマリ

### 2.1 公式 SONiC (`sonic-net.github.io/SONiC/`)
- 実体は GitHub Pages の HLD ダンプ + Wiki への redirect。
- 第 1 階層が「HLD 一覧の Markdown 群」で、**カテゴリ分けも入口分離もほぼ存在しない**。
- 検索は GitHub の grep 相当しかない。
- **本プロジェクトが超えるべき最低ライン**。ここは参考にならない。

### 2.2 FRR (`docs.frrouting.org`)
- 第 1 階層 4 件: Introduction / Basics / Protocols / Appendix。
- サイドバー階層型（Sphinx Furo / RTD theme）。
- **強み**: プロトコル単位で「概念 + 設定 + CLI」が 1 ページに完結している（BGP, OSPF など）。検索は Sphinx 標準で機能する。
- **弱み**: タスクベースの入口がなく「ECMP を有効にしたい」「ルートフィルタを書きたい」が複数プロトコル横断で迷子になる。Concept/Task/Reference の分離は弱い。

### 2.3 NVIDIA Cumulus Linux
- 第 1 階層 ~9 件: Quick Start / Installation Management / System Configuration / **Layer 1, Layer 2, Layer 3** / Network Virtualization / Monitoring & Troubleshooting / **Reference**（NVUE Command / Format Reference）。
- **強み**: 「Quick Start → 設定章（OSI 層別） → 運用章 → Reference」という**実装に追従する自然な順序**。Reference（CLI 一覧）が明確に独立。商用らしくバージョン切替が前面。
- **弱み**: Concept と How-to の分離は薄い。Layer 別配置は OSI を知らない読者にはやや堅い。

### 2.4 Arista EOS
- Software / Hardware / Reference の三柱。Configuration Guide と Command Reference が PDF として明示分離。
- **強み**: 「Configuration Guide」「Command Reference」「Release Notes」「Design Guide」が**ファイル単位で明示分離**されており、目的別に PDF を取りに行ける。
- **弱み**: 認証必須・PDF 主体・検索性が低い。OSS の参考にはなりにくいが、**「Configuration Guide と Command Reference を分ける」という原則**は普遍。

### 2.5 Linux kernel (`docs.kernel.org`)
- **読者ロール別**の大区分: admin-guide / process / dev-tools / driver-API / core-API / userspace-API / subsystem / arch。
- **強み**: 巨大プロジェクトを「**Who reads it**」で 1 次分割している。HLD のような実装ノートは subsystem 配下に押し込められ、ユーザー向け章を汚染しない。
- **弱み**: subsystem 内部は寄せ集めで品質が揃わない（本プロジェクト現状と似ている）。

### 2.6 Kubernetes (`kubernetes.io/docs/`)
- **教科書的 IA**: **Concepts / Tasks / Tutorials / Reference** の 4 分割（Diátaxis フレームワーク）。
  - **Concepts**: 「Pod とは」「Scheduler とは」など概念解説（理論）。
  - **Tasks**: 「特定の目的を達成する手順」（how-to、短く焦点的）。
  - **Tutorials**: 「順に進めて完成する学習体験」（Hello Minikube 等）。
  - **Reference**: API / CLI / 設定ファイル仕様（網羅）。
- ホーム画面は 6 枚カード（Understand / Try / Set up / Learn how to use / Look up reference / Contribute）で**読み手の現在地から動詞で誘導**。
- バージョン切替、言語切替、Edit this page、Glossary、強力な検索。
- **強み**: 読者が「何を求めているか」を最初の 1 クリックで分岐できる。
- **弱み**: 学習コストが高い（Tasks と Tutorials の境界判断など）。

---

## 3. `sonic-unofficial-docs` 現状評価

### 3.1 現在の第 1 階層（`docs/.pages` 順）

```
index.md / guides / topics / architecture / routing / switching /
overlay / acl-qos / system / management / platform / internals /
reference / categories
```

14 項目。内訳:

- **読み手別ガイド** `guides/`: beginner / operator / developer / evaluator（4 ロール）。**Kubernetes の 6 枚カードに相当**する読者誘導入口。良い試み。
- **読み物** `topics/`: BGP, VXLAN EVPN, VRF/ECMP, DualToR, L2 VLAN/LAG, ACL/CoPP/Mirror, QoS/Buffer, Telemetry/SNMP（9 章、各章が concept/setup/operations/internals/advanced に細分化）。**Cumulus の章立てに相当**する読み物。
- **機能ドメイン** `architecture` / `routing` / `switching` / `overlay` / `acl-qos` / `system` / `management` / `platform` / `internals` の **9 つの並列ディレクトリ**: 全 HLD ベースの個別ページ（HLD 1 件 = 1 ページ）。**FRR の Protocols / kernel の subsystem に相当**。
- **リファレンス** `reference/`: cli / config-db / yang。**EOS Command Reference に相当**。
- **横断カテゴリ** `categories/`: DASH / SmartSwitch / DualToR / Reboot / Multi-ASIC / BGP-EVPN / SAI 拡張 / MIB-SNMP / gNMI / Container-Build（10 タグ）。**kernel の "subsystem" 横断ビュー**に相当。

### 3.2 最も似ているサイト

**FRR + Cumulus + kernel のハイブリッド**。
- HLD ダンプ層（`routing/`, `switching/`, ...）= FRR の Protocols / kernel の subsystem。
- 読み物層（`topics/`）= Cumulus の「Layer 章」。
- ガイド層（`guides/`）= Kubernetes ホームカード。

意図は良いが、**「4 つの平行する IA が同じ第 1 階層に並んでいる」**ことが「わかりづらさ」の根因と推定される。

### 3.3 致命的に劣っているポイント

1. **第 1 階層の過密 (14 項目)**: Kubernetes は 4、Cumulus は ~9、FRR は 4。読者は最初の 1 クリックで迷う。`topics / architecture / routing / switching / overlay / acl-qos / system / management / platform / internals` の **10 個が並列**しており、`routing` と `topics/02-bgp` のどちらを開くべきか直感に頼るしかない。
2. **HLD 系 9 ディレクトリ（455 ページの大半）が "Reference の中身を Concept の入口に展開してしまっている"**: Kubernetes 流に言えば**個別 HLD は Reference**であり、第 1 階層に並べるべきではない。kernel が subsystem を末端に押し込めているのと逆。
3. **Concept / Task / Reference の入口分離が無い**: `topics/` には concept/setup/operations が**章内に閉じている**ため、「タスクだけを横串で見たい」（例: `config interface ip add` を引きたい）読者の入口がない。
4. **`categories/` がもう 1 つの平行 IA として独立**: 「同じ機能ファミリーを 1 箇所で見る」目的なら、本来は**タグ機能** (`mkdocs-material` の tags プラグイン) で実現すべきもの。ディレクトリとして第 1 階層に出すと「14 番目の選択肢」になり負担。
5. **`architecture` と `internals` の意味的境界が曖昧**: 読者は両方を開かざるを得ない。
6. **`guides/` がせっかく良いのに第 1 階層の 2 番目に隠れている**: Kubernetes のホーム 6 枚カードのような**視覚的入口**になっていない（`index.md` の箇条書きで埋もれる）。
7. **検索動線の弱さ**: CLI / CONFIG_DB key / YANG leaf 名で引きたい読者向けの**専用検索入口**（Glossary 的なもの）が無い。

### 3.4 良いポイント（維持すべき）

- 読み手ロール別ガイドの設計思想は Kubernetes に学べている。
- `topics/` 内の `concept / setup / operations / internals / advanced` 5 分割は **Diátaxis に近い**良い構造。
- 検証ステータス（`code-verified` / `discrepancy-found` / `hld-only`）は他に類を見ない強み。Reference を担っているという意識が明確。
- `awesome-pages` による各ディレクトリ自律運用と `.pages` 並び順制御は MkDocs プラクティスとして正しい。

---

## 4. 推奨構造（実例ベース）

### 4.1 推奨パターン: **Diátaxis 4 分割 + 読者ロールカード**

Kubernetes の **Concepts / Tasks / Tutorials / Reference** を SONiC ドメインにマップする。第 1 階層を **5 項目**（ホーム除く）まで圧縮する。

```
docs/
├── index.md              ホーム: 6 枚カード（読み手ロール + Try + Look up reference）
├── tutorials/            Kubernetes の Tutorials 相当
│   ├── evaluator-quickstart  （旧 guides/evaluator）
│   └── sonic-vs-on-gns3      （旧 architecture/sonic-on-gns3-vm 等）
├── concepts/             Kubernetes の Concepts 相当 = 「読み物」
│   ├── overview          （旧 topics/01-overview）
│   ├── routing           （旧 topics/02-bgp, 04-vrf-ecmp, など Routing 系の concept.md）
│   ├── switching         （旧 topics/06-l2-vlan-lag）
│   ├── overlay           （旧 topics/03-vxlan-evpn, 05-dual-tor）
│   ├── acl-qos           （旧 topics/07-acl-copp-mirror, 08-qos-buffer）
│   ├── management        （旧 topics/09-telemetry-snmp）
│   └── architecture      （SAI / Redis / Orchagent 等の SONiC 内部概念）
├── tasks/                Kubernetes の Tasks 相当 = 「特定目的の手順」
│   ├── configure-bgp-session
│   ├── enable-warm-reboot
│   ├── troubleshoot-dataplane
│   └── ... （現状 `topics/*/setup.md` `operations.md` から抽出）
├── reference/            EOS Command Reference + kernel subsystem 相当
│   ├── cli/              （現状そのまま）
│   ├── config-db/        （現状そのまま）
│   ├── yang/             （現状そのまま）
│   └── hld/              ← **現在の routing/ switching/ overlay/ acl-qos/ system/
│                            management/ platform/ internals/ architecture/ を
│                            すべてここに集約**（9 → 1）
│       ├── routing/
│       ├── switching/
│       └── ...
└── contribute/           （プロジェクトの方針、verification ステータスの読み方）
```

**`categories/`** は廃止し、`mkdocs-material` の **tags プラグイン** に置換。各ページ frontmatter の `tags:` で `[dash, smartswitch, dual-tor, ...]` を付け、`/tags/` ページで横串閲覧。

### 4.2 ホーム `index.md` を Kubernetes 6 枚カード化

`grid cards` 拡張で:

```
[ SONiC を理解する ]   [ SONiC を試す ]
   → Concepts へ          → Tutorials へ

[ クラスタを構築する ] [ SONiC を運用する ]
   → Tasks (setup) へ     → Tasks (operate) へ

[ リファレンスを引く ] [ コントリビュート ]
   → Reference へ          → Contribute へ
```

これで「設定方法を引きたい / 概念を知りたい / リファレンスを引きたい」の **3 つの主動線が最初の画面で分岐**する。

### 4.3 移行の現実解（段階的に）

完全な再構成は破壊的なので、以下の順で段階移行を推奨:

| Phase | 作業 | 影響 |
|---|---|---|
| A | `docs/index.md` を grid cards 化、`guides/` をホーム画面に格上げ | 既存パス不変、ホームのみ刷新 |
| B | `categories/` を廃止し、`tags` プラグイン導入 + 各ページに frontmatter tags 付与（既に `area:` がある） | 既存パス維持、`/categories/*` から `/tags/*` へ redirect |
| C | `routing / switching / overlay / acl-qos / system / management / platform / internals / architecture` を `reference/hld/<area>/` 配下へ移動。`mkdocs-redirects` で旧 URL を 301 | リンク切れなし、第 1 階層が **5 項目**になる |
| D | `topics/` を `concepts/` にリネーム、`topics/*/setup.md` `operations.md` を `tasks/` に抽出して再構成 | Diátaxis 完成 |

Phase A・B だけでも「14 → 12 項目 + 視覚的入口」になり、体感の改善は大きい。

---

## 5. 結論

| 項目 | 評価 |
|---|---|
| 最も近いサイト | FRR + Cumulus + kernel のハイブリッド |
| 学ぶべき相違点 | **Kubernetes の Diátaxis 4 分割**（Concepts / Tasks / Tutorials / Reference）と**ホーム 6 枚カード**による動線分岐 |
| 致命的劣後 | 第 1 階層 14 項目、HLD 系 9 ディレクトリの並列展開、Concept/Task/Reference 入口分離の不在 |
| 推奨アクション | Phase A（ホーム grid cards 化）→ B（tags 化）→ C（HLD を reference/hld/ 配下へ集約）→ D（topics → concepts/tasks 分離） |

`guides/` の読者ロール設計と、検証ステータス（code-verified 等）の透明性は他に類を見ない強みで、これらを土台にした上で **「読み手の最初の 1 クリック」を Kubernetes 並みに 4〜6 択へ圧縮する**ことが、「わかりづらさ」解消の最短経路である。
