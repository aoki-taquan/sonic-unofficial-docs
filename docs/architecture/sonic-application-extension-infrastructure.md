---
title: SONiC Application Extension Infrastructure（sonic-package-manager / SPM）
area: architecture
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/SONiC
    path: doc/sonic-application-extension/sonic-application-extention-hld.md
    ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
    - FEATURE
  cli:
    - sonic-package-manager
    - spm
  yang: []
---

!!! success "裏取りステータス: code-verified"
    実装裏取り済み（下記コード位置）。SPM CLI: sonic-utilities/sonic_package_manager/{main.py,manifest.py,manager.py,database.py,dockerapi.py} で確認。

# SONiC Application Extension Infrastructure（sonic-package-manager / SPM）

## 概要

3rd-party / 任意の docker コンテナを「SONiC application extension」として **inbox 機能と同じ管理面で扱う** ためのフレームワーク[^1]。狙い:

- アプリ追加が `apt`-相当の単一 CLI で済む（`sonic-package-manager install`）
- 通常の SONiC 機能と同じく `FEATURE` テーブル・`config feature` で on/off
- warm reboot / reset-factory・showtech・syslog 等の運用フックに統一して載る
- 動作するために必要な base image や他機能を **manifest** に宣言し、互換性を機械的に検証

## 構成要素

```mermaid
flowchart LR
    REG[(コンテナレジストリ)] --> PM[sonic-package-manager]
    PM --> PKGDB[/var/lib/sonic-package-manager/\n(installed manifests)]
    PM --> DOCKER[(local docker images)]
    PM --> CFGDB[CONFIG_DB\nFEATURE エントリ追加]
    CFGDB --> HC[hostcfgd]
    HC --> SVC[/etc/systemd/system/<feature>.service]
    SVC --> CONT[docker run --name <feature>]
```

主要なコンポーネント[^1]:

- **CLI `sonic-package-manager`（別名 SPM）**: install / uninstall / upgrade / list / show / repository サブコマンドを提供
- **manifest**: コンテナイメージに同梱される JSON。package 名、version、依存（base image / 他 package / SONiC version 範囲）、起動引数、warm-reboot 対応フラグ、CLI 拡張・showtech プラグイン等のフック宣言
- **`hostcfgd`**: `FEATURE` 追加に追従して systemd unit を rendering し start/stop を駆動
- **CLI plugin**: 各 package が `click` ベースの CLI を `sonic-utilities` に動的 register（plugin entry-point）

## ライフサイクル

```mermaid
flowchart LR
    INST[install <repo>:<tag>] --> PULL[image pull]
    PULL --> VERIFY[manifest 検証\n(version / 依存 / SONiC ver)]
    VERIFY --> REGISTER[FEATURE エントリ追加\nCLI plugin register\nshowtech plugin register]
    REGISTER --> ENABLE[config feature state <pkg> enabled]
    ENABLE --> RUN[hostcfgd → systemd → docker]
    RUN --> UNINST[uninstall]
    UNINST --> STOP[feature disable]
    STOP --> CLEAN[FEATURE 削除\nimage / plugin 削除]
```

manifest が必須宣言する項目（HLD ベース）[^1]:

- `name`、`version`
- `base-os` / `min-sonic-version` / `max-sonic-version`
- `depends` / `breaks`（他 package との互換性）
- `service` / `container` 起動オプション（warm-reboot 対応、privileged 必要性、namespaces）
- `cli`（`config` / `show` への拡張サブコマンド）
- `processes`（critical processes として監視するか）

## 設定

### 関連する CONFIG_DB

| Table | 説明 |
|-------|------|
| `FEATURE` | install したアプリも inbox 機能と同列に扱う |

### 関連する CLI

| Command | 用途 |
|---------|------|
| `sonic-package-manager install <repo>:<tag>` | install |
| `sonic-package-manager uninstall <name>` | uninstall |
| `sonic-package-manager upgrade <name> <new-version>` | バージョン更新 |
| `sonic-package-manager list` | 現在の package 一覧 |
| `sonic-package-manager show package versions <name>` | バージョン情報 |
| `config feature state <name> {enabled,disabled}` | 起動制御（inbox と同じ） |

## 制限事項

- **manifest 互換性検査の限界**: `min-sonic-version` / `depends` で表せない暗黙依存（kernel module、SAI 拡張等）は捕まえられない
- **warm reboot 対応**: package 側の対応が必要。非対応 package は warm reboot でリセットされる
- **CLI plugin の衝突**: 同じ `config <subcommand>` を複数 package が登録すると挙動不定
- **資源管理**: cgroup / メモリ / CPU 上限はコンテナ起動オプションでしか制御できない

## 干渉する機能

- **inbox 機能の `FEATURE`**: 名前空間が同じため衝突に注意
- **warm/fast reboot**: 非対応 package の data plane 連続性は保証できない
- **show techsupport**: package 側 plugin が登録されないと、その docker のログが収集されない

## トラブルシューティング

- install 失敗 → `sonic-package-manager` のログ、image pull 権限、manifest 検証エラーを確認
- 起動しない → `systemctl status <feature>` と docker ログ、`config feature` 状態を確認
- CLI が出ない → plugin entry-point の取り込み、`sonic-utilities` の再起動 / shell の再ログイン

## 引用元

[^1]: `sonic-net/SONiC` `doc/sonic-application-extension/sonic-application-extention-hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- concerns hint:
- sonic-package-manager (SPM) CLI の sonic-utilities への取り込みと entry-point の確認
- manifest スキーマ（base-os / min-sonic-version / depends 等）の現行実装フィールド名確認
- hostcfgd の FEATURE → systemd unit rendering ロジック現行確認
- CONFIG_DB FEATURE スキーマと package 由来 feature の処理差分確認
- warm reboot 非対応 package のフォールバック挙動確認
- third-party container hardening / 資源制限機構の現行実装確認
-->
