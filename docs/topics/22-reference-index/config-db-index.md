---
title: CONFIG_DB 横断索引
description: CONFIG_DB 横断索引 — docs/reference/config-db/ 配下の 293 ページを、機能章ごとに
  table family で並べ直した索引である。
area: topics
verification: meta
last_verified: 2026-05-10
related:
  cli:
  - config vrf
  config_db:
  - CRM
  - VRF
  - DEVICE_METADATA
  - FEATURE
  - SYSTEM_DEFAULTS
  - FLEX_COUNTER_TABLE
  - AUTO_TECHSUPPORT
  yang:
  - sonic-crm
  - sonic-vrf
---

# CONFIG_DB 横断索引

`docs/reference/config-db/` 配下の 293 ページを、機能章ごとに table family で並べ直した索引である。[CONFIG_DB](../../reference/glossary.md#term-config_db) は [SONiC](../../reference/glossary.md#term-sonic) の構成入力点であり、CLI / [YANG](../../reference/glossary.md#term-yang) / `config_db.json` の三者を裏で同一のスキーマでつないでいる。table 名から章を逆引きする場合も本ページを使う。

## 機能章別 table family

### 01 SONiC 全体像と設定基盤

- [DEVICE_METADATA](../../reference/config-db/device-metadata.md)
- [FEATURE](../../reference/config-db/feature.md)
- [SYSTEM_DEFAULTS](../../reference/config-db/system-defaults.md)
- [FLEX_COUNTER_TABLE](../../reference/config-db/flex-counter-table.md)
- [AUTO_TECHSUPPORT](../../reference/config-db/auto-techsupport.md)
- [KDUMP](../../reference/config-db/kdump.md)

### 02 BGP と FRR 制御プレーン

- [BGP_GLOBALS](../../reference/config-db/bgp-globals.md) / [BGP_GLOBALS_AF](../../reference/config-db/bgp-globals-af.md)
- [BGP_DEVICE_GLOBAL](../../reference/config-db/bgp-device-global.md)
- [BGP_NEIGHBOR](../../reference/config-db/bgp-neighbor.md) / [BGP_NEIGHBOR_AF](../../reference/config-db/bgp-neighbor-af.md)
- [BGP_PEER_GROUP](../../reference/config-db/bgp-peer-group.md) / [BGP_PEER_GROUP_AF](../../reference/config-db/bgp-peer-group-af.md)
- [BGP_AGGREGATE_ADDRESS](../../reference/config-db/bgp-aggregate-address.md)
- [PREFIX_LIST](../../reference/config-db/prefix-list.md) / [PREFIX_SET](../../reference/config-db/prefix-set.md)
- [AS_PATH_SET](../../reference/config-db/as-path-set.md) / [COMMUNITY_SET](../../reference/config-db/community-set.md)
- [ROUTE_MAP](../../reference/config-db/route-map.md)

入口: [02-bgp/setup.md](../02-bgp/setup.md)。

### 03 VXLAN / EVPN / VNET オーバーレイ

- [VXLAN_TUNNEL](../../reference/config-db/vxlan-tunnel.md) / [VXLAN_TUNNEL_MAP](../../reference/config-db/vxlan-tunnel-map.md)
- [VNET](../../reference/config-db/vnet.md)
- [TUNNEL](../../reference/config-db/tunnel.md) / [TUNNEL_DECAP_TABLE](../../reference/config-db/tunnel-decap-table.md)

入口: [03-vxlan-evpn/setup.md](../03-vxlan-evpn/setup.md)。

### 04 VRF / ECMP / RIB-FIB

- [VRF](../../reference/config-db/vrf.md)
- [STATIC_ROUTE](../../reference/config-db/static-route.md)
- [FG_NHG](../../reference/config-db/fg-nhg.md)
- [INTERFACE](../../reference/config-db/interface.md) / [LOOPBACK_INTERFACE](../../reference/config-db/loopback-interface.md)

入口: [04-vrf-ecmp/setup.md](../04-vrf-ecmp/setup.md)。

### 05 Dual-ToR と Mux 制御

- [MUX_CABLE](../../reference/config-db/mux-cable.md)
- [PEER_SWITCH](../../reference/config-db/peer-switch.md)

入口: [05-dual-tor/setup.md](../05-dual-tor/setup.md)。

### 06 L2 / VLAN / LAG / MC-LAG

- [VLAN](../../reference/config-db/vlan.md) / [VLAN_MEMBER](../../reference/config-db/vlan-member.md) / [VLAN_INTERFACE](../../reference/config-db/vlan-interface.md)
- [VLAN_SUB_INTERFACE](../../reference/config-db/vlan-sub-interface.md)
- [PORT](../../reference/config-db/port.md)
- [PORTCHANNEL](../../reference/config-db/portchannel.md) / [PORTCHANNEL_MEMBER](../../reference/config-db/portchannel-member.md) / [PORTCHANNEL_INTERFACE](../../reference/config-db/portchannel-interface.md)
- [DEVICE_NEIGHBOR](../../reference/config-db/device-neighbor.md) / [DEVICE_NEIGHBOR_METADATA](../../reference/config-db/device-neighbor-metadata.md)

入口: [06-l2-vlan-lag/setup.md](../06-l2-vlan-lag/setup.md)。

### 07 ACL / CoPP / Mirror

- [ACL_TABLE](../../reference/config-db/acl-table.md) / [ACL_RULE](../../reference/config-db/acl-rule.md)
- [POLICER](../../reference/config-db/policer.md)
- [MIRROR_SESSION](../../reference/config-db/mirror-session.md)
- [COPP_GROUP](../../reference/config-db/copp-group.md) / [COPP_TRAP](../../reference/config-db/copp-trap.md)
- [PBH](../../reference/config-db/pbh.md)
- [DEBUG_COUNTER](../../reference/config-db/debug-counter.md)
- [CRM](../../reference/config-db/crm.md)

入口: [07-acl-copp-mirror/setup.md](../07-acl-copp-mirror/setup.md)。

### 08 QoS / Buffer / PFC / Watermark (未実装章)

- [BUFFER_POOL](../../reference/config-db/buffer-pool.md) / [BUFFER_PROFILE](../../reference/config-db/buffer-profile.md)
- [BUFFER_PG](../../reference/config-db/buffer-pg.md) / [BUFFER_QUEUE](../../reference/config-db/buffer-queue.md)
- [QUEUE](../../reference/config-db/queue.md) / [SCHEDULER](../../reference/config-db/scheduler.md) / [WRED_PROFILE](../../reference/config-db/wred-profile.md)
- [DSCP_TO_TC_MAP](../../reference/config-db/dscp-to-tc-map.md) / [TC_TO_QUEUE_MAP](../../reference/config-db/tc-to-queue-map.md) / [PORT_QOS_MAP](../../reference/config-db/port-qos-map.md)
- [PFC_PRIORITY_TO_PRIORITY_GROUP_MAP](../../reference/config-db/pfc-priority-to-priority-group-map.md) / [PFC_WD](../../reference/config-db/pfc-wd.md)

### 09 Telemetry / SNMP / Observability (未実装章)

- [SFLOW](../../reference/config-db/sflow.md)
- [TELEMETRY](../../reference/config-db/telemetry.md)
- [SYSLOG_SERVER](../../reference/config-db/syslog-server.md)
- [CRM](../../reference/config-db/crm.md) (07 章と共有、運用視点で再参照)

### 12 Multi-ASIC / Chassis (未実装章)

- [KUBERNETES_MASTER](../../reference/config-db/kubernetes-master.md)

### 15 Security / AAA / FIPS (未実装章)

- [TACPLUS_SERVER](../../reference/config-db/tacplus-server.md)
- [LDAP_SERVER](../../reference/config-db/ldap-server.md)
- [MGMT_INTERFACE](../../reference/config-db/mgmt-interface.md) / [MGMT_PORT](../../reference/config-db/mgmt-port.md) / [MGMT_VRF_CONFIG](../../reference/config-db/mgmt-vrf-config.md)

### 16 NAT / DHCP Relay / Time-DNS (未実装章)

- [NAT](../../reference/config-db/nat.md)
- [DHCP_SERVER_IPV4](../../reference/config-db/dhcp-server-ipv4.md) / [DHCPV4_RELAY](../../reference/config-db/dhcpv4-relay.md)
- [NTP_GLOBAL](../../reference/config-db/ntp-global.md) / [NTP_SERVER](../../reference/config-db/ntp-server.md)

## 辞書から章への逆引き

`docs/reference/config-db/index.md` には全 293 table の一覧が並ぶ。読者が table 名を知っているが章を知らない場合、本ページの上記節のなかで table 名を検索すれば章に到達できる。

## 主入口が複数章にまたがる table

| Table | 主入口 | 関連参照 |
|---|---|---|
| INTERFACE | 06 章 (port 設定) | 04 章 ([VRF](../../reference/glossary.md#term-vrf) binding) |
| VLAN_INTERFACE | 06 章 | 04 章 (VRF binding) |
| [CRM](../../reference/glossary.md#term-crm) | 07 章 | 09 章 (resource 監視) |
| FLEX_COUNTER_TABLE | 01 章 | 07 / 09 章 (counter 種別ごと) |
| KDUMP | 01 章 | 11 章 (reboot lifecycle) |

<!-- glossary-links-injected: 8ba32e5aa69d -->
