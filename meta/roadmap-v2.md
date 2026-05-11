# Roadmap v2 (post v1.0)

v1.0 出荷 GO 達成 (2026-05-11, 監査 9.79/10) 後の中長期ロードマップ。粒度は v1.1 / v1.2 / v2.0 の 3 段階で、各バージョンは独立 release 可能。

## 0. 前提・スコープ

- 対象: SONiC コミュニティ版 (master) の日本語非公式ドキュメント
- 体制: AI agent 主導 + 人間レビュー (PR squash merge)
- 既存 455+ ページの維持運用と新規拡張を両立させる
- v1.0 GA 後は「破壊的再構成」は原則禁止。frontmatter schema・URL は安定化

## 1. v1.1 — 運用フェーズ確立 (目標: 2026-Q3, 約 1〜2 ヶ月)

### 1.1 目的
v1.0 を「動いてる静的サイト」から「外部読者と継続的にやりとりするドキュメント」に格上げする。コミュニティ受け入れと upstream 追従の運用化が中心。

### 1.2 想定機能 / 作業

| 項目 | 内容 | ボリューム | 優先度 |
|------|------|-----------|--------|
| GitHub Issues triage プロセス | `documentation/typo` / `documentation/discrepancy` / `documentation/request` の 3 ラベル制度。週次で agent が triage、`docs/` への反映 PR を自動生成 | M (運用設計 2d + 自動化スクリプト 3d) | 高 |
| GitHub Discussions 受付 | Q&A カテゴリ常設。よくある質問は `docs/faq/` に昇格する流れを定義 | S (テンプレ + ガイド 1d) | 中 |
| Issue → backlog 連携 | `documentation/request` ラベル付き issue を `meta/backlog/community/*.json` に自動取り込み | M (gh CLI script + Writer pipeline 拡張 3d) | 高 |
| 定期 master 追従サイクル | `meta/index/repos.json` の SHA を週次更新 → 差分 diff から再検証対象を抽出 → Verifier batch 起動 | L (Indexer v3: 差分検出 5d + Verifier 連携 3d) | 高 |
| `verification` ステータス劣化検知 | upstream 変更で `code-verified` が古くなったページを `stale-verified` に降格する自動 job | M (検証日時 + commit SHA 比較 3d) | 中 |
| Release Notes 自動生成 | merged PR をカテゴリ別に集計、月次 `docs/changelog/YYYY-MM.md` を生成 | S (script 2d) | 中 |
| ベンチマーク自動測定 | `mkdocs build --strict` 時間 / ページ数 / 平均文字数を CI で記録、推移を可視化 | S (workflow 1d) | 低 |

### 1.3 成功指標 (KPI)
- 外部 issue 受付から PR merge までのリードタイム: median 7 日以内
- 月次 master SHA 更新: 100% 実施
- `stale-verified` ページ比率: 全体の 10% 以下を維持

## 2. v1.2 — 多言語化 (目標: 2026-Q4 〜 2027-Q1, 約 3〜4 ヶ月)

### 2.1 目的
日本語版で得たコンテンツ資産を英語にも展開。SONiC 上流コミュニティへの還流可能性を作る。

### 2.2 想定機能 / 作業

| 項目 | 内容 | ボリューム | 優先度 |
|------|------|-----------|--------|
| mkdocs i18n 構成 | `mkdocs-static-i18n` プラグイン導入。`docs/ja/` `docs/en/` の物理分離 or suffix 方式の検討 | M (PoC 2d + 全体移行 3d) | 高 |
| 翻訳優先ページ選定 | アクセスログ + コミュニティ需要 + 「他言語に存在しないユニーク内容」基準で 30〜50 ページ選定 | S (選定 1d) | 高 |
| 優先ページ英訳 (Phase A) | Topics 章 12 件 + Tutorials 5 件 + Architecture overview 5 件 ≒ 22 ページを agent 翻訳 + 人間軽レビュー | L (1 ページ ~30 分 agent + レビュー、合計 ~3w) | 高 |
| 英訳 Phase B | Reference (CLI/CONFIG_DB/YANG) サマリと FAQ ≒ 30 ページ | L (~4w) | 中 |
| 翻訳メタデータ | frontmatter に `translations: { en: <path> }` 追加。SCHEMA.md 更新 | S (1d) | 高 |
| 言語切替 UI | Material テーマの language selector を有効化、未訳ページは原文へフォールバック | S (1d) | 中 |
| 訳語統一辞書 | `meta/glossary.{ja,en}.yaml`。ASIC/SAI/EVPN 等の固有訳を一元化、Reviewer が逸脱検知 | M (初版 + lint 3d) | 中 |
| 上流コミュニティ告知 | sonic-net Slack / GitHub Discussions で英語版公開を周知 | S (0.5d) | 低 |

### 2.3 範囲外 (v1.2 ではやらない)
- 中国語・韓国語等の追加言語 (需要を見てから v1.3 以降)
- HLD 全件の英訳 (上流 HLD は元々英語、再生成価値が低い)
- 機械翻訳バッチで全 455 ページ一括翻訳 (品質保証が破綻する)

### 2.4 成功指標
- 英訳ページ 50 件以上が `mkdocs build --strict` でビルド成功
- 上流コミュニティから feedback issue が最低 5 件発生

## 3. v2.0 — ベンダー版取り扱い再検討 (目標: 2027-Q2 以降, 6 ヶ月+)

### 3.1 背景
v1.0 時点で「ベンダー版 SONiC (NVIDIA / Edgecore / Cisco / AsterNOS 等) はスコープ外」を明示。ただし読者からは「Enterprise SONiC や SONiC-OS との関係が分からない」という需要が継続的に存在。v2.0 で態度を再決定する。

### 3.2 検討オプション

| Option | 概要 | Pros | Cons | 規模感 |
|--------|------|------|------|--------|
| A. スコープ拡張 (本リポに統合) | `docs/vendor/{nvidia,edgecore,cisco,asternos}/` を追加 | 読者は一箇所で完結 | コミュニティ版との混在で「これ実装と違うけど…」問題が複雑化。ベンダー NDA 文書を引用できない | XL (専用 Indexer + 各ベンダー専門 agent、6m+) |
| B. 別リポ分離 (推奨候補) | `sonic-vendor-unofficial-docs` 等を新設、共通 schema/プロンプトのみ本リポから共有 | 関心分離、ライセンス境界が明快 | リポ往来コスト、テンプレ重複の同期 | L (リポ立ち上げ 2w + 各ベンダー 1m ずつ) |
| C. 比較ページのみ追加 | `docs/comparison/community-vs-vendor.md` 1〜数枚で比較表のみ | 低コスト、需要に最低限応える | 詳細需要には応えられない | S (調査含めて 1w) |
| D. 何もしない | 明示的に「コミュニティ版専業」で v2.0 を出す | フォーカス維持 | 読者離れリスク | 0 |

### 3.3 v2.0 で行う意思決定
- 上記 A〜D のどれを採るかを v1.2 完了時点の状況 (コミュニティ要望、メンテ余力、法務リスク) で再判定
- 同時に v1.0 で凍結した frontmatter schema / URL を「破壊的変更を許容する版」として再設計可能 (URL redirect プランを v2.0 リリース要件に含める)

### 3.4 v2.0 で他に検討する技術項目 (Option 非依存)

| 項目 | 内容 | 優先度 |
|------|------|--------|
| 検索改善 | mkdocs Material 標準検索 → Algolia DocSearch / Meilisearch への移行 | 中 |
| 図の自動生成 | YANG → mermaid class diagram, RouteOrch dependency graph を CI で自動再生成 | 中 |
| Reference API 化 | CLI/CONFIG_DB/YANG リファレンスを JSON-LD で配信、外部ツール連携 (LLM RAG 等) を容易に | 低 |
| ダーク/印刷モード調整 | mermaid のテーマ追従と PDF 出力 | 低 |

## 4. 共通 (全バージョン)

- 各バージョンの開始時に `meta/release-checklist-vX.md` を新規作成し、v1.0 と同等の GO/NO-GO 監査を実施
- ロードマップ自体も生きたドキュメント。四半期ごとに見直し PR を出す
- main 直 push 禁止 / OPEN PR 残禁止 / `isolation: worktree` の運用ルールは v1.0 から不変

## 5. 直近 (v1.0 → v1.1 移行期) のアクション

1. このロードマップ自体を merge (本 PR)
2. CLAUDE.md にバージョン状態を反映済み (v1.0 GA、次は v1.1 運用フェーズ着手)
3. v1.1 着手の最初の 1 手は「Indexer v3 (週次 SHA 差分検出)」の設計メモ作成

## 6. 現状進捗 (v1.0 GA 後の累積、2026-05-11 round 30 時点)

v1.0 GA (2026-05-11、監査 9.79/10) 後に v1.1 着手前の品質固めとして iteration L〜AF を実施。本セクションはそのスナップショット。

### 6.1 iteration L〜AF サマリ

- **32 並列バッチ × 4-6 PR/iter = 約 150 追加 PR**、累積 **1078+ PR** に到達
- 主要改善:
  - `hld-only` 0 件達成（round 27 以降 5 round 連続で母集団から消失）
  - **glossary 5500+ リンク注入**（NVGRE / VXLAN / VTEP / SAI / orchagent 等の用語が hover で説明される状態）
  - **CDB / YANG / CLI mermaid 90%+ カバー**（Reference 系の自動生成パイプライン完成）
  - **ops-hint (運用入口表) 100%**（HLD ページの末尾「運用入口表」が全 HLD 系で確認可能）
  - Topics chapter-progress 表（22 章すべての chapter-index に進捗表を埋め込み、未完 split-child の可視化）
  - style guide / site map / changelog の整備、frontmatter lint 強化、`check_link_density.py` 導入
- **品質スコア推移**: round 12 (4.85) → round 27 (4.941) → round 29 (4.944) → round 30 (**4.944**) で **4.94+ で安定プラトー化**。母集団真値が **4.94 ± 0.005** の極狭帯域に 4 round 連続収束したことを round 30 で確認
- 奇偶交互運用 (奇数 round = random / 偶数 round = stratified) を round 28 で確立し、round 29-30 で 2 周目完走

### 6.2 残課題 (v1.1 本格着手前に処理する候補)

| 項目 | 内容 | 規模 |
|------|------|------|
| Topics advanced 残数 | DASH / SmartSwitch HA / MCLAG / EVPN-VXLAN 等の advanced 章で chapter-progress 表に未完表示の split-child を集中執筆 | 10〜15 ページ |
| 低密度ページ残数削減 | `related` 合計 ≤ 2 件のページを 30 件以下まで圧縮（現状 ~50 件） | M |
| CLI mermaid 100% 化 | CLI Reference 70 ページ中 90% は mermaid 済み、残 7 ページを mermaid 補完か `_no_mermaid: true` opt-out で 100% に | S |
| `_no_related_*` opt-out seed | `meta/index/cli-yang-mapping.json` を実投入、本質的に空が正解の Reference 15〜20 件に明示マーカー | S |
| discrepancy `related.yang` 残 6 補完 | round 28 で informational 検出 9 件中 3 件補完済み、残 6 件を補完 + 2 件に `_no_yang` 明示 | M |
| document i18n 検討 | v1.2 着手のための PoC（`mkdocs-static-i18n` 1 ページ移行試走） | S |

これらが概ね処理されたタイミングで **v1.1 (運用フェーズ確立)** の Indexer v3 設計に正式着手する想定。

### 6.3 監査履歴ハイライト

| Round | 平均 | サンプリング | 備考 |
|-------|------|------------|------|
| 12 | 4.85 | random | early baseline |
| 19 | 4.90 | random | glossary boost 前 |
| 26 | 4.92 | random | partial-empty 一掃 |
| 27 | 4.941 | **stratified 初投入** | サブセット軸別平均算出 |
| 28 | 4.94 | random | 奇偶交互運用確立 |
| 29 | 4.944 | stratified 2 周目 | scheme mature 確認 |
| **30** | **4.944** | random 2 周目 | **母集団真値 4.94 ± 0.005 確定** |
