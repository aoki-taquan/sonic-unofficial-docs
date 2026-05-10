# Reference 未カバー洗い出しレポート

作成日: 2026-05-10

## 前提

- CLI は `meta/index/cli.json` の `kind=group` を対象に、既存 `docs/reference/cli/*.md` が表す command prefix と照合した。`config` と `show cli` は集約 root として未カバー数から除外した。
- CONFIG_DB は `sonic-buildimage/src/sonic-yang-models/yang-models/` の 136 YANG モジュールから、モジュール top container 直下の大文字 `container` を CONFIG_DB テーブル候補として抽出し、`docs/reference/config-db/*.md` のページ見出しと照合した。
- YANG は `meta/index/yang.json` の 136 module 名と `docs/reference/yang/*.md` のファイル名を照合した。
- 重要度は、運用頻度、データプレーン影響、既存 Reference との隣接度、CLI から設定される可能性を元にした暫定推定。

## CLI

- 既存カバー数: 44 / 110 group nodes (40.0%)
- 未カバー数: 66

### 未カバー一覧

| サブグループ | 重要度 |
|---|---|
| `config asic-sdk-health-event` | medium |
| `config asic-sdk-health-event suppress` | medium |
| `config banner` | medium |
| `config bmp` | medium |
| `config buffer` | high |
| `config buffer priority-group` | high |
| `config buffer priority-group lossless` | high |
| `config buffer profile` | high |
| `config buffer queue` | high |
| `config buffer shared-headroom-pool` | high |
| `config cbf` | low |
| `config clock` | medium |
| `config dropcounters` | medium |
| `config interface_naming_mode` | medium |
| `config ipv6` | medium |
| `config ipv6 disable` | medium |
| `config ipv6 enable` | medium |
| `config loopback` | medium |
| `config mirror_session` | medium |
| `config mirror_session erspan` | medium |
| `config mirror_session span` | medium |
| `config ntp` | medium |
| `config pfcwd` | high |
| `config platform` | high |
| `config platform firmware` | high |
| `config qos` | high |
| `config rate` | medium |
| `config serial_console` | medium |
| `config ssh` | medium |
| `config subinterface` | medium |
| `config switch-fast-linkup` | medium |
| `config vnet` | high |
| `config warm_restart` | high |
| `config watermark` | medium |
| `config watermark telemetry` | medium |
| `config ztp` | medium |
| `show cli asic-sdk-health-event` | medium |
| `show cli banner` | medium |
| `show cli bfd` | high |
| `show cli bmp` | medium |
| `show cli buffer` | high |
| `show cli buffer_pool` | high |
| `show cli clock` | medium |
| `show cli headroom-pool` | medium |
| `show cli ipv6` | medium |
| `show cli lldp` | high |
| `show cli mac` | medium |
| `show cli management_interface` | medium |
| `show cli mgmt-vrf` | high |
| `show cli pfc` | high |
| `show cli pfcwd` | high |
| `show cli priority-group` | high |
| `show cli priority-group drop` | high |
| `show cli priority-group persistent-watermark` | high |
| `show cli priority-group watermark` | high |
| `show cli priority-group watermark telemetry` | low |
| `show cli queue` | high |
| `show cli serial_console` | medium |
| `show cli snmpagentaddress` | medium |
| `show cli snmptrap` | medium |
| `show cli ssh` | medium |
| `show cli storm-control` | medium |
| `show cli subinterfaces` | medium |
| `show cli switch-fast-linkup` | medium |
| `show cli vrrp` | medium |
| `show cli vrrp6` | medium |

### 次バッチ優先候補

- `config buffer` (high)
- `config buffer priority-group` (high)
- `config buffer profile` (high)
- `config buffer queue` (high)
- `config pfcwd` (high)
- `config platform firmware` (high)
- `config qos` (high)
- `config vnet` (high)
- `config warm_restart` (high)
- `show cli buffer` (high)
- `show cli buffer_pool` (high)
- `show cli pfc` (high)
- `show cli pfcwd` (high)
- `show cli priority-group` (high)
- `show cli queue` (high)
- `show cli mgmt-vrf` (high)
- `show cli lldp` (high)
- `show cli bfd` (high)

## CONFIG_DB

- 既存カバー数: 64 / 207 table containers (30.9%)
- 未カバー数: 143

### 未カバー一覧

| テーブル | YANG module | 重要度 |
|---|---|---|
| `ASIC_SENSORS` | `sonic-asic-sensors` | medium |
| `AUTO_TECHSUPPORT_FEATURE` | `sonic-auto_techsupport` | medium |
| `BANNER_MESSAGE` | `sonic-banner` | medium |
| `BGP_ALLOWED_PREFIXES` | `sonic-bgp-allowed-prefix` | high |
| `BGP_BBR` | `sonic-bgp-bbr` | low |
| `BGP_GLOBALS_AF` | `sonic-bgp-global` | high |
| `BGP_GLOBALS_AF_AGGREGATE_ADDR` | `sonic-bgp-global` | high |
| `BGP_GLOBALS_AF_NETWORK` | `sonic-bgp-global` | high |
| `BGP_INTERNAL_NEIGHBOR` | `sonic-bgp-internal-neighbor` | low |
| `BGP_MONITORS` | `sonic-bgp-monitor` | high |
| `BGP_GLOBALS_LISTEN_PREFIX` | `sonic-bgp-peergroup` | low |
| `BGP_PEER_RANGE` | `sonic-bgp-peerrange` | high |
| `BGP_SENTINELS` | `sonic-bgp-sentinel` | low |
| `BGP_VOQ_CHASSIS_NEIGHBOR` | `sonic-bgp-voq-chassis-neighbor` | high |
| `BMP` | `sonic-bmp` | medium |
| `BREAKOUT_CFG` | `sonic-breakout_cfg` | high |
| `BUFFER_PORT_EGRESS_PROFILE_LIST` | `sonic-buffer-port-egress-profile-list` | high |
| `BUFFER_PORT_INGRESS_PROFILE_LIST` | `sonic-buffer-port-ingress-profile-list` | high |
| `CABLE_LENGTH` | `sonic-cable-length` | medium |
| `CHASSIS_MODULE` | `sonic-chassis-module` | medium |
| `CONSOLE_PORT` | `sonic-console` | medium |
| `CONSOLE_SWITCH` | `sonic-console` | medium |
| `DASH_VNET` | `sonic-dash` | low |
| `DASH_QOS` | `sonic-dash` | low |
| `DASH_ENI` | `sonic-dash` | low |
| `DASH_ACL_IN` | `sonic-dash` | low |
| `DASH_ACL_OUT` | `sonic-dash` | low |
| `DASH_ACL_GROUP` | `sonic-dash` | low |
| `DASH_ACL_RULE` | `sonic-dash` | low |
| `DASH_APPLIANCE` | `sonic-dash` | low |
| `DASH_ROUTING_TYPE` | `sonic-dash` | low |
| `DASH_ROUTE_TABLE` | `sonic-dash` | low |
| `DASH_VNET_MAPPING_TABLE` | `sonic-dash` | low |
| `DEBUG_COUNTER_DROP_REASON` | `sonic-debug-counter` | medium |
| `DEBUG_DROP_MONITOR` | `sonic-debug-counter` | medium |
| `DEFAULT_LOSSLESS_BUFFER_PARAMETER` | `sonic-default-lossless-buffer-parameter` | medium |
| `DHCP_SERVER_IPV4_CUSTOMIZED_OPTIONS` | `sonic-dhcp-server-ipv4` | medium |
| `DHCP_SERVER_IPV4_RANGE` | `sonic-dhcp-server-ipv4` | medium |
| `DHCP_SERVER_IPV4_PORT` | `sonic-dhcp-server-ipv4` | medium |
| `DHCP_SERVER` | `sonic-dhcp-server` | high |
| `DHCP_RELAY` | `sonic-dhcpv6-relay` | high |
| `DNS_NAMESERVER` | `sonic-dns` | high |
| `DNS_OPTIONS` | `sonic-dns` | high |
| `DOT1P_TO_TC_MAP` | `sonic-dot1p-tc-map` | high |
| `DSCP_TO_FC_MAP` | `sonic-dscp-fc-map` | high |
| `EXP_TO_FC_MAP` | `sonic-exp-fc-map` | high |
| `FABRIC_MONITOR` | `sonic-fabric-monitor` | medium |
| `FABRIC_PORT` | `sonic-fabric-port` | high |
| `SWITCH_FAST_LINKUP` | `sonic-fast-linkup` | medium |
| `FG_NHG_PREFIX` | `sonic-fine-grained-ecmp` | high |
| `FG_NHG_MEMBER` | `sonic-fine-grained-ecmp` | high |
| `FIPS` | `sonic-fips` | medium |
| `FLOW_COUNTER_ROUTE_PATTERN` | `sonic-flex_counter` | low |
| `GNMI` | `sonic-gnmi` | medium |
| `GNMI_CLIENT_CERT` | `sonic-gnmi` | medium |
| `GRPCCLIENT` | `sonic-grpcclient` | medium |
| `SWITCH_HASH` | `sonic-hash` | medium |
| `HEARTBEAT` | `sonic-heartbeat` | low |
| `HIGH_FREQUENCY_TELEMETRY_PROFILE` | `sonic-high-frequency-telemetry` | medium |
| `HIGH_FREQUENCY_TELEMETRY_GROUP` | `sonic-high-frequency-telemetry` | medium |
| `LLDP` | `sonic-lldp` | high |
| `LLDP_PORT` | `sonic-lldp` | high |
| `LOGGER` | `sonic-logger` | medium |
| `LOSSLESS_TRAFFIC_PATTERN` | `sonic-lossless-traffic-pattern` | low |
| `MACSEC_PROFILE` | `sonic-macsec` | medium |
| `MCLAG_DOMAIN` | `sonic-mclag` | high |
| `MCLAG_INTERFACE` | `sonic-mclag` | high |
| `MCLAG_UNIQUE_IP` | `sonic-mclag` | high |
| `MEMORY_STATISTICS` | `sonic-memory-statistics` | low |
| `MPLS_TC_TO_TC_MAP` | `sonic-mpls-tc-map` | low |
| `MUX_LINKMGR` | `sonic-mux-linkmgr` | medium |
| `STATIC_NAPT` | `sonic-nat` | high |
| `STATIC_NAT` | `sonic-nat` | high |
| `NAT_GLOBAL` | `sonic-nat` | high |
| `NAT_POOL` | `sonic-nat` | high |
| `NAT_BINDINGS` | `sonic-nat` | high |
| `NEIGH` | `sonic-neigh` | medium |
| `NTP_KEY` | `sonic-ntp` | medium |
| `NVGRE_TUNNEL` | `sonic-nvgre-tunnel` | medium |
| `NVGRE_TUNNEL_MAP` | `sonic-nvgre-tunnel` | medium |
| `PASSW_HARDENING` | `sonic-passwh` | low |
| `PBH_HASH_FIELD` | `sonic-pbh` | high |
| `PBH_HASH` | `sonic-pbh` | high |
| `PBH_RULE` | `sonic-pbh` | high |
| `PBH_TABLE` | `sonic-pbh` | high |
| `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` | `sonic-pfc-priority-priority-group-map` | high |
| `MAP_PFC_PRIORITY_TO_QUEUE` | `sonic-pfc-priority-queue-map` | high |
| `PORT_QOS_MAP` | `sonic-port-qos-map` | high |
| `RESTAPI` | `sonic-restapi` | medium |
| `ROUTE_REDISTRIBUTE` | `sonic-route-common` | medium |
| `ROUTE_MAP_SET` | `sonic-route-map` | medium |
| `PREFIX` | `sonic-routing-policy-sets` | low |
| `EXTENDED_COMMUNITY_SET` | `sonic-routing-policy-sets` | low |
| `SERIAL_CONSOLE` | `sonic-serial-console` | low |
| `SFLOW_COLLECTOR` | `sonic-sflow` | medium |
| `SFLOW_SESSION` | `sonic-sflow` | medium |
| `MID_PLANE_BRIDGE` | `sonic-smart-switch` | low |
| `DPUS` | `sonic-smart-switch` | low |
| `DPU` | `sonic-smart-switch` | low |
| `REMOTE_DPU` | `sonic-smart-switch` | low |
| `VDPU` | `sonic-smart-switch` | low |
| `DASH_HA_GLOBAL_CONFIG` | `sonic-smart-switch` | low |
| `SNMP` | `sonic-snmp` | medium |
| `SNMP_COMMUNITY` | `sonic-snmp` | medium |
| `SNMP_USER` | `sonic-snmp` | medium |
| `SNMP_AGENT_ADDRESS_CONFIG` | `sonic-snmp` | medium |
| `STP` | `sonic-spanning-tree` | medium |
| `STP_VLAN` | `sonic-spanning-tree` | medium |
| `STP_VLAN_PORT` | `sonic-spanning-tree` | medium |
| `STP_PORT` | `sonic-spanning-tree` | medium |
| `STP_MST` | `sonic-spanning-tree` | medium |
| `STP_MST_INST` | `sonic-spanning-tree` | medium |
| `STP_MST_PORT` | `sonic-spanning-tree` | medium |
| `SRV6_MY_LOCATORS` | `sonic-srv6` | medium |
| `SRV6_MY_SIDS` | `sonic-srv6` | medium |
| `SSH_SERVER` | `sonic-ssh-server` | medium |
| `STATIC_ROUTE` | `sonic-static-route` | high |
| `PORT_STORM_CONTROL` | `sonic-storm-control` | high |
| `STORMOND_CONFIG` | `sonic-stormond-config` | low |
| `SUBNET_DECAP` | `sonic-subnet-decap` | medium |
| `SUPPRESS_ASIC_SDK_HEALTH_EVENT` | `sonic-suppress-asic-sdk-health-event` | medium |
| `SYSLOG_CONFIG` | `sonic-syslog` | medium |
| `SYSLOG_CONFIG_FEATURE` | `sonic-syslog` | medium |
| `AAA` | `sonic-system-aaa` | medium |
| `LDAP` | `sonic-system-ldap` | medium |
| `SYSTEM_PORT` | `sonic-system-port` | low |
| `RADIUS` | `sonic-system-radius` | medium |
| `RADIUS_SERVER` | `sonic-system-radius` | medium |
| `TACPLUS` | `sonic-system-tacacs` | medium |
| `TC_TO_DSCP_MAP` | `sonic-tc-dscp-map` | medium |
| `TC_TO_PRIORITY_GROUP_MAP` | `sonic-tc-priority-group-map` | medium |
| `TELEMETRY_CLIENT` | `sonic-telemetry_client` | medium |
| `SWITCH_TRIMMING` | `sonic-trimming` | medium |
| `VERSIONS` | `sonic-versions` | low |
| `VLAN_SUB_INTERFACE` | `sonic-vlan-sub-interface` | high |
| `VNET` | `sonic-vnet` | high |
| `VNET_ROUTE` | `sonic-vnet` | high |
| `VNET_ROUTE_TUNNEL` | `sonic-vnet` | high |
| `VOQ_INBAND_INTERFACE` | `sonic-voq-inband-interface` | high |
| `VXLAN_EVPN_NVO` | `sonic-vxlan` | high |
| `WARM_RESTART` | `sonic-warm-restart` | high |
| `XCVRD_LOG` | `sonic-xcvrd-log` | low |
| `ZTP` | `sonic-ztp` | medium |

### 次バッチ優先候補

- `VNET` (`sonic-vnet`, high)
- `VNET_ROUTE` (`sonic-vnet`, high)
- `VNET_ROUTE_TUNNEL` (`sonic-vnet`, high)
- `VLAN_SUB_INTERFACE` (`sonic-vlan-sub-interface`, high)
- `STATIC_ROUTE` (`sonic-static-route`, high)
- `NAT_GLOBAL` (`sonic-nat`, high)
- `NAT_POOL` (`sonic-nat`, high)
- `NAT_BINDINGS` (`sonic-nat`, high)
- `STATIC_NAT` (`sonic-nat`, high)
- `STATIC_NAPT` (`sonic-nat`, high)
- `PBH_TABLE` (`sonic-pbh`, high)
- `PBH_RULE` (`sonic-pbh`, high)
- `PORT_QOS_MAP` (`sonic-port-qos-map`, high)
- `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` (`sonic-pfc-priority-priority-group-map`, high)
- `MAP_PFC_PRIORITY_TO_QUEUE` (`sonic-pfc-priority-queue-map`, high)
- `BGP_GLOBALS_AF` (`sonic-bgp-global`, high)
- `BGP_GLOBALS_AF_AGGREGATE_ADDR` (`sonic-bgp-global`, high)
- `BGP_GLOBALS_AF_NETWORK` (`sonic-bgp-global`, high)
- `DHCP_SERVER` (`sonic-dhcp-server`, high)
- `DHCP_RELAY` (`sonic-dhcpv6-relay`, high)

## YANG

- 既存カバー数: 29 / 136 modules (21.3%)
- 未カバー数: 107

### 未カバー一覧

| module | 重要度 |
|---|---|
| `sonic-asic-sensors` | medium |
| `sonic-auto_techsupport` | medium |
| `sonic-banner` | medium |
| `sonic-bgp-aggregate-address` | high |
| `sonic-bgp-allowed-prefix` | high |
| `sonic-bgp-bbr` | low |
| `sonic-bgp-common` | low |
| `sonic-bgp-device-global` | high |
| `sonic-bgp-internal-neighbor` | low |
| `sonic-bgp-monitor` | high |
| `sonic-bgp-peerrange` | high |
| `sonic-bgp-prefix-list` | low |
| `sonic-bgp-sentinel` | low |
| `sonic-bgp-voq-chassis-neighbor` | high |
| `sonic-bmp` | medium |
| `sonic-breakout_cfg` | high |
| `sonic-buffer-port-egress-profile-list` | high |
| `sonic-buffer-port-ingress-profile-list` | high |
| `sonic-cable-length` | medium |
| `sonic-chassis-module` | medium |
| `sonic-console` | medium |
| `sonic-crm` | medium |
| `sonic-dash` | low |
| `sonic-debug-counter` | medium |
| `sonic-default-lossless-buffer-parameter` | medium |
| `sonic-device_neighbor` | medium |
| `sonic-device_neighbor_metadata` | medium |
| `sonic-dhcp-server-ipv4` | medium |
| `sonic-dhcp-server` | high |
| `sonic-dhcpv4-relay` | high |
| `sonic-dhcpv6-relay` | high |
| `sonic-dns` | high |
| `sonic-dot1p-tc-map` | high |
| `sonic-dscp-fc-map` | high |
| `sonic-events-bgp` | low |
| `sonic-events-common` | low |
| `sonic-events-dhcp-relay` | low |
| `sonic-events-host` | low |
| `sonic-events-swss` | low |
| `sonic-events-syncd` | low |
| `sonic-exp-fc-map` | high |
| `sonic-fabric-monitor` | medium |
| `sonic-fabric-port` | high |
| `sonic-fast-linkup` | medium |
| `sonic-fine-grained-ecmp` | high |
| `sonic-fips` | medium |
| `sonic-flex_counter` | low |
| `sonic-gnmi` | medium |
| `sonic-grpcclient` | medium |
| `sonic-hash` | medium |
| `sonic-heartbeat` | low |
| `sonic-high-frequency-telemetry` | medium |
| `sonic-kdump` | medium |
| `sonic-kubernetes_master` | medium |
| `sonic-lldp` | high |
| `sonic-logger` | medium |
| `sonic-lossless-traffic-pattern` | low |
| `sonic-macsec` | medium |
| `sonic-memory-statistics` | low |
| `sonic-mgmt_interface` | medium |
| `sonic-mgmt_port` | medium |
| `sonic-mgmt_vrf` | medium |
| `sonic-mpls-tc-map` | low |
| `sonic-mux-cable` | medium |
| `sonic-mux-linkmgr` | low |
| `sonic-nat` | high |
| `sonic-neigh` | medium |
| `sonic-nvgre-tunnel` | medium |
| `sonic-passwh` | low |
| `sonic-pbh` | high |
| `sonic-peer-switch` | medium |
| `sonic-pfc-priority-priority-group-map` | high |
| `sonic-pfc-priority-queue-map` | high |
| `sonic-port-qos-map` | high |
| `sonic-restapi` | medium |
| `sonic-routing-policy-sets` | low |
| `sonic-serial-console` | medium |
| `sonic-sflow` | high |
| `sonic-smart-switch` | low |
| `sonic-snmp` | high |
| `sonic-spanning-tree` | high |
| `sonic-srv6` | low |
| `sonic-ssh-server` | medium |
| `sonic-static-route` | high |
| `sonic-storm-control` | high |
| `sonic-stormond-config` | low |
| `sonic-subnet-decap` | medium |
| `sonic-suppress-asic-sdk-health-event` | medium |
| `sonic-system-defaults` | medium |
| `sonic-system-ldap` | medium |
| `sonic-system-port` | low |
| `sonic-system-radius` | medium |
| `sonic-system-tacacs` | medium |
| `sonic-tc-dscp-map` | medium |
| `sonic-tc-priority-group-map` | medium |
| `sonic-telemetry` | medium |
| `sonic-telemetry_client` | medium |
| `sonic-trimming` | medium |
| `sonic-tunnel` | medium |
| `sonic-versions` | low |
| `sonic-vlan-sub-interface` | high |
| `sonic-vnet` | high |
| `sonic-voq-inband-interface` | high |
| `sonic-warm-restart` | high |
| `sonic-wred-profile` | high |
| `sonic-xcvrd-log` | low |
| `sonic-ztp` | medium |

### 次バッチ優先候補

- `sonic-vnet` (high)
- `sonic-vlan-sub-interface` (high)
- `sonic-static-route` (high)
- `sonic-nat` (high)
- `sonic-pbh` (high)
- `sonic-port-qos-map` (high)
- `sonic-pfc-priority-priority-group-map` (high)
- `sonic-pfc-priority-queue-map` (high)
- `sonic-bgp-aggregate-address` (high)
- `sonic-bgp-allowed-prefix` (high)
- `sonic-bgp-device-global` (high)
- `sonic-bgp-monitor` (high)
- `sonic-bgp-peerrange` (high)
- `sonic-breakout_cfg` (high)
- `sonic-dhcp-server` (high)
- `sonic-dhcpv6-relay` (high)
- `sonic-dns` (high)
- `sonic-lldp` (high)
- `sonic-spanning-tree` (high)
- `sonic-warm-restart` (high)
