---
title: config pfcwd サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
    - config pfcwd
    - pfcwd
  yang: []
---

# config pfcwd サブコマンド

## 概要

`config pfcwd` は PFC watchdog の設定操作を `pfcwd` 実行ファイルへ委譲するラッパー。Click 側で範囲・選択肢を検証し、実際の CONFIG_DB 更新や daemon 連携は `pfcwd` 側が担う[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config pfcwd start [options] <ports>... <detection-time>` | port 群で PFC watchdog を開始 |
| `config pfcwd stop` | PFC watchdog を停止 |
| `config pfcwd interval <poll_interval>` | counter polling 間隔を設定 |
| `config pfcwd counter_poll enable\|disable` | counter polling を有効/無効化 |
| `config pfcwd big_red_switch enable\|disable` | BIG_RED_SWITCH mode を有効/無効化 |
| `config pfcwd pfc_stat_history enable\|disable [ports]...` | historical statistics を有効/無効化 |
| `config pfcwd start_default` | default 設定で PFC watchdog を開始 |

## 各コマンドの詳細

### `config pfcwd start`

**用法**:

```
config pfcwd start [--action drop|forward|alert]
                   [--restoration-time <100-60000>]
                   [--pfc-stat-history]
                   [--verbose]
                   <ports>... <detection-time>
```

`<detection-time>` は 100-5000 ms。`--restoration-time` は 100-60000 ms。`ports` には個別 port または `all` を渡す想定で、CLI は `pfcwd start ...` を組み立てて実行する[^2]。

### その他の設定

- `stop` は `pfcwd stop` を実行する。
- `interval <poll_interval>` は 100-1000 ms の範囲を Click で検証し、`pfcwd interval <poll_interval>` を実行する。
- `counter_poll`, `big_red_switch`, `pfc_stat_history` は `enable` / `disable` のみ受け付ける。
- `start_default` は `pfcwd start_default` を実行する。

## 注意

- このページで扱う `config pfcwd` は wrapper であり、DB table 名や永続化の詳細は `pfcwd` 側の実装に依存する。
- `show pfcwd config` / `show pfcwd stats` も同じ `pfcwd` 実行ファイルへ委譲される。

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: `config pfcwd` グループと各 command は `config/main.py` の PFC watchdog セクションで定義される。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L3450>

[^2]: `start` は Click の range/choice 検証後、`pfcwd start` に引数を渡す。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L3454>

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: QoS / Buffer / PFC / Watermark](../../topics/08-qos-buffer/index.md)

<!-- /topics-back-ref -->
