---
title: config checkpoint サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
    - config checkpoint
    - config rollback
    - config list-checkpoints
    - config delete-checkpoint
  yang: []
---

# config checkpoint サブコマンド

## 概要

`config checkpoint` は **現在の CONFIG_DB スナップショットを名前付きで保存** する。後で `config rollback <name>` でこの時点まで戻せる。実装は `config/main.py:checkpoint()`[^1]。

## シグネチャ

```
config checkpoint <checkpoint-name> [-v|--verbose]
```

| 引数/オプション | 意味 |
|----|------|
| `<checkpoint-name>` | チェックポイント名 (必須) |
| `-v`, `--verbose` | 内部処理の詳細出力 |

## 処理フロー

1. `GenericUpdater().checkpoint(checkpoint_name, verbose)` を呼び出し
    - 内部で **現行 CONFIG_DB をダンプ** し、デフォルトのチェックポイント保存ディレクトリへ JSON で保存
2. 成功時 `Checkpoint created successfully.` を cyan で出力。失敗時は `ctx.fail(ex)` で abort

## 関連サブコマンド

| コマンド | 役割 |
|---------|-----|
| `config list-checkpoints [-t]` | 既存チェックポイント一覧 (`-t` で last modified time 付き) |
| `config rollback <name>` | 名前付きチェックポイントまで CONFIG_DB を巻き戻す (差分置換) |
| `config delete-checkpoint <name>` | チェックポイント削除 |

## 注意

- チェックポイント保存先は `GenericUpdater` の実装依存 (`/etc/sonic/checkpoints/` 系) で、ホスト側ファイルシステム上に永続化される
- ロールバックは `config replace` と同じ差分置換 (`GenericUpdater().rollback()`) で disruption を最小化する
- 同名のチェックポイントを上書きできるかは `GenericUpdater` の実装依存 (例外を上げる場合あり)

## CONFIG_DB との接点

CONFIG_DB を READ のみ (チェックポイント保存)。書き込みは `rollback` 時のみ。

<!-- ref-triangle:start -->

## 関連リファレンス

- CLI: [`config replace`](config-replace.md), [`config save`](config-save.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `checkpoint()` 実装は `config/main.py` L2061-L2075、`rollback()` は L2038-L2059、`list-checkpoints` は L2093-L2106、`delete-checkpoint` は L2077-L2091。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L2061>
