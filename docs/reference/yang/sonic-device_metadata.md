---
title: sonic-device_metadata YANG
description: sonic-device_metadata YANG — DEVICE_METADATA YANG Module for SONiC OS
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
- repo: sonic-net/sonic-buildimage
  path: src/sonic-yang-models/yang-models/sonic-device_metadata.yang
  ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db:
  - DEVICE_METADATA
  cli: []
  yang:
  - sonic-device_neighbor
  - sonic-device_neighbor_metadata
---

# sonic-device_metadata YANG

## 概要

- module: `sonic-device_metadata`
- namespace: `http://github.com/sonic-net/sonic-device_metadata`
- revision: `2026-04-10`
- import: `ietf-yang-types`, `ietf-inet-types`, `sonic-types`
- top container: `sonic-device_metadata`

[DEVICE_METADATA](../../reference/glossary.md#term-device_metadata) [YANG](../../reference/glossary.md#term-yang) Module for [SONiC](../../reference/glossary.md#term-sonic) OS[^1]

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-device_metadata"]
  C1[("CONFIG_DB<br/>DEVICE_METADATA")]
  Y --> C1
  D1["SwitchOrch"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## 関連ページ

<!-- yang-xref -->

本 YANG モジュールに対応する CONFIG_DB / CLI / HLD / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。

### 対応 CONFIG_DB

- [`DEVICE_METADATA`](../config-db/device-metadata.md)

### 関連 HLD

- [Chassis Line Card 自動プロビジョニング（sonic-provisiond / provision_module）](../../platform/automatic-module-provisioning-for-chassis.md)

<!-- /yang-xref -->

## ツリー

```text
module: sonic-device_metadata
  +--rw sonic-device_metadata
     +--rw DEVICE_METADATA
        +--rw localhost
        |  +--rw hwsku?                              stypes:hwsku
        |  +--rw asic_id?                            string
        |  +--rw default_bgp_status?                 enumeration
        |  +--rw docker_routing_config_mode?         string
        |  +--rw hostname?                           stypes:hostname
        |  +--rw platform?                           string
        |  +--rw mac?                                yang:mac-address
        |  +--rw default_pfcwd_status?               enumeration
        |  +--rw bgp_asn?                            inet:as-number
        |  +--rw deployment_id?                      uint32
        |  +--rw type?                               string
        |  +--rw buffer_model?                       string
        |  +--rw frr_mgmt_framework_config?          boolean
        |  +--rw synchronous_mode?                   enumeration
        |  +--rw yang_config_validation?             stypes:mode-status
        |  +--rw cloudtype?                          string
        |  +--rw region?                             string
        |  +--rw sub_role?                           string
        |  +--rw downstream_subrole?                 string
        |  +--rw resource_type?                      string
        |  +--rw mgmt_type?                          string
        |  +--rw cluster?                            string
        |  +--rw subtype?                            string
        |  +--rw peer_switch?                        stypes:hostname
        |  +--rw storage_device?                     boolean
        |  +--rw asic_name?                          string
        |  +--rw switch_id?                          uint16
        |  +--rw switch_type?                        string
        |  +--rw max_cores?                          uint8
        |  +--rw dhcp_server?                        stypes:admin_mode
        |  +--rw bgp_adv_lo_prefix_as_128?           boolean
        |  +--rw suppress-fib-pending?               enumeration
        |  +--rw async_swss_rec?                     enumeration
        |  +--rw rack_mgmt_map?                      string
        |  +--rw timezone?                           stypes:timezone-name-type
        |  +--rw create_only_config_db_buffers?      boolean
        |  +--rw supporting_bulk_counter_groups*     string
        |  +--rw bgp_router_id?                      inet:ipv4-address
        |  +--rw chassis_hostname?                   stypes:hostname
        |  +--rw slice_type?                         string
        |  +--rw location_type?                      string
        |  +--rw nexthop_group?                      enumeration
        |  +--rw ring_thread_enabled?                boolean
        |  +--rw t2_group_asns*                      inet:as-number
        |  +--rw anchor_route_source*                string
        |  +--rw orch_northbond_dash_zmq_enabled?    boolean
        |  +--rw orch_northbond_route_zmq_enabled?   boolean
        |  +--rw syslog_with_osversion?              boolean
        |  +--rw syslog_counter?                     boolean
        |  +--rw has_sonic_dhcpv4_relay?             stypes:boolean_type
        |  +--rw zebra_nexthop?                      enumeration
        +--rw bmc
           +--rw bmc_if_name?    string
           +--rw bmc_if_addr?    inet:ipv4-address
           +--rw bmc_addr?       inet:ipv4-address
           +--rw bmc_net_mask?   inet:ipv4-address
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `hwsku` | `sonic-device_metadata/DEVICE_METADATA/localhost/hwsku` | `stypes:hwsku` |  |  |  | Hardware SKU identifier defining port layout and capabilities. |
| `asic_id` | `sonic-device_metadata/DEVICE_METADATA/localhost/asic_id` | `string` |  |  | length 1..16 | asic_id is unique identifier of the asic used by [SAI](../../reference/glossary.md#term-sai) for initialization. |
| `default_bgp_status` | `sonic-device_metadata/DEVICE_METADATA/localhost/default_bgp_status` | `enumeration` |  | up | up, down | Default [BGP](../../reference/glossary.md#term-bgp) daemon operational state on startup. |
| `docker_routing_config_mode` | `sonic-device_metadata/DEVICE_METADATA/localhost/docker_routing_config_mode` | `string` |  | unified | pattern `separated|unified|split|split-unified` | This leaf allows different configuration modes for [FRR](../../reference/glossary.md#term-frr): - separated: [FRR](../../reference/glossary.md#term-frr) config generated from ConfigDB, each [FRR](../../reference/glossary.md#term-frr) daemon has its own config file - unified: FRR config generated from ConfigDB, singl... |
| `hostname` | `sonic-device_metadata/DEVICE_METADATA/localhost/hostname` | `stypes:hostname` |  |  |  | System hostname for the device. |
| `platform` | `sonic-device_metadata/DEVICE_METADATA/localhost/platform` | `string` |  |  | length 1..255 | Platform identifier (vendor and model). |
| `mac` | `sonic-device_metadata/DEVICE_METADATA/localhost/mac` | `yang:mac-address` |  |  |  | System base MAC address. |
| `default_pfcwd_status` | `sonic-device_metadata/DEVICE_METADATA/localhost/default_pfcwd_status` | `enumeration` |  | disable | disable, enable | Default [PFC](../../reference/glossary.md#term-pfc) watchdog operational state on startup. |
| `bgp_asn` | `sonic-device_metadata/DEVICE_METADATA/localhost/bgp_asn` | `inet:as-number` |  |  |  | [BGP](../../reference/glossary.md#term-bgp) autonomous system number for the device. |
| `deployment_id` | `sonic-device_metadata/DEVICE_METADATA/localhost/deployment_id` | `uint32` |  |  |  | Deployment identifier for grouping devices in the same network segment. |
| `type` | `sonic-device_metadata/DEVICE_METADATA/localhost/type` | `string` |  |  | pattern `ToRRouter|LeafRouter|SpineChassisFrontendRouter|ChassisBa...` | Device role type (e.g., ToRRouter, LeafRouter, SpineRouter). |
| `buffer_model` | `sonic-device_metadata/DEVICE_METADATA/localhost/buffer_model` | `string` |  |  | pattern `dynamic|traditional` | This leaf is added for dynamic buffer calculation. The dynamic model represents the model in which the buffer configurations, like the headroom sizes and buffer pool sizes, are dynamically calculat... |
| `frr_mgmt_framework_config` | `sonic-device_metadata/DEVICE_METADATA/localhost/frr_mgmt_framework_config` | `boolean` |  | false |  | FRR configurations are handled by sonic-frr-mgmt-framework module when set to true, otherwise, sonic-[bgpcfgd](../../reference/glossary.md#term-bgpcfgd) handles the FRR configurations based on the predefined templates. |
| `synchronous_mode` | `sonic-device_metadata/DEVICE_METADATA/localhost/synchronous_mode` | `enumeration` |  | enable | enable, disable | Enable or disable [ASIC](../../reference/glossary.md#term-asic) synchronous mode for [orchagent](../../reference/glossary.md#term-orchagent). |
| `yang_config_validation` | `sonic-device_metadata/DEVICE_METADATA/localhost/yang_config_validation` | `stypes:mode-status` |  | disable |  | Enable or disable [YANG](../../reference/glossary.md#term-yang) model validation for configuration changes. |
| `cloudtype` | `sonic-device_metadata/DEVICE_METADATA/localhost/cloudtype` | `string` |  |  |  | Cloud environment type where the device is deployed. |
| `region` | `sonic-device_metadata/DEVICE_METADATA/localhost/region` | `string` |  |  |  | Geographic region where the device is deployed. |
| `sub_role` | `sonic-device_metadata/DEVICE_METADATA/localhost/sub_role` | `string` |  |  |  | sub_role indicates if [ASIC](../../reference/glossary.md#term-asic) is FrontEnd or BackEnd. |
| `downstream_subrole` | `sonic-device_metadata/DEVICE_METADATA/localhost/downstream_subrole` | `string` |  |  |  | Sub-role of the downstream device connected to this device. |
| `resource_type` | `sonic-device_metadata/DEVICE_METADATA/localhost/resource_type` | `string` |  |  |  | Resource type classification for the device. |
| `mgmt_type` | `sonic-device_metadata/DEVICE_METADATA/localhost/mgmt_type` | `string` |  |  |  | Indicates the management type of this device. |
| `cluster` | `sonic-device_metadata/DEVICE_METADATA/localhost/cluster` | `string` |  |  |  | The switch is a member of this cluster. |
| `subtype` | `sonic-device_metadata/DEVICE_METADATA/localhost/subtype` | `string` |  |  | pattern `DualToR|SmartSwitch|Supervisor|UpstreamLC|DownstreamLC` | Device subtype for specialized topology roles (e.g., DualToR, [SmartSwitch](../../reference/glossary.md#term-smartswitch)). |
| `peer_switch` | `sonic-device_metadata/DEVICE_METADATA/localhost/peer_switch` | `stypes:hostname` |  |  |  | Hostname of the peer switch in a dual ToR configuration. |
| `storage_device` | `sonic-device_metadata/DEVICE_METADATA/localhost/storage_device` | `boolean` |  |  |  | Indicates whether the device is connected to a storage backend. |
| `asic_name` | `sonic-device_metadata/DEVICE_METADATA/localhost/asic_name` | `string` |  |  |  | On a VoQ switch, the [ASIC](../../reference/glossary.md#term-asic) Name is used as a qualifier in global database keys to create a system wide unique key. |
| `switch_id` | `sonic-device_metadata/DEVICE_METADATA/localhost/switch_id` | `uint16` |  |  |  | Vendor specific switch ID. Identifies switch chip. |
| `switch_type` | `sonic-device_metadata/DEVICE_METADATA/localhost/switch_type` | `string` |  |  | pattern `chassis-packet|fabric|npu|voq|dpu|dummy-sup` | Type of switch. Default is [NPU](../../reference/glossary.md#term-npu), on a [VOQ](../../reference/glossary.md#term-voq) switch voq is used for a regular switching device while fabric is used for a fabric device. chassis-packet is used for chassis in packet mode. |
| `max_cores` | `sonic-device_metadata/DEVICE_METADATA/localhost/max_cores` | `uint8` |  |  |  | Maximum number of cores in a VoQ Switch (chassis). |
| `dhcp_server` | `sonic-device_metadata/DEVICE_METADATA/localhost/dhcp_server` | `stypes:admin_mode` |  |  |  | Indicate whether enable the embedded DHCP server. |
| `bgp_adv_lo_prefix_as_128` | `sonic-device_metadata/DEVICE_METADATA/localhost/bgp_adv_lo_prefix_as_128` | `boolean` |  |  |  | Advertise Loopback0 interface IPv6 /128 subnet address as it is with set to true. By default [SONiC](../../reference/glossary.md#term-sonic) advertises /128 subnet prefix in Loopback0 as /64 subnet route |
| `suppress-fib-pending` | `sonic-device_metadata/DEVICE_METADATA/localhost/suppress-fib-pending` | `enumeration` |  | disabled | enabled, disabled | Enable [BGP](../../reference/glossary.md#term-bgp) suppress FIB pending feature. BGP will wait for route FIB installation before announcing routes |
| `async_swss_rec` | `sonic-device_metadata/DEVICE_METADATA/localhost/async_swss_rec` | `enumeration` |  | disabled | enabled, disabled | Enable asynchronous swss.rec recording in [orchagent](../../reference/glossary.md#term-orchagent). |
| `rack_mgmt_map` | `sonic-device_metadata/DEVICE_METADATA/localhost/rack_mgmt_map` | `string` |  |  | length 0..128 | Information of rack mgmt map. |
| `timezone` | `sonic-device_metadata/DEVICE_METADATA/localhost/timezone` | `stypes:timezone-name-type` |  | UTC | length 1..255 | The TZ database name to use for the system, such as 'Europe/Stockholm'. |
| `create_only_config_db_buffers` | `sonic-device_metadata/DEVICE_METADATA/localhost/create_only_config_db_buffers` | `boolean` |  |  |  | If this attribute exists and is equal to true - the buffers will be created according to the config_db configuration (for example BUFFER_QUEUE\|* table), otherwise the maximum available buffers (wh... |
| `supporting_bulk_counter_groups` | `sonic-device_metadata/DEVICE_METADATA/localhost/supporting_bulk_counter_groups` | `string` |  |  |  | This field contains a list of counter groups that support bulk operation. |
| `bgp_router_id` | `sonic-device_metadata/DEVICE_METADATA/localhost/bgp_router_id` | `inet:ipv4-address` |  |  |  | BGP Router identifier |
| `chassis_hostname` | `sonic-device_metadata/DEVICE_METADATA/localhost/chassis_hostname` | `stypes:hostname` |  |  |  | hostname of the chassis to which this linecard or supervisor belongs to |
| `slice_type` | `sonic-device_metadata/DEVICE_METADATA/localhost/slice_type` | `string` |  |  |  | Metadata tag for the device. |
| `location_type` | `sonic-device_metadata/DEVICE_METADATA/localhost/location_type` | `string` |  |  |  | Location type for the device. |
| `nexthop_group` | `sonic-device_metadata/DEVICE_METADATA/localhost/nexthop_group` | `enumeration` |  | disabled | enabled, disabled | Enable or disable Nexthop Group feature. This value only takes effect during boot time. |
| `ring_thread_enabled` | `sonic-device_metadata/DEVICE_METADATA/localhost/ring_thread_enabled` | `boolean` |  | false |  | Enable gRingMode of OrchDaemon, which would set up its ring thread to accelerate task execution. |
| `t2_group_asns` | `sonic-device_metadata/DEVICE_METADATA/localhost/t2_group_asns` | `inet:as-number` |  |  |  | ASNs inner same group |
| `anchor_route_source` | `sonic-device_metadata/DEVICE_METADATA/localhost/anchor_route_source` | `string` |  |  |  | Set source of anchor route |
| `orch_northbond_dash_zmq_enabled` | `sonic-device_metadata/DEVICE_METADATA/localhost/orch_northbond_dash_zmq_enabled` | `boolean` |  | true |  | Enable ZMQ feature on [APPL_DB](../../reference/glossary.md#term-appl_db) [DASH](../../reference/glossary.md#term-dash) tables. |
| `orch_northbond_route_zmq_enabled` | `sonic-device_metadata/DEVICE_METADATA/localhost/orch_northbond_route_zmq_enabled` | `boolean` |  | false |  | Enable ZMQ feature on [APPL_DB](../../reference/glossary.md#term-appl_db) ROUTE tables. |
| `syslog_with_osversion` | `sonic-device_metadata/DEVICE_METADATA/localhost/syslog_with_osversion` | `boolean` |  | false |  | Enable syslog with OS version feature. |
| `syslog_counter` | `sonic-device_metadata/DEVICE_METADATA/localhost/syslog_counter` | `boolean` |  | false |  | Enable syslog counter feature. |
| `has_sonic_dhcpv4_relay` | `sonic-device_metadata/DEVICE_METADATA/localhost/has_sonic_dhcpv4_relay` | `stypes:boolean_type` |  | false |  | This configuration controls the dhcpv4 relay process |
| `zebra_nexthop` | `sonic-device_metadata/DEVICE_METADATA/localhost/zebra_nexthop` | `enumeration` |  | enabled | enabled, disabled | Enable or disable next hop group support. This value only takes effect during boot time |
| `bmc_if_name` | `sonic-device_metadata/DEVICE_METADATA/bmc/bmc_if_name` | `string` |  |  | length 1..64 | BMC interface name |
| `bmc_if_addr` | `sonic-device_metadata/DEVICE_METADATA/bmc/bmc_if_addr` | `inet:ipv4-address` |  |  |  | BMC interface IP address |
| `bmc_addr` | `sonic-device_metadata/DEVICE_METADATA/bmc/bmc_addr` | `inet:ipv4-address` |  |  |  | BMC IP address |
| `bmc_net_mask` | `sonic-device_metadata/DEVICE_METADATA/bmc/bmc_net_mask` | `inet:ipv4-address` |  |  |  | BMC network mask |

## leafref / 依存

- なし（このモジュール内で直接 leafref を持つ leaf はない）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `DEVICE_METADATA`

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-banner`](sonic-banner.md)
- [`sonic-feature`](sonic-feature.md)
- [`sonic-fips`](sonic-fips.md)
- [`sonic-kdump`](sonic-kdump.md)
- [`sonic-lldp`](sonic-lldp.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`DEVICE_METADATA`](../config-db/device-metadata.md)

<!-- ref-triangle:end -->

<!-- ops-hint -->
## 運用ヒント

### 典型的なデプロイ位置

- デバイス全体のメタデータ。`DEVICE_METADATA|localhost` を init / hwsku 判定 / mgmt-framework が広範に参照する。

### よくある落とし穴

- `hwsku` / `platform` を runtime で書き換えると swss / [syncd](../../reference/glossary.md#term-syncd) の起動 SKU 判定が破綻する。`config save` 後の再起動で整合させる。

### 関連する config / show コマンド

```bash
sonic-db-cli CONFIG_DB hgetall 'DEVICE_METADATA|localhost'
show version
```
<!-- /ops-hint -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-device_metadata.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: bcd3ab0b11e4 -->
