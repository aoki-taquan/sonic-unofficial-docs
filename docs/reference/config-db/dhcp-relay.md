---
title: DHCP_RELAY テーブル
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dhcpv6-relay.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - DHCP_RELAY
    - VLAN
  cli:
    - config dhcp_relay
  yang:
    - sonic-dhcpv6-relay
---

# DHCP_RELAY テーブル

## 概要

`DHCP_RELAY` テーブルは VLAN インターフェース単位の DHCPv6 リレーエージェント設定を保持する[^1]。`sonic-dhcp-relay` リポの `dhcp6relay` プロセスが CONFIG_DB を購読し、`/etc/dhcp/` 設定を生成して DHCPv6 リレーを起動する。

YANG モジュール名は `sonic-dhcpv6-relay` だが、CONFIG_DB のテーブル名は **`DHCP_RELAY`**（共通名で IPv4 リレー (`DHCPV4_RELAY` または `VLAN` の `dhcp_servers` leaf) と区別される）。

## key 構造

```
DHCP_RELAY|<name>
```

| キー | 型 | 説明 |
|------|----|------|
| `name` | string | VLAN インターフェース名（`Vlan100` 等） |

## フィールド

| フィールド | 型 | 説明 |
|-----------|----|------|
| `dhcpv6_servers` | leaf-list `inet:ipv6-address` (`ordered-by user`) | リレー先 DHCPv6 サーバの IPv6 アドレス集合 |
| `rfc6939_support` | string `true`/`false` | RFC 6939 (Client Link-Layer Address option) サポートの有無 |
| `interface_id` | string `true`/`false` | リレー時に Interface-ID オプションを挿入するか |

## 制約

- `name` は plain string（YANG では VLAN への leafref が外されている。VLAN 削除時の整合性は実装側で担保）
- `rfc6939_support` / `interface_id` の値は文字列パターン `false|true` で boolean を模擬

## 購読者

- `dhcp6relay` (sonic-dhcp-relay)

## 関連 CONFIG_DB / YANG / CLI

- 関連 CONFIG_DB: `VLAN`、`VLAN_INTERFACE`、`DHCP_SERVER_IPV4` (IPv4 側は別系統)
- 関連 YANG: `sonic-dhcpv6-relay`
- 関連 CLI: `config dhcp_relay`

## 引用元

[^1]: YANG 定義: `sonic-dhcpv6-relay.yang`. <https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/src/sonic-yang-models/yang-models/sonic-dhcpv6-relay.yang>

## 関連ページ
- [CONFIG_DB: DHCPv4 Relay](dhcpv4-relay.md)
- [CONFIG_DB: VLAN](vlan.md)
