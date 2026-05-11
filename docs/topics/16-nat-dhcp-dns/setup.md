---
title: 設定
area: topics
verification: meta
last_verified: 2026-05-10
sources:
  - docs/reference/cli/config-nat.md
  - docs/reference/cli/show-nat.md
  - docs/reference/cli/config-dhcp-relay.md
  - docs/reference/config-db/nat.md
  - docs/reference/config-db/dhcpv4-relay.md
  - docs/reference/config-db/dhcp-server-ipv4.md
  - docs/reference/yang/sonic-nat.md
  - docs/reference/yang/sonic-dhcp-server.md
---

# 設定

この章の機能は CLI と CONFIG_DB の二系統から設定でき、それぞれ YANG モデルで形式化されています。各リファレンスページの内容はそちら側を正にし、ここでは「どこを最初に編集するか」と「どの順で組み合わせるか」だけ示します。

## NAT の設定入口

NAT は次のレイヤで構成します。

- グローバル: `NAT_GLOBAL` で機能 enable / timeout / TCP/UDP の挙動を決めます。CLI は `config nat feature enable` と `config nat add ...`。
- ゾーン: `NAT_ZONE` で interface に inside / outside を付けます（`config interface nat add inside|outside`）。
- 静的: `STATIC_NAT` / `STATIC_NAPT` で 1:1 アドレス / port マッピング。
- 動的: `NAT_POOL` + `NAT_BINDINGS` + ACL でプール / バインディング / マッチ条件を組みます。

CLI ツリーは [config nat](../../reference/cli/config-nat.md) / [show nat](../../reference/cli/show-nat.md) を参照してください。CONFIG_DB スキーマは [NAT テーブル群](../../reference/config-db/nat.md) と [sonic-nat YANG](../../reference/yang/sonic-nat.md) にあります。

## DHCP relay の設定入口

DHCPv4 relay は VLAN ごとに upstream server を指定する形です。

- CLI: `config vlan dhcp_relay add <vlan> <server_ip>` / `config vlan dhcp_relay del ...`。CLI plugin の正確な階層は [config dhcp_relay リファレンス](../../reference/cli/config-dhcp-relay.md) を参照してください。
- CONFIG_DB: `DHCP_RELAY|<vlan>` の `dhcp_servers` リスト。v6 は同 entry の `dhcpv6_servers` と `dhcpv6_option|rfc6939_support`。詳細は [DHCPV4_RELAY スキーマ](../../reference/config-db/dhcpv4-relay.md) にあります。
- giaddr 固定: `config interface ip add --secondary` で `VLAN_INTERFACE` に `secondary: "true"` を付けると、primary IPv4 が `-pg` で giaddr に固定されます。

per-interface counter / Option 82 は CLI / CONFIG_DB レベルでは特別な操作が要らず、relay 起動時に自動で COUNTERS_DB に書かれます。

## DHCP server の設定入口

ポートベース DHCP server は次の順で書きます。

1. `FEATURE|dhcp_server` の `state: enabled` で `docker-dhcp-server` を起動。
2. `DHCP_SERVER_IPV4|<vlan>` で subnet / lease time / gateway を設定。
3. `DHCP_SERVER_IPV4_RANGE` で払い出し範囲を定義。
4. `DHCP_SERVER_IPV4_PORT|<vlan>|<port>` でポート単位の IP 予約や VLAN へのバインドを設定。
5. 追加 option が必要なら `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` を使います。

CLI は `config dhcp_server ipv4 ...` / `show dhcp_server ipv4 ...` で、CONFIG_DB スキーマは [DHCP_SERVER_IPV4 群](../../reference/config-db/dhcp-server-ipv4.md)、YANG は [sonic-dhcp-server](../../reference/yang/sonic-dhcp-server.md) にあります。

## 典型構成: ToR の relay + 集中 server

VLAN 10 / 20 を持つ ToR で、外部 DHCP server に中継する最小構成は次の通りです。

```
config vlan dhcp_relay add 10 10.0.0.1
config vlan dhcp_relay add 20 10.0.0.1
```

書き込まれる CONFIG_DB は `DHCP_RELAY|Vlan10` / `Vlan20` で、`dhcp_servers: ["10.0.0.1"]` です。v6 を併用するなら `dhcpv6_servers` を別途追加します。secondary subnet を運用する場合は VLAN_INTERFACE 側で `secondary: "true"` の付与を忘れずに。

## 典型構成: ToR ローカル DHCP server

`docker-dhcp-server` を有効化し、VLAN 10 で pool を払い出す例の輪郭は次の通りです。

```
config feature state dhcp_server enabled
config dhcp_server ipv4 add Vlan10 --gw 10.10.0.1 --netmask 255.255.0.0 --lease-time 86400
config dhcp_server ipv4 range add pool1 10.10.0.100 10.10.0.200
config dhcp_server ipv4 ip bind Vlan10 Ethernet4 --range pool1
```

各サブコマンドの正確な引数は [config dhcp_server CLI](../../reference/cli/config-dhcp-relay.md) と各 [DHCP_SERVER_IPV4 系 CONFIG_DB ページ](../../reference/config-db/dhcp-server-ipv4.md) を参照してください。relay は同 VLAN で kea へ向くよう自動的に dhcprelayd が config を書き換えます。

## 関連ページ

- [config nat](../../reference/cli/config-nat.md)
- [show nat](../../reference/cli/show-nat.md)
- [config dhcp_relay](../../reference/cli/config-dhcp-relay.md)
- [NAT CONFIG_DB スキーマ](../../reference/config-db/nat.md)
- [DHCPV4_RELAY CONFIG_DB](../../reference/config-db/dhcpv4-relay.md)
- [DHCP_SERVER_IPV4 CONFIG_DB](../../reference/config-db/dhcp-server-ipv4.md)
- [sonic-nat YANG](../../reference/yang/sonic-nat.md)
- [sonic-dhcp-server YANG](../../reference/yang/sonic-dhcp-server.md)
