---
title: config load サブコマンド
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
    - config load
    - config save
    - config reload
  yang: []
---

# config load サブコマンド

## 概要

`config load` は **保存済み config DB JSON を CONFIG_DB に追加投入** する。`config reload` と異なり **既存 CONFIG_DB を flush しない** 点が特徴 (追記マージ)。実装は `config/main.py:load()`[^1]。

## シグネチャ

```
config load [-y|--yes] [<filename>]
```

| 引数/オプション | 意味 |
|----|------|
| `-y`, `--yes` | 確認プロンプトをスキップ |
| `<filename>` | 入力ファイル名。multi-ASIC では `,` 区切りで複数 (host + 各 namespace ASIC)。未指定時はデフォルトパス |

`<filename>` 未指定時のデフォルト:

- host: `/etc/sonic/config_db.json`
- ASIC namespace `N`: `/etc/sonic/config_db<N>.json`

## 処理フロー

1. 確認プロンプト (デフォルトはファイル名を含むメッセージ、`-y` で抑止)
2. multi-ASIC かどうか判定し `num_cfg_file` 算出
3. namespace ごとに以下を実行
    - ファイル存在チェック (なければスキップ)
    - `sonic-cfggen [-n <ns>] -j <file> --write-to-db` を実行し、JSON を CONFIG_DB に書き込む

## 注意

- **既存 CONFIG_DB は flush されない**。完全にクリア → ロードしたい場合は `config reload` を使う
- service 再起動は行わない (`reload` は行う)
- ファイル不在は警告 echo のみで処理続行 (該当 namespace スキップ)
- `-y` を付けない場合は `click.confirm(..., abort=True)` で abort 可

## CONFIG_DB との接点

`sonic-cfggen -j <file> --write-to-db` 経由で **CONFIG_DB に書き込む** 。READ は行わない。

<!-- ref-triangle:start -->

## 関連リファレンス

- CLI: [`config save`](config-save.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `load()` 実装は `config/main.py` L1851-L1910。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/main.py#L1851>
