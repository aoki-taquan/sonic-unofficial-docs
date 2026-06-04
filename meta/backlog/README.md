# Backlog 残 8 件の分類整理（2026-06-04 update — SmartSwitch HA 2 件を split 実装済として archive）

`meta/backlog/<area>/*.json` に残る **10 件** のタスクを、品質ゲート観点で **drop（廃止候補）/ low-priority（v1.1 以降）/ defer（既存大型ページへ統合）** の 3 カテゴリに分類する。

`meta/_gen_backlog.py` の Indexer 段で除外フィルタを足すことで、再生成時の継続的なノイズ流入を防ぐ。本 README は v1.1 サイクル開始時の判断材料として使う。

## 0. 分類サマリ（round 38 update）

| カテゴリ | 件数 | 処理方針 |
|----------|------|----------|
| **low-priority**（v1.1 検討） | 8 | 内容自体は有用だが、既存ページとの重複 / scope outside / 大型 HLD で着手コスト大 |
| **doc-exists-split で archive 済**（本 update） | 2 | SmartSwitch HA HLD / Detailed Design は split 実装済 |
| **drop / defer（_archived へ移動済）** | 5 | round 38 PR で `meta/backlog/_archived/<area>/` へ物理移動 |
| **drop（旧分類で _archived 化済）** | 27 | round 36 以前に既に _archived へ移動済 |
| **合計（現存 active）** | **8** | - |

## 1. 本 PR (chore/q40-an-audit38-backlog) でのアクション

round 36 時点で 42 件 → drop 27 件を _archived 化済（リリースノート 13 + 章節断片 9 + ビルド系 3 + テンプレ 1 + 重複 1）。残 15 件のうち、**本 PR で defer 4 件 + 実質 drop 1 件 = 5 件**を `_archived` へ追加移動した:

### 1.1 defer → archived（4 件、既存ページへ取込済 or 実体無）

| 移動元 | 移動先 | 理由 |
|--------|--------|------|
| `acl-qos/flow-charts.json` | `_archived/acl-qos/flow-charts.json` | 6KB、acl-qos 既存ページ群の mermaid 図で実質再現済 |
| `architecture/import-the-vendor-to-module-mapping.json` | `_archived/architecture/import-the-vendor-to-module-mapping.json` | 15KB、`docs/architecture/` 系で同等の内容を扱い済 |
| `routing/egress-acl-bug-fix-description.json` | `_archived/routing/egress-acl-bug-fix-description.json` | 3KB、ACL 設計ページの「実装との乖離」セクションへ統合済 |
| `routing/ecmp-calculator.json` | `_archived/routing/ecmp-calculator.json` | 28B、実体無の stub |

### 1.2 drop → archived（1 件、空ファイル）

| 移動元 | 移動先 | 理由 |
|--------|--------|------|
| `management/pins-supplementary-hld.json` | `_archived/management/pins-supplementary-hld.json` | 73B のみで本体ほぼ空、独立ページ化不可 |

## 2. low-priority カテゴリ（10 件、v1.1 検討）

内容は有用だが、現状の優先度では着手コストが見合わない。v1.1 サイクル開始時に再判断する。本 PR では active 状態で `meta/backlog/<area>/` に保持する。

### 2.1 大型 HLD（4 件、>50KB）

| ファイル | サイズ | 備考 |
|---------|--------|------|
| `system/cmis-diagnostic-monitoring-overview-in-sonic.json` | 221KB | CMIS 光学診断モニタリング。`docs/platform/` 配下に統合 or 独立ページ化のいずれか |
| `system/sonic-command-line-interface-guide.json` | 608KB | CLI ガイド全文。すでに `docs/reference/cli/` 25 件で個別 CLI ページ化済のため、独立ガイド化は重複 |

> 2026-06-04 update: SmartSwitch HA HLD (149KB) / Detailed Design (62KB) の 2 件は `architecture/smartswitch-high-availability-high-level-design-dpu-scope-dpu-driven-setup-{,concepts,internals,operations}.md` と `architecture/smartswitch-high-availability-manager-daemon-hamgrd-design{,-concepts,-internals,-operations,-limitations}.md` で split 実装済のため `_archived/` へ移動した。`meta/scripts/cleanup_backlog.py` に `doc-exists-split` 検出（`<slug>-*.md` glob）を追加し、同種の split 実装済 backlog を以後自動 archive する。これにより audit の「stale-vs-backlog」課題（未実装 slug を 0 点で叩く）を構造的に解消する。

### 2.2 telemetry / openconfig 系（3 件）

| ファイル | サイズ | 備考 |
|---------|--------|------|
| `system/high-frequency-telemetry-high-level-design-omit-in-toc.json` | 29KB | slug 末尾 `omit-in-toc` が示唆通り元 HLD で TOC 非掲載扱い |
| `system/openconfig-support-for-system-features.json` | 28KB | OpenConfig system 機能サポート |
| `system/sonic-grpc-data-telemetry.json` | 52KB | gRPC データテレメトリ HLD |

### 2.3 PINS / chassis（2 件）

| ファイル | サイズ | 備考 |
|---------|--------|------|
| `platform/pins-sonic-control-plane-for-generic-sai-extensions.json` | 32KB | PINS SAI 拡張 |
| `system/sonic-chassis-platform-management-monitoring.json` | 38KB | chassis platform 管理。`topics/20-multi-asic-chassis` 配下に統合候補 |

### 2.4 第三者拡張（1 件）

| ファイル | サイズ | 備考 |
|---------|--------|------|
| `system/third-party-container-management-enhancements-to-sonic-application-extensions-fr.json` | 18KB | slug 末尾 `-fr` 断片、第三者コンテナ管理。SAE (SONiC Application Extension) 関連で内容ありだが、slug 整形が必要 |

## 3. 既に _archived 化済の旧 drop 27 件（参考、round 36 以前）

以下は round 36 以前に物理削除（_archived 化）した drop カテゴリ。本セクションは履歴目的で残す。

- リリースノート 13 件（`architecture/sonic-NNNNNN-release-notes.json`）— SONiC コミュニティの公式リリースノートを別所で AI 再構成する意義は低い
- 章節断片・目次系 9 件（`architecture/goals` / `internals/1-scope` / `switching/1-document-history` / `platform/list-of-tables` / `routing/about-this-manual` / `system/all-fields-are-mandatory` / `platform/meeting-recordings` / `routing/web-file-server-population-script` / `routing/sysctl-w-net-ipv4-ip-forward-1`）
- ビルド系断片 3 件（`architecture/build-improvements-hld-2` / `system/build-improvements-hld` / `architecture/sonic-reproduceable-build`）
- テスト計画テンプレ 1 件（`architecture/sonic-test-plan-template`）
- grpc-data-telemetry 重複 1 件（`system/sonic-grpc-data-telemetry-2`）

## 4. Indexer 除外フィルタ実装（v1.1 開始時、未着手）

`meta/_gen_backlog.py` に以下の正規表現 stoplist を組み込むことで、再生成時の継続的なノイズ流入を防ぐ:

```python
# meta/_gen_backlog.py に追加予定
EXCLUDE_PATTERNS = [
    r"^sonic-\d{6}-release-notes$",            # リリースノート
    r"^\d+-(scope|document-history|introduction)$",  # 章節番号付き断片
    r"^(goals|list-of-tables|about-this-manual|meeting-recordings)$",  # 汎用名断片
    r"-hld-\d+$",                              # Part N 断片
    r"^[a-z-]+-\d+$",                          # 末尾数字 (重複 Part)
]
EXCLUDE_MIN_SIZE_BYTES = 200  # 200 バイト未満の stub を除外
```

これにより本 PR で _archived 化した 5 件 + 旧 drop 27 件 = 計 32 件が再生成時にも自動除外される。

## 5. 関連ドキュメント

- [low-impact 残課題スナップショット](../../docs/reference/verification/residual-tasks.md)
- [品質ロードマップ](../quality-roadmap.md)
- [roadmap v2](../roadmap-v2.md)
- [監査 round 38（stratified 6 周目 / サブ軸正式運用 3 周目 / backlog 残 10 件確定）](../quality-audit-38.md)
- [監査 round 37（random 6 周目 / 4.972 / サブ軸 5b・6b random 初 5.00 飽和）](../quality-audit-37.md)
- [監査 round 36（stratified 5 周目 / シリーズ最高 4.993 / サブ軸正式運用 1 周目）](../quality-audit-36.md)
