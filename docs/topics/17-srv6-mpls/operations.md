---
title: 運用
description: 運用 — SRv6 / MPLS / Path Tracing の運用確認は、「設定が CONFIG_DB に正しく入ったか」「FRR /
  netlink 経由で APP_DB に渡ったか」「SAI / ASIC に programming されたか」の三段を順に追います。
area: topics
verification: meta
last_verified: 2026-05-11
sources: []
related:
  cli:
  - show interfaces
  - clear counters
  - show bgp
  - config qos
  - config bgp
  config_db:
  - CRM
  - PORT_QOS_MAP
  - BGP_NEIGHBOR
  - BGP_GLOBALS
  - BGP_PEER_GROUP_AF
  - BGP_GLOBALS_AF_NETWORK
  - BGP_GLOBALS_AF_AGGREGATE_ADDR
  yang:
  - sonic-bgp-global
  - sonic-bgp-neighbor
  - sonic-crm
  - sonic-bgp-bbr
  - sonic-bgp-peerrange
  - sonic-bgp-device-global
  - sonic-bgp-sentinel
---

# 運用

[SRv6](../../reference/glossary.md#term-srv6) / [MPLS](../../reference/glossary.md#term-mpls) / Path Tracing の運用確認は、「設定が [CONFIG_DB](../../reference/glossary.md#term-config_db) に正しく入ったか」「[FRR](../../reference/glossary.md#term-frr) / netlink 経由で APP_DB に渡ったか」「[SAI](../../reference/glossary.md#term-sai) / [ASIC](../../reference/glossary.md#term-asic) に programming されたか」の三段を順に追います。本ページは各機能の出口（show コマンド / DB / ログ）と、よく遭遇する異常パターン、その復旧手順を実例ベースで並べます。

## SRv6

### 設定が CONFIG_DB に入ったかの確認

```bash
admin@sonic:~$ redis-cli -n 4 KEYS "SRV6_MY_LOCATORS|*"
1) "SRV6_MY_LOCATORS|loc1"
admin@sonic:~$ redis-cli -n 4 HGETALL "SRV6_MY_LOCATORS|loc1"
1) "prefix"
2) "fc00:0:1::/48"
3) "block_len"
4) "32"
5) "node_len"
6) "16"
7) "func_len"
8) "16"
admin@sonic:~$ redis-cli -n 4 KEYS "SRV6_MY_SIDS|*"
1) "SRV6_MY_SIDS|loc1|fc00:0:1:e000::"
2) "SRV6_MY_SIDS|loc1|fc00:0:1:e001::"
```

`uA` / `End.X` の SID は `nexthop` フィールドに紐づく nexthop IP が **既知の neighbor** でないと FRR / `srv6orch` は pending 扱いになります。

### FRR への配線確認

```bash
admin@sonic:~$ vtysh -c "show segment-routing srv6 locator"
Locator:
Name                 ID      Prefix                   Status
--------------------------------------------------------------------------------
loc1                 1       fc00:0:1::/48            Up

admin@sonic:~$ vtysh -c "show segment-routing srv6 sid"
 *... Selected SID
Function          Context                       Owner         Locator
-------------------------------------------------------------------------------
fc00:0:1:e000::   uN                            zebra         loc1
fc00:0:1:e001::   uA (nh fe80::1)               bgp           loc1
```

[bgpcfgd](../../reference/glossary.md#term-bgpcfgd) 経由で `vtysh` に流れる経路は [アーキテクチャ](architecture.md) を参照します。`vtysh` 側に出ない場合は bgpcfgd ログ（`/var/log/syslog` 内 `bgpcfgd` プレフィックス）を見ます。

### APP_DB / ASIC_DB の programming 確認

```bash
admin@sonic:~$ redis-cli -n 0 KEYS "SRV6_MY_SID_TABLE:*"
1) "SRV6_MY_SID_TABLE:32:16:16:0:fc00:0:1:e000::"
admin@sonic:~$ redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_MY_SID_ENTRY:*" | wc -l
2
```

APP_DB に乗っているのに [ASIC_DB](../../reference/glossary.md#term-asic_db) に出ない場合、`srv6orch` の pending queue で止まっている可能性が高いです。`docker exec swss supervisorctl tail -f orchagent` で `SRv6Orch` のログを追います。次のいずれかが典型です。

| 症状 | 原因 | 対処 |
| --- | --- | --- |
| `Failed to find nexthop ...` を繰り返す | uA / End.X の nexthop IPv6 の neighbor 未解決 | 対向に IPv6 ping、`ip -6 neigh show` で reachable 化 |
| `SAI_STATUS_NOT_SUPPORTED` を返す | ASIC が SRv6 endpoint behavior 非対応 | platform 章 / SAI vendor 表で対応確認 |
| `Locator block/node/func length mismatch` | CONFIG_DB の locator と SID prefix 不整合 | `SRV6_MY_LOCATORS` の `block_len`/`node_len`/`func_len` を再確認 |

### トラフィック観測

MySID 単位の counter は phase 機能で、現状の [SONiC](../../reference/glossary.md#term-sonic) master では IPv6 forwarding 全体の [RIF](../../reference/glossary.md#term-rif) counter で代用するのが現実的です。

```bash
admin@sonic:~$ sonic-clear counters
admin@sonic:~$ show interfaces counters rif
    IFACE    RX_OK    RX_BPS    RX_PPS  ...
---------  -------  --------  --------  ...
Ethernet0      120    9.6 KB        80  ...
```

uA / End.X が forwarding しているかを概観するには十分です。ヘッダ単位の観察が必要なら `tcpdump -i <intf> -nn ip6 proto 43` で SRH を見ます。

## MPLS

### per-RIF 有効化の確認

```bash
admin@sonic:~$ redis-cli -n 4 HGET "INTERFACE|Ethernet0" mpls
enable
admin@sonic:~$ redis-cli -n 0 HGETALL "INTF_TABLE:Ethernet0" | grep -A1 mpls
mpls
enable
```

`show interfaces mpls` 系 CLI の提供範囲は実装依存です。`show runningconfiguration` で `mpls` 行が出れば CONFIG_DB には入っています。

### FRR / LSP の確認

```bash
admin@sonic:~$ vtysh -c "show mpls table"
 Inbound Label  Type        Nexthop         Outbound Label
 -----------------------------------------------------------
 16             Static      10.0.0.1        17
 17             Static      10.0.0.2        Pop Label
```

LSP が消えるパターンは多くが LDP / [BGP](../../reference/glossary.md#term-bgp)-LU の neighbor down です。`vtysh -c "show mpls ldp neighbor"` / `vtysh -c "show bgp ipv4 labeled-unicast summary"` を最初に見ます。

### APP_DB と ASIC_DB

```bash
admin@sonic:~$ redis-cli -n 0 KEYS "LABEL_ROUTE_TABLE:*" | head
1) "LABEL_ROUTE_TABLE:16"
2) "LABEL_ROUTE_TABLE:17"
admin@sonic:~$ redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_INSEG_ENTRY:*" | wc -l
2
```

APP_DB と ASIC_DB の件数が乖離していれば `orchagent` 側で SAI install に失敗している可能性が高く、`ERROR_DB` を見ます（[SAI 失敗ハンドリング](../../platform/hld-for-handling-sai-failures.md)）。

```bash
admin@sonic:~$ redis-cli -n 13 KEYS "ERROR_*" | head
admin@sonic:~$ redis-cli -n 13 HGETALL "ERROR_INSEG_ENTRY|16"
1) "operation"
2) "create"
3) "rc"
4) "SAI_STATUS_TABLE_FULL"
```

### CRM と QoS

```bash
admin@sonic:~$ crm show resources mpls_inseg
Resource Name    Used Count    Available Count
---------------  ------------  ---------------
mpls_inseg       2             16382

admin@sonic:~$ crm show thresholds mpls_inseg
admin@sonic:~$ sudo config crm thresholds mpls inseg type percentage
admin@sonic:~$ sudo config crm thresholds mpls inseg high 85
```

大規模静的 LSP では事前に threshold を設定すると、`/var/log/syslog` に [CRM](../../reference/glossary.md#term-crm) の警告が出ます。[QoS](../../reference/glossary.md#term-qos) が効かないときは `MPLS_TC_TO_TC_MAP` → `PORT_QOS_MAP` の参照を CONFIG_DB から辿ります。

## Path Tracing

### CONFIG_DB と show

```bash
admin@sonic:~$ show interface path-tracing
  Interface    PT Interface ID    PT Timestamp Template
-----------  -----------------  -----------------------
Ethernet0    513                template3
admin@sonic:~$ redis-cli -n 4 HGETALL "PORT|Ethernet0" | grep -A1 pt_
pt_interface_id
513
pt_timestamp_template
template3
```

### ASIC programming

```bash
admin@sonic:~$ redis-cli -n 1 HGETALL "ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x..." | grep -A1 PATH_TRACING
SAI_PORT_ATTR_PATH_TRACING_INTF
513
SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE
SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_TEMPLATE3
```

probe 生成・回収は SONiC 外側（PT Source / Sink / Regional Collector）の仕事です。SONiC は midpoint として **HbH-PT の MCD を書き足す** だけなので、検証は経路上で実トラフィックをキャプチャして MCD が増えているかを確認するのが手っ取り早いです。

SRv6 `H.Encaps.Red` と Path Tracing を併用するときは、外側 IPv6 の HbH-PT が内側にどう写るかが ASIC 実装依存で、[HLD](../../reference/glossary.md#term-hld) の前提と乖離していることがあります（[discrepancy](../../routing/path-tracing-midpoint.md) 参照）。

## 障害切り分けの順序（共通）

機能を問わず、次の順で潰すと迷いにくくなります。

1. **CONFIG_DB**: 設定が入っているか（`redis-cli -n 4`）。
2. **APP_DB / netlink**: FRR / [fpmsyncd](../../reference/glossary.md#term-fpmsyncd) / bgpcfgd の中継が動いているか（`redis-cli -n 0`、`vtysh -c "show ..."`）。
3. **ASIC_DB**: [orchagent](../../reference/glossary.md#term-orchagent) が SAI に投げたか（`redis-cli -n 1`）。
4. **ERROR_DB**: SAI が拒否していないか（`redis-cli -n 13`）。
5. **ASIC counter / RIF counter**: パケットが本当に流れているか（`show interfaces counters rif`、`show interfaces counters`）。
6. **キャプチャ**: ヘッダ・ラベル・HbH-PT の中身まで降りる（`tcpdump`、ASIC の port mirror）。

特に SRv6 と MPLS は、route の入口（FRR vs CONFIG_DB 直書き）が複数あるため、APP_DB をスキップして CONFIG_DB と ASIC_DB だけ見ると「片方の経路が動いていることに気付けない」事故が起きます。

## ログの場所

| 経路 | ログ | grep キーワード |
| --- | --- | --- |
| FRR | `/var/log/frr/zebra.log`、`bgpd.log` | `srv6`、`mpls`、`label` |
| bgpcfgd | `/var/log/syslog` | `bgpcfgd`、`SRv6Mgr` |
| fpmsyncd | `docker exec bgp supervisorctl tail fpmsyncd` | `LABEL_ROUTE`、`netlink` |
| orchagent | `docker exec swss supervisorctl tail orchagent` | `Srv6Orch`、`MplsRouteOrch` |
| [syncd](../../reference/glossary.md#term-syncd) | `docker exec syncd supervisorctl tail syncd` | `SAI_STATUS`、`MY_SID`、`INSEG` |

## 関連ページ

- [router interface counters](../../routing/router-interface-counters-in-sonic.md)
- [MPLS HLD](../../routing/mpls-for-sonic-high-level-design-document.md)
- [Path Tracing Midpoint](../../routing/path-tracing-midpoint.md)
- [SRv6 HLD](../../routing/segment-routing-over-ipv6-srv6-hld.md)
- [SAI 失敗ハンドリング](../../platform/hld-for-handling-sai-failures.md)
- [BGP 章](../02-bgp/index.md)
- [VRF / ECMP 章](../04-vrf-ecmp/index.md)（next-hop / nexthop group の確認）
- [SWSS / SAI / Redis 章](../20-swss-sai-redis/index.md)（共通の SAI 失敗観察）

<!-- glossary-links-injected: ec18b66e3507 -->
