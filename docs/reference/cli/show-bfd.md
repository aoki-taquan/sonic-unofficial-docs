---
title: show bfd サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db: []
  cli:
    - show bfd
  yang: []
---

# show bfd サブコマンド

## 概要

`show bfd` は STATE_DB の `BFD_SESSION_TABLE` を読み出し、BFD (Bidirectional Forwarding Detection) セッションの状態を表示する CLI グループ[^1]。BFD セッションの生成は FRR / orchagent 側で行われ、`show bfd` は state を読むだけの参照系コマンド。

multi-ASIC 環境では `--namespace` でスコープを指定でき、未指定時は全 ASIC の合計が表示される。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show bfd summary [-n <namespace>]` | 全 BFD セッションのサマリ表示 |
| `show bfd peer <peer_ip> [-n <namespace>]` | 指定 peer IP の BFD セッション情報 |

## 各コマンドの詳細

### `show bfd summary`

**用法**:

```
show bfd summary [-n|--namespace <namespace>]
```

**動作**:
STATE_DB から `BFD_SESSION_TABLE|*` を全件取得する。multi-ASIC では namespace 一覧を `multi_asic.get_namespace_list()` から得て、各 namespace を順次走査する[^2]。

表示カラムは:

| カラム | STATE_DB のフィールド/key |
|--------|----------------------------|
| Peer Addr | key 4 番目 |
| Interface | key 3 番目 |
| Vrf | key 2 番目 |
| State | `state` |
| Type | `type` |
| Local Addr | `local_addr` |
| TX Interval | `tx_interval` |
| RX Interval | `rx_interval` |
| Multiplier | `multiplier` |
| Multihop | `multihop` |
| Local Discriminator | `local_discriminator` (欠落時は `NA`) |

key の形式は `BFD_SESSION_TABLE|<vrf>|<interface>|<peer_ip>`。

### `show bfd peer <peer_ip>`

**用法**:

```
show bfd peer <peer_ip> [-n|--namespace <namespace>]
```

**動作**:
`BFD_SESSION_TABLE|*|<peer_ip>` の key を STATE_DB から拾い上げ、見つからなければ `No BFD sessions found for peer IP <peer_ip>` を表示。同じ peer IP で複数 VRF / interface のセッションが返ることがある。

<!-- evidence:
source: sonic-net/sonic-utilities/show/main.py#L2713-L2746 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @bfd.command()
  def peer(db, peer_ip, namespace):
      bfd_keys = db.db_clients[namespace].keys(db.db.STATE_DB, "BFD_SESSION_TABLE|*|{}".format(peer_ip))
      ...
      if bfd_keys is None or len(bfd_keys) == 0:
          click.echo("No BFD sessions found for peer IP {}".format(peer_ip))
-->

## 注意

- `show bfd summary` は STATE_DB のみを参照する。CONFIG_DB 上の `BFD_SESSION` テーブルとは表示が一致しない場合がある（admin shut 状態など）。
- `show bfd peer <peer_ip>` の `<peer_ip>` には IPv6 (例 `fe80::1`) も渡せる。

## 引用元

[^1]: `show bfd` グループ定義は `show/main.py` L2671-L2746。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L2671>

[^2]: multi-ASIC スコープ判定 ロジック。`show/main.py` L2686-L2692。
