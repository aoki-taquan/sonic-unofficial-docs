---
title: リファレンス
description: "リファレンス — CLI、CONFIG_DB、YANG を機械抽出ベースで整理する参照章。"
verification: stub
---

# リファレンス
CLI、CONFIG_DB、YANG を機械抽出ベースで整理する参照章。
## この章の読み方
この章は運用中に直接引く参照情報を集める。CLI、CONFIG_DB、YANG の 3 系統を起点に、HLD ページから参照される実装上の名前を確認する。
## 検証状況
- ページ数: 135
- 分布: Code-verified: 135

## ページ一覧

| ページ | 検証 |
|---|---|
| **CLI** |  |
| [clear (sonic-clear) コマンド](cli/clear.md) | Code-verified |
| [config aaa / tacacs / radius サブコマンド](cli/config-aaa.md) | Code-verified |
| [config acl サブコマンド](cli/config-acl.md) | Code-verified |
| [config bgp サブコマンド](cli/config-bgp.md) | Code-verified |
| [config dhcp_relay / dhcpv4_relay サブコマンド](cli/config-dhcp-relay.md) | Code-verified |
| [config interface サブコマンド](cli/config-interface.md) | Code-verified |
| [config kdump サブコマンド](cli/config-kdump.md) | Code-verified |
| [config mclag サブコマンド](cli/config-mclag.md) | Code-verified |
| [config muxcable サブコマンド](cli/config-muxcable.md) | Code-verified |
| [config nat サブコマンド](cli/config-nat.md) | Code-verified |
| [config portchannel サブコマンド](cli/config-portchannel.md) | Code-verified |
| [config route サブコマンド（static route）](cli/config-route.md) | Code-verified |
| [config save / load / reload / replace / qos reload](cli/config-mgmt-trio.md) | Code-verified |
| [config sflow サブコマンド](cli/config-sflow.md) | Code-verified |
| [config snmp / snmpagentaddress / snmptrap サブコマンド](cli/config-snmp.md) | Code-verified |
| [config syslog サブコマンド](cli/config-syslog.md) | Code-verified |
| [config vlan サブコマンド](cli/config-vlan.md) | Code-verified |
| [config vrf サブコマンド](cli/config-vrf.md) | Code-verified |
| [config vxlan サブコマンド](cli/config-vxlan.md) | Code-verified |
| [debug / undebug コマンド群](cli/debug-group.md) | Code-verified |
| [reboot / fast-reboot / warm-reboot コマンド](cli/reboot-fast-warm.md) | Code-verified |
| [show acl サブコマンド](cli/show-acl.md) | Code-verified |
| [show bgp / show ip bgp / show ipv6 bgp サブコマンド](cli/show-bgp.md) | Code-verified |
| [show feature サブコマンド](cli/show-feature.md) | Code-verified |
| [show interfaces サブコマンド](cli/show-interfaces.md) | Code-verified |
| [show ip サブコマンド](cli/show-ip.md) | Code-verified |
| [show mclag (mclagdctl) コマンド](cli/show-mclag.md) | Code-verified |
| [show muxcable サブコマンド](cli/show-muxcable.md) | Code-verified |
| [show nat サブコマンド](cli/show-nat.md) | Code-verified |
| [show platform サブコマンド](cli/show-platform.md) | Code-verified |
| [show route-map コマンド](cli/show-route-map.md) | Code-verified |
| [show runningconfiguration / startupconfiguration サブコマンド](cli/show-running-config.md) | Code-verified |
| [show system-health サブコマンド](cli/show-system-health.md) | Code-verified |
| [show techsupport コマンド](cli/show-techsupport.md) | Code-verified |
| [show vlan サブコマンド](cli/show-vlan.md) | Code-verified |
| [sonic-cfggen コマンド](cli/sonic-cfggen.md) | Code-verified |
| [sonic-installer コマンド](cli/sonic-installer.md) | Code-verified |
| [sonic-package-manager コマンド](cli/sonic-package-manager.md) | Code-verified |
| **CONFIG_DB** |  |
| [ACL_RULE テーブル](config-db/acl-rule.md) | Code-verified |
| [ACL_TABLE テーブル](config-db/acl-table.md) | Code-verified |
| [AS_PATH_SET テーブル](config-db/as-path-set.md) | Code-verified |
| [AUTO_TECHSUPPORT テーブル](config-db/auto-techsupport.md) | Code-verified |
| [BGP_AGGREGATE_ADDRESS テーブル](config-db/bgp-aggregate-address.md) | Code-verified |
| [BGP_DEVICE_GLOBAL テーブル](config-db/bgp-device-global.md) | Code-verified |
| [BGP_GLOBALS テーブル](config-db/bgp-globals.md) | Code-verified |
| [BGP_NEIGHBOR テーブル](config-db/bgp-neighbor.md) | Code-verified |
| [BGP_NEIGHBOR_AF テーブル](config-db/bgp-neighbor-af.md) | Code-verified |
| [BGP_PEER_GROUP テーブル](config-db/bgp-peer-group.md) | Code-verified |
| [BGP_PEER_GROUP_AF テーブル](config-db/bgp-peer-group-af.md) | Code-verified |
| [BUFFER_PG テーブル](config-db/buffer-pg.md) | Code-verified |
| [BUFFER_POOL テーブル](config-db/buffer-pool.md) | Code-verified |
| [BUFFER_PROFILE テーブル](config-db/buffer-profile.md) | Code-verified |
| [BUFFER_QUEUE テーブル](config-db/buffer-queue.md) | Code-verified |
| [COMMUNITY_SET テーブル](config-db/community-set.md) | Code-verified |
| [COPP_GROUP テーブル](config-db/copp-group.md) | Code-verified |
| [COPP_TRAP テーブル](config-db/copp-trap.md) | Code-verified |
| [CRM テーブル](config-db/crm.md) | Code-verified |
| [DEBUG_COUNTER テーブル](config-db/debug-counter.md) | Code-verified |
| [DEVICE_METADATA テーブル](config-db/device-metadata.md) | Code-verified |
| [DEVICE_NEIGHBOR テーブル](config-db/device-neighbor.md) | Code-verified |
| [DEVICE_NEIGHBOR_METADATA テーブル](config-db/device-neighbor-metadata.md) | Code-verified |
| [DHCPV4_RELAY テーブル](config-db/dhcpv4-relay.md) | Code-verified |
| [DHCP_SERVER_IPV4 テーブル](config-db/dhcp-server-ipv4.md) | Code-verified |
| [DSCP_TO_TC_MAP テーブル](config-db/dscp-to-tc-map.md) | Code-verified |
| [FEATURE テーブル](config-db/feature.md) | Code-verified |
| [FG_NHG テーブル](config-db/fg-nhg.md) | Code-verified |
| [FLEX_COUNTER_TABLE テーブル](config-db/flex-counter-table.md) | Code-verified |
| [INTERFACE テーブル](config-db/interface.md) | Code-verified |
| [KDUMP テーブル](config-db/kdump.md) | Code-verified |
| [KUBERNETES_MASTER テーブル](config-db/kubernetes-master.md) | Code-verified |
| [LDAP_SERVER テーブル](config-db/ldap-server.md) | Code-verified |
| [LOOPBACK_INTERFACE テーブル](config-db/loopback-interface.md) | Code-verified |
| [MGMT_INTERFACE テーブル](config-db/mgmt-interface.md) | Code-verified |
| [MGMT_PORT テーブル](config-db/mgmt-port.md) | Code-verified |
| [MGMT_VRF_CONFIG テーブル](config-db/mgmt-vrf-config.md) | Code-verified |
| [MIRROR_SESSION テーブル](config-db/mirror-session.md) | Code-verified |
| [MUX_CABLE テーブル](config-db/mux-cable.md) | Code-verified |
| [NTP テーブル (global)](config-db/ntp-global.md) | Code-verified |
| [NTP_SERVER テーブル](config-db/ntp-server.md) | Code-verified |
| [PEER_SWITCH テーブル](config-db/peer-switch.md) | Code-verified |
| [PFC_WD テーブル](config-db/pfc-wd.md) | Code-verified |
| [POLICER テーブル](config-db/policer.md) | Code-verified |
| [PORT テーブル](config-db/port.md) | Code-verified |
| [PORTCHANNEL テーブル](config-db/portchannel.md) | Code-verified |
| [PORTCHANNEL_INTERFACE テーブル](config-db/portchannel-interface.md) | Code-verified |
| [PORTCHANNEL_MEMBER テーブル](config-db/portchannel-member.md) | Code-verified |
| [PREFIX_LIST テーブル (BGP)](config-db/prefix-list.md) | Code-verified |
| [PREFIX_SET テーブル](config-db/prefix-set.md) | Code-verified |
| [QUEUE テーブル](config-db/queue.md) | Code-verified |
| [ROUTE_MAP テーブル](config-db/route-map.md) | Code-verified |
| [SCHEDULER テーブル](config-db/scheduler.md) | Code-verified |
| [SFLOW テーブル](config-db/sflow.md) | Code-verified |
| [SYSLOG_SERVER テーブル](config-db/syslog-server.md) | Code-verified |
| [SYSTEM_DEFAULTS テーブル](config-db/system-defaults.md) | Code-verified |
| [TACPLUS_SERVER テーブル](config-db/tacplus-server.md) | Code-verified |
| [TC_TO_QUEUE_MAP テーブル](config-db/tc-to-queue-map.md) | Code-verified |
| [TELEMETRY テーブル](config-db/telemetry.md) | Code-verified |
| [TUNNEL テーブル](config-db/tunnel.md) | Code-verified |
| [TUNNEL_DECAP_TABLE (APPL_DB)](config-db/tunnel-decap-table.md) | Code-verified |
| [VLAN テーブル](config-db/vlan.md) | Code-verified |
| [VLAN_INTERFACE テーブル](config-db/vlan-interface.md) | Code-verified |
| [VLAN_MEMBER テーブル](config-db/vlan-member.md) | Code-verified |
| [VRF テーブル](config-db/vrf.md) | Code-verified |
| [VXLAN_TUNNEL テーブル](config-db/vxlan-tunnel.md) | Code-verified |
| [VXLAN_TUNNEL_MAP テーブル](config-db/vxlan-tunnel-map.md) | Code-verified |
| [WRED_PROFILE テーブル](config-db/wred-profile.md) | Code-verified |
| **YANG** |  |
| [sonic-bgp-global YANG](yang/sonic-bgp-global.md) | Code-verified |
| [sonic-bgp-neighbor YANG](yang/sonic-bgp-neighbor.md) | Code-verified |
| [sonic-bgp-peergroup YANG](yang/sonic-bgp-peergroup.md) | Code-verified |
| [sonic-buffer-pg YANG](yang/sonic-buffer-pg.md) | Code-verified |
| [sonic-buffer-pool YANG](yang/sonic-buffer-pool.md) | Code-verified |
| [sonic-buffer-profile YANG](yang/sonic-buffer-profile.md) | Code-verified |
| [sonic-buffer-queue YANG](yang/sonic-buffer-queue.md) | Code-verified |
| [sonic-copp YANG](yang/sonic-copp.md) | Code-verified |
| [sonic-device_metadata YANG](yang/sonic-device_metadata.md) | Code-verified |
| [sonic-dscp-tc-map YANG](yang/sonic-dscp-tc-map.md) | Code-verified |
| [sonic-feature YANG](yang/sonic-feature.md) | Code-verified |
| [sonic-interface YANG](yang/sonic-interface.md) | Code-verified |
| [sonic-loopback-interface YANG](yang/sonic-loopback-interface.md) | Code-verified |
| [sonic-mclag YANG](yang/sonic-mclag.md) | Code-verified |
| [sonic-mirror-session YANG](yang/sonic-mirror-session.md) | Code-verified |
| [sonic-ntp YANG](yang/sonic-ntp.md) | Code-verified |
| [sonic-pfcwd YANG](yang/sonic-pfcwd.md) | Code-verified |
| [sonic-port YANG](yang/sonic-port.md) | Code-verified |
| [sonic-portchannel YANG](yang/sonic-portchannel.md) | Code-verified |
| [sonic-queue YANG](yang/sonic-queue.md) | Code-verified |
| [sonic-route-common YANG](yang/sonic-route-common.md) | Code-verified |
| [sonic-route-map YANG](yang/sonic-route-map.md) | Code-verified |
| [sonic-scheduler YANG](yang/sonic-scheduler.md) | Code-verified |
| [sonic-syslog YANG](yang/sonic-syslog.md) | Code-verified |
| [sonic-system-aaa YANG](yang/sonic-system-aaa.md) | Code-verified |
| [sonic-tc-queue-map YANG](yang/sonic-tc-queue-map.md) | Code-verified |
| [sonic-vlan YANG](yang/sonic-vlan.md) | Code-verified |
| [sonic-vrf YANG](yang/sonic-vrf.md) | Code-verified |
| [sonic-vxlan YANG](yang/sonic-vxlan.md) | Code-verified |

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: リファレンス横断索引](../topics/22-reference-index/index.md)
