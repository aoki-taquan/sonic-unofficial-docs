---
title: 頻出 SAI 属性早見表
description: "頻出 SAI 属性早見表 — SONiC syncd は SAI (Switch Abstraction Interface) を介して ASIC に設定を投入する。本ページは"
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
- repo: sonic-net/sonic-sairedis
  path: meta/
  ref: 88bc51ae95df66977601957515e5527119ffd4c5
- repo: sonic-net/sonic-swss
  path: orchagent/
  ref: 88bc51ae95df66977601957515e5527119ffd4c5
related:
  config_db: []
  cli: []
  yang: []
  _no_related: true
---

# 頻出 SAI 属性早見表

## 概要

[SONiC](../reference/glossary.md#term-sonic) [syncd](../reference/glossary.md#term-syncd) は [SAI](../reference/glossary.md#term-sai) (Switch Abstraction Interface) を介して [ASIC](../reference/glossary.md#term-asic) に設定を投入する。本ページは
**[orchagent](../reference/glossary.md#term-orchagent) / syncd が実際に参照する SAI 属性のうち頻出のもの**を object_type 別にまとめた早見表。
属性名・object_type・用途・関連 orchagent クラス / [CONFIG_DB](../reference/glossary.md#term-config_db) テーブル・関連ドキュメントを併記する。

データ収集は `.cache/sonic-sources/sonic-swss/orchagent/` 配下を `grep -roh 'SAI_<TYPE>_ATTR_[A-Z_0-9]*'`
で全件抽出し、頻出かつ意味の明確なものに絞った（commit
[`88bc51a`](https://github.com/sonic-net/sonic-sairedis/commit/88bc51ae95df66977601957515e5527119ffd4c5)
時点）。網羅性を狙うものではなく、トラブルシュート時に「この属性は何をしている / どの orch が触る」を
即引きするための索引である。

完全な属性定義は [sonic-net/SAI](https://github.com/sonic-net/SAI) の
`inc/sai*.h` を参照。

## SWITCH (`sai_switch_api`)

| 属性 | 用途 | 関連 orch / DB |
|------|------|----------------|
| `SAI_SWITCH_ATTR_INIT_SWITCH` | スイッチ初期化フラグ | `SwitchOrch` |
| `SAI_SWITCH_ATTR_CPU_PORT` | CPU ポートの OID | `PortsOrch`, `HostifMgr` |
| `SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID` | デフォルト VR OID | `VRFOrch` |
| `SAI_SWITCH_ATTR_DEFAULT_1Q_BRIDGE_ID` | デフォルト .1Q ブリッジ | `PortsOrch` |
| `SAI_SWITCH_ATTR_DEFAULT_TRAP_GROUP` | 既定 [CoPP](../reference/glossary.md#term-copp) trap group | `CoppOrch` |
| `SAI_SWITCH_ATTR_PORT_LIST` | 全ポート OID リスト | `PortsOrch` |
| `SAI_SWITCH_ATTR_PORT_NUMBER` | ポート数 | `PortsOrch` |
| `SAI_SWITCH_ATTR_SRC_MAC_ADDRESS` | スイッチ自身の MAC | `SwitchOrch` |
| `SAI_SWITCH_ATTR_FDB_AGING_TIME` | [FDB](../reference/glossary.md#term-fdb) エージングタイマ | `SwitchOrch` (`SWITCH\|switch` table) |
| `SAI_SWITCH_ATTR_ECMP_HASH` / `LAG_HASH` | [ECMP](../reference/glossary.md#term-ecmp)/[LAG](../reference/glossary.md#term-lag) ハッシュ OID | `SwitchOrch` |
| `SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_ALGORITHM` | ECMP ハッシュアルゴ | `SwitchOrch` |
| `SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_SEED` | ECMP ハッシュ seed | `SwitchOrch` |
| `SAI_SWITCH_ATTR_ACL_STAGE_INGRESS` / `ACL_STAGE_EGRESS` | サポート [ACL](../reference/glossary.md#term-acl) ステージ | `AclOrch` (capability 取得) |
| `SAI_SWITCH_ATTR_ACL_ENTRY_MINIMUM_PRIORITY` / `MAXIMUM_PRIORITY` | ACL prio 範囲 | `AclOrch` |
| `SAI_SWITCH_ATTR_AVAILABLE_IPV4_ROUTE_ENTRY` / `IPV6_ROUTE_ENTRY` | 残ルートテーブル容量 | `CrmOrch` |
| `SAI_SWITCH_ATTR_AVAILABLE_IPV4_NEIGHBOR_ENTRY` / `IPV6_NEIGHBOR_ENTRY` | neighbor 残 | `CrmOrch` |
| `SAI_SWITCH_ATTR_AVAILABLE_FDB_ENTRY` | FDB 残 | `CrmOrch` |
| `SAI_SWITCH_ATTR_AVAILABLE_ACL_TABLE` / `ACL_TABLE_GROUP` | ACL リソース残 | `CrmOrch` |
| `SAI_SWITCH_ATTR_AVAILABLE_NEXT_HOP_GROUP_ENTRY` / `MEMBER_ENTRY` | NHG 残 | `CrmOrch` |
| `SAI_SWITCH_ATTR_FDB_EVENT_NOTIFY` | FDB イベント通知 cb | `FdbOrch` |
| `SAI_SWITCH_ATTR_PORT_STATE_CHANGE_NOTIFY` | リンク状態通知 cb | `PortsOrch` |
| `SAI_SWITCH_ATTR_BFD_SESSION_STATE_CHANGE_NOTIFY` | [BFD](../reference/glossary.md#term-bfd) 状態通知 cb | `BfdOrch` |
| `SAI_SWITCH_ATTR_SHUTDOWN_REQUEST_NOTIFY` | warm shutdown 通知 | `SwitchOrch` |
| `SAI_SWITCH_ATTR_RESTART_WARM` / `WARM_RECOVER` | warm boot 制御 | `OrchDaemon`, `syncd` |
| `SAI_SWITCH_ATTR_PRE_SHUTDOWN` | pre-shutdown phase | warm boot |
| `SAI_SWITCH_ATTR_AVERAGE_TEMP` | 平均温度 (read-only) | `SensorOrch` |
| `SAI_SWITCH_ATTR_NUMBER_OF_ACTIVE_PORTS` | active port 数 | `PortsOrch` |
| 関連: [SAI/syncd 内部](../topics/20-swss-sai-redis/internals.md), [CRM 閾値超過](runbooks/crm-threshold-exceeded.md) | | |

## PORT (`sai_port_api`)

| 属性 | 用途 | 関連 orch / DB |
|------|------|----------------|
| `SAI_PORT_ATTR_ADMIN_STATE` | up/down | `PortsOrch` (`PORT\|admin_status`) |
| `SAI_PORT_ATTR_OPER_STATUS` | 物理リンク状態 (RO) | `PortsOrch` |
| `SAI_PORT_ATTR_SPEED` / `OPER_SPEED` | 速度設定 / 実効値 | `PortsOrch` (`PORT\|speed`) |
| `SAI_PORT_ATTR_MTU` | L2 MTU | `PortsOrch` (`PORT\|mtu`) |
| `SAI_PORT_ATTR_HW_LANE_LIST` | [SerDes](../reference/glossary.md#term-serdes) lane | `PortsOrch` (`PORT\|lanes`) |
| `SAI_PORT_ATTR_FEC_MODE` / `OPER_PORT_FEC_MODE` | FEC | `PortsOrch` (`PORT\|fec`) |
| `SAI_PORT_ATTR_AUTO_NEG_MODE` | AN | `PortsOrch` (`PORT\|autoneg`) |
| `SAI_PORT_ATTR_ADVERTISED_SPEED` / `ADVERTISED_FEC_MODE` / `ADVERTISED_AUTO_NEG_MODE` | AN 広告 | `PortsOrch` |
| `SAI_PORT_ATTR_INTERFACE_TYPE` / `ADVERTISED_INTERFACE_TYPE` | 媒体 | `PortsOrch` |
| `SAI_PORT_ATTR_MEDIA_TYPE` / `ADVERTISED_MEDIA_TYPE` | 媒体タイプ | `PortsOrch` |
| `SAI_PORT_ATTR_INTERNAL_LOOPBACK_MODE` | ループバック | `PortsOrch` |
| `SAI_PORT_ATTR_LINK_TRAINING_ENABLE` / `LINK_TRAINING_FAILURE_STATUS` | LT | `PortsOrch` |
| `SAI_PORT_ATTR_HOST_TX_READY_STATUS` / `HOST_TX_SIGNAL_ENABLE` | host TX ready | `PortsOrch` (sfputil 連携) |
| `SAI_PORT_ATTR_PORT_VLAN_ID` | PVID | `VlanMgr` / `PortsOrch` |
| `SAI_PORT_ATTR_INGRESS_ACL` / `EGRESS_ACL` | ACL 表バインド | `AclOrch` |
| `SAI_PORT_ATTR_INGRESS_MIRROR_SESSION` / `EGRESS_MIRROR_SESSION` | mirror バインド | `MirrorOrch` |
| `SAI_PORT_ATTR_INGRESS_SAMPLEPACKET_ENABLE` / `EGRESS_SAMPLEPACKET_ENABLE` | sFlow | `SflowOrch` |
| `SAI_PORT_ATTR_INGRESS_MACSEC_ACL` / `EGRESS_MACSEC_ACL` | [MACsec](../reference/glossary.md#term-macsec) ACL | `MACsecOrch` |
| `SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID` / `MULTICAST_STORM_CONTROL_POLICER_ID` / `FLOOD_STORM_CONTROL_POLICER_ID` | storm control | `PfcWdOrch` 等 |
| `SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP` / `DSCP_TO_TC_MAP` / `TC_TO_QUEUE_MAP` | [QoS](../reference/glossary.md#term-qos) マップ | `QosOrch` |
| `SAI_PORT_ATTR_QOS_INGRESS_BUFFER_PROFILE_LIST` / `EGRESS_BUFFER_PROFILE_LIST` | バッファ | `BufferOrch` |
| `SAI_PORT_ATTR_QOS_MAXIMUM_HEADROOM_SIZE` | headroom 上限 | `BufferOrch` |
| `SAI_PORT_ATTR_PRIORITY_FLOW_CONTROL` / `_MODE` / `_RX` / `_TX` | [PFC](../reference/glossary.md#term-pfc) | `PfcWdOrch`, `QosOrch` |
| `SAI_PORT_ATTR_GLOBAL_FLOW_CONTROL_FORWARD` / `PRIORITY_FLOW_CONTROL_FORWARD` | FC 転送可否 | `PortsOrch` |
| `SAI_PORT_ATTR_INGRESS_PRIORITY_GROUP_LIST` / `NUMBER_OF_INGRESS_PRIORITY_GROUPS` | PG | `BufferOrch` |
| `SAI_PORT_ATTR_PORT_SERDES_ID` | SerDes attribute object | `PortsOrch` |
| `SAI_PORT_ATTR_ISOLATION_GROUP` | private [VLAN](../reference/glossary.md#term-vlan) 分離 | `IsoGrpOrch` |
| `SAI_PORT_ATTR_FABRIC_ATTACHED` / `FABRIC_ATTACHED_PORT_INDEX` / `FABRIC_ATTACHED_SWITCH_ID` / `FABRIC_ISOLATE` | [VOQ](../reference/glossary.md#term-voq) fabric | `FabricPortsOrch` |
| `SAI_PORT_ATTR_PATH_TRACING_INTF` / `PATH_TRACING_TIMESTAMP_TYPE` | Path tracing | `PortsOrch` |
| `SAI_PORT_ATTR_IPG` | inter-packet gap | `PortsOrch` |
| 関連: [Port 設計](../topics/14-platform-port-optics/architecture.md), [QoS/Buffer](../topics/08-qos-buffer/architecture.md) | | |

## VLAN (`sai_vlan_api`)

| 属性 | 用途 | 関連 orch / DB |
|------|------|----------------|
| `SAI_VLAN_ATTR_VLAN_ID` | VID | `VlanMgr` (`VLAN\|Vlan<N>`) |
| `SAI_VLAN_ATTR_MEMBER_LIST` | VLAN メンバ | `VlanMgr` (`VLAN_MEMBER`) |
| `SAI_VLAN_ATTR_STP_INSTANCE` | STP インスタンス | `StpOrch` |
| `SAI_VLAN_ATTR_INGRESS_ACL` / `EGRESS_ACL` | VLAN にバインドする ACL | `AclOrch` |
| `SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_CONTROL_TYPE` / `_FLOOD_GROUP` | 未知 UC フラッディング | `VlanMgr` |
| `SAI_VLAN_ATTR_UNKNOWN_MULTICAST_FLOOD_CONTROL_TYPE` | 未知 MC | `VlanMgr` |
| `SAI_VLAN_ATTR_BROADCAST_FLOOD_CONTROL_TYPE` / `_FLOOD_GROUP` | BC | `VlanMgr` |
| 関連: [L2 VLAN/LAG](../topics/06-l2-vlan-lag/architecture.md) | | |

## LAG (`sai_lag_api`)

| 属性 | 用途 | 関連 orch / DB |
|------|------|----------------|
| `SAI_LAG_ATTR_PORT_VLAN_ID` | PVID | `PortsOrch` (LAG 側) |
| `SAI_LAG_ATTR_INGRESS_ACL` / `EGRESS_ACL` | LAG ACL バインド | `AclOrch` |
| `SAI_LAG_ATTR_TPID` | LAG TPID | `PortsOrch` |
| `SAI_LAG_ATTR_SYSTEM_PORT_AGGREGATE_ID` | VOQ system LAG | `PortsOrch` (chassis) |
| 関連: [LAG / teamd](../topics/06-l2-vlan-lag/architecture.md) | | |

## BRIDGE_PORT (`sai_bridge_api`)

| 属性 | 用途 | 関連 orch |
|------|------|-----------|
| `SAI_BRIDGE_PORT_ATTR_TYPE` | PORT / SUB_PORT / TUNNEL | `PortsOrch`, `VxlanTunnelOrch` |
| `SAI_BRIDGE_PORT_ATTR_PORT_ID` | underlying port | `PortsOrch` |
| `SAI_BRIDGE_PORT_ATTR_BRIDGE_ID` | 所属ブリッジ | `PortsOrch` |
| `SAI_BRIDGE_PORT_ATTR_ADMIN_STATE` | bridge port up/down | `PortsOrch` |
| `SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE` | learning モード | `PortsOrch` (`PORT\|learn_mode`) |
| `SAI_BRIDGE_PORT_ATTR_TUNNEL_ID` | [VXLAN](../reference/glossary.md#term-vxlan) tunnel BP | `VxlanTunnelOrch` |
| `SAI_BRIDGE_PORT_ATTR_ISOLATION_GROUP` | private VLAN | `IsoGrpOrch` |

## BFD_SESSION (`sai_bfd_api`)

| 属性 | 用途 | 関連 orch / DB |
|------|------|----------------|
| `SAI_BFD_SESSION_ATTR_TYPE` | ASYNC_ACTIVE 等 | `BfdOrch` (`BFD_SESSION_TABLE`) |
| `SAI_BFD_SESSION_ATTR_LOCAL_DISCRIMINATOR` / `REMOTE_DISCRIMINATOR` | discriminator | `BfdOrch` |
| `SAI_BFD_SESSION_ATTR_MIN_TX` / `MIN_RX` / `MULTIPLIER` | タイマ | `BfdOrch` |
| `SAI_BFD_SESSION_ATTR_SRC_IP_ADDRESS` / `DST_IP_ADDRESS` | session 端点 | `BfdOrch` |
| `SAI_BFD_SESSION_ATTR_SRC_MAC_ADDRESS` / `DST_MAC_ADDRESS` | L2 ヘッダ | `BfdOrch` |
| `SAI_BFD_SESSION_ATTR_PORT` | tx 出力ポート | `BfdOrch` |
| `SAI_BFD_SESSION_ATTR_VIRTUAL_ROUTER` | 所属 [VRF](../reference/glossary.md#term-vrf) | `BfdOrch` |
| `SAI_BFD_SESSION_ATTR_BFD_ENCAPSULATION_TYPE` | encap (none / IP-in-IP) | `BfdOrch` |
| `SAI_BFD_SESSION_ATTR_IPHDR_VERSION` | v4 / v6 | `BfdOrch` |
| `SAI_BFD_SESSION_ATTR_UDP_SRC_PORT` | UDP src | `BfdOrch` |
| `SAI_BFD_SESSION_ATTR_HW_LOOKUP_VALID` | HW lookup 有効 | `BfdOrch` |
| `SAI_BFD_SESSION_ATTR_MULTIHOP` | mhop BFD | `BfdOrch` |
| `SAI_BFD_SESSION_ATTR_TOS` | [DSCP](../reference/glossary.md#term-dscp)/TOS | `BfdOrch` |
| 関連: [BFD HW offload](../routing/bfd-hw-offload.md) | | |

## ICMP_ECHO_SESSION (`sai_icmp_echo_api`)

| 属性 | 用途 | 関連 orch |
|------|------|-----------|
| `SAI_ICMP_ECHO_SESSION_ATTR_GUID` / `COOKIE` | session 識別子 | `IcmpOrch` |
| `SAI_ICMP_ECHO_SESSION_ATTR_SRC_IP_ADDRESS` / `DST_IP_ADDRESS` | 端点 | `IcmpOrch` |
| `SAI_ICMP_ECHO_SESSION_ATTR_SRC_MAC_ADDRESS` / `DST_MAC_ADDRESS` | L2 | `IcmpOrch` |
| `SAI_ICMP_ECHO_SESSION_ATTR_TX_INTERVAL` / `RX_INTERVAL` | timer | `IcmpOrch` |
| `SAI_ICMP_ECHO_SESSION_ATTR_PORT` / `VIRTUAL_ROUTER` | 出力面 | `IcmpOrch` |
| `SAI_ICMP_ECHO_SESSION_ATTR_HW_LOOKUP_VALID` | HW lookup | `IcmpOrch` |
| `SAI_ICMP_ECHO_SESSION_ATTR_IPHDR_VERSION` / `TOS` / `TTL` | IP ヘッダ | `IcmpOrch` |
| `SAI_ICMP_ECHO_SESSION_ATTR_STATS_COUNT_MODE` / `SELECTIVE_COUNTER_LIST` | 統計 | `IcmpOrch` |

## ACL_TABLE / ACL_ENTRY / ACL_COUNTER (`sai_acl_api`)

| 属性 | 用途 | 関連 orch / DB |
|------|------|----------------|
| `SAI_ACL_TABLE_ATTR_ACL_STAGE` | INGRESS / EGRESS | `AclOrch` (`ACL_TABLE\|stage`) |
| `SAI_ACL_TABLE_ATTR_ACL_BIND_POINT_TYPE_LIST` | port / lag / vlan / switch | `AclOrch` (`bind_points`) |
| `SAI_ACL_TABLE_ATTR_ACL_ACTION_TYPE_LIST` | 許可アクション | `AclOrch` |
| `SAI_ACL_TABLE_ATTR_FIELD_*` (DST_IP / SRC_IP / DST_IPV6 / SRC_IPV6 / DST_MAC / SRC_MAC / ETHER_TYPE / IP_PROTOCOL / L4_SRC_PORT / L4_DST_PORT / TCP_FLAGS / DSCP / ECN / TTL / ICMP_TYPE / ICMP_CODE / ICMPV6_TYPE / ICMPV6_CODE / IN_PORT / OUT_PORT / ACL_RANGE_TYPE / ACL_IP_TYPE / ACL_IP_FRAG / GRE_KEY / TUNNEL_VNI / INNER_*) | マッチ可能フィールド | `AclOrch` (`match` 列) |
| `SAI_ACL_TABLE_ATTR_AVAILABLE_ACL_ENTRY` / `AVAILABLE_ACL_COUNTER` | エントリ残 | `CrmOrch` |
| `SAI_ACL_ENTRY_ATTR_TABLE_ID` | 所属テーブル | `AclOrch` |
| `SAI_ACL_ENTRY_ATTR_PRIORITY` | エントリ優先度 | `AclOrch` (`priority`) |
| `SAI_ACL_ENTRY_ATTR_ADMIN_STATE` | enable/disable | `AclOrch` |
| `SAI_ACL_ENTRY_ATTR_FIELD_*` | 個別ルールのマッチ値 | `AclOrch` |
| `SAI_ACL_ENTRY_ATTR_ACTION_PACKET_ACTION` | FORWARD / DROP / TRAP / COPY | `AclOrch` (`PACKET_ACTION`) |
| `SAI_ACL_ENTRY_ATTR_ACTION_REDIRECT` / `REDIRECT_LIST` | redirect 先 | `AclOrch` |
| `SAI_ACL_ENTRY_ATTR_ACTION_COUNTER` | counter バインド | `AclOrch` |
| `SAI_ACL_ENTRY_ATTR_ACTION_MIRROR_INGRESS` / `MIRROR_EGRESS` | mirror | `AclOrch` + `MirrorOrch` |
| `SAI_ACL_ENTRY_ATTR_ACTION_SET_DSCP` / `SET_ECN` / `SET_TC` | rewrite | `AclOrch` |
| `SAI_ACL_ENTRY_ATTR_ACTION_DECREMENT_TTL` / `NO_NAT` | misc | `AclOrch` |
| `SAI_ACL_ENTRY_ATTR_ACTION_DTEL_*` | DTel | `DTelOrch` |
| `SAI_ACL_ENTRY_ATTR_ACTION_MACSEC_FLOW` | MACsec flow バインド | `MACsecOrch` |
| `SAI_ACL_COUNTER_ATTR_TABLE_ID` | 所属テーブル | `AclOrch` |
| `SAI_ACL_COUNTER_ATTR_ENABLE_PACKET_COUNT` / `ENABLE_BYTE_COUNT` | カウント有効化 | `AclOrch` |
| `SAI_ACL_COUNTER_ATTR_PACKETS` / `BYTES` | カウンタ値 | `FlexCounterOrch` |
| 関連: [ACL/CoPP/Mirror](../topics/07-acl-copp-mirror/architecture.md) | | |

## MIRROR_SESSION (`sai_mirror_api`)

| 属性 | 用途 | 関連 orch |
|------|------|-----------|
| `SAI_MIRROR_SESSION_ATTR_TYPE` | LOCAL / REMOTE / ENHANCED_REMOTE | `MirrorOrch` |
| `SAI_MIRROR_SESSION_ATTR_MONITOR_PORT` | 監視出力ポート | `MirrorOrch` |
| `SAI_MIRROR_SESSION_ATTR_SRC_IP_ADDRESS` / `DST_IP_ADDRESS` | ERSPAN 端点 | `MirrorOrch` |
| `SAI_MIRROR_SESSION_ATTR_SRC_MAC_ADDRESS` / `DST_MAC_ADDRESS` | ERSPAN L2 | `MirrorOrch` |
| `SAI_MIRROR_SESSION_ATTR_GRE_PROTOCOL_TYPE` / `ERSPAN_ENCAPSULATION_TYPE` | encap | `MirrorOrch` |
| `SAI_MIRROR_SESSION_ATTR_IPHDR_VERSION` / `TOS` / `TTL` | IP ヘッダ | `MirrorOrch` |
| `SAI_MIRROR_SESSION_ATTR_VLAN_HEADER_VALID` / `VLAN_TPID` / `VLAN_ID` / `VLAN_PRI` / `VLAN_CFI` | VLAN タグ | `MirrorOrch` |
| `SAI_MIRROR_SESSION_ATTR_POLICER` / `TC` | mirror traffic 制御 | `MirrorOrch` |

## BUFFER_POOL / BUFFER_PROFILE (`sai_buffer_api`)

| 属性 | 用途 | 関連 orch / DB |
|------|------|----------------|
| `SAI_BUFFER_POOL_ATTR_TYPE` | INGRESS / EGRESS | `BufferOrch` (`BUFFER_POOL`) |
| `SAI_BUFFER_POOL_ATTR_SIZE` | プール容量 | `BufferOrch` |
| `SAI_BUFFER_POOL_ATTR_THRESHOLD_MODE` | static / dynamic | `BufferOrch` |
| `SAI_BUFFER_POOL_ATTR_XOFF_SIZE` | 共有 headroom | `BufferOrch` |
| `SAI_BUFFER_PROFILE_ATTR_POOL_ID` | 紐づくプール | `BufferOrch` (`BUFFER_PROFILE\|pool`) |
| `SAI_BUFFER_PROFILE_ATTR_BUFFER_SIZE` | 保証量 | `BufferOrch` (`size`) |
| `SAI_BUFFER_PROFILE_ATTR_THRESHOLD_MODE` | dyn/static | `BufferOrch` |
| `SAI_BUFFER_PROFILE_ATTR_SHARED_DYNAMIC_TH` / `SHARED_STATIC_TH` | 共有閾値 | `BufferOrch` (`dynamic_th` / `static_th`) |
| `SAI_BUFFER_PROFILE_ATTR_XOFF_TH` / `XON_TH` / `XON_OFFSET_TH` | PFC 閾値 | `BufferOrch` |
| `SAI_BUFFER_PROFILE_ATTR_PACKET_ADMISSION_FAIL_ACTION` | drop 動作 | `BufferOrch` |
| 関連: [QoS/Buffer](../topics/08-qos-buffer/architecture.md) | | |

## QUEUE / SCHEDULER / WRED (`sai_queue_api`, `sai_scheduler_api`, `sai_wred_api`)

| 属性 | 用途 | 関連 orch |
|------|------|-----------|
| `SAI_QUEUE_ATTR_TYPE` | UC / MC / ALL | `QosOrch` |
| `SAI_QUEUE_ATTR_INDEX` | キュー番号 | `QosOrch` |
| `SAI_QUEUE_ATTR_BUFFER_PROFILE_ID` | キュー bufprof | `BufferOrch` |
| `SAI_QUEUE_ATTR_WRED_PROFILE_ID` | [WRED](../reference/glossary.md#term-wred) バインド | `QosOrch` |
| `SAI_QUEUE_ATTR_PAUSE_STATUS` | PFC pause 状態 (RO) | `PfcWdOrch` |
| `SAI_QUEUE_ATTR_PFC_DLR_INIT` | DLR トリガ | `PfcWdOrch` |
| `SAI_SCHEDULER_ATTR_SCHEDULING_TYPE` | SP / WRR / [DWRR](../reference/glossary.md#term-dwrr) | `QosOrch` (`SCHEDULER\|type`) |
| `SAI_SCHEDULER_ATTR_SCHEDULING_WEIGHT` | weight | `QosOrch` (`weight`) |
| `SAI_SCHEDULER_ATTR_METER_TYPE` | bytes / packets | `QosOrch` |
| `SAI_SCHEDULER_ATTR_MIN_BANDWIDTH_RATE` / `MIN_BANDWIDTH_BURST_RATE` | min shaper | `QosOrch` |
| `SAI_SCHEDULER_ATTR_MAX_BANDWIDTH_RATE` / `MAX_BANDWIDTH_BURST_RATE` | max shaper | `QosOrch` |
| `SAI_WRED_ATTR_GREEN_ENABLE` / `YELLOW_ENABLE` / `RED_ENABLE` | 色別 enable | `QosOrch` (`WRED_PROFILE`) |
| `SAI_WRED_ATTR_*_MIN_THRESHOLD` / `*_MAX_THRESHOLD` / `*_DROP_PROBABILITY` | 各色しきい値 | `QosOrch` |
| `SAI_WRED_ATTR_WEIGHT` | EWMA weight | `QosOrch` |
| `SAI_WRED_ATTR_ECN_MARK_MODE` | ECN マーキング | `QosOrch` (`ecn`) |

## HOSTIF / HOSTIF_TRAP (`sai_hostif_api`)

| 属性 | 用途 | 関連 orch |
|------|------|-----------|
| `SAI_HOSTIF_ATTR_TYPE` | NETDEV / FD / GENETLINK | `HostIntfMgr` |
| `SAI_HOSTIF_ATTR_OBJ_ID` | 対応する port / [RIF](../reference/glossary.md#term-rif) | `HostIntfMgr` |
| `SAI_HOSTIF_ATTR_NAME` | netdev 名 (Ethernet0 等) | `HostIntfMgr` |
| `SAI_HOSTIF_ATTR_OPER_STATUS` | netdev 状態 | `PortsOrch` |
| `SAI_HOSTIF_ATTR_VLAN_TAG` | tag / strip / keep | `HostIntfMgr` |
| `SAI_HOSTIF_ATTR_QUEUE` | hostif 受信キュー | `HostIntfMgr` |
| `SAI_HOSTIF_ATTR_GENETLINK_MCGRP_NAME` | genetlink グループ | `HostIntfMgr` (sFlow / psample) |
| `SAI_HOSTIF_TRAP_ATTR_TRAP_TYPE` | [BGP](../reference/glossary.md#term-bgp) / [LACP](../reference/glossary.md#term-lacp) / [ARP](../reference/glossary.md#term-arp) / [LLDP](../reference/glossary.md#term-lldp) 等 | `CoppOrch` (`COPP_TRAP`) |
| `SAI_HOSTIF_TRAP_ATTR_PACKET_ACTION` | TRAP / COPY / DROP | `CoppOrch` |
| `SAI_HOSTIF_TRAP_ATTR_TRAP_PRIORITY` | trap 優先度 | `CoppOrch` |
| `SAI_HOSTIF_TRAP_ATTR_TRAP_GROUP` | 所属 trap group (policer 共有) | `CoppOrch` |
| `SAI_HOSTIF_TRAP_ATTR_COUNTER_ID` | counter バインド | `CoppOrch` |
| 関連: [CoPP/ACL/Mirror](../topics/07-acl-copp-mirror/architecture.md) | | |

## TUNNEL (`sai_tunnel_api`)

| 属性 | 用途 | 関連 orch |
|------|------|-----------|
| `SAI_TUNNEL_ATTR_TYPE` | VXLAN / IPINIP / [MPLS](../reference/glossary.md#term-mpls) / SRV6 | `VxlanTunnelOrch`, `TunnelDecapOrch` |
| `SAI_TUNNEL_ATTR_UNDERLAY_INTERFACE` / `OVERLAY_INTERFACE` | RIF | `VxlanTunnelOrch` |
| `SAI_TUNNEL_ATTR_ENCAP_SRC_IP` / `ENCAP_DST_IP` | encap 端点 | `VxlanTunnelOrch` |
| `SAI_TUNNEL_ATTR_ENCAP_TTL_MODE` / `ENCAP_TTL_VAL` | TTL | `VxlanTunnelOrch` |
| `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` | uniform / pipe | `TunnelDecapOrch` |
| `SAI_TUNNEL_ATTR_ENCAP_DSCP_MODE` / `DECAP_DSCP_MODE` | DSCP モード | tunnel orch |
| `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` / `DECAP_ECN_MODE` | ECN | tunnel orch |
| `SAI_TUNNEL_ATTR_ENCAP_MAPPERS` / `DECAP_MAPPERS` | TC/DSCP map list | `QosOrch` 連携 |
| `SAI_TUNNEL_ATTR_ENCAP_QOS_TC_TO_QUEUE_MAP` / `TC_AND_COLOR_TO_DSCP_MAP` | encap QoS | `QosOrch` |
| `SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP` / `TC_TO_PRIORITY_GROUP_MAP` | decap QoS | `QosOrch` |
| `SAI_TUNNEL_ATTR_PEER_MODE` | P2P / P2MP | `VxlanTunnelOrch` |
| `SAI_TUNNEL_ATTR_LOOPBACK_PACKET_ACTION` | loopback ロジック | `TunnelDecapOrch` |
| 関連: [VXLAN/EVPN](../topics/03-vxlan-evpn/architecture.md) | | |

## ROUTER_INTERFACE (`sai_router_interface_api`)

| 属性 | 用途 | 関連 orch |
|------|------|-----------|
| `SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID` | 所属 VRF | `IntfsOrch` |
| `SAI_ROUTER_INTERFACE_ATTR_TYPE` | PORT / VLAN / SUB_PORT / LOOPBACK | `IntfsOrch` |
| `SAI_ROUTER_INTERFACE_ATTR_PORT_ID` / `VLAN_ID` | underlying | `IntfsOrch` |
| `SAI_ROUTER_INTERFACE_ATTR_SRC_MAC_ADDRESS` / `MY_MAC` | RIF MAC | `IntfsOrch` |
| `SAI_ROUTER_INTERFACE_ATTR_MTU` | L3 MTU | `IntfsOrch` (`INTERFACE\|mtu`) |
| `SAI_ROUTER_INTERFACE_ATTR_ADMIN_V4_STATE` / `ADMIN_V6_STATE` / `ADMIN_MPLS_STATE` | プロトコル個別 admin | `IntfsOrch` |
| `SAI_ROUTER_INTERFACE_ATTR_V4_MCAST_ENABLE` / `V6_MCAST_ENABLE` | MC RIF | `IntfsOrch` |
| `SAI_ROUTER_INTERFACE_ATTR_NAT_ZONE_ID` | [NAT](../reference/glossary.md#term-nat) zone | `NatOrch` |
| `SAI_ROUTER_INTERFACE_ATTR_LOOPBACK_PACKET_ACTION` | self-loop drop | `IntfsOrch` |
| `SAI_ROUTER_INTERFACE_ATTR_OUTER_VLAN_ID` | sub-port VID | `IntfsOrch` |

## VIRTUAL_ROUTER (`sai_virtual_router_api`)

| 属性 | 用途 | 関連 orch |
|------|------|-----------|
| `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE` / `ADMIN_V6_STATE` | VR 単位の admin | `VRFOrch` |
| `SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS` | VR MAC | `VRFOrch` |
| `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION` | TTL=1 動作 | `VRFOrch` |
| `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION` | IP options 動作 | `VRFOrch` |
| `SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION` | 未知 MC | `VRFOrch` |
| 関連: [VRF/ECMP](../topics/04-vrf-ecmp/architecture.md) | | |

## ROUTE / NEIGHBOR / NEXT_HOP / NEXT_HOP_GROUP (`sai_route_api`, `sai_neighbor_api`, `sai_next_hop_api`, `sai_next_hop_group_api`)

| 属性 | 用途 | 関連 orch |
|------|------|-----------|
| `SAI_ROUTE_ENTRY_ATTR_PACKET_ACTION` | FORWARD / DROP / TRAP / NOACTION | `RouteOrch` |
| `SAI_ROUTE_ENTRY_ATTR_NEXT_HOP_ID` | NH / NHG / port | `RouteOrch` |
| `SAI_ROUTE_ENTRY_ATTR_COUNTER_ID` | flex counter | `FlexCounterOrch` |
| `SAI_ROUTE_ENTRY_ATTR_META_DATA` | route メタ (subnet 識別等) | `RouteOrch` |
| `SAI_ROUTE_ENTRY_ATTR_IP_ADDR_FAMILY` | v4 / v6 | `RouteOrch` |
| `SAI_ROUTE_ENTRY_ATTR_PREFIX_AGG_ID` | prefix 集約 ID | `RouteOrch` |
| `SAI_NEIGHBOR_ENTRY_ATTR_DST_MAC_ADDRESS` | neighbor MAC | `NeighOrch` |
| `SAI_NEIGHBOR_ENTRY_ATTR_NO_HOST_ROUTE` | host route 抑止 | `NeighOrch` |
| `SAI_NEIGHBOR_ENTRY_ATTR_ENCAP_INDEX` | overlay encap idx | `NeighOrch` ([EVPN](../reference/glossary.md#term-evpn)) |
| `SAI_NEIGHBOR_ENTRY_ATTR_IS_LOCAL` | local neighbor | `NeighOrch` |
| `SAI_NEXT_HOP_ATTR_TYPE` | IP / TUNNEL / MPLS / SRV6 | `NeighOrch` / `VxlanTunnelOrch` |
| `SAI_NEXT_HOP_ATTR_IP` / `ROUTER_INTERFACE_ID` | 基本 NH | `NeighOrch` |
| `SAI_NEXT_HOP_ATTR_TUNNEL_ID` / `TUNNEL_VNI` / `TUNNEL_MAC` | overlay NH | `VxlanTunnelOrch` |
| `SAI_NEXT_HOP_ATTR_LABELSTACK` / `OUTSEG_TYPE` | MPLS PUSH | `MplsOrch` |
| `SAI_NEXT_HOP_ATTR_SRV6_SIDLIST_ID` | [SRv6](../reference/glossary.md#term-srv6) H.Encaps | `Srv6Orch` |
| `SAI_NEXT_HOP_ATTR_DISABLE_DECREMENT_TTL` / `DISABLE_*_REWRITE` | rewrite 抑止 | `NeighOrch` |
| `SAI_NEXT_HOP_GROUP_ATTR_TYPE` | ECMP / FINE_GRAIN_ECMP / PROTECTION | `NhgOrch` |
| `SAI_NEXT_HOP_GROUP_ATTR_NEXT_HOP_LIST` | メンバ NH | `NhgOrch` |
| `SAI_NEXT_HOP_GROUP_ATTR_NEXT_HOP_MEMBER_WEIGHT_LIST` | weighted ECMP | `NhgOrch` |
| `SAI_NEXT_HOP_GROUP_ATTR_CONFIGURED_SIZE` / `REAL_SIZE` | bucket size | `NhgOrch` |
| `SAI_NEXT_HOP_GROUP_ATTR_SELECTION_MAP` | hash → bucket map | `NhgOrch` (FG-ECMP) |
| 関連: [VRF/ECMP](../topics/04-vrf-ecmp/architecture.md), [BGP](../topics/02-bgp/architecture.md) | | |

## FDB / POLICER / SAMPLEPACKET / SRV6 / COUNTER / MACSEC

| 属性 | 用途 | 関連 orch |
|------|------|-----------|
| `SAI_FDB_ENTRY_ATTR_TYPE` | STATIC / DYNAMIC | `FdbOrch` (`FDB\|`) |
| `SAI_FDB_ENTRY_ATTR_BRIDGE_PORT_ID` | 学習先 BP | `FdbOrch` |
| `SAI_FDB_ENTRY_ATTR_PACKET_ACTION` | FWD / DROP / TRAP | `FdbOrch` |
| `SAI_FDB_ENTRY_ATTR_ALLOW_MAC_MOVE` | MAC move 許可 | `FdbOrch` |
| `SAI_FDB_ENTRY_ATTR_ENDPOINT_IP` | EVPN remote [VTEP](../reference/glossary.md#term-vtep) | `FdbOrch` (EVPN) |
| `SAI_POLICER_ATTR_METER_TYPE` | BYTES / PACKETS | `CoppOrch`, `PolicerOrch` |
| `SAI_POLICER_ATTR_MODE` | Sr_TCM / Tr_TCM / STORM | policer |
| `SAI_POLICER_ATTR_COLOR_SOURCE` | BLIND / AWARE | policer |
| `SAI_POLICER_ATTR_CIR` / `CBS` / `PIR` / `PBS` | レート | policer |
| `SAI_POLICER_ATTR_GREEN_PACKET_ACTION` / `YELLOW_PACKET_ACTION` / `RED_PACKET_ACTION` | color 別動作 | policer |
| `SAI_SAMPLEPACKET_ATTR_SAMPLE_RATE` | sFlow rate | `SflowOrch` |
| `SAI_SRV6_SIDLIST_ATTR_TYPE` / `SEGMENT_LIST` | SID リスト | `Srv6Orch` |
| `SAI_COUNTER_ATTR_TYPE` | 汎用 counter type | `FlexCounterOrch` |
| `SAI_MACSEC_PORT_ATTR_PORT_ID` / `MACSEC_DIRECTION` | MACsec ポート | `MACsecOrch` |
| `SAI_MACSEC_SC_ATTR_FLOW_ID` / `MACSEC_SCI` / `MACSEC_CIPHER_SUITE` / `ENCRYPTION_ENABLE` / `MACSEC_XPN64_ENABLE` / `MACSEC_EXPLICIT_SCI_ENABLE` / `MACSEC_DIRECTION` | SC | `MACsecOrch` |
| `SAI_MACSEC_SA_ATTR_SC_ID` / `AN` / `SAK` / `AUTH_KEY` / `SALT` / `MACSEC_SSCI` / `CURRENT_XPN` / `CONFIGURED_EGRESS_XPN` / `MINIMUM_INGRESS_XPN` / `MACSEC_DIRECTION` | SA | `MACsecOrch` |

## 使い方

- syncd の `SAI_REDIS` ログや `saidump` 出力中の `SAI_*_ATTR_*` を本表で検索すれば、
  どの orch が書いた・どの CONFIG_DB に対応するかを当てやすい。
- [ASIC_DB](../reference/glossary.md#term-asic_db) (`COUNTERS_DB` 上の [Redis](../reference/glossary.md#term-redis)) を `redis-cli -n 1 HGETALL ASIC_STATE:SAI_OBJECT_TYPE_PORT:oid:0x...`
  すると、ここに並ぶ属性キーがそのまま値として現れる。
- 完全な仕様（取得可否・型・デフォルト値・mandatory flag）は SAI ヘッダの doxygen コメントに記載。
  本表は「実装で実際に触られているかどうか」を補完するもの。

## 引用元

- [sonic-net/sonic-sairedis](https://github.com/sonic-net/sonic-sairedis/tree/88bc51ae95df66977601957515e5527119ffd4c5) @ `88bc51ae95df66977601957515e5527119ffd4c5` (SAI submodule pin)
- [sonic-net/sonic-swss `orchagent/`](https://github.com/sonic-net/sonic-swss/tree/master/orchagent) — `SAI_*_ATTR_*` の全件 grep より抽出
- SAI ヘッダ本体: [sonic-net/SAI](https://github.com/sonic-net/SAI) の `inc/sai*.h`

<!-- glossary-links-injected: 86b69c729fae -->
