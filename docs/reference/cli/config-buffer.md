---
title: config buffer サブコマンド
description: "config buffer サブコマンド — config buffer は dynamic buffer が有効なシステムで、CONFIG_DB の BUFFER_PROFILE を追加・更新する CLI グループ。"
area: reference
verification: code-verified
last_verified: 2026-05-10
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - BUFFER_PROFILE
    - BUFFER_POOL
    - DEFAULT_LOSSLESS_BUFFER_PARAMETER
  cli:
    - config buffer
  yang: []
---

# config buffer サブコマンド

## 概要

`config buffer` は dynamic buffer が有効なシステムで、CONFIG_DB の `BUFFER_PROFILE` を追加・更新する CLI グループ。グループ入口で `DEVICE_METADATA|localhost` の `buffer_model` を確認し、dynamic 以外では実行を拒否する[^1]。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config buffer profile add <profile> [options]` | `BUFFER_PROFILE|<profile>` を新規作成 |
| `config buffer profile set <profile> [options]` | 既存 profile を更新 |

## 各コマンドの詳細

### `config buffer profile add <profile>`

**用法**:

```
config buffer profile add <profile>
    [--xon <bytes>]
    [--xoff <bytes>]
    [--size <bytes>]
    [--dynamic_th <value>]
    [--pool <pool>]
```

`BUFFER_PROFILE|<profile>` が既に存在する場合はエラー。存在しない場合、`update_profile()` を通じて `pool`, `xon`, `xoff`, `size`, `dynamic_th` を組み立て、`ValidatedConfigDBConnector` で CONFIG_DB に書き込む[^2]。

`--pool` を省略すると `ingress_lossless_pool` が使われる。指定 pool は `BUFFER_POOL` に存在する必要がある。

### `config buffer profile set <profile>`

**用法**:

```
config buffer profile set <profile>
    [--xon <bytes>]
    [--xoff <bytes>]
    [--size <bytes>]
    [--dynamic_th <value>]
    [--pool <pool>]
```

既存 `BUFFER_PROFILE|<profile>` を更新する。profile が存在しなければエラー。既存 profile が `xoff` を持たない dynamic headroom 計算型の場合、`--xoff` を指定して非 dynamic 型へ変える操作は拒否される[^3]。

## 関連する CONFIG_DB

| テーブル | キー | 操作 |
|----------|------|------|
| `BUFFER_PROFILE` | `<profile>` | profile の作成・更新 |
| `BUFFER_POOL` | `<pool>` | 指定 pool の存在確認 |
| `DEFAULT_LOSSLESS_BUFFER_PARAMETER` | 任意 | shared headroom pool 判定 |

## 注意

- `config interface buffer priority_group ...` と `config interface buffer queue ...` は別グループで、port 上の `BUFFER_PG` / `BUFFER_QUEUE` バインドを操作する。本ページは root の `config buffer profile` を対象にする。
- CLI 抽出上の `config buffer priority-group` / `queue` 候補は、実装上は `config interface buffer ...` 配下にある。

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`BUFFER_PROFILE`](../config-db/buffer-profile.md) / [`BUFFER_POOL`](../config-db/buffer-pool.md) / [`DEFAULT_LOSSLESS_BUFFER_PARAMETER`](../config-db/default-lossless-buffer-parameter.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `config buffer` グループ定義と dynamic buffer チェック。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L8481>

[^2]: `profile add` は既存 entry を確認してから `update_profile()` を呼ぶ。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L8494>

[^3]: `profile set` の存在確認と `xoff` 変更制限。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L8514>
