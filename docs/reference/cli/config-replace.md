---
title: config replace サブコマンド
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
    - config replace
    - config rollback
    - config checkpoint
    - config apply-patch
  yang: []
---

# config replace サブコマンド

## 概要

`config replace` は **`GenericUpdater` を介して現行 CONFIG_DB をターゲット JSON で差分置換** する。disruption を最小化し、変更のあるテーブル/エントリのみを更新する。実装は `config/main.py:replace()`[^1]。

## シグネチャ

```
config replace <target-file-path>
               [-f|--format CONFIGDB|SONICYANG]
               [-d|--dry-run]
               [-n|--ignore-non-yang-tables]  (hidden)
               [-i|--ignore-path <JsonPointer>]  (hidden, multiple)
               [-v|--verbose]
               [-t|--path-trace <PATH>]  (hidden)
```

| 引数/オプション | 意味 |
|----|------|
| `<target-file-path>` | 置換先となる **完全な** config JSON (差分ではない) |
| `-f`, `--format` | `CONFIGDB` (ABNF 形式 / デフォルト) または `SONICYANG` |
| `-d`, `--dry-run` | 実際の書き込みを行わず差分計算のみ |
| `-n`, `--ignore-non-yang-tables` | YANG model のないテーブルの validation を無視 (hidden) |
| `-i`, `--ignore-path <ptr>` | 指定 JsonPointer 配下の validation を無視 (複数指定可、hidden) |
| `-v`, `--verbose` | 内部処理の詳細出力 |
| `-t`, `--path-trace <PATH>` | patch 生成の決定パスを JSON で出力 (hidden) |

## 処理フロー

1. `print_dry_run_message()` で dry-run バナー (該当時)
2. ターゲットファイルを読み込み JSON parse
3. `--path-trace` 指定時、出力先ファイルを open
4. `GenericUpdater().replace(target_config, format, verbose, dry_run, ignore_non_yang_tables, ignore_path, trace_io=...)` を実行
    - 内部で **JSON patch** を生成し、依存順 sort 後にテーブル単位で `ConfigDBConnector` 経由で適用
    - YANG validation を実行 (`ignore_*` で部分 skip 可能)
5. 成功時に `Config replaced successfully.` を cyan で表示。例外は `ctx.fail(ex)` で abort

## 注意

- **target-file は完全な config** でなければならない (一部の更新は `config apply-patch` を使う)
- ACL のみが変わる場合は ACL テーブルのみ更新され、DHCP など他 service には影響しない (最小 disruption 設計)
- multi-ASIC: `GenericUpdater` 自体が namespace を扱う設計だが、フォーマットは ConfigDB のキー構造に従う

## CONFIG_DB との接点

`GenericUpdater` 経由で CONFIG_DB を**差分書き込み**。差分計算には YANG model が使われる。

<!-- ref-triangle:start -->

## 関連リファレンス

- CLI: [`config checkpoint`](config-checkpoint.md), [`config save`](config-save.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `replace()` 実装は `config/main.py` L1981-L2036。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L1981>
