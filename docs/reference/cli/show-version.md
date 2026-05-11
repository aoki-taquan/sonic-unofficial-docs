---
title: show version サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
    - show version
  yang: []
---

# show version サブコマンド

## 概要

`show version` は **SONiC のビルド情報、プラットフォーム情報、シャーシ情報、稼働時間、現在時刻**、および docker イメージ一覧をまとめて出力する。実装は `show/main.py:version()`[^1]。

## シグネチャ

```
show version [--brief]
```

| オプション | 意味 |
|---|---|
| `--brief` | docker イメージ一覧を省略する |

## 出力内容

`version()` は以下のソースから情報を集約する。

| 行 | データソース |
|---|---|
| `SONiC Software Version: SONiC.<build_version>` | `device_info.get_sonic_version_info()`（`/etc/sonic/sonic_version.yml`） |
| `SONiC OS Version` | 同上 (`sonic_os_version`) |
| `Distribution: Debian <ver>` | 同上 (`debian_version`) |
| `Kernel` | 同上 / フォールバックで `os.uname().release` |
| `Build commit` / `Build date` / `Built by` | 同上 |
| `Platform` / `HwSKU` / `ASIC` / `ASIC Count` | `device_info.get_platform_info()`（`/etc/sonic/sonic_version.yml` と platform.json） |
| `Serial Number` / `Switch-Host Serial Number` / `Model Number` / `Hardware Revision` | `platform.get_chassis_info()`（platform API 経由で EEPROM 等） |
| `Uptime` | `uptime` コマンド出力 |
| `Date` | Python 側 `datetime.now()` |

`--brief` を付けない場合、最後に `sudo docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}"` を実行して docker イメージ一覧を続けて出力する[^1]。

## 注意

- `Switch-Host Serial Number` は `chassis_info['switch_host_serial']` が `'N/A'` でない場合のみ表示される（モジュラシャーシ向けの追加項目）。
- `Date` は **コマンド起動時の Python プロセスローカル時刻**。`Uptime` は外部 `uptime(1)` 実行結果。両者の取得タイミングがわずかにずれることがある。

## CONFIG_DB との接点

なし（ファイル `/etc/sonic/sonic_version.yml`, platform API, docker daemon を読むのみ）。

## 引用元

[^1]: `version()` 実装は `show/main.py` L1714-L1750。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L1714>
