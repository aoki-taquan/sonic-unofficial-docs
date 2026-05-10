---
title: config vlan サブコマンド
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-utilities
    path: config/vlan.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
  - repo: sonic-net/sonic-utilities
    path: config/main.py
    ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  config_db:
    - VLAN
    - VLAN_MEMBER
    - VLAN_INTERFACE
    - DHCP_RELAY
    - STP_VLAN
    - STP_VLAN_PORT
    - STP_PORT
  cli:
    - config vlan
    - config vlan member
  yang: []
---

# config vlan サブコマンド

## 概要

`config vlan` は VLAN の作成・削除、メンバ追加・削除、Proxy-ARP のオン／オフを担当する。`config/vlan.py` に実装が分離されており、`config/main.py` 末尾の `config.add_command(vlan.vlan)` で登録される構造[^1]。

新規 VLAN 作成時は `VLAN` テーブルだけでなく **`DHCP_RELAY` テーブルにも空エントリを書き込む**仕様。これは `dhcp_relay` の対象 VLAN が `VLAN` テーブルではなく `DHCP_RELAY` テーブルから引かれるための互換的な設計。

## コマンド一覧

| コマンド | 用途 |
|---------|------|
| `config vlan add <vid>` | VLAN を作成 |
| `config vlan del <vid>` | VLAN を削除 |
| `config vlan proxy_arp <vid> <enabled\|disabled>` | VLAN_INTERFACE の proxy ARP を切替 |
| `config vlan member add <vid> <port>` | VLAN にポートをメンバ追加 |
| `config vlan member del <vid> <port>` | VLAN メンバを削除 |

## 各コマンドの詳細

### `config vlan add <vid> [-m|--multiple]`

**用法**:

```
config vlan add <vid> [-m|--multiple]
```

**引数**:

- `<vid>` ... 単一 VLAN ID（2-4094 の整数）。`-m` 指定時は `100,200,300` や `100-110` のような複数指定が可能

**動作**:

1. `is_vlanid_in_range` で VLAN ID が `2-4094` であることを検証（`1` は default として弾く）
2. 既存 `VLAN` エントリ・`DHCP_RELAY` エントリと衝突しないか確認
3. PVST がグローバルに有効なら `stp.vlan_enable_stp` で `STP_VLAN` を埋める
4. `set_dhcp_relay_table('VLAN', ...)` で **`VLAN` テーブルと `DHCP_RELAY` テーブル両方**に `Vlan<vid>` のエントリを作成

<!-- evidence:
source: sonic-net/sonic-utilities/config/vlan.py#L95-L141 (sha: 39732bceb8bdefe706518ab40623bbbba6ff33b9)
excerpt: |
  @vlan.command('add')
  def add_vlan(ctx, vid, multiple):
      ...
      stp.vlan_enable_stp(config_db, vlan)
      set_dhcp_relay_table('VLAN', config_db, vlan, {'vlanid': str(vid)})
-->

### `config vlan del <vid> [-m|--multiple] [--no_restart_dhcp_relay]`

**用法**:

```
config vlan del <vid> [-m|--multiple] [--no_restart_dhcp_relay]
```

**動作**:
`VLAN_MEMBER` 配下の関連エントリ、`VLAN_INTERFACE`、`STP_VLAN` / `STP_VLAN_PORT`、最後に `VLAN` 本体を順に削除する。`--no_restart_dhcp_relay` 指定時は `dhcp_relay` サービスの再起動を抑制（DHCPv6 Relay 設定が空であることが前提）。

### `config vlan proxy_arp <vid> <enabled|disabled>`

**動作**:
`VLAN_INTERFACE|Vlan<vid>` の `proxy_arp` フィールドを `enabled` / `disabled` で書き換え、その後 `restart_ndppd()` で `ndppd` を再起動する[^2]。

### `config vlan member add <vid> <port> [-u] [-m] [-e]`

**オプション**:

- `-u, --untagged` ... untagged メンバとして登録
- `-m, --multiple` ... `<vid>` をカンマ区切り or 範囲で複数指定
- `-e, --except_flag` ... 指定 vlan 以外の全 VLAN にメンバ追加

**動作**:
`VLAN_MEMBER|<vlan>|<port>` を `tagging_mode: untagged|tagged` で作成。多数の事前チェックを行う:

- VLAN が存在するか
- ポート (`PORT` または `PORTCHANNEL`) が存在し、PORTCHANNEL_MEMBER に既に組み込まれていないか
- ポートが mirror destination ではないか
- ポートの `mode` が `routed` でないか（`access` / `trunk` の整合性も確認）
- グローバル STP 有効時は `enable_stp_on_port` で `STP_PORT` を埋める

### `config vlan member del <vid> <port> [-m] [-e]`

**動作**:
`VLAN_MEMBER|<vlan>|<port>` を削除し、グローバル STP が有効なら `disable_stp_on_vlan_port` で `STP_VLAN_PORT` / `STP_PORT` を整理。さらに `STATE_DB` の `DHCPv6_COUNTER_TABLE|<port>` / `DHCP_COUNTER_TABLE|<port>` も掃除する。

## 関連する CONFIG_DB

| テーブル | 書き換え内容 | 操作するコマンド |
|----------|--------------|------------------|
| `VLAN` | エントリ作成・削除 | `add` / `del` |
| `DHCP_RELAY` | `vlanid` 付きエントリ作成・削除 | `add` / `del` |
| `VLAN_INTERFACE` | `proxy_arp` フィールド | `proxy_arp` |
| `VLAN_MEMBER` | `<vlan>|<port>` の `tagging_mode` | `member add` / `del` |
| `STP_VLAN` / `STP_VLAN_PORT` / `STP_PORT` | PVST 有効時の追従 | `add` / `del` / `member ...` |

## 引用元

[^1]: `vlan` グループは `config/vlan.py` で定義され、`config/main.py` 末尾で `config.add_command(vlan.vlan)` 相当の登録が行われる。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/vlan.py>

[^2]: `proxy_arp` は VLAN そのものではなく `VLAN_INTERFACE` テーブルに書き込まれる（L3 SVI 機能のため）。`config/vlan.py` L302-L320。<https://github.com/sonic-net/sonic-utilities/blob/39732bceb8bdefe706518ab40623bbbba6ff33b9/config/vlan.py#L302>

## 関連ページ
- [HLD: Switchport モードと VLAN CLI 拡張](../../switching/switch-port-modes-and-vlan-cli-enhancement.md)
- [CONFIG_DB: VLAN](../config-db/vlan.md)
- [CONFIG_DB: VLAN_MEMBER](../config-db/vlan-member.md)
- [YANG: sonic-vlan](../yang/sonic-vlan.md)
