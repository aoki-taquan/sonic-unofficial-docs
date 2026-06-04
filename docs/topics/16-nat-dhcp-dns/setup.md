---
title: 設定
description: 設定 — この章の機能は CLI と CONFIG_DB の二系統から設定でき、それぞれ YANG モデルで形式化されています。各リファレンスページの内容はそちら側を正にし、ここでは「どこを最初に編集するか」と「どの順で組み合わせるか」だけ示します。
area: topics
verification: meta
last_verified: 2026-05-10
sources: []
related:
  cli:
  - config nat
  - config interface
  - show nat
  - config vlan
  - config acl
  - show interfaces
  - show ip
  config_db:
  - VLAN_INTERFACE
  - NAT
  - VLAN
  - DHCP_RELAY
  - DHCP_SERVER_IPV4
  - ACL_RULE
  - ACL_TABLE
  yang:
  - sonic-nat
  - sonic-dhcp-server
  - sonic-vlan
  - sonic-vlan-sub-interface
---

# 設定

この章の機能は CLI と [CONFIG_DB](../../reference/glossary.md#term-config_db) の二系統から設定でき、それぞれ [YANG](../../reference/glossary.md#term-yang) モデルで形式化されています。各リファレンスページの内容はそちら側を正にし、ここでは「どこを最初に編集するか」と「どの順で組み合わせるか」だけ示します。

## NAT の設定入口

[NAT](../../reference/glossary.md#term-nat) は次のレイヤで構成します。

- グローバル: `NAT_GLOBAL` で機能 enable / timeout / TCP/UDP の挙動を決めます。CLI は `config nat feature enable` と `config nat add ...`。
- ゾーン: `NAT_ZONE` で interface に inside / outside を付けます（`config interface nat add inside|outside`）。
- 静的: `STATIC_NAT` / `STATIC_NAPT` で 1:1 アドレス / port マッピング。
- 動的: `NAT_POOL` + `NAT_BINDINGS` + [ACL](../../reference/glossary.md#term-acl) でプール / バインディング / マッチ条件を組みます。

CLI ツリーは [config nat](../../reference/cli/config-nat.md) / [show nat](../../reference/cli/show-nat.md) を参照してください。CONFIG_DB スキーマは [NAT テーブル群](../../reference/config-db/nat.md) と [sonic-nat YANG](../../reference/yang/sonic-nat.md) にあります。

## DHCP relay の設定入口

DHCPv4 relay は [VLAN](../../reference/glossary.md#term-vlan) ごとに upstream server を指定する形です。

- CLI: `config vlan dhcp_relay add <vlan> <server_ip>` / `config vlan dhcp_relay del ...`。CLI plugin の正確な階層は [config dhcp_relay リファレンス](../../reference/cli/config-dhcp-relay.md) を参照してください。
- CONFIG_DB: `DHCP_RELAY|<vlan>` の `dhcp_servers` リスト。v6 は同 entry の `dhcpv6_servers` と `dhcpv6_option|rfc6939_support`。詳細は [DHCPV4_RELAY スキーマ](../../reference/config-db/dhcpv4-relay.md) にあります。
- giaddr 固定: `config interface ip add --secondary` で `VLAN_INTERFACE` に `secondary: "true"` を付けると、primary IPv4 が `-pg` で giaddr に固定されます。

per-interface counter / Option 82 は CLI / CONFIG_DB レベルでは特別な操作が要らず、relay 起動時に自動で [COUNTERS_DB](../../reference/glossary.md#term-counters_db) に書かれます。

## DHCP server の設定入口

ポートベース DHCP server は次の順で書きます。

1. `FEATURE|dhcp_server` の `state: enabled` で `docker-dhcp-server` を起動。
2. `DHCP_SERVER_IPV4|<vlan>` で subnet / lease time / gateway を設定。
3. `DHCP_SERVER_IPV4_RANGE` で払い出し範囲を定義。
4. `DHCP_SERVER_IPV4_PORT|<vlan>|<port>` でポート単位の IP 予約や VLAN へのバインドを設定。
5. 追加 option が必要なら `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` を使います。

CLI は `config dhcp_server ipv4 ...` / `show dhcp_server ipv4 ...` で、CONFIG_DB スキーマは [DHCP_SERVER_IPV4 群](../../reference/config-db/dhcp-server-ipv4.md)、YANG は [sonic-dhcp-server](../../reference/yang/sonic-dhcp-server.md) にあります。

## 設定シナリオ 1: 静的 NAT で内部サーバを公開

`inside` インターフェース配下の `10.10.0.5:80` を、`outside` の `203.0.113.10:80` で公開する例。

```bash
# NAT を有効化
sudo config nat feature enable

# inside / outside zone を割り当て
sudo config interface ip add Vlan10 10.10.0.1/24
sudo config interface nat add inside  Vlan10
sudo config interface ip add Ethernet48 203.0.113.10/30
sudo config interface nat add outside Ethernet48

# 静的 NAPT
sudo config nat add static tcp 10.10.0.5 80 203.0.113.10 80
```

CONFIG_DB はおおよそ次の形になります。

```json
{
    "NAT_GLOBAL": {"Values": {"admin_mode": "enabled", "nat_timeout": "600", "nat_tcp_timeout": "86400", "nat_udp_timeout": "300"}},
    "NAT_ZONE": {
        "Vlan10":    {"nat_zone": "1"},
        "Ethernet48":{"nat_zone": "0"}
    },
    "STATIC_NAPT": {
        "203.0.113.10|TCP|80": {"local_ip": "10.10.0.5", "local_port": "80"}
    }
}
```

確認:

```bash
show nat config static
show nat translations
show nat statistics
```

`show nat translations` の典型出力:

```text
Protocol    Source            Destination        Translated Source    Translated Destination
----------  ----------------  -----------------  -------------------  -----------------------
tcp         198.51.100.4:53245  203.0.113.10:80   198.51.100.4:53245   10.10.0.5:80
```

## 設定シナリオ 2: 動的 NAT プール + ACL マッチ

`10.10.0.0/24` の発信トラフィックを `203.0.113.32-203.0.113.47` でマスカレード。

```bash
sudo config nat add pool POOL1 203.0.113.32-203.0.113.47
sudo config acl add table NAT_ACL L3 -p Ethernet48
sudo config acl rule create NAT_ACL R10 --src-ip 10.10.0.0/24 --action FORWARD
sudo config nat add binding BIND1 POOL1 NAT_ACL -nat_type snat
```

`NAT_POOL` / `NAT_BINDINGS` テーブルに反映され、`natsyncd` が conntrack を作成して `APPL_DB:NAT_TABLE` 経由で [SAI](../../reference/glossary.md#term-sai) へ流します。

## 設定シナリオ 3: ToR の DHCP relay と giaddr 固定


VLAN 10 / 20 を持つ ToR で、外部 DHCP server に中継する最小構成は次の通りです。

```bash
config vlan dhcp_relay add 10 10.0.0.1
config vlan dhcp_relay add 20 10.0.0.1
```

書き込まれる CONFIG_DB は `DHCP_RELAY|Vlan10` / `Vlan20` で、`dhcp_servers: ["10.0.0.1"]` です。v6 を併用するなら `dhcpv6_servers` を別途追加します。secondary subnet を運用する場合は VLAN_INTERFACE 側で `secondary: "true"` の付与を忘れずに。

確認:

```bash
show dhcp_relay ipv4 interfaces
show dhcp_relay ipv4 statistics
```

`show dhcp_relay ipv4 interfaces` 例:

```text
Interface    DHCP Helper Address
-----------  ---------------------
Vlan10       10.0.0.1
Vlan20       10.0.0.1
```

`show dhcp_relay ipv4 statistics` で `bootp_request_sent_to_server` / `bootp_reply_sent_to_client` のカウンタが進むことを確認します。giaddr を secondary IP に固定したい場合は `VLAN_INTERFACE|Vlan10|10.10.99.1/32` を `secondary: "true"` で追加し、`dhcrelay` の `-pg` でその IP が選ばれるようにします。

## 設定シナリオ 4: ToR ローカル DHCP server

`docker-dhcp-server` を有効化し、VLAN 10 で pool を払い出す例の輪郭は次の通りです。

```bash
config feature state dhcp_server enabled
config dhcp_server ipv4 add Vlan10 --gw 10.10.0.1 --netmask 255.255.0.0 --lease-time 86400
config dhcp_server ipv4 range add pool1 10.10.0.100 10.10.0.200
config dhcp_server ipv4 ip bind Vlan10 Ethernet4 --range pool1
```

`config dhcp_server` サブコマンド群は現時点で専用 CLI リファレンスページが整備されておらず、ソースコード (`sonic-utilities/config/plugins/dhcp_server.py`) と [DHCP_SERVER_IPV4 系 CONFIG_DB ページ](../../reference/config-db/dhcp-server-ipv4.md) を参照してください。relay 側のコマンドは [config dhcp_relay CLI](../../reference/cli/config-dhcp-relay.md) を参照。relay は同 VLAN で kea へ向くよう自動的に dhcprelayd が config を書き換えます。

CONFIG_DB は次のようになります。

```json
{
    "FEATURE": {"dhcp_server": {"state": "enabled"}},
    "DHCP_SERVER_IPV4": {
        "Vlan10": {"gateway": "10.10.0.1", "lease_time": "86400", "mode": "PORT", "netmask": "255.255.0.0", "state": "enabled"}
    },
    "DHCP_SERVER_IPV4_RANGE": {
        "pool1": {"range": "10.10.0.100,10.10.0.200"}
    },
    "DHCP_SERVER_IPV4_PORT": {
        "Vlan10|Ethernet4": {"ranges@": "pool1"}
    }
}
```

確認:

```bash
show dhcp_server ipv4 info
show dhcp_server ipv4 lease
```

`show dhcp_server ipv4 lease` 出力例:

```text
VLAN       MAC                IP             Lease Start          Lease End
---------  -----------------  -------------  -------------------  -------------------
Vlan10     52:54:00:aa:bb:cc  10.10.0.100    2026-05-11 09:12:30  2026-05-12 09:12:30
```

## 設定エラーと対処

| 症状 | 原因 | 対処 |
|---|---|---|
| `show nat translations` が空のまま | inside / outside zone が貼られていない | `show interfaces nat-zone`、各 interface に対して `config interface nat add inside/outside` |
| 静的 NAT 投入後も `conntrack -L` に出ない | NAT_GLOBAL の `admin_mode` が `disabled` | `config nat feature enable` で `admin_mode: enabled` を確認 |
| 動的 NAT のプールが枯渇 | プール範囲不足 / aging が長い | `nat_timeout` を短く、または `NAT_POOL` の range を拡張 |
| relay 経由で DISCOVER が server に届かない | giaddr が `0.0.0.0` のまま / VLAN_INTERFACE が L3 化されていない | `show ip interfaces` で VLAN の IP を確認、`docker logs dhcp_relay` を確認 |
| local DHCP server がリースを払い出さない | `DHCP_SERVER_IPV4_PORT` の `ranges@` がレンジ名と不一致 | レンジ名のスペル、`Vlan10|<port>` の port が実存することを確認 |
| Option 82 が付かない | relay version が古い / `vlan_dhcp_relay` 系の `enable_option_82` が false | `redis-cli HGET DHCP_RELAY|Vlan10 enable_option_82` を確認 |

## 設定シナリオ 5: VLAN 単位の DNS resolver 配布

DHCP server / relay の Option 6（DNS server）と Option 15（domain name）を VLAN 単位で配布します。relay の場合は upstream server 側で設定しますが、local server を使うときは `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` で書きます。

```json
{
    "DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS": {
        "dns": {"id": "6", "type": "ip-list", "value": "10.10.0.2,10.10.0.3"},
        "domain": {"id": "15", "type": "string", "value": "corp.example.com"}
    },
    "DHCP_SERVER_IPV4": {
        "Vlan10": {"customized_options@": "dns,domain", "gateway":"10.10.0.1","lease_time":"86400","mode":"PORT","netmask":"255.255.0.0","state":"enabled"}
    }
}
```

クライアント側で `cat /etc/resolv.conf` に `10.10.0.2` / `10.10.0.3` と `search corp.example.com` が降りてくれば成功です。

## 関連リファレンス

- CLI: `config nat`、`show nat`、`config interface nat`、`config vlan dhcp_relay`、`config dhcp_server ipv4`、`show dhcp_relay ipv4`、`show dhcp_server ipv4`
- CONFIG_DB: `NAT_GLOBAL`、`NAT_ZONE`、`STATIC_NAT`、`STATIC_NAPT`、`NAT_POOL`、`NAT_BINDINGS`、`DHCP_RELAY`、`DHCP_SERVER_IPV4`、`DHCP_SERVER_IPV4_RANGE`、`DHCP_SERVER_IPV4_PORT`、`DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS`、`VLAN_INTERFACE`（secondary giaddr 用）
- [APPL_DB](../../reference/glossary.md#term-appl_db): `NAT_TABLE`、`NAPT_TABLE`、`NAT_TWICE_TABLE`
- COUNTERS_DB: NAT / DHCP relay の per-entry / per-interface counter
- YANG: [`sonic-nat`](../../reference/yang/sonic-nat.md)、[`sonic-dhcp-server`](../../reference/yang/sonic-dhcp-server.md)、`sonic-dhcpv4-relay`

## 関連ページ

- [config nat](../../reference/cli/config-nat.md)
- [show nat](../../reference/cli/show-nat.md)
- [config dhcp_relay](../../reference/cli/config-dhcp-relay.md)
- [NAT CONFIG_DB スキーマ](../../reference/config-db/nat.md)
- [DHCPV4_RELAY CONFIG_DB](../../reference/config-db/dhcpv4-relay.md)
- [DHCP_SERVER_IPV4 CONFIG_DB](../../reference/config-db/dhcp-server-ipv4.md)
- [sonic-nat YANG](../../reference/yang/sonic-nat.md)
- [sonic-dhcp-server YANG](../../reference/yang/sonic-dhcp-server.md)

<!-- glossary-links-injected: 469d17d8763e -->
