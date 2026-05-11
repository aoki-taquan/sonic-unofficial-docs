---
title: show uptime サブコマンド
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
    - show uptime
    - show version
  yang: []
---

# show uptime サブコマンド

## 概要

`show uptime` は **システムの稼働時間**を `uptime -p` で「pretty 形式」で表示する click コマンド[^1]。出力例: `up 3 weeks, 2 days, 4 hours, 15 minutes`。

## シグネチャ

```
show uptime [--verbose]
```

| オプション | 意味 |
|---|---|
| `--verbose` | 起動コマンド文字列を echo |

## 実装

```python
@cli.command()
@click.option('--verbose', is_flag=True, help="Enable verbose output")
def uptime(verbose):
    """Show system uptime"""
    cmd = ['uptime', '-p']
    run_command(cmd, display_cmd=verbose)
```

`-p` は GNU procps の `uptime` が解釈するオプションで、`12:34:56 up 3 days, 4:15, 2 users, load average: ...` の形式ではなく `up 3 days, 4 hours, 15 minutes` のような可読形式を出す。

## 関連

`show version` も内部で `uptime`（フラグなし）を呼び、`Uptime: 12:34:56 up 3 days, 4:15, 2 users, load average: ...` として組み込まれる。フル稼働状況とロードアベレージまで欲しい場合は `show version` の方が情報量が多い。

## CONFIG_DB との接点

なし（kernel の `/proc/uptime` を読む `uptime(1)` のラッパ）。

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: `uptime` コマンドの実装は `show/main.py` L2211-L2216。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L2211>
