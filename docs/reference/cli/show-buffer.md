---
title: show buffer サブコマンド
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
    - show buffer
  yang: []
---

# show buffer サブコマンド

## 概要

`show buffer` は buffer 設定・状態の表示を `mmuconfig` に委譲する CLI グループ。`show/main.py` では `show buffer configuration` が定義され、namespace と verbose を `mmuconfig -l` に渡す[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show buffer configuration [--namespace <ns>] [--verbose]` | buffer configuration を表示 |

## 詳細

**用法**:

```
show buffer configuration [--namespace <ns>|--namespace all] [--verbose]
```

実行コマンドは次の通り。

```
mmuconfig -l [-n <namespace>] [-vv]
```

`--namespace` は multi-ASIC namespace 名または `all` を受け付ける。`--verbose` は `mmuconfig` に `-vv` を渡す。

## 注意

- `show buffer_pool` と `show headroom-pool` は別の top-level group。
- 実際に表示される項目は `mmuconfig` 側の実装と platform の buffer model に依存する。

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: `show buffer` と `configuration` command の定義。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L2466>
