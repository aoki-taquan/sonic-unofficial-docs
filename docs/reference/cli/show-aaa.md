---
title: show aaa サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - AAA
  cli:
    - show aaa
    - show tacacs
    - show radius
    - config aaa
  yang:
    - sonic-aaa
---

# show aaa サブコマンド

## 概要

`show aaa` は CONFIG_DB の **`AAA` テーブル**を読み、`authentication` / `authorization` / `accounting` 各機能の現在値（または default 値）を行ごとに表示する click コマンド[^1]。`show tacacs` / `show radius` とセットで運用する。

## シグネチャ

```
show aaa
```

引数・オプションなし。

## 動作

1. `db.cfgdb.get_table('AAA')` で `AAA` テーブルを取得。
2. 内部に以下のデフォルト辞書を用意:

   ```python
   aaa = {
       'authentication': {
           'login':       'local (default)',
           'failthrough': 'False (default)',
       },
       'authorization': {
           'login': 'local (default)',
       },
       'accounting': {
           'login': 'disable (default)',
       },
   }
   ```

3. CONFIG_DB 側に `authentication` / `authorization` / `accounting` 各 row があれば、それで上記辞書を `update()` で上書き。
4. `AAA <function> <key> <value>` の形式で 1 行ずつ `click.echo()` する。

例:

```
AAA authentication login tacacs+,local
AAA authentication failthrough True
AAA authorization login tacacs+
AAA accounting login tacacs+
```

CONFIG_DB に該当キーが無ければ `(default)` 表記のまま出る（実装上、上書きされなかった項目に対しては default 文字列がそのまま残る）。

## CONFIG_DB との接点

| テーブル | キー | 説明 |
|---|---|---|
| `AAA` | `authentication` / `authorization` / `accounting` | `login` / `failthrough` などの値を保持。`config aaa` 系コマンドで書き込まれる |

書き込み側は `config/aaa.py` 経由。実サーバ定義は `TACPLUS` / `TACPLUS_SERVER` / `RADIUS` / `RADIUS_SERVER` 等の別テーブルにあり、それぞれ `show tacacs` / `show radius` で表示する。

<!-- ref-triangle:start -->

## 関連リファレンス

- YANG: `sonic-aaa`
- CONFIG_DB: [`AAA`](../config-db/aaa.md)

<!-- ref-triangle:end -->

## 引用元

[^1]: `aaa()` コマンドの実装は `show/main.py` L2269-L2299。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L2269>
