---
title: 運用
description: 運用 — ACL / CoPP / mirror の調査では、設定が存在するか、ASIC に反映されたか、counter が増えるかを分けて確認します。CONFIG_DB
  に見えていることと、実際に hardware に作られていることは同じではありません。
area: topics
verification: meta
last_verified: 2026-05-10
sources:
- docs/acl-qos/enhancements-on-show-acl-commands.md
- docs/acl-qos/sonic-port-mirroring-hld.md
- docs/acl-qos/everflow-test-plan.md
- docs/acl-qos/configurable-drop-counters-in-sonic.md
- docs/acl-qos/sonic-test-ingress-discards-hld.md
- docs/architecture/port-illegal-packets-drop-design.md
related:
  cli:
  - show acl
  - show flowcnt
  - show interfaces
  - show ip
  - show arp
  config_db:
  - COPP_TRAP
  - VLAN
  - SNMP
  - MIRROR_SESSION
  - COPP_GROUP
  yang: []
---

# 運用

[ACL](../../reference/glossary.md#term-acl) / [CoPP](../../reference/glossary.md#term-copp) / mirror の調査では、設定が存在するか、[ASIC](../../reference/glossary.md#term-asic) に反映されたか、counter が増えるかを分けて確認します。[CONFIG_DB](../../reference/glossary.md#term-config_db) に見えていることと、実際に hardware に作られていることは同じではありません。

## ACL の状態確認

最初に `show acl table` と `show acl rule` で table / rule の存在と status を見ます。show ACL 強化により、`AclOrch` が [STATE_DB](../../reference/glossary.md#term-state_db) の `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` に Active / Inactive を出すため、リソース不足や [SAI](../../reference/glossary.md#term-sai) 失敗で作成できなかった場合を CLI 側から判別できます。

```text
admin@sonic:~$ show acl table
Name          Type      Binding         Description    Stage    Status
------------  --------  --------------  -------------  -------  --------
DATAACL       L3        Ethernet0       data plane     ingress  Active
EVERFLOW      MIRROR    PortChannel0    mirror traffic ingress  Active
EVERFLOWV6    MIRRORV6  PortChannel0    mirror v6      ingress  Inactive
```

`Inactive` が出ているとき、原因はおおむね以下のいずれかです。

| Status | 典型原因 | 確認場所 |
|--------|----------|----------|
| `Inactive` (作成直後) | SAI table create が失敗、[TCAM](../../reference/glossary.md#term-tcam) スロット不足 | `/var/log/syslog` の `orchagent` SAI_STATUS |
| `Inactive` (port バインド) | 対象 port が削除済み / admin down 直後 | `show interfaces status` |
| `Active` だが hit しない | match field が ASIC で未サポート | `swssloglevel -l INFO -c orchagent` で再現確認 |

次に `aclshow` で rule counter を見ます。counter が期待通り増えない場合は、traffic が match していない、priority で別 rule に先に当たっている、counter polling が止まっている、ASIC に rule が入っていない、の順に切り分けます。

```text
admin@sonic:~$ aclshow -a
RULE NAME      TABLE NAME      PRIO    PACKETS COUNT    BYTES COUNT
-------------  --------------  ------  ---------------  -----------
DENY_RULE_1    DATAACL         9999    12345            1518000
PERMIT_ANY     DATAACL         1       0                0
```

counter polling が止まっているかは `counterpoll show` で `ACL_STAT` group の状態を確認します。`disable` なら `counterpoll acl enable` で復活させます。STATE_DB / [COUNTERS_DB](../../reference/glossary.md#term-counters_db) の対応は以下のとおりです。

| DB | Key 例 | 用途 |
|----|--------|------|
| `CONFIG_DB` | `ACL_TABLE\|DATAACL`, `ACL_RULE\|DATAACL\|RULE_1` | 設定 |
| `STATE_DB` | `ACL_TABLE_TABLE\|DATAACL` | 作成結果 (status) |
| `COUNTERS_DB` | `COUNTERS:oid:0x...` / `ACL_COUNTER_RULE_MAP` | rule 単位 counter |
| `ASIC_DB` | `ASIC_STATE:SAI_OBJECT_TYPE_ACL_TABLE:oid:...` | SAI 反映 |

設定が CONFIG_DB に入っているのに [ASIC_DB](../../reference/glossary.md#term-asic_db) に出ていない場合は [orchagent](../../reference/glossary.md#term-orchagent) が握っているので syslog を見ます。

## Mirror の確認

Mirror は session と ACL action の 2 段で確認します。`MIRROR_SESSION` が有効になっているか、collector への経路があるか、SPAN の `dst_port` が正しいかを先に見ます。その後、mirror 用 ACL table / rule が Active で、該当 rule counter が増えるかを見ます。

```text
admin@sonic:~$ show mirror_session
ERSPAN Sessions
Name      Status  SRC IP       DST IP       GRE  DSCP  TTL  Queue  Policer  Monitor Port  SRC Port  Direction
--------  ------  -----------  -----------  ---  ----  ---  -----  -------  ------------  --------  ---------
everflow0 active  10.1.0.32    2.2.2.2      0x88be  8   255   0      -        Ethernet8     Ethernet0 rx
```

`Status: inactive` のときは、collector への route が無い、neighbor MAC が解けていない、policer が無効、のいずれかが多いです。

```text
admin@sonic:~$ redis-cli -n 6 hgetall "MIRROR_SESSION_TABLE|everflow0"
1) "status"
2) "active"
3) "monitor_port"
4) "Ethernet8"
5) "dst_mac"
6) "ec:0d:9a:xx:xx:xx"
7) "route_prefix"
8) "2.2.2.2/32"
9) "next_hop_ip"
10) "10.0.0.1@PortChannel0"
```

Everflow では [LAG](../../reference/glossary.md#term-lag)、[ECMP](../../reference/glossary.md#term-ecmp)、neighbor MAC 変更、IPv6、egress ACL などが絡みます。mirror packet が出ない場合、ACL の match 失敗だけでなく、collector 経路や egress mirror capability も疑います。Everflow テストプランの観点に従い、collector route が ECMP の場合は member すべての MAC が STATE_DB に解決されているかを `show ip route` と `show arp` で揃えます。

## Drop 調査の入口

drop 調査では、何を落としているかで見る counter が変わります。

| 見たいもの | 主な入口 | 代表コマンド / DB |
|------------|----------|-------------------|
| ACL rule で drop したか | ACL counter | `aclshow` |
| port ingress discard | port counter | `portstat` |
| [RIF](../../reference/glossary.md#term-rif) / L3 error | interface counter | `intfstat` |
| drop reason 別の ASIC drop | debug counter | `show dropcounters counts` |
| CPU punt の量 | trap flow counter | `show flowcnt trap` |

不正パケットの ingress discard テストでは Ethernet 層、IP 層、ACL 層で期待 counter が異なります。`SMAC=DMAC` のような L2 drop と、TTL 0 や壊れた IP header のような L3 error と、ACL `DROP` は同じ場所に出ません。

## Debug Counter

設定可能な drop counter は SAI debug counter を使い、drop reason の組み合わせをユーザが定義します。`show dropcounters capabilities` で type ごとの残スロットとサポート理由を確認し、`config dropcounters install` で必要な counter を作ります。

```text
admin@sonic:~$ show dropcounters capabilities
Counter Type             Total
PORT_INGRESS_DROPS       3
SWITCH_INGRESS_DROPS     2

Reasons supported per counter type:
PORT_INGRESS_DROPS:
  SMAC_EQUALS_DMAC
  SMAC_MULTICAST
  TTL
  L3_ANY
  ACL_ANY
  ...
```

設定〜観測の典型フロー:

```bash
# 残スロットを確認
show dropcounters capabilities

# SMAC=DMAC を独立 counter で計測する
config dropcounters install BAD_SMAC PORT_INGRESS_DROPS '[SMAC_EQUALS_DMAC,SMAC_MULTICAST]' -d "L2 sanity drops"

# 確認
show dropcounters configuration
show dropcounters counts

# 不要になったら削除
config dropcounters delete BAD_SMAC
```

drop counter は「なぜ落ちたか」を見る道具です。ACL counter は「どの rule に hit したか」を見る道具です。両方を同時に使うと、ACL で期待通り drop しているのか、別の ASIC reason で落ちているのかを分けられます。

## SNMP / MIB から見る場合

port illegal packets drop design は、RIF / [VLAN](../../reference/glossary.md#term-vlan) など L3 側の SAI counter を Interface MIB へどう集約するかを扱います。[SNMP](../../reference/glossary.md#term-snmp) で `ifInErrors` や `ifOutErrors` を監視している環境では、L2 port counter と RIF counter の集約方針がトラブルシュート結果に影響します。

snmpwalk で `IF-MIB::ifInErrors` が振り切れているのに `portstat` の RX_ERR が静かな場合、RIF 側の counter が SNMP 集約されている可能性があります。逆もまた然りで、SNMP モニタと CLI counter の数字が違っても整合は取れているケースが多いです。

## CoPP の確認

CoPP (Control Plane [Policer](../../reference/glossary.md#term-policer)) は CPU 向け punt traffic を trap group ごとに policing します。`show copp` 系のコマンドは限定的なので、CONFIG_DB と `show flowcnt trap` を併用します。

```text
admin@sonic:~$ show flowcnt trap stats
    Trap Name         Packets    Bytes    PPS    Trap Group
-----------------  ---------    -----    -----    ----------
arp_req               1234       98720    12       arp
arp_resp              2345      187600    23       arp
bgp                     10        1000     0       bgp_lacp
lacp                   100       12000     1       bgp_lacp
ip2me                   50        4000     0       default
```

該当 trap が想定 PPS を超えると policer で drop され、対応プロトコル ([BGP](../../reference/glossary.md#term-bgp) / [LACP](../../reference/glossary.md#term-lacp) / [ARP](../../reference/glossary.md#term-arp)) が落ち始めます。`COPP_TABLE` の `cir` / `cbs` と `red_action: drop` を確認し、必要なら trap group ごとに緩めます。

| 観点 | 入口 | DB |
|------|------|-----|
| trap group 設定 | `redis-cli -n 4 keys "COPP_*"` | CONFIG_DB `COPP_TRAP` / `COPP_GROUP` |
| trap PPS | `show flowcnt trap stats` | COUNTERS_DB `COUNTERS_TRAP_NAME_MAP` |
| police 結果 | hostif policer drop | ASIC_DB `SAI_OBJECT_TYPE_POLICER` |

## 対応コマンド早見表

| 症状 | 最初に叩くコマンド | 次に見る場所 |
|------|--------------------|--------------|
| ACL を作ったのに効かない | `show acl table` / `show acl rule` で Status | STATE_DB `ACL_TABLE_TABLE`、syslog `orchagent` |
| ACL counter が増えない | `aclshow -a` + `counterpoll show` | COUNTERS_DB、priority 衝突 |
| mirror が collector に着かない | `show mirror_session` | route / arp / `MIRROR_SESSION_TABLE` |
| 突然 BGP が落ちた | `show flowcnt trap stats` | `COPP_TRAP` の cir/cbs |
| port が drop している | `portstat` → `show dropcounters counts` | debug counter で reason 切り分け |
| L3 で drop している | `intfstat` | RIF counter / TTL / IP header |
| CPU が忙しい | `top` + `show flowcnt trap` | trap PPS 上位、CoPP |

## 関連ページ

- [show acl 強化](../../acl-qos/enhancements-on-show-acl-commands.md)
- [SONiC Port Mirroring](../../acl-qos/sonic-port-mirroring-hld.md)
- [Everflow テストプラン](../../acl-qos/everflow-test-plan.md)
- [設定可能な Drop Counter](../../acl-qos/configurable-drop-counters-in-sonic.md)
- [ingress discards テスト計画](../../acl-qos/sonic-test-ingress-discards-hld.md)
- [ポート不正パケットドロップ設計](../../architecture/port-illegal-packets-drop-design.md)
- 章 [08 QoS / Buffer](../08-qos-buffer/operations.md) — queue / PG drop と [PFC](../../reference/glossary.md#term-pfc)
- 章 [09 telemetry / SNMP / observability](../09-telemetry-snmp/operations.md) — techsupport と system health
- 章 [10 gNMI / OpenConfig](../10-gnmi-openconfig/operations.md) — ACL / mirror を [gNMI](../../reference/glossary.md#term-gnmi) で設定する場合
- [CoPP neighbor-miss trap と強化](../../acl-qos/copp-neighbor-miss-trap-and-enhancements.md) — CoPP の trap group 設計
- [CoPP manager リデザイン テストプラン](../../acl-qos/copp-manager-redesign-test-plan.md) — trap 別の挙動確認の観点

<!-- glossary-links-injected: c006405759d8 -->
