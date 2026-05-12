---
title: config platform firmware サブコマンド
description: config platform firmware サブコマンド — config platform firmware は platform
  firmware 操作を fwutil に委譲する CLI グループ。install と update は未知オプションを Click で解釈せず、そのまま fwutil
  へ渡す。
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
- repo: sonic-net/sonic-utilities
  path: config/main.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-utilities
  path: show/platform.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
  - config platform firmware
  - show platform firmware
  yang:
  - sonic-device_metadata
  _no_related_config_db: true
---

# config platform firmware サブコマンド

## 概要

`config platform firmware` は platform firmware 操作を `fwutil` に委譲する CLI グループ。`install` と `update` は未知オプションを Click で解釈せず、そのまま `fwutil` へ渡す[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config platform firmware install [fwutil args...]` | platform firmware install を実行 |
| `config platform firmware update [fwutil args...]` | platform firmware update を実行 |
| `show platform firmware [fwutil args...]` | firmware 情報を表示 |

## 各コマンドの詳細

### `config platform firmware install`

**用法**:

```
config platform firmware install [fwutil args...]
```

実装は `["fwutil", "install"] + args` を `subprocess.check_call()` で実行する。`fwutil` が非 0 で終了した場合、その return code で CLI も終了する。

### `config platform firmware update`

**用法**:

```
config platform firmware update [fwutil args...]
```

`install` と同じ構造で、実行コマンドだけが `fwutil update` になる。

### `show platform firmware`

**用法**:

```
show platform firmware [fwutil args...]
```

表示側は `sudo fwutil show` に委譲する[^2]。サポートされる component 名・firmware target・追加オプションは platform plugin と `fwutil` 実装に依存する。

## 注意

- この CLI は [CONFIG_DB](../../reference/glossary.md#term-config_db) を直接編集しない。
- `add_help_option=False` のため、`config platform firmware install --help` のような引数も原則 `fwutil` に渡される。

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: `config platform firmware` の `install` / `update` 定義。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L8734>

[^2]: `show platform firmware` は `sudo fwutil show` を実行する。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/platform.py#L290>

<!-- cli-mermaid -->
### データフロー (手動作成)

```mermaid
flowchart LR
  CLI["config platform firmware"]
  FW["fwutil install / update"]
  PA["platform_api<br/>(Component.install_firmware)"]
  HW["フラッシュデバイス / BIOS / BMC"]
  CLI --> FW
  FW --> PA
  PA --> HW
```

!!! note "凡例"
    platform 系 (CLI → fwutil → platform_api → HW) のミニ図。CONFIG_DB を直接介さないコマンドのため手動で記述。
<!-- /cli-mermaid -->

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Platform / Port / Optics / PHY](../../topics/14-platform-port-optics/index.md)

<!-- /topics-back-ref -->

<!-- ops-hint -->
## 運用ヒント

### 典型的な利用シーン

- BIOS / CPLD / [FPGA](../../reference/glossary.md#term-fpga) / SSD の firmware install と確認。
- fwutil でのスケジュール更新 (next / boot)。

### よくある落とし穴

- `install` 後の reboot 種別 (cold / warm / fast / power) を間違えると flash しない。
- firmware 競合状態で install を中断すると BIOS が brick することがある。電源断厳禁。

### 関連する show / debug

```bash
show platform firmware status
show platform firmware version
fwutil show status
```
<!-- /ops-hint -->

<!-- cli-sibling -->
### 関連 CLI コマンド

- [`show platform`](show-platform.md) — show platform サブコマンド
- [`show clock`](show-clock.md) — show clock サブコマンド
- [`show environment`](show-environment.md) — show environment サブコマンド
- [`show feature`](show-feature.md) — show feature サブコマンド
- [`show services`](show-services.md) — show services サブコマンド

<!-- /cli-sibling -->

<!-- glossary-links-injected: d12a6eddadee -->
