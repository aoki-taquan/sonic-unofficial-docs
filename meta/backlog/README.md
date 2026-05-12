# Backlog 残 42 件の分類整理（2026-05-12 時点）

`meta/backlog/<area>/*.json` に残る 42 件のタスクを、品質ゲート観点で **drop（廃止候補）/ low-priority（v1.1 以降）/ defer（既存大型ページへ統合）** の 3 カテゴリに分類する。

`meta/_gen_backlog.py` の Indexer 段で除外フィルタを足すことで、再生成時の継続的なノイズ流入を防ぐ。本 README は v1.1 サイクル開始時の判断材料として使う。

## 0. 分類サマリ

| カテゴリ | 件数 | 処理方針 |
|----------|------|----------|
| **drop**（廃止候補・Indexer 除外推奨） | 27 | 章節断片・目次・release-notes・introduction 系で、独立ページ化する価値が低い |
| **low-priority**（v1.1 検討） | 11 | 内容自体は有用だが、既存ページとの重複 / scope outside / 大型 HLD で着手コスト大 |
| **defer**（既存ページへ統合） | 4 | 既存の大型 HLD ページの 1 セクションとして既に取り込み済み or 取り込み予定 |
| **合計** | **42** | - |

## 1. drop カテゴリ（27 件、Indexer 除外推奨）

以下は HLD 切り出し時に生まれた **章節断片 / 目次 / リリースノート / 履歴セクション** で、独立した「日本語非公式ドキュメント」としての価値が低い。`meta/_gen_backlog.py` で正規表現除外を追加すべき候補。

### 1.1 リリースノート（13 件、`sonic-NNNNNN-release-notes`）

`architecture/` 配下に 201904 〜 202505 の 13 個。SONiC コミュニティの公式リリースノートを別所で AI 再構成する意義は低い（公式 GitHub Release ページがある）。

- `architecture/sonic-201904-release-notes.json`
- `architecture/sonic-201911-release-notes.json`
- `architecture/sonic-202006-release-notes.json`
- `architecture/sonic-202012-release-notes.json`
- `architecture/sonic-202106-release-notes.json`
- `architecture/sonic-202111-release-notes.json`
- `architecture/sonic-202205-release-notes.json`
- `architecture/sonic-202211-release-notes.json`
- `architecture/sonic-202305-release-notes.json`
- `architecture/sonic-202311-release-notes.json`
- `architecture/sonic-202405-release-notes.json`
- `architecture/sonic-202411-release-notes.json`
- `architecture/sonic-202505-release-notes.json`

**処方**: Indexer に `slug ~ ^sonic-\d{6}-release-notes$` 除外フィルタを追加。

### 1.2 章節断片・目次系（9 件、汎用名スラグ）

特定 HLD の章節タイトル（"Goals" / "Scope" / "Document History" / "List of Tables" 等）が単独 slug として誤抽出されたもの。元 HLD では文脈を持つが、単独ページ化すると意味不明。

- `architecture/goals.json` — 単独 "Goals"（どの HLD の goals か文脈なし）
- `internals/1-scope.json` — "1. Scope" 章節
- `switching/1-document-history.json` — 改版履歴セクション
- `platform/list-of-tables.json` — 表目次（110KB だが本体は表番号一覧）
- `routing/about-this-manual.json` — マニュアル序文
- `system/all-fields-are-mandatory.json` — フィールド注記
- `platform/meeting-recordings.json` — ミーティング録画リンク集
- `routing/web-file-server-population-script.json` — 補助スクリプト断片
- `routing/sysctl-w-net-ipv4-ip-forward-1.json` — sysctl 個別パラメータ

**処方**: Indexer に汎用名 stoplist（`^\d+-` / `goals` / `scope` / `document-history` / `list-of-tables` / `about-this-manual` 等）を追加。

### 1.3 ビルド系断片（3 件）

- `architecture/build-improvements-hld-2.json` — `build-improvements-hld` の Part 2 で、Part 1 はすでに `system/build-improvements-hld.json` として残っているが両方 drop 推奨
- `system/build-improvements-hld.json` — 同上
- `architecture/sonic-reproduceable-build.json` — `sonic-reproducible-build` の typo slug。再現性ビルドは v1.1 で `topics/19-build-packaging` 配下に統合候補

**処方**: build 系 3 件は `topics/19-build-packaging/reproducible-build.md` として将来統合（low-priority 移行候補だが、現状 drop で支障なし）。

### 1.4 テスト計画テンプレ（1 件）

- `architecture/sonic-test-plan-template.json` — 3KB のテンプレート。中身が無いため drop。

### 1.5 grpc-data-telemetry 重複（1 件）

- `system/sonic-grpc-data-telemetry-2.json` — 既に `system/sonic-grpc-data-telemetry.json` があり Part 2 は重複。Part 1 のみ low-priority に残す。

## 2. low-priority カテゴリ（11 件、v1.1 検討）

内容は有用だが、現状の優先度では着手コストが見合わない。v1.1 サイクル開始時に再判断する。

### 2.1 大型 HLD（4 件、>50KB）

- `architecture/smartswitch-high-availability-high-level-design.json` (149KB) — SmartSwitch HA HLD。既に `overlay/dash-ha-state-machine.md` 等で部分的にカバー済みだが、HA 全体像の独立ページは v1.2（章単位分割）候補
- `platform/smartswitch-high-availability-detailed-design.json` (62KB) — SmartSwitch HA Detailed Design。上記と対をなす
- `system/cmis-diagnostic-monitoring-overview-in-sonic.json` (221KB) — CMIS 光学診断モニタリング。`docs/platform/` 配下に統合 or 独立ページ化のいずれか
- `system/sonic-command-line-interface-guide.json` (608KB) — CLI ガイド全文。すでに `docs/reference/cli/` 25 件で個別 CLI ページ化済のため、独立ガイド化は重複

### 2.2 telemetry / openconfig 系（3 件）

- `system/high-frequency-telemetry-high-level-design-omit-in-toc.json` (29KB) — 高頻度テレメトリ HLD。slug 末尾の `omit-in-toc` が示唆通り元 HLD で TOC 非掲載扱い
- `system/openconfig-support-for-system-features.json` (28KB) — OpenConfig system 機能サポート
- `system/sonic-grpc-data-telemetry.json` (52KB) — gRPC データテレメトリ HLD（Part 2 は drop）

### 2.3 PINS / chassis（3 件）

- `management/pins-supplementary-hld.json` (73B) — 73 バイトのみで本体ほぼ空。Indexer 段で空ファイル除外を足せば drop。今期 low-priority 留保
- `platform/pins-sonic-control-plane-for-generic-sai-extensions.json` (32KB) — PINS SAI 拡張
- `system/sonic-chassis-platform-management-monitoring.json` (38KB) — chassis platform 管理。`topics/20-multi-asic-chassis` 配下に統合候補

### 2.4 第三者拡張（1 件）

- `system/third-party-container-management-enhancements-to-sonic-application-extensions-fr.json` (18KB) — slug 末尾 `-fr` 断片、第三者コンテナ管理。SAE (SONiC Application Extension) 関連で内容ありだが、slug 整形が必要

## 3. defer カテゴリ（4 件、既存ページへ統合）

既存ページのセクションとして既にカバー済 or 取り込み予定。`meta/backlog` から除去して問題ない。

- `acl-qos/flow-charts.json` (6KB) — `docs/acl-qos/` 配下の既存 ACL pipeline ページに flow-chart として吸収済（`docs/acl-qos/enhancements-to-add-or-del-ports-dynamically.md` 等の mermaid 図で再現）
- `architecture/import-the-vendor-to-module-mapping.json` (15KB) — ベンダ → モジュールマッピング。`docs/architecture/sonic-vendor-module-mapping.md` で同等内容を扱い済
- `routing/egress-acl-bug-fix-description.json` (3KB) — egress ACL バグ修正履歴。`docs/acl-qos/` の ACL 設計ページの "実装との乖離" セクションへ統合済
- `routing/ecmp-calculator.json` (28B) — 28 バイトのみ。実体なしで defer = 実質 drop

## 4. 整理アクション（推奨実施順）

1. **Indexer 除外フィルタ追加**（v1.1 開始時）: 上記 §1.1 / §1.2 / §1.5 の正規表現 stoplist を `meta/_gen_backlog.py` に組み込み、再生成時に自動除外
2. **drop 27 件の物理削除**: Indexer 除外後、`meta/backlog/_archived/<area>/<slug>.json` へ移動（既存 archived 344 件と同列）。本 PR では物理削除は行わず、本 README で論理的に「drop 判定済」とマーキングするにとどめる
3. **defer 4 件の物理削除**: 既存ページに吸収済が確認できているため、v1.1 サイクル開始時にまとめて `_archived` 化
4. **low-priority 11 件**: v1.1 ロードマップ会議で再判断、着手可否を決定

## 5. 関連ドキュメント

- [low-impact 残課題スナップショット](../../docs/reference/verification/residual-tasks.md)
- [品質ロードマップ](../quality-roadmap.md)
- [roadmap v2](../roadmap-v2.md)
- [監査 round 36（stratified 5 周目 / サブ軸正式運用 1 周目）](../quality-audit-36.md)
