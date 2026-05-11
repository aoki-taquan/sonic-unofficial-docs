---
title: config save サブコマンド
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
    - config save
    - config load
    - config reload
  yang: []
---

# config save サブコマンド

## 概要

`config save` は **現在の CONFIG_DB を JSON ファイルに書き出す**。multi-ASIC 環境では複数 namespace を別ファイルに保存できる。実装は `config/main.py:save()`[^1]。

## シグネチャ

```
config save [-y|--yes] [<filename>]
```

| 引数/オプション | 意味 |
|----|------|
| `-y`, `--yes` | 上書きプロンプトをスキップ |
| `<filename>` | 出力ファイル名。multi-ASIC では `,` 区切りで複数指定 (host + 各 namespace ASIC) |

`<filename>` 未指定時のデフォルト:

- host namespace: `/etc/sonic/config_db.json` (`DEFAULT_CONFIG_DB_FILE`)
- ASIC namespace `N`: `/etc/sonic/config_db<N>.json`

## 処理フロー

1. multi-ASIC かどうか判定し、必要な config ファイル数 `num_cfg_file` を算出
2. `<filename>` が単一かつ multi-ASIC の場合は `multiasic_save_to_singlefile()` で全 namespace を 1 ファイルに集約して終了
3. それ以外は namespace ごとに以下を実行
    - `sonic-cfggen [-n <ns>] -d --print-data > <file>` で CONFIG_DB ダンプ
    - `sort_dict()` でキーをソートして再書き出し (差分の安定化目的)
    - `os.fsync()` でディスクに同期

## 注意

- 上書き確認プロンプトはデフォルトで出る (`-y` で抑止)
- 単一ファイル指定 (`<filename>` 個数 1) で multi-ASIC の場合は `multiasic_save_to_singlefile()` 経路に分岐し、内部フォーマットが namespace ごとのキーを持つ集約 JSON になる[^1]
- `config save` は CONFIG_DB を読むだけで、再起動や service への通知は行わない

## CONFIG_DB との接点

CONFIG_DB を `sonic-cfggen -d --print-data` で読み出すのみ (書き込みは行わない)。

<!-- ref-triangle:start -->

## 関連リファレンス

- CLI: [`config reload` 系](config-default-route.md) (実装は同一ファイル内)

<!-- ref-triangle:end -->

## 引用元

[^1]: `save()` 実装は `config/main.py` L1789-L1849。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L1789>
