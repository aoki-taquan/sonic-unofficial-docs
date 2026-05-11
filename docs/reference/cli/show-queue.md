---
title: show queue サブコマンド
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
    - show queue
  yang: []
---

# show queue サブコマンド

## 概要

`show queue` は queue counter、WRED counter、queue watermark を表示する CLI グループ。counter は `queuestat` / `wredstat`、watermark は `watermarkstat` へ委譲する[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show queue counters [INTERFACE_NAME] [options]` | queue counters を表示 |
| `show queue wredcounters [INTERFACE_NAME] [options]` | WRED counters を表示 |
| `show queue watermark unicast [options]` | unicast queue user watermark |
| `show queue watermark multicast [options]` | multicast queue user watermark |
| `show queue watermark all [options]` | 全 queue user watermark |
| `show queue persistent-watermark unicast [options]` | unicast queue persistent watermark |
| `show queue persistent-watermark multicast [options]` | multicast queue persistent watermark |
| `show queue persistent-watermark all [options]` | 全 queue persistent watermark |

## counters

**用法**:

```
show queue counters [INTERFACE_NAME]
    [--namespace <ns>] [--all] [--trim] [--voq]
    [--nonzero] [--json] [--verbose]
```

実行コマンドは `queuestat`。interface 指定時は `-p <port>`、namespace は `-n`、`--all` は `-a`、`--trim` は `-T`、`--voq` は `-V`、`--nonzero` は `-nz`、`--json` は `-j` に変換される。

## wredcounters

**用法**:

```
show queue wredcounters [INTERFACE_NAME]
    [--namespace <ns>] [--json] [--voq]
    [--nonzero] [--summary] [--verbose]
```

実行コマンドは `wredstat`。`--summary` は `-s`、その他は counters と同じ変換。

## watermark

`watermark` は `watermarkstat -t q_shared_uni|q_shared_multi|q_shared_all` を実行する。`persistent-watermark` はさらに `-p` を追加する。各 command は `--namespace` と `--json` を受け付ける。

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: `show queue` グループと配下 command。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L774>
