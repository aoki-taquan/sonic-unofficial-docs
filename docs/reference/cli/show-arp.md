---
title: show arp サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
  - repo: sonic-net/sonic-utilities
    path: scripts/nbrshow
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
    - show arp
    - show ip arp
    - clear arp
  yang: []
---

# show arp サブコマンド

## 概要

`show arp` は IPv4 の **隣接テーブル（ARP テーブル）**を表示する click コマンド。実装は単なる薄いラッパで、内部では `scripts/nbrshow` を `-4` 付きで起動する[^1]。`nbrshow` 側が APPL_DB の `NEIGH_TABLE` と kernel の `ip neigh` 出力を突き合わせて表形式に整形する。

## シグネチャ

```
show arp [<ipaddress>] [-if <iface>] [-n <namespace>] [-d <display>] [--verbose]
```

| オプション | 意味 |
|---|---|
| `<ipaddress>` (positional, optional) | 1 エントリのみ絞り込む IPv4 アドレス |
| `-if`, `--iface` | インタフェース名でフィルタ。`alias` モード時は `iface_alias_converter.alias_to_name()` で内部名へ変換 |
| `-n`, `--namespace` | multi-ASIC 時の namespace 指定（`multi_asic_click_options` 由来） |
| `-d`, `--display` | `all` / `frontend` 等の display スコープ |
| `--verbose` | 起動する `nbrshow` コマンド文字列を echo |

## 起動コマンド

```python
cmd = ['nbrshow', '-4']
if ipaddress: cmd += ['-ip', str(ipaddress)]
if iface:     cmd += ['-if', str(iface)]      # alias 名は内部名に変換
if namespace: cmd += ['-n', str(namespace)]
cmd += ['-d', str(display)]
```

`nbrshow` 自体は Python スクリプトで、`scripts/nbrshow` に置かれている。

## 別名と関連

`show ip arp` も同じ `arp` コマンドを `show ip` グループに `add_command` した結果として動く（cli 直下と `ip` サブ両方に同じ関数が登録される）。

クリア側は `sonic-clear arp [<ipaddress>] [-n <ns>]` が対称。詳細は [clear (sonic-clear) コマンド](clear.md) を参照。

## CONFIG_DB との接点

ARP テーブルは **kernel の neighbor table**（および swss/neighsyncd 経由で APPL_DB の `NEIGH_TABLE` に同期）で管理されるため、`show arp` 自体は CONFIG_DB を読まない。

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: `arp` の click 定義と `nbrshow -4` 起動部分は `show/main.py` L421-L446。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L421>
