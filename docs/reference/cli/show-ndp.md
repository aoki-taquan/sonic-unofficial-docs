---
title: show ndp サブコマンド
description: show ndp サブコマンド — show ndp は IPv6 の Neighbor Discovery テーブルを表示する click
  コマンド。show arp と対称な実装で、内部では scripts/nbrshow を -6 付きで起動する。
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
- repo: sonic-net/sonic-utilities
  path: clear/main.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
  - show arp
  - sonic-clear ndp
  yang:
  - sonic-neigh
  _no_related_config_db: true
---

# show ndp サブコマンド

## 概要

`show ndp` は IPv6 の **Neighbor Discovery テーブル**を表示する click コマンド。`show arp` と対称な実装で、内部では `scripts/nbrshow` を `-6` 付きで起動する[^1]。

## シグネチャ

```bash
show ndp [<ip6address>] [-if <iface>] [-n <namespace>] [-d <display>] [--verbose]
```

| オプション | 意味 |
|---|---|
| `<ip6address>` (positional, optional) | 絞り込む IPv6 アドレス |
| `-if`, `--iface` | インタフェース名フィルタ |
| `-n`, `--namespace` | multi-[ASIC](../../reference/glossary.md#term-asic) 時の namespace |
| `-d`, `--display` | 表示スコープ (`all` / `frontend` など) |
| `--verbose` | 起動コマンド文字列を echo |

## 起動コマンド

```python
cmd = ['nbrshow', '-6']
if ip6address: cmd += ['-ip', str(ip6address)]
if iface:      cmd += ['-if', str(iface)]
if namespace:  cmd += ['-n', str(namespace)]
cmd += ['-d', str(display)]
```

注意: `show arp` 側は `alias` モード時に `iface_alias_converter.alias_to_name()` でインタフェース名を変換するロジックがあるが、**`show ndp` 側にはそれが無い**。`alias` モード環境で `-if` を使う場合、内部名（例: `Ethernet0`）を直接指定する必要がある。

## 別名と関連

`show ndp` は `cli` ルート直下に登録されている (`@cli.command()`) のみで、master 時点では `show ipv6` グループ配下にエイリアス登録されていない[^2]。同グループのサブコマンドは `interfaces` / `prefix-list` / `route` / `protocol` (および routing-stack に応じた `bgp`) で、IPv6 近隣テーブル参照は `show ndp` が唯一のエントリポイント。

IPv4 側の対称コマンドは [`show arp`](show-arp.md) で、同じく `nbrshow` を `-4` 付きで呼び出す。クリア側は `sonic-clear ndp [<ipaddress>] [-n <ns>]` (内部で `ip -6 neigh del` を実行)[^3]。詳細は [clear (sonic-clear) コマンド](clear.md) を参照。

## CONFIG_DB との接点

[NDP](../../reference/glossary.md#term-ndp) テーブルは **kernel の IPv6 neighbor table** および swss/[neighsyncd](../../reference/glossary.md#term-neighsyncd) で [APPL_DB](../../reference/glossary.md#term-appl_db) に同期されるもので、[CONFIG_DB](../../reference/glossary.md#term-config_db) を読まない。

<!-- cli-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  CLI["show ndp"]
  SRC0[("APPL_DB<br/>NEIGH_TABLE")]
  V0["nbrshow (-6)"]
  SRC0 --> V0 --> CLI
```

!!! note "凡例"
    show 系 (データソース → ラッパスクリプト → CLI) のミニ図。CONFIG_DB は経由しない。
<!-- /cli-mermaid -->

<!-- ref-triangle:start -->

## 関連リファレンス

- (関連リンクなし)

<!-- ref-triangle:end -->

## 引用元

[^1]: `ndp` の click 定義と `nbrshow -6` 起動は `show/main.py` L452-L472。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L452>

[^2]: `ipv6` グループの定義と subcommand 列挙 (`prefix-list` / `interfaces` / `route` / `protocol`) は `show/main.py` L1495-L1565。`ipv6.add_command(ndp)` 相当の登録は無く、`ipv6.add_command(bgp)` のみが routing-stack 依存で行われる (L1571 周辺)。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L1495>

[^3]: `sonic-clear ndp` の実装は `clear/main.py` L553-L580 で、`ip -6 neigh show` で dev を引いた後 `ip -6 neigh del` を実行する。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/clear/main.py#L553>

<!-- ops-hint -->
## 運用ヒント

### 典型的な利用シーン

- IPv6 隣接の NS/NA 状態確認、SLAAC 動作検証。

### よくある落とし穴

- Link-local アドレスは scope 付き表示。`fe80::xxx%Ethernet0` の `%` 以降は interface scope。
- Duplicate Address Detection (DAD) 失敗時は state が `FAILED` で kernel に残る。

### 関連する show / debug

```bash
show ndp
ip -6 neigh show
sonic-db-cli APPL_DB keys 'NEIGH_TABLE:*'
```
<!-- /ops-hint -->

<!-- cli-sibling -->
<!-- cli-sibling:manual -->
### 関連 CLI コマンド

- [`show arp`](show-arp.md) — IPv4 ARP テーブル表示 (`nbrshow -4`、対称コマンド)
- [`clear`](clear.md) — `sonic-clear ndp` を含むクリア系コマンド群
- [`show ip`](show-ip.md) — `show ip` グループ (route / interfaces / bgp など)

<!-- /cli-sibling -->

<!-- glossary-links-injected: c006405759d8 -->
