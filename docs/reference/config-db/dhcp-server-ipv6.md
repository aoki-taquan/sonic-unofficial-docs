---
title: DHCP_SERVER_IPV6 テーブル
description: "DHCP_SERVER_IPV6 テーブル — 組み込み DHCPv6 サーバ機能の設定テーブル（2026-05 時点で未実装。SONiC master は DHCPv6 リレーのみ対応）。"
area: reference
hard: 0
verification: stub
monitor: not_implemented
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dhcp-server-ipv4.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-dhcpv6-relay.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
    - DHCP_SERVER_IPV4
    - DHCP_RELAY
  cli: []
  yang: []
  _no_related_cli: true
  _no_related_yang: true
---

# DHCP_SERVER_IPV6 テーブル

!!! warning "未実装"
    `DHCP_SERVER_IPV6` テーブルは **2026-05-14 時点で sonic-net/sonic-buildimage master に存在しない**。
    SONiC の組み込み DHCP サーバ機能は IPv4 専用（`DHCP_SERVER_IPV4`）のみ実装されている。
    このページは将来の実装に備えたプレースホルダーである。

## 概要

SONiC は DHCPv6 **リレー**機能（`DHCP_RELAY` テーブル）を持つが、DHCPv6 **サーバ**機能は未実装である。IPv4 側の対応テーブルである `DHCP_SERVER_IPV4` が `dhcpservd` + kea-dhcp4 によって実装されているのに対し、kea-dhcp6 を管理するデーモンおよび対応 CONFIG_DB テーブルは存在しない。

<!-- defaults -->
## フィールドデフォルト (Phase A 調査)

**調査結果: フィールドなし（テーブル未実装）**

SONiC master における `DHCP_SERVER_IPV6` テーブルの YANG モデル、Python デーモン、CLI プラグインは確認されなかった。コード由来のデフォルト値を抽出できるフィールドが存在しない。

実装済み IPv4 版との対比:

| 確認対象 | IPv4 (`DHCP_SERVER_IPV4`) | IPv6 (`DHCP_SERVER_IPV6`) |
|---------|--------------------------|--------------------------|
| YANG モデル | `sonic-dhcp-server-ipv4.yang` | なし |
| デーモン | `dhcpservd` (kea-dhcp4) | なし |
| CLI | `config dhcp_server ipv4` | なし |
| 主要フィールド | `state`, `lease_time`, `mode`, `gateway`, `netmask` | 未定義 |

> Evidence: sonic-buildimage@9ea932ec — `src/sonic-yang-models/yang-models/` にて `sonic-dhcp-server-ipv6.yang` 不在を確認。`doc/dhcp_server/port_based_dhcp_server_high_level_design.md` に「IPv4 Port Based DHCP_SERVER」と明記。

<!-- /defaults -->

<!-- side-effects -->
## 副次 DB 書込 (Direction B — dhcp6relay が書く先)

> ソース: `sonic-net/sonic-dhcp-relay dhcp6relay/src/relay.cpp`

`DHCP_SERVER_IPV6` テーブルは未実装だが、DHCPv6 リレー機能を担う `dhcp6relay` プロセスは
`DHCP_RELAY` テーブルを読み込み、STATE_DB へカウンタを書き込む。将来の `DHCP_SERVER_IPV6`
実装時も同等のカウンタ機構が継承される見込みのため、現在の動作を記録する。

### STATE_DB

`dhcp6relay` は起動時および各 DHCPv6 メッセージ受信時に `DHCPv6_COUNTER_TABLE` へ書き込む。

```cpp
// dhcp6relay/src/relay.cpp:18
static std::string counter_table = "DHCPv6_COUNTER_TABLE|";
```

#### 初期化（`initialize_counter`）

VLAN インターフェースの LLA が確認できたタイミングで呼び出される（`lla_check_callback` → `relay.cpp:1401`）。

| テーブル | キー形式 | 書込フィールド | 初期値 | タイミング |
|----------|----------|----------------|--------|------------|
| `DHCPv6_COUNTER_TABLE` | `<vlan_ifname>` | `Unknown`, `Solicit`, `Advertise`, `Request`, `Confirm`, `Renew`, `Rebind`, `Reply`, `Release`, `Decline`, `Reconfigure`, `Information-Request`, `Relay-Forward`, `Relay-Reply`, `Malformed` | `"0"` | `initialize_counter()` 呼び出し時（LLA 確認後） |

事前に `clear_counter()` で既存エントリ（パターン `DHCPv6_COUNTER_TABLE|*`）を全削除してから再初期化する。

#### カウンタ増分（`increase_counter`）

各 DHCPv6 メッセージ処理時に該当フィールドをインクリメントする（`relay.cpp:292-305`）。

| 書込パス | 対象フィールド | タイミング |
|----------|----------------|------------|
| `relay_client()` — クライアント→サーバ方向 | `Solicit` / `Request` / `Confirm` / `Renew` / `Rebind` / `Release` / `Decline` / `Information-Request` / `Malformed` のいずれか | クライアントパケット受信時 |
| `relay_relay_forw()` — Relay-Forward 転送 | `Relay-Forward` | Relay-Forward パケットをサーバへ転送するとき |
| `relay_relay_reply()` — サーバ→クライアント方向 | `Advertise` / `Reply` / `Reconfigure` / `Relay-Reply` / `Malformed` / `Unknown` のいずれか | サーバ応答パケット受信時 |
| ループバック受信（loopback インターフェース） | `Relay-Reply` | ループバックソケットから受信時（`relay.cpp:1098`） |

書込みは `state_db->hset(table_name, type, toString(count + 1))` で行われ、
フィールドが存在しない場合は `"1"` で新規作成される。

### 設定ファイル書込

`dhcp6relay` は設定ファイルへの書込みを行わない。すべての状態情報は STATE_DB のみに保持される。

> Evidence: `sonic-net/sonic-dhcp-relay@dhcp6relay/src/relay.cpp:18,52-68,273-306,1342-1348,1401`

<!-- /side-effects -->

## DHCPv6 サポートの現状

SONiC の DHCPv6 対応は次の 2 要素のみ:

1. **DHCPv6 リレー** — `DHCP_RELAY` テーブル（sonic-dhcpv6-relay.yang）。VLAN ごとに `dhcpv6_servers`、`rfc6939_support`、`interface_id` を設定し、`dhcrelay` プロセスが DHCPv6 RELAY-FORWARD/REPLY をプロキシする
2. **DHCPv6 リレーカウンタ** — `show dhcp6relay_counters` CLI で統計確認可能

DHCPv6 サーバ機能（kea-dhcp6 管理、ステートフル/ステートレスアドレス配布）はコミュニティ版 master には存在しない。

## 関連ドキュメント

- [DHCP_SERVER_IPV4 テーブル](dhcp-server-ipv4.md) — 実装済み IPv4 版
- [DHCP_RELAY テーブル（DHCPv4）](dhcp-relay.md)
- [DHCPv4 リレー テーブル](dhcpv4-relay.md)

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`DHCP_SERVER_IPV4`](dhcp-server-ipv4.md)、[`DHCP_RELAY`](dhcp-relay.md)

<!-- ref-triangle:end -->
