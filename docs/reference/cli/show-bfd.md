---
title: show bfd サブコマンド
description: "show bfd サブコマンド — show bfd は BFD (Bidirectional Forwarding Detection) セッションの状態を表示するグループ。データ源は STATE_DB の BFD_SESSION_TABLE||| であり、CONFIG_DB ではない。"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-utilities
    path: show/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - BFD_SESSION_TABLE
  cli:
    - show bfd
  yang: []
---

# show bfd サブコマンド

## 概要

`show bfd` は BFD (Bidirectional Forwarding Detection) セッションの状態を表示するグループ。データ源は **STATE_DB** の `BFD_SESSION_TABLE|<vrf>|<interface>|<peer>` であり、CONFIG_DB ではない[^1]。BFD セッションは BGP や static route との連動で動的に生成・破棄されるため、状態は STATE_DB のみが正となる。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `show bfd summary` | 全 BFD セッションの一覧 |
| `show bfd peer <peer_ip>` | 指定 peer IP のセッションのみ表示 |

## 各コマンドの詳細

### `show bfd summary`

**用法**:

```
show bfd summary [-n|--namespace <ns>]
```

**オプション**:

- `-n / --namespace` ... multi-ASIC 環境での namespace 指定（`multi_asic_namespace_validation_callback` で検証）

**動作**:
multi-ASIC 環境では `multi_asic.get_namespace_list()` を全走査、それ以外は `DEFAULT_NAMESPACE` のみ。各 namespace の STATE_DB から `BFD_SESSION_TABLE|*` の全キーを列挙し、`local_discriminator` が無い場合は `NA` を補って表示する[^2]。

**表示カラム**:

```
Peer Addr | Interface | Vrf | State | Type | Local Addr |
TX Interval | RX Interval | Multiplier | Multihop | Local Discriminator
```

key 構造: `BFD_SESSION_TABLE|<vrf>|<interface>|<peer_addr>`、splitting で `key_values[3]=peer`, `key_values[2]=interface`, `key_values[1]=vrf`。

<!-- evidence:
source: sonic-net/sonic-utilities/show/main.py#L2682-L2710 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @bfd.command()
  def summary(db, namespace):
      ...
      for ns in namespace_list:
          bfd_keys = db.db_clients[ns].keys(db.db.STATE_DB, "BFD_SESSION_TABLE|*")
          ...
          for key in bfd_keys:
              key_values = key.split('|')
              values = db.db_clients[ns].get_all(db.db.STATE_DB, key)
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-utilities/show/main.py#L2682-L2710 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)"

    **出典**:

    `sonic-net/sonic-utilities/show/main.py#L2682-L2710 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)`

    **抜粋**:

    ```text
    @bfd.command()
    def summary(db, namespace):
        ...
        for ns in namespace_list:
            bfd_keys = db.db_clients[ns].keys(db.db.STATE_DB, "BFD_SESSION_TABLE|*")
            ...
            for key in bfd_keys:
                key_values = key.split('|')
                values = db.db_clients[ns].get_all(db.db.STATE_DB, key)
    ```

<!-- evidence-rendered:end -->

### `show bfd peer <peer_ip>`

**用法**:

```
show bfd peer <peer_ip> [-n|--namespace <ns>]
```

**引数**:

- `<peer_ip>` ... 必須。表示対象 BFD peer の IP アドレス

**動作**:
`BFD_SESSION_TABLE|*|<peer_ip>` でフィルタリングして該当セッションのみ表示。同じ peer に対して複数 VRF / interface のセッションが存在し得るため、複数行が返ることがある。該当セッションが無ければ `No BFD sessions found for peer IP <peer_ip>`。

## 関連する STATE_DB

| テーブル / key | フィールド |
|----------------|------------|
| `BFD_SESSION_TABLE|<vrf>|<interface>|<peer>` | `state`, `type`, `local_addr`, `tx_interval`, `rx_interval`, `multiplier`, `multihop`, `local_discriminator` |

## 補足

- BFD セッションの **生成・削除** は `show bfd` のスコープ外。BGP/static route 側の設定や `bfdsyncd` の動作による
- `local_discriminator` は古い実装では存在しないため `NA` に置換するガードがある

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: `BFD_SESSION_TABLE`

<!-- ref-triangle:end -->

## 引用元

[^1]: STATE_DB を参照する `db.db_clients[ns].keys(db.db.STATE_DB, "BFD_SESSION_TABLE|*")` のロジック。

[^2]: <https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/show/main.py#L2672>

## 関連ページ

- [reference/CLI: show bgp](show-bgp.md)
- [reference/CLI: show ip](show-ip.md)
