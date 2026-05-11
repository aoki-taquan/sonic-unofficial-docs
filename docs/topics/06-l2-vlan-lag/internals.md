---
title: 内部実装
area: topics
verification: meta
last_verified: 2026-05-11
sources: []
---

# 内部実装

L2 / VLAN / LAG / MC-LAG の内部実装は「kernel と orchagent の二重管理」を理解するのが鍵です。Linux bond / bridge / vlan device の状態と、SAI の LAG / VLAN member / FDB entry が常に同期しているわけではなく、teamd / portsyncd / vlanmgrd / fdbsyncd が橋渡しをします。

## データフロー

```mermaid
flowchart LR
  CFG[(CONFIG_DB<br/>PORT/VLAN/PORTCHANNEL)] --> TEAMD[teamd<br/>+ teamsyncd]
  CFG --> VLANMGRD[vlanmgrd]
  CFG --> INTFMGRD[intfmgrd]
  TEAMD --> KERNEL[Linux bond]
  VLANMGRD --> KERNEL2[Linux bridge / vlan]
  KERNEL -->|netlink| PORTSYNCD[portsyncd]
  KERNEL2 -->|netlink| FDBSYNCD[fdbsyncd]
  PORTSYNCD --> APPL[(APPL_DB<br/>PORT/LAG_TABLE/LAG_MEMBER_TABLE)]
  FDBSYNCD --> APPL2[(APPL_DB<br/>FDB_TABLE)]
  APPL --> ORCH[orchagent<br/>PortsOrch / LagOrch / VlanOrch / FdbOrch]
  APPL2 --> ORCH
  ORCH --> ASIC[(ASIC_DB<br/>LAG / VLAN / FDB / BRIDGE)]
  ICCP[iccpd<br/>MC-LAG] --> APPL
```

## 主要 Orch / daemon の責務

| コンポーネント | 主なクラス | 責務 |
| --- | --- | --- |
| `PortsOrch` (`orchagent/portsorch.cpp`) | `PortsOrch::doTask`、`initializePort`、`addLag`、`addLagMember` | PORT / LAG / VLAN を SAI に投入。最も巨大な Orch |
| `VlanMgr` (`cfgmgr/vlanmgr.cpp`) | `VlanMgr::doTask` | CONFIG_DB の `VLAN` / `VLAN_MEMBER` を bridge fdb 設定と APPL_DB に反映 |
| `IntfMgr` (`cfgmgr/intfmgr.cpp`) | `IntfMgr::doTask` | router interface の IP/MTU を kernel に設定し、orchagent 用 APPL_DB key を作る |
| `FdbOrch` (`orchagent/fdborch.cpp`) | `FdbOrch::doTask`、`addFdbEntry`、`handleFdbNotification` | static FDB と learned FDB の管理、aging notification |
| `teamd` / `teamsyncd` | open source teamd + `teamsyncd.cpp` | LACP の実装は teamd。teamsyncd が kernel bond state を STATE_DB / APPL_DB へ |
| `portsyncd` (`portsyncd/portsyncd.cpp`) | `PortSyncd::run` | netlink で kernel の link state を APPL_DB に反映 |
| `fdbsyncd` (`fdbsyncd/fdbsync.cpp`) | EVPN type-2 同期も担う。kernel bridge fdb と APPL_DB の同期 |
| `iccpd` (`linkmgrd` ではなく `iccpd`) | `iccpd/` 配下 | MC-LAG 制御。ICCP メッセージで peer と sync、active/standby を決め APPL_DB に書く |

## SAI 属性の使用一覧

| object | 属性 |
| --- | --- |
| `SAI_OBJECT_TYPE_LAG` | `SAI_LAG_ATTR_PORT_VLAN_ID`、`SAI_LAG_ATTR_INGRESS_ACL`、`SAI_LAG_ATTR_DROP_UNTAGGED` |
| `SAI_OBJECT_TYPE_LAG_MEMBER` | `SAI_LAG_MEMBER_ATTR_LAG_ID`、`SAI_LAG_MEMBER_ATTR_PORT_ID`、`SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE` |
| `SAI_OBJECT_TYPE_VLAN` | `SAI_VLAN_ATTR_VLAN_ID`、`SAI_VLAN_ATTR_LEARN_DISABLE` |
| `SAI_OBJECT_TYPE_VLAN_MEMBER` | `SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID`、`SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE` |
| `SAI_OBJECT_TYPE_BRIDGE_PORT` | `SAI_BRIDGE_PORT_ATTR_TYPE = PORT`、`SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE` |
| `SAI_OBJECT_TYPE_FDB_ENTRY` | `SAI_FDB_ENTRY_ATTR_TYPE = STATIC/DYNAMIC`、`SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID`、`SAI_FDB_ENTRY_ATTR_PACKET_ACTION` |
| `SAI_OBJECT_TYPE_STP` | `SAI_STP_ATTR_VLAN_LIST`（PVST 系で参照） |

MC-LAG では `SAI_LAG_MEMBER_ATTR_EGRESS_DISABLE = true` を peer link 側に設定して loopback を防ぐ実装が使われます。

## Redis テーブル参照関係

```
CONFIG_DB:
  PORT, VLAN, VLAN_MEMBER, PORTCHANNEL, PORTCHANNEL_MEMBER,
  FDB, MCLAG_DOMAIN, MCLAG_INTERFACE, STP, STP_PORT
APPL_DB:
  PORT_TABLE, LAG_TABLE, LAG_MEMBER_TABLE,
  VLAN_TABLE, VLAN_MEMBER_TABLE, FDB_TABLE, STP_TABLE
STATE_DB:
  PORT_TABLE, LAG_TABLE, FDB_TABLE, MCLAG_REMOTE_FDB_TABLE
COUNTERS_DB:
  COUNTERS:<oid> (port, queue, PG)
ASIC_DB:
  LAG, LAG_MEMBER, VLAN, VLAN_MEMBER, BRIDGE_PORT, FDB_ENTRY, STP
```

`FdbOrch` は ASIC からの notification (`SAI_FDB_EVENT_LEARNED / AGED / FLUSHED`) を Redis pub/sub 経由で受け、APPL_DB.FDB_TABLE を更新します。MC-LAG の remote FDB は iccpd が `MCLAG_REMOTE_FDB_TABLE` に書き、`FdbOrch` がそれを static 同等として SAI に投入します。

## ZMQ / Redis pub/sub

- 通常 L2 系は ProducerStateTable / SubscriberStateTable の Redis pub/sub のみ。ZMQ は使いません。
- FDB notification は `ASIC_DB` の notification channel（Redis pub/sub）で `FdbOrch` に届きます。
- teamsyncd → APPL_DB は netlink → ProducerStateTable で、teamd 自体は Unix socket DBus で teamsyncd と話します。

## 既知の実装上の制約

- VLAN ID は SONiC では `Vlan<id>` の文字列キーで扱われ、`VLAN_MEMBER|Vlan100|Ethernet0` のように `|` 区切り。`vlanmgrd` 内で id の桁違いやスペースが入ると silent に skip されることが過去 issue で報告されています。
- MC-LAG（iccpd ベース）と EVPN-MH（EVPN multi-homing、FRR ベース）は別実装で、同じスイッチで両立する設計にはなっていません。
- FDB MAC move は ASIC 通知遅延と orchagent 内のリオーダリングで一時的に同じ MAC が複数ポート所属に見えることがあります。`FdbOrch::handleFdbNotification` が `SAI_FDB_EVENT_MOVE` を扱いますが、ASIC が MOVE ではなく LEARNED + DELETE を別タイミングで上げる場合に瞬間的に重複が出ます。
- LAG member の dynamic add/remove は SAI 側で `EGRESS_DISABLE` を切り替えるだけの実装と、`LAG_MEMBER` を作り直す実装があり、ベンダで挙動が違います。`PortsOrch::setLagMemberEgressDisable` 経路を取れない ASIC では一瞬パケットロスが入ります。
- STP は SONiC では PVST / RPVST の制御プレーンが limited で、`stp` モジュール ([sonic-stp](https://github.com/sonic-net/sonic-stp)) が有効になっている場合のみ動きます。

## 関連ページ

- [L2 basic mode test plan](../../switching/sonic-basic-l2-mode-test-plan.md)
- [MC-LAG enhancements](../../switching/mclag-enhancements.md)
- [LAG on distributed VOQ system](../../switching/lag-on-distributed-voq-system.md)
- [SONiC IP LAG incremental update](../../switching/sonic-ip-lag-incremental-update.md)
