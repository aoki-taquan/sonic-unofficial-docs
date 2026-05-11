---
title: config warm_restart サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - WARM_RESTART
    - FEATURE
  cli:
    - config warm_restart
    - show warm_restart
  yang: []
---

# config warm_restart サブコマンド

## 概要

`config warm_restart` は warm restart の enable 状態と daemon timer を設定する CLI グループ。enable/disable は STATE_DB の `WARM_RESTART_ENABLE_TABLE|<module>` を更新し、timer 系は CONFIG_DB の `WARM_RESTART` を更新する[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config warm_restart enable [--namespace <ns>] [<module>]` | module の warm restart を有効化 |
| `config warm_restart disable [--namespace <ns>] [<module>]` | module の warm restart を無効化 |
| `config warm_restart neighsyncd_timer [--namespace <ns>] <seconds>` | `swss` の neighsyncd timer を設定 |
| `config warm_restart bgp_timer [--namespace <ns>] <seconds>` | `bgp` の timer を設定 |
| `config warm_restart teamsyncd_timer [--namespace <ns>] <seconds>` | `teamd` の teamsyncd timer を設定 |
| `config warm_restart bgp_eoiu [--namespace <ns>] [true|false]` | BGP EOIU を設定 |

## 各コマンドの詳細

### enable / disable

`<module>` を省略すると `system`。`module != system` の場合は CONFIG_DB `FEATURE` テーブルに存在する feature 名だけを受け付ける。namespace 指定が無い場合、single-ASIC では default namespace、multi-ASIC では default + ASIC namespace 群に反映する[^2]。

### timer 系

- `neighsyncd_timer` は `WARM_RESTART|swss` の `neighsyncd_timer` を更新する。adhoc validation が有効な場合は 1-9998 秒。
- `bgp_timer` は `WARM_RESTART|bgp` の `bgp_timer` を更新する。adhoc validation が有効な場合は 1-3599 秒。
- `teamsyncd_timer` は `WARM_RESTART|teamd` の `teamsyncd_timer` を更新する。adhoc validation が有効な場合は 1-3599 秒。
- `bgp_eoiu` は `WARM_RESTART|bgp` の `bgp_eoiu` を `true` / `false` で更新する。

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`WARM_RESTART`](../config-db/warm-restart.md) / [`FEATURE`](../config-db/feature.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `config warm_restart` グループは CONFIG_DB と STATE_DB connector を namespace ごとに初期化する。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L3940>

[^2]: `enable` / `disable` は `WARM_RESTART_ENABLE_TABLE|<module>` の `enable` フィールドを書き込む。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L3973>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: Reboot / Upgrade / Lifecycle](../../topics/11-reboot/index.md)

<!-- /topics-back-ref -->
