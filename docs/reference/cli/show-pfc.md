---
title: show pfc サブコマンド
description: "show pfc サブコマンド — show pfc は PFC counter と PFC priority mapping を表示する CLI グループ。show pfcwd は同じ領域の watchdog 表示 wrapper で、pfcwd show ... に委譲する。"
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
    - show pfc
    - show pfcwd
  yang: []
---

# show pfc サブコマンド

## 概要

`show pfc` は PFC counter と PFC priority mapping を表示する CLI グループ。`show pfcwd` は同じ領域の watchdog 表示 wrapper で、`pfcwd show ...` に委譲する[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show pfc counters [options]` | PFC counters を表示 |
| `show pfc priority [options]` | PFC priority 設定を表示 |
| `show pfc asymmetric [options]` | asymmetric PFC 設定を表示 |
| `show pfcwd config [-d true|false]` | PFC watchdog config を表示 |
| `show pfcwd stats [-d true|false]` | PFC watchdog stats を表示 |

## 詳細

`show pfc` 配下の command は `pfcstat` / `pfc` 系 utility を実行する wrapper として定義される。interface alias mode の場合は必要に応じて alias を SONiC port 名へ変換してから外部コマンドへ渡す。

`show pfcwd config` は `pfcwd show config -d <display>`、`show pfcwd stats` は `pfcwd show stats -d <display>` を実行する。`display` は multi-ASIC 共通 option の表示制御値[^2]。

## 注意

- `config interface pfc ...` は設定系で、`show pfc` は表示系。
- PFC watchdog の永続化や counter の詳細は `pfcwd` 実装側に依存する。

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: `show pfc` グループ定義。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L670>

[^2]: `show pfcwd` の `config` / `stats` wrapper。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L724>
