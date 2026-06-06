---
title: CONFIG_DB 横断索引
description: CONFIG_DB 横断索引 — docs/reference/config-db/ 配下の table 群を機能章ごとに並べ直し、章入口
  (setup.md) への逆引きを提供する索引である。
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

`docs/reference/config-db/` 配下の table reference ページを、機能章ごとに table family で並べ直した索引である。[CONFIG_DB](../../reference/glossary.md#term-config_db) は [SONiC](../../reference/glossary.md#term-sonic) の構成入力点であり、CLI / [YANG](../../reference/glossary.md#term-yang) / `config_db.json` の三者を裏で同一のスキーマでつないでいる。table 名から章を逆引きする場合も本ページを使う。本索引は主要 table のみを列挙する代表 view であり、`docs/reference/config-db/index.md` の全件一覧と併用する。

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

### 08 QoS / Buffer / PFC / Watermark

- [BUFFER_POOL](../../reference/config-db/buffer-pool.md) / [BUFFER_PROFILE](../../reference/config-db/buffer-profile.md)
- [BUFFER_PG](../../reference/config-db/buffer-pg.md) / [BUFFER_QUEUE](../../reference/config-db/buffer-queue.md)
- [QUEUE](../../reference/config-db/queue.md) / [SCHEDULER](../../reference/config-db/scheduler.md) / [WRED_PROFILE](../../reference/config-db/wred-profile.md)
- [DSCP_TO_TC_MAP](../../reference/config-db/dscp-to-tc-map.md) / [TC_TO_QUEUE_MAP](../../reference/config-db/tc-to-queue-map.md) / [PORT_QOS_MAP](../../reference/config-db/port-qos-map.md)
- [PFC_PRIORITY_TO_PRIORITY_GROUP_MAP](../../reference/config-db/pfc-priority-to-priority-group-map.md) / [PFC_WD](../../reference/config-db/pfc-wd.md)

入口: [08-qos-buffer/setup.md](../08-qos-buffer/setup.md)。

### 09 Telemetry / SNMP / Observability

- [SFLOW](../../reference/config-db/sflow.md) / [SFLOW_COLLECTOR](../../reference/config-db/sflow-collector.md) / [SFLOW_SESSION](../../reference/config-db/sflow-session.md)
- [TELEMETRY](../../reference/config-db/telemetry.md) / [TELEMETRY_CLIENT](../../reference/config-db/telemetry-client.md)
- [SNMP](../../reference/config-db/snmp.md) / [SNMP_AGENT_ADDRESS_CONFIG](../../reference/config-db/snmp-agent-address-config.md)
- [SYSLOG_SERVER](../../reference/config-db/syslog-server.md)
- [TAM](../../reference/config-db/tam.md)
- [CRM](../../reference/config-db/crm.md) (07 章と共有、運用視点で再参照)

入口: [09-telemetry-snmp/setup.md](../09-telemetry-snmp/setup.md)。

### 10 gNMI / OpenConfig / gNOI

- [GNMI](../../reference/config-db/gnmi.md) / [GNMI_SERVER](../../reference/config-db/gnmi-server.md) / [GNMI_DIALIN](../../reference/config-db/gnmi-dialin.md)

入口: [10-gnmi-openconfig/setup.md](../10-gnmi-openconfig/setup.md)。

### 11 Reboot / Warm-restart Lifecycle

- [WARM_RESTART](../../reference/config-db/warm-restart.md)
- [KDUMP](../../reference/config-db/kdump.md) (01 章と共有、reboot lifecycle 視点で再参照)

入口: [11-reboot/setup.md](../11-reboot/setup.md)。

### 12 Multi-ASIC / Chassis / VOQ

- [CHASSIS_MODULE](../../reference/config-db/chassis-module.md)
- [VOQ_INBAND_INTERFACE](../../reference/config-db/voq-inband-interface.md)
- [FABRIC_MONITOR](../../reference/config-db/fabric-monitor.md) / [FABRIC_PORT](../../reference/config-db/fabric-port.md)
- [KUBERNETES_MASTER](../../reference/config-db/kubernetes-master.md)

入口: [12-multi-asic-voq/setup.md](../12-multi-asic-voq/setup.md)。

### 13 DASH / SmartSwitch

- [DPU](../../reference/config-db/dpu.md) / [DPU_ENI](../../reference/config-db/dpu-eni.md)
- [SMART_SWITCH](../../reference/config-db/smart-switch.md) / [SMART_SWITCH_DPU](../../reference/config-db/smart-switch-dpu.md)
- [DASH_ENI](../../reference/config-db/dash-eni.md)

入口: [13-dash-smartswitch/setup.md](../13-dash-smartswitch/setup.md)。

### 14 Platform / Port / Optics

- [PORT](../../reference/config-db/port.md)
- [BREAKOUT_CFG](../../reference/config-db/breakout-cfg.md)
- [CABLE_LENGTH](../../reference/config-db/cable-length.md)
- [PORT_STORM_CONTROL](../../reference/config-db/port-storm-control.md)
- [CONSOLE_PORT](../../reference/config-db/console-port.md)

入口: [14-platform-port-optics/setup.md](../14-platform-port-optics/setup.md)。

### 15 Security / AAA / FIPS

- [AAA](../../reference/config-db/aaa.md)
- [TACPLUS_SERVER](../../reference/config-db/tacplus-server.md)
- [RADIUS](../../reference/config-db/radius.md) / [RADIUS_SERVER](../../reference/config-db/radius-server.md)
- [LDAP_SERVER](../../reference/config-db/ldap-server.md)
- [SSH_SERVER](../../reference/config-db/ssh-server.md) / [SSH_CONFIG](../../reference/config-db/ssh-config.md)
- [PASSW_HARDENING](../../reference/config-db/passw-hardening.md) / [FIPS](../../reference/config-db/fips.md)
- [MGMT_INTERFACE](../../reference/config-db/mgmt-interface.md) / [MGMT_PORT](../../reference/config-db/mgmt-port.md) / [MGMT_VRF_CONFIG](../../reference/config-db/mgmt-vrf-config.md)

入口: [15-security-aaa/setup.md](../15-security-aaa/setup.md)。

### 16 NAT / DHCP Relay / Time-DNS

- [NAT](../../reference/config-db/nat.md) / [NAT_POOL](../../reference/config-db/nat-pool.md) / [NAT_BINDINGS](../../reference/config-db/nat-bindings.md) / [NAT_STATIC](../../reference/config-db/nat-static.md) / [NAT_ZONE](../../reference/config-db/nat-zone.md)
- [DHCP_SERVER_IPV4](../../reference/config-db/dhcp-server-ipv4.md) / [DHCP_SERVER_IPV6](../../reference/config-db/dhcp-server-ipv6.md)
- [DHCP_RELAY](../../reference/config-db/dhcp-relay.md) / [DHCPV4_RELAY](../../reference/config-db/dhcpv4-relay.md)
- [NTP_GLOBAL](../../reference/config-db/ntp-global.md) / [NTP_SERVER](../../reference/config-db/ntp-server.md)

入口: [16-nat-dhcp-dns/setup.md](../16-nat-dhcp-dns/setup.md)。

### 17 SRv6 / MPLS

- [SRV6_MY_LOCATORS](../../reference/config-db/srv6-my-locators.md) / [SRV6_MY_SIDS](../../reference/config-db/srv6-my-sids.md)
- [SRV6_APPLB](../../reference/config-db/srv6-applb.md)

入口: [17-srv6-mpls/setup.md](../17-srv6-mpls/setup.md)。

### 18 P4 / PINS

- [PIN_CONFIG](../../reference/config-db/pin-config.md)

入口: [18-p4-pins/setup.md](../18-p4-pins/setup.md)。

### 19 Build / Packaging

CONFIG_DB を直接更新する table はない (build 時の image 設定が主)。

入口: [19-build-packaging/setup.md](../19-build-packaging/setup.md)。

### 20 SWSS / SAI / Redis

- [FLEX_COUNTER_TABLE](../../reference/config-db/flex-counter-table.md) (01 章と共有、[orchagent](../../reference/glossary.md#term-orchagent) / [syncd](../../reference/glossary.md#term-syncd) 視点で再参照)

入口: [20-swss-sai-redis/setup.md](../20-swss-sai-redis/setup.md)。

### 21 Lab / Developer

CONFIG_DB の専用 table はない (lab DUT 操作は他章の table を流用)。

入口: [21-lab-vs-developer/setup.md](../21-lab-vs-developer/setup.md)。

## 辞書から章への逆引き

`docs/reference/config-db/index.md` には CONFIG_DB の全 table 一覧が並ぶ。読者が table 名を知っているが章を知らない場合、本ページの上記節のなかで table 名を検索すれば章に到達できる。

## 主入口が複数章にまたがる table

| Table | 主入口 | 関連参照 |
|---|---|---|
| INTERFACE | 06 章 (port 設定) | 04 章 ([VRF](../../reference/glossary.md#term-vrf) binding) |
| VLAN_INTERFACE | 06 章 | 04 章 (VRF binding) |
| [CRM](../../reference/glossary.md#term-crm) | 07 章 | 09 章 (resource 監視) |
| FLEX_COUNTER_TABLE | 01 章 | 07 / 09 章 (counter 種別ごと) |
| KDUMP | 01 章 | 11 章 (reboot lifecycle) |

<!-- glossary-links-injected: 17e7bf57ecf3 -->
