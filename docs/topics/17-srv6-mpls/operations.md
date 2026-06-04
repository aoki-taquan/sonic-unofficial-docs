---
title: 運用
description: SRv6 / MPLS / Path Tracing の運用確認は「設定が CONFIG_DB に正しく入ったか」「FRR / netlink 経由で
  APP_DB に渡ったか」「SAI / ASIC に programming されたか」の三段を順に追います。各機能の出口（show コマンド / DB
  / ログ）と典型的な異常パターンを実例ベースで整理します。
area: topics
verification: code-verified
last_verified: 2026-06-04
sources:
- repo: sonic-net/sonic-swss
  path: orchagent/srv6orch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: orchagent/srv6orch.h
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss
  path: orchagent/portsorch.cpp
  ref: 4305596156d70e9797e8a881b3d19b46de0bce0d
- repo: sonic-net/sonic-swss-common
  path: common/schema.h
  ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
- repo: sonic-net/sonic-utilities
  path: show/srv6.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
- repo: sonic-net/sonic-utilities
  path: scripts/route_check.py
  ref: 39732bceb8bdefe706518ab40623bbbba6ff33b9
related:
  cli:
  - show srv6 locators
  - show srv6 static-sids
  - show srv6 stats
  - show mpls
  - show interfaces counters rif
  - sonic-clear counters
  - crm show resources mpls_inseg
  config_db:
  - SRV6_MY_LOCATORS
  - SRV6_MY_SIDS
  - INTERFACE
  - PORT
  - MPLS_TC_TO_TC_MAP
  - PORT_QOS_MAP
  - CRM
  yang:
  - sonic-srv6
  - sonic-interface
  - sonic-port
  - sonic-crm
---

# 運用

[SRv6](../../reference/glossary.md#term-srv6) / [MPLS](../../reference/glossary.md#term-mpls) / Path Tracing の運用確認は、「設定が [CONFIG_DB](../../reference/glossary.md#term-config_db) に正しく入ったか」「[FRR](../../reference/glossary.md#term-frr) / netlink 経由で APP_DB に渡ったか」「[SAI](../../reference/glossary.md#term-sai) / [ASIC](../../reference/glossary.md#term-asic) に programming されたか」の三段を順に追います。本ページは各機能の出口（show コマンド / DB / ログ）と、よく遭遇する異常パターン、その復旧手順を実例ベースで並べます。

## SRv6

### 設定が CONFIG_DB に入ったかの確認

CONFIG_DB のテーブル名は `SRV6_MY_LOCATORS` / `SRV6_MY_SIDS` です[^schema][^show-srv6]。

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

CLI からは `show srv6 locators` / `show srv6 static-sids` で同等の情報が取れます[^show-srv6]。

<!-- evidence:
sonic-swss-common/common/schema.h L398-399 @ 158de8d3:
  #define CFG_SRV6_MY_SID_TABLE_NAME      "SRV6_MY_SIDS"
  #define CFG_SRV6_MY_LOCATOR_TABLE_NAME  "SRV6_MY_LOCATORS"
sonic-utilities/show/srv6.py L10-11 @ 39732bce:
  CONFIG_DB_MY_SID_TABLE     = 'SRV6_MY_SIDS'
  CONFIG_DB_MY_LOCATORS_TABLE = 'SRV6_MY_LOCATORS'
sonic-swss/orchagent/srv6orch.cpp L341-343 @ 43055961:
  auto blen = fvsGetValue(fvs, "block_len", true);
  auto nlen = fvsGetValue(fvs, "node_len", true);
  auto flen = fvsGetValue(fvs, "func_len", true);
-->

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

APP_DB のテーブル名は `SRV6_MY_SID_TABLE`、ASIC_DB は `SAI_OBJECT_TYPE_MY_SID_ENTRY` です[^schema][^srv6orch]。

```bash
admin@sonic:~$ redis-cli -n 0 KEYS "SRV6_MY_SID_TABLE:*"
1) "SRV6_MY_SID_TABLE:32:16:16:0:fc00:0:1:e000::"
admin@sonic:~$ redis-cli -n 1 KEYS "ASIC_STATE:SAI_OBJECT_TYPE_MY_SID_ENTRY:*" | wc -l
2
```

APP_DB のキーは `block_len:node_len:func_len:args_len:sid-ip` の形式で、`srv6orch` 内のコメント (L2210) でもこの順序が明示されています[^srv6orch]。

APP_DB に乗っているのに [ASIC_DB](../../reference/glossary.md#term-asic_db) に出ない場合、`srv6orch` の pending queue で止まっている可能性が高いです。`docker exec swss supervisorctl tail -f orchagent` で `SRv6Orch` のログを追います。次のいずれかが典型です。

| 症状 | 原因 | 対処 |
| --- | --- | --- |
| `Failed to find nexthop ...` を繰り返す | uA / End.X の nexthop IPv6 の neighbor 未解決 | 対向に IPv6 ping、`ip -6 neigh show` で reachable 化 |
| `SAI_STATUS_NOT_SUPPORTED` を返す | ASIC が SRv6 endpoint behavior 非対応 | platform 章 / SAI vendor 表で対応確認 |
| `Locator block/node/func length mismatch` | CONFIG_DB の locator と SID prefix 不整合 | `SRV6_MY_LOCATORS` の `block_len`/`node_len`/`func_len` を再確認 |

### トラフィック観測

MySID 単位の counter は `show srv6 stats` で参照できますが[^show-srv6-stats]、forwarding 量の概観には IPv6 全体の [RIF](../../reference/glossary.md#term-rif) counter が手早く有効です。

```bash
admin@sonic:~$ sonic-clear counters
admin@sonic:~$ show interfaces counters rif
    IFACE    RX_OK    RX_BPS    RX_PPS  ...
---------  -------  --------  --------  ...
Ethernet0      120    9.6 KB        80  ...
```

ヘッダ単位の観察が必要なら `tcpdump -i <intf> -nn ip6 proto 43` で SRH を見ます。

## MPLS

### per-RIF 有効化の確認

```bash
admin@sonic:~$ redis-cli -n 4 HGET "INTERFACE|Ethernet0" mpls
enable
admin@sonic:~$ redis-cli -n 0 HGETALL "INTF_TABLE:Ethernet0" | grep -A1 mpls
mpls
enable
```

`show runningconfiguration` で `mpls` 行が出れば CONFIG_DB には入っています。`show interfaces` 系で MPLS 専用サブコマンドは現状提供されていません。

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

APP_DB は `LABEL_ROUTE_TABLE`[^schema-mpls]、ASIC_DB は `SAI_OBJECT_TYPE_INSEG_ENTRY` です。

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

`crmorch` は `CRM_MPLS_INSEG` を `SAI_OBJECT_TYPE_INSEG_ENTRY` にマッピングしてカウントします[^crm]。大規模静的 LSP では事前に threshold を設定すると、`/var/log/syslog` に [CRM](../../reference/glossary.md#term-crm) の警告が出ます。[QoS](../../reference/glossary.md#term-qos) が効かないときは `MPLS_TC_TO_TC_MAP` → `PORT_QOS_MAP` の参照を CONFIG_DB から辿ります。

## Path Tracing

### CONFIG_DB の確認

Path Tracing の per-port 設定は `PORT` テーブルの `pt_interface_id` / `pt_timestamp_template` フィールドで持ちます[^pt-schema][^portsorch-pt]。`show interfaces path-tracing` 相当の専用 CLI は現行 master の `sonic-utilities` には未実装で、確認は `redis-cli` か `show runningconfiguration` で行います。

```bash
admin@sonic:~$ redis-cli -n 4 HGETALL "PORT|Ethernet0" | grep -A1 pt_
pt_interface_id
513
pt_timestamp_template
template3
```

### ASIC programming

`portsorch` が `SAI_PORT_ATTR_PATH_TRACING_INTF` および `SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE` を Port に書き込みます[^[portsorch](../../reference/glossary.md#term-portsorch)-pt]。timestamp の `template1`〜`template4` は `SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_*_*` にマッピングされます[^portsorch-pt-map]。

```bash
admin@sonic:~$ redis-cli -n 1 HGETALL "ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x..." | grep -A1 PATH_TRACING
SAI_PORT_ATTR_PATH_TRACING_INTF
513
SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE
SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_TEMPLATE3
```

<!-- evidence:
sonic-swss/orchagent/portsorch.cpp L213-218 @ 43055961:
  static map<string, sai_port_path_tracing_timestamp_type_t> pt_timestamp_template_map =
  {
    { "template1", SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_8_15  },
    { "template2", SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_12_19 },
    { "template3", SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_16_23 },
    { "template4", SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_20_27 }
  };
sonic-swss/orchagent/portsorch.cpp L11487, L11507 @ 43055961:
  attr.id = SAI_PORT_ATTR_PATH_TRACING_INTF;
  attr.id = SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE;
-->

probe 生成・回収は [SONiC](../../reference/glossary.md#term-sonic) 外側（PT Source / Sink / Regional Collector）の仕事です。SONiC は midpoint として **HbH-PT の MCD を書き足す** だけなので、検証は経路上で実トラフィックをキャプチャして MCD が増えているかを確認するのが手っ取り早いです。

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

## 引用元

[^schema]: `sonic-net/sonic-swss-common` `common/schema.h` L169, L398-399 @ `158de8d3` — `CFG_SRV6_MY_LOCATOR_TABLE_NAME = "SRV6_MY_LOCATORS"`、`CFG_SRV6_MY_SID_TABLE_NAME = "SRV6_MY_SIDS"`、`APP_SRV6_MY_SID_TABLE_NAME = "SRV6_MY_SID_TABLE"`。
[^show-srv6]: `sonic-net/sonic-utilities` `show/srv6.py` L10-11, L51-58 @ `39732bce` — `show srv6 locators` が `SRV6_MY_LOCATORS` を、`show srv6 static-sids` が `SRV6_MY_SIDS` / `SRV6_MY_SID_TABLE` を読みます。
[^show-srv6-stats]: `sonic-net/sonic-utilities` `show/srv6.py` L150-151 @ `39732bce` — `show srv6 stats` サブコマンド。
[^srv6orch]: `sonic-net/sonic-swss` `orchagent/srv6orch.cpp` L104-107, L1453-1454, L2210 @ `43055961` — APP_DB / CONFIG_DB の両 SRv6 テーブルを購読し、MySID キーを `block_len:node_len:function_len:args_len:sid-ip` の順で分解します。
[^schema-mpls]: `sonic-net/sonic-swss-common` `common/schema.h` L48 @ `158de8d3` — `APP_LABEL_ROUTE_TABLE_NAME = "LABEL_ROUTE_TABLE"`。
[^crm]: `sonic-net/sonic-swss` `orchagent/crmorch.cpp` L113 @ `43055961` — `CRM_MPLS_INSEG` を `SAI_OBJECT_TYPE_INSEG_ENTRY` にマッピング。
[^pt-schema]: `sonic-net/sonic-swss` `doc/swss-schema.md` L30, L1026 @ `43055961` — `PORT` テーブルの `pt_interface_id` (1-4095) と `pt_timestamp_template` フィールド定義。
[^portsorch-pt]: `sonic-net/sonic-swss` `orchagent/portsorch.cpp` L1420, L1435, L11484-11507 @ `43055961` — `portsorch` が `SAI_PORT_ATTR_PATH_TRACING_INTF` / `SAI_PORT_ATTR_PATH_TRACING_TIMESTAMP_TYPE` を Port に設定。
[^portsorch-pt-map]: `sonic-net/sonic-swss` `orchagent/portsorch.cpp` L213-218 @ `43055961` — `template1`〜`template4` の文字列を `SAI_PORT_PATH_TRACING_TIMESTAMP_TYPE_*_*` にマッピング。

<!-- glossary-links-injected: 4e8b9837844c -->
