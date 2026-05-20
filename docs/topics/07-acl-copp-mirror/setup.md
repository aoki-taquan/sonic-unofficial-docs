---
title: 設定
description: 設定 — ACL の最小設定は、table を作り、rule JSON を流し、show で確認する流れです。config acl は table
  の作成・削除と JSON の一括投入を提供しますが、個別 rule を CLI 引数で追加するインタフェースではありません。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/reference/cli/config-acl.md
- docs/reference/cli/show-acl.md
- docs/reference/cli/config-mirror-session.md
- docs/reference/config-db/acl-table.md
- docs/reference/config-db/acl-rule.md
- docs/reference/config-db/policer.md
- docs/reference/config-db/mirror-session.md
- docs/reference/config-db/copp-group.md
- docs/reference/config-db/copp-trap.md
- docs/reference/yang/sonic-copp.md
- docs/reference/yang/sonic-mirror-session.md
related:
  cli:
  - show acl
  - config acl
  - config bgp
  - show bgp
  config_db:
  - COPP_GROUP
  - POLICER
  - COPP_TRAP
  - MIRROR_SESSION
  - ACL_RULE
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  yang:
  - sonic-copp
  - sonic-mirror-session
  - sonic-bgp-monitor
  - sonic-bgp-peergroup
  - sonic-bgp-peerrange
  - sonic-bgp-global
  - sonic-bgp-bbr
---

# 設定

[ACL](../../reference/glossary.md#term-acl) の最小設定は、table を作り、rule JSON を流し、show で確認する流れです。`config acl` は table の作成・削除と JSON の一括投入を提供しますが、個別 rule を CLI 引数で追加するインタフェースではありません。rule は JSON に書いて `config acl update full` または `incremental` で投入します。

## 最小 ACL

例として `Ethernet0` に入ってくる特定送信元を drop する L3 ACL を考えます。

```bash
config acl add table DATAACL L3 -p Ethernet0 -s ingress -d "drop selected sources"
```

rule は JSON で定義します。

```json
{
  "ACL_RULE": {
    "DATAACL|DROP_SRC_10_0_0_1": {
      "PRIORITY": "1000",
      "SRC_IP": "10.0.0.1/32",
      "PACKET_ACTION": "DROP"
    }
  }
}
```

投入は次の形です。

```bash
config acl update incremental acl-rules.json
show acl table DATAACL
show acl rule DATAACL
```

設定を読むときは `ACL_TABLE|DATAACL` の `type`、`stage`、`ports` を先に見ます。その後に `ACL_RULE|DATAACL|DROP_SRC_10_0_0_1` の `PRIORITY`、match、action を見ます。

## ACL_RULE の基本

`PRIORITY` は値が大きいほど優先です。match は `SRC_IP` / `DST_IP`、`SRC_IPV6` / `DST_IPV6`、`IP_PROTOCOL`、`L4_SRC_PORT` / `L4_DST_PORT`、`ETHER_TYPE`、`TCP_FLAGS` などを組み合わせます。action は `PACKET_ACTION`、`REDIRECT_ACTION`、mirror action、`POLICER`、[DSCP](../../reference/glossary.md#term-dscp) 書換などです。

table type が action の可否を制限するため、rule JSON だけを別 table に移すと失敗することがあります。特に egress stage、mirror、DSCP 書換、packet trimming のような action は [ASIC](../../reference/glossary.md#term-asic) capability の影響を受けます。

## Policer

`POLICER` は単独で packet を分類しません。ACL rule、[CoPP](../../reference/glossary.md#term-copp) group、mirror session などから参照される rate limiting 部品です。`METER_TYPE`、`MODE`、`CIR` / `CBS`、`PIR` / `PBS`、色別 action を持ちます。

ACL で使う場合は rule の action として policer 名を参照します。CoPP では `COPP_GROUP` 内に queue、trap action、meter、rate を持つ形で control plane traffic に適用されます。

## Mirror Session

`MIRROR_SESSION` は SPAN または ERSPAN のセッション定義です。SPAN はローカル `dst_port` へコピーし、ERSPAN は `src_ip`、`dst_ip`、GRE type、DSCP、TTL などの outer header を持って collector へ送ります。

ACL と組み合わせる場合、先に mirror session を作り、`ACL_RULE` から `MIRROR_ACTION`、`MIRROR_INGRESS_ACTION`、`MIRROR_EGRESS_ACTION` で参照します。ポート単位で常時 mirror したい場合は `MIRROR_SESSION.src_port` / `direction` 側を読む方が近道です。

## CoPP

CoPP は `COPP_TRAP` が trap ID 群を定義し、`COPP_GROUP` が CPU queue と policer を定義します。`COPP_TRAP.trap_group` が `COPP_GROUP` を参照し、`coppmgr` が [APPL_DB](../../reference/glossary.md#term-appl_db) の `COPP_TABLE` に変換し、`CoppOrch` が [SAI](../../reference/glossary.md#term-sai) hostif trap / trap group / policer に反映します。

[YANG](../../reference/glossary.md#term-yang) の正本は `sonic-copp` で、`COPP_GROUP` と `COPP_TRAP` の tree、leaf、leafref を確認できます。mirror session の YANG は `sonic-mirror-session` で、ERSPAN / SPAN の必須条件や `POLICER` への leafref を確認できます。

## 典型シナリオ 1: 上位 uplink で source IP filter ACL を入れる

「上位 spine から特定 prefix (10.0.0.0/8) しか受け取らない」というケース。

### CLI と JSON

```bash
# 1. ingress ACL table を作る
sudo config acl add table UPLINK_FILTER L3 -p PortChannel10,PortChannel20 -s ingress
```

rule JSON (`/tmp/uplink_filter.json`):

```json
{
  "ACL_RULE": {
    "UPLINK_FILTER|ALLOW_10_8": {
      "PRIORITY": "9999",
      "SRC_IP": "10.0.0.0/8",
      "PACKET_ACTION": "FORWARD"
    },
    "UPLINK_FILTER|DENY_ANY": {
      "PRIORITY": "1",
      "SRC_IP": "0.0.0.0/0",
      "PACKET_ACTION": "DROP"
    }
  }
}
```

投入:

```bash
sudo acl-loader update incremental /tmp/uplink_filter.json
```

[CONFIG_DB](../../reference/glossary.md#term-config_db) の表現:

```json
{
  "ACL_TABLE": {
    "UPLINK_FILTER": {
      "type": "L3",
      "stage": "ingress",
      "ports@": "PortChannel10,PortChannel20",
      "policy_desc": "uplink prefix filter"
    }
  },
  "ACL_RULE": {
    "UPLINK_FILTER|ALLOW_10_8": {
      "PRIORITY": "9999",
      "SRC_IP": "10.0.0.0/8",
      "PACKET_ACTION": "FORWARD"
    },
    "UPLINK_FILTER|DENY_ANY": {
      "PRIORITY": "1",
      "SRC_IP": "0.0.0.0/0",
      "PACKET_ACTION": "DROP"
    }
  }
}
```

`ports@` の末尾の `@` は ConfigDB の list 型表記です。CLI 経由なら自動付与されます。

### 確認

```bash
show acl table UPLINK_FILTER
show acl rule UPLINK_FILTER
```

`show acl table` の典型出力:

```text
Name            Type    Binding             Description           Stage
--------------  ------  ------------------  --------------------  -------
UPLINK_FILTER   L3      PortChannel10       uplink prefix filter  ingress
                        PortChannel20
```

`show acl rule UPLINK_FILTER`:

```text
Table          Rule          Priority    Action    Match
-------------  ------------  ----------  --------  -------------------
UPLINK_FILTER  ALLOW_10_8    9999        FORWARD   SRC_IP: 10.0.0.0/8
UPLINK_FILTER  DENY_ANY      1           DROP      SRC_IP: 0.0.0.0/0
```

`show acl rule` の counter 列 (`Packets`/`Bytes`) は `aclshow` を使うと数値で見えます。

## 典型シナリオ 2: ERSPAN mirror session を ACL から起動する

特定 TCP flag が立った flow だけを collector に飛ばす。

```json
{
  "MIRROR_SESSION": {
    "investig8": {
      "src_ip": "10.1.0.1",
      "dst_ip": "10.99.0.10",
      "gre_type": "0x88be",
      "dscp": "8",
      "ttl": "64",
      "queue": "0"
    }
  },
  "ACL_TABLE": {
    "MIRROR_ACL": {
      "type": "MIRROR",
      "stage": "ingress",
      "ports@": "Ethernet0"
    }
  },
  "ACL_RULE": {
    "MIRROR_ACL|TCP_SYN": {
      "PRIORITY": "9000",
      "IP_PROTOCOL": "6",
      "TCP_FLAGS": "0x02/0x02",
      "MIRROR_INGRESS_ACTION": "investig8"
    }
  }
}
```

確認:

```bash
show mirror_session
```

```text
ERSPAN Sessions
Name        Status    SRC IP     DST IP       GRE     DSCP    TTL    Queue
----------  --------  ---------  -----------  ------  ------  -----  ------
investig8   active    10.1.0.1   10.99.0.10   0x88be  8       64     0
```

`Status: error` の場合は dst_ip への route 未到達か、underlay reachability の問題。

## 典型シナリオ 3: BGP control-plane traffic の CoPP rate を上げる

default の [BGP](../../reference/glossary.md#term-bgp) CoPP rate を引き上げて、フラップ復旧時の neighbor 再収束を速くする。

```json
{
  "COPP_GROUP": {
    "queue4_group2": {
      "queue": "4",
      "trap_action": "trap",
      "trap_priority": "4",
      "cbs": "6000",
      "cir": "6000"
    }
  },
  "COPP_TRAP": {
    "bgp": {
      "trap_ids": "bgp,bgpv6",
      "trap_group": "queue4_group2"
    }
  }
}
```

確認:

```bash
show copp -t bgp
show copp config
```

`COPP_TRAP.trap_ids` の値は `coppmgr` が認識する hostif trap 名のリストです (`arp,bgp,bgpv6,dhcp,...`)。誤った trap 名は無視されるため、`docker logs swss` で `Unknown trap id` を確認できます。

## sonic-cfggen で投入する場合

```bash
sonic-cfggen -a "$(cat copp_patch.json)" --write-to-db
config save -y
```

`acl-loader` 経由でない `config_db.json` 直接書き換えは reboot しないと swss が認識しません。runtime 反映には `acl-loader update incremental` を使う方が安全です。

## よくある設定エラーと対処

`sonic-utilities/acl_loader/main.py` の `AclLoaderException` から抜粋:

| エラーメッセージ | 原因 | 対処 |
|---|---|---|
| `Table <name> does not exist` | rule の table 名が table 未作成 | 先に `config acl add table` |
| `Session <name> does not exist` | mirror action から未存在 session を参照 | 先に MIRROR_SESSION を作成 |
| `Invalid input file <path>` | JSON の構文 / schema 不正 | jq で構文を確認 |
| `Unknown rule action <action> in table <t>, rule <r>` | action 名 typo | reference の action 一覧を確認 |
| `Rule action <action> is not supported in table <t>, rule <r>` | table type と action 不整合 (例: L3 table に mirror action) | table type を `MIRROR` 系に変更 |
| `Mirroring session does not exist` | mirror action 参照先 不在 | 先に session 作成 |
| `Invalid mirror stage passed <stage>` | stage 値 typo | `ingress` / `egress` のいずれか |
| `IP_PROTOCOL=<n> is not TCP, but TCP flags were provided` | protocol 不一致 | `IP_PROTOCOL=6` か TCP_FLAGS 削除 |
| `IP_PROTOCOL=<n> is not ICMP, but ICMP fields were provided` | protocol 不一致 | `IP_PROTOCOL=1` か ICMP field 削除 |
| `IP_PROTOCOL=<n> is not ICMPV6, but ICMPV6 fields were provided` | protocol 不一致 | `IP_PROTOCOL=58` か ICMPV6 field 削除 |
| `VLAN ID <n> is out of bounds (0, 4096)` | match の VLAN_ID 範囲外 | 1〜4094 に修正 |
| `ICMP type/code <n> is out of bounds [0, 255]` | match の ICMP 値範囲外 | 0〜255 に修正 |
| `l2:ethertype must be provided for rule in table type L3V4V6` | dual family table で ethertype 必須 | `ETHER_TYPE` を追加 |
| `ethertype=<n> is neither ETHERTYPE_IPV4 nor ETHERTYPE_IPV6 for IP rule` | ethertype 値が IPv4/IPv6 外 | `0x0800` または `0x86dd` を指定 |

action / match 制約は ASIC capability に依存する部分があるため、SAI レイヤで弾かれた場合は `swss` syslog に `SAI_STATUS_NOT_SUPPORTED` が出ます。

## 関連ページ

- [config acl サブコマンド](../../reference/cli/config-acl.md)
- [show acl サブコマンド](../../reference/cli/show-acl.md)
- [config mirror_session サブコマンド](../../reference/cli/config-mirror-session.md)
- [ACL_TABLE テーブル](../../reference/config-db/acl-table.md)
- [ACL_RULE テーブル](../../reference/config-db/acl-rule.md)
- [POLICER テーブル](../../reference/config-db/policer.md)
- [MIRROR_SESSION テーブル](../../reference/config-db/mirror-session.md)
- [COPP_GROUP テーブル](../../reference/config-db/copp-group.md)
- [COPP_TRAP テーブル](../../reference/config-db/copp-trap.md)
- [sonic-copp YANG](../../reference/yang/sonic-copp.md)
- [sonic-mirror-session YANG](../../reference/yang/sonic-mirror-session.md)

<!-- glossary-links-injected: c006405759d8 -->
