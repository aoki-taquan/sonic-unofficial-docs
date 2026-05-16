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

<!-- ordering -->
## 書込み順依存 (Phase B 調査)

`DHCP_SERVER_IPV6` は未実装だが、SONiC の DHCPv6 リレー機能（`DHCP_RELAY` テーブル / `dhcp6relay` プロセス）には以下の順序依存が確認されている。将来 `DHCP_SERVER_IPV6` が実装された場合も同等の VLAN 前提条件が継承される見込み。

### VLAN_INTERFACE 先行が必須

`dhcp6relay` の起動時 (`initialize_swss()` → `processRelayNotification()`) は `DHCP_RELAY|<vlan>` エントリを処理する際に CONFIG_DB の `VLAN_INTERFACE|<vlan>|*` キーを検索し、**IPv6 アドレス（コロン含む）が 1 件も存在しない VLAN は無条件でスキップ**する。

```
// dhcp6relay/src/config_interface.cpp:130-148
const std::string match_pattern = "VLAN_INTERFACE|" + vlan + "|*";
auto keys = config_db->keys(match_pattern);
...
if (!has_ipv6_address) {
    syslog(LOG_WARNING, "%s doesn't have IPv6 address configured, skip it", vlan.c_str());
    continue;
}
```

runtime 中の動的更新は「コンテナ再起動が必要」ログを出すのみで設定反映されないため、**DHCP_RELAY 書込み前に VLAN_INTERFACE への IPv6 アドレス付与が完了していること**が必要。

推奨書込み順序:

```
1. VLAN（ブリッジ定義）
2. VLAN_INTERFACE|<vlan>|<ipv6-prefix>  ← IPv6 グローバルアドレス
3. DHCP_RELAY|<vlan>（dhcpv6_servers を含む）
```

### dhcp6relay 起動条件（supervisor テンプレート）

`dhcpv6-relay.agents.j2` / `dhcp-relay.programs.j2` は supervisord エントリを Jinja2 で動的生成する。`dhcp6relay` プログラムは次の条件がすべて真のときのみ登録・起動される:

1. `VLAN_INTERFACE` にエントリが存在する
2. 当該 VLAN が `DHCP_RELAY` に存在し `dhcpv6_servers` が空でない
3. `dhcpv6_servers` に有効な IPv6 アドレスが 1 件以上含まれる

条件を満たさない状態でコンテナが起動すると `dhcp6relay` はそもそも supervisord に登録されない。

### systemd 起動順（dhcp-relay.service）

`dhcp_relay.service.j2` は以下の `After=` を持つ:

```
After=config-setup.service swss.service syncd.service teamd.service
```

`teamd.service` が完了して VLAN インターフェースが UP し LLA が生成された後に `dhcp-relay` コンテナが起動するため、**LLA 未生成によるソケット開設失敗は通常発生しない**。ただし `After=` は完了順序のみ保証し、CONFIG_DB への全データ書込みは `config-setup.service` の完了に依存する。

> Evidence: `sonic-net/sonic-dhcp-relay@dhcp6relay/src/config_interface.cpp:130-148`、`sonic-net/sonic-buildimage@dockers/docker-dhcp-relay/dhcpv6-relay.agents.j2:2-10`、`sonic-net/sonic-buildimage@files/build_templates/dhcp_relay.service.j2:4`

<!-- /ordering -->

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
