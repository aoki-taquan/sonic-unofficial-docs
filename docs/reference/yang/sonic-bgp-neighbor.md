---
title: sonic-bgp-neighbor YANG
description: "sonic-bgp-neighbor YANG — sonic-net/sonic-buildimage src/sonic-yang-models/yang-models/sonic-bgp-neighbor.yang @ 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd"
area: reference
verification: code-verified
last_verified: 2026-05-09
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-bgp-neighbor.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [BGP_NEIGHBOR, BGP_NEIGHBOR_AF]
  cli: ["config bgp"]
  yang: [sonic-bgp-global, sonic-bgp-peergroup, sonic-route-map, sonic-port]
---

# sonic-bgp-neighbor YANG

## 概要

- module: `sonic-bgp-neighbor`
- namespace: `http://github.com/sonic-net/sonic-bgp-neighbor`
- revision: `2021-02-26`
- import: `ietf-inet-types`, `sonic-bgp-common`, `sonic-port`, `sonic-portchannel`, `sonic-bgp-global`, `sonic-bgp-peergroup`
- top container: `sonic-bgp-neighbor`

SONIC [BGP](../../reference/glossary.md#term-bgp) Neighbor[^1]

<!-- yang-mermaid -->
### データフロー (自動生成)

```mermaid
flowchart LR
  Y["sonic-bgp-neighbor"]
  C1[("CONFIG_DB<br/>BGP_NEIGHBOR")]
  Y --> C1
  D1["bgpcfgd"]
  C1 --> D1
```

!!! note "凡例"
    YANG モジュールから CONFIG_DB テーブル経由で subscribe する daemon/orch までを `docs/reference/config-db-orch-map.md` から機械生成したミニ図。詳細・例外は本ページ本文を参照。
<!-- /yang-mermaid -->

## 関連ページ

<!-- yang-xref -->

本 YANG モジュールに対応する CONFIG_DB / CLI / HLD / Topics への相互リンク。`inject_yang_xref.py` により自動生成されます。

### 対応 CONFIG_DB

- [`BGP_NEIGHBOR`](../config-db/bgp-neighbor.md)
- [`BGP_NEIGHBOR_AF`](../config-db/bgp-neighbor-af.md)

### 関連 CLI

- [`config bgp`](../cli/config-bgp.md)

### 関連 HLD

- [sonic-bgp-aggregate-address YANG](../../reference/yang/sonic-bgp-aggregate-address.md)
- [sonic-bgp-sentinel YANG](../../reference/yang/sonic-bgp-sentinel.md)

<!-- /yang-xref -->

## ツリー

```text
module: sonic-bgp-neighbor
  +--rw sonic-bgp-neighbor
     +--rw BGP_NEIGHBOR
     |  +--rw BGP_NEIGHBOR_TEMPLATE_LIST* [neighbor]
     |  |  +--rw neighbor        inet:ip-address
     |  |  +--rw asn?            uint32
     |  |  +--rw holdtime?       uint16
     |  |  +--rw keepalive?      uint16
     |  |  +--rw local_addr?     inet:ip-address
     |  |  +--rw name?           string
     |  |  +--rw nhopself?       uint8
     |  |  +--rw rrclient?       uint8
     |  |  +--rw admin_status?   stypes:admin_status
     |  +--rw BGP_NEIGHBOR_LIST* [vrf_name neighbor]
     |     +--rw vrf_name                              -> /bgpg:sonic-bgp-global/BGP_GLOBALS/BGP_GLOBALS_LIST/vrf_name
     |     +--rw neighbor                              union
     |     +--rw peer_group_name?                      -> /bgppg:sonic-bgp-peergroup/BGP_PEER_GROUP/BGP_PEER_GROUP_LIST[bgppg:vrf_name=current()/../vrf_name]/peer_group_name
     |     +--rw local_asn?                            uint32
     |     +--rw name?                                 string
     |     +--rw asn?                                  uint32
     |     +--rw peer_type?                            bgp_peer_type
     |     +--rw ebgp_multihop?                        boolean
     |     +--rw ebgp_multihop_ttl?                    uint8
     |     +--rw auth_password?                        string
     |     +--rw keepalive?                            uint16
     |     +--rw holdtime?                             uint16
     |     +--rw conn_retry?                           uint16
     |     +--rw min_adv_interval?                     uint16
     |     +--rw local_addr?                           union
     |     +--rw passive_mode?                         boolean
     |     +--rw capability_ext_nexthop?               boolean
     |     +--rw disable_ebgp_connected_route_check?   boolean
     |     +--rw enforce_first_as?                     boolean
     |     +--rw solo_peer?                            boolean
     |     +--rw ttl_security_hops?                    uint8
     |     +--rw bfd?                                  boolean
     |     +--rw bfd_check_ctrl_plane_failure?         boolean
     |     +--rw capability_dynamic?                   boolean
     |     +--rw dont_negotiate_capability?            boolean
     |     +--rw enforce_multihop?                     boolean
     |     +--rw override_capability?                  boolean
     |     +--rw peer_port?                            uint16
     |     +--rw shutdown_message?                     string
     |     +--rw strict_capability_match?              boolean
     |     +--rw admin_status?                         stypes:admin_status
     |     +--rw local_as_no_prepend?                  boolean
     |     +--rw local_as_replace_as?                  boolean
     +--rw BGP_NEIGHBOR_AF
        +--rw BGP_NEIGHBOR_AF_LIST* [vrf_name neighbor afi_safi]
           +--rw vrf_name                        -> /bgpg:sonic-bgp-global/BGP_GLOBALS/BGP_GLOBALS_LIST/vrf_name
           +--rw neighbor                        -> ../../../BGP_NEIGHBOR/BGP_NEIGHBOR_LIST[vrf_name=current()/../vrf_name]/neighbor
           +--rw afi_safi                        string
           +--rw admin_status?                   stypes:admin_status
           +--rw send_default_route?             boolean
           +--rw default_rmap?                   -> /rmap:sonic-route-map/ROUTE_MAP_SET/ROUTE_MAP_SET_LIST/name
           +--rw max_prefix_limit?               uint32
           +--rw max_prefix_warning_only?        boolean
           +--rw max_prefix_warning_threshold?   uint8
           +--rw max_prefix_restart_interval?    uint16
           +--rw route_map_in*                   -> /rmap:sonic-route-map/ROUTE_MAP_SET/ROUTE_MAP_SET_LIST/name
           +--rw route_map_out*                  -> /rmap:sonic-route-map/ROUTE_MAP_SET/ROUTE_MAP_SET_LIST/name
           +--rw soft_reconfiguration_in?        boolean
           +--rw unsuppress_map_name?            -> /rmap:sonic-route-map/ROUTE_MAP_SET/ROUTE_MAP_SET_LIST/name
           +--rw rrclient?                       boolean
           +--rw weight?                         uint16
           +--rw as_override?                    boolean
           +--rw send_community?                 bgp_community_type
           +--rw tx_add_paths?                   bgp_tx_add_paths_type
           +--rw unchanged_as_path?              boolean
           +--rw unchanged_med?                  boolean
           +--rw unchanged_nexthop?              boolean
           +--rw filter_list_in?                 -> /rpolsets:sonic-routing-policy-sets/AS_PATH_SET/AS_PATH_SET_LIST/name
           +--rw filter_list_out?                -> /rpolsets:sonic-routing-policy-sets/AS_PATH_SET/AS_PATH_SET_LIST/name
           +--rw nhself?                         boolean
           +--rw nexthop_self_force?             boolean
           +--rw prefix_list_in?                 -> /rpolsets:sonic-routing-policy-sets/PREFIX_SET/PREFIX_SET_LIST/name
           +--rw prefix_list_out?                -> /rpolsets:sonic-routing-policy-sets/PREFIX_SET/PREFIX_SET_LIST/name
           +--rw remove_private_as_enabled?      boolean
           +--rw replace_private_as?             boolean
           +--rw remove_private_as_all?          boolean
           +--rw allow_as_in?                    boolean
           +--rw allow_as_count?                 uint8
           +--rw allow_as_origin?                boolean
           +--rw cap_orf?                        sonic_bgp_orf
           +--rw route_server_client?            boolean
```

## leaf 一覧

| leaf | パス | 型 | 必須 | デフォルト | enum / 範囲 / leafref | 説明 |
|------|------|----|------|-----------|----------------------|------|
| `neighbor` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_TEMPLATE_LIST/neighbor` | `inet:ip-address` | yes |  |  | [BGP](../../reference/glossary.md#term-bgp) Neighbor address |
| `asn` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_TEMPLATE_LIST/asn` | `uint32` |  |  | range 0..4294967295 | Peer AS number. |
| `holdtime` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_TEMPLATE_LIST/holdtime` | `uint16` |  |  |  | [BGP](../../reference/glossary.md#term-bgp) hold time in seconds; session is reset if no keepalive is received within this period. |
| `keepalive` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_TEMPLATE_LIST/keepalive` | `uint16` |  |  |  | BGP keepalive interval in seconds. |
| `local_addr` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_TEMPLATE_LIST/local_addr` | `inet:ip-address` |  |  |  | Local source address to use for the BGP session. |
| `name` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_TEMPLATE_LIST/name` | `string` |  |  |  | Human-readable description text for this BGP peer. |
| `nhopself` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_TEMPLATE_LIST/nhopself` | `uint8` |  |  | range 0..1 | Set nexthop to self for routes advertised to this peer. |
| `rrclient` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_TEMPLATE_LIST/rrclient` | `uint8` |  |  | range 0..1 | Configure this neighbor as a route reflector client. |
| `admin_status` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_TEMPLATE_LIST/admin_status` | `stypes:admin_status` |  |  |  | Administrative status to enable or disable this BGP peer. |
| `vrf_name` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/vrf_name` | `leafref` | yes |  | /bgpg:sonic-bgp-global/bgpg:BGP_GLOBALS/bgpg:BGP_GLOBALS_LIST/bgpg:vrf_name | Network-instance/[VRF](../../reference/glossary.md#term-vrf) name |
| `neighbor` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/neighbor` | `union` | yes |  | union(inet:ip-address, leafref, leafref, string) | BGP Neighbor, it will be neighbor address or interface name |
| `peer_group_name` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/peer_group_name` | `leafref` |  |  | /bgppg:sonic-bgp-peergroup/bgppg:BGP_PEER_GROUP/bgppg:BGP_PEER_GROUP_LIST[bgppg:vrf_name=current()/../vrf_name]/bgppg:peer_group_name | Peer group name |
| `local_asn` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/local_asn` | `uint32` |  |  | range 1..4294967295 | Local AS number |
| `name` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/name` | `string` |  |  |  | Peer description |
| `asn` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/asn` | `uint32` |  |  | range 1..4294967295 | Peer AS number |
| `peer_type` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/peer_type` | `bgp_peer_type` |  |  |  | BGP peer type internal/external |
| `ebgp_multihop` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/ebgp_multihop` | `boolean` |  |  |  | Enable eBGP multihop to allow peering with non-directly-connected external neighbors. |
| `ebgp_multihop_ttl` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/ebgp_multihop_ttl` | `uint8` |  |  | range 1..255 | Maximum number of hops for eBGP multihop sessions. |
| `auth_password` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/auth_password` | `string` |  |  |  | MD5 authentication password for the BGP session. |
| `keepalive` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/keepalive` | `uint16` |  |  |  | BGP keepalive interval in seconds. |
| `holdtime` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/holdtime` | `uint16` |  |  |  | BGP hold time in seconds; session is reset if no keepalive is received within this period. |
| `conn_retry` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/conn_retry` | `uint16` |  |  | range 1..65535 | BGP connect retry timer in seconds. |
| `min_adv_interval` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/min_adv_interval` | `uint16` |  |  | range 0..600 | Minimum interval in seconds between sending BGP route updates to a peer. |
| `local_addr` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/local_addr` | `union` |  |  | union(inet:ip-address, leafref, leafref, leafref, string) | Local source address or interface name to use for connection. |
| `passive_mode` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/passive_mode` | `boolean` |  |  |  | Wait for the peer to initiate the BGP session instead of actively connecting. |
| `capability_ext_nexthop` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/capability_ext_nexthop` | `boolean` |  |  |  | Advertise extended nexthop capability to allow IPv4 prefixes over IPv6 nexthops. |
| `disable_ebgp_connected_route_check` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/disable_ebgp_connected_route_check` | `boolean` |  |  |  | Disable the check that an eBGP peer's address must be a connected route. |
| `enforce_first_as` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/enforce_first_as` | `boolean` |  |  |  | Require the first AS in the AS path to be the peer's AS number for eBGP sessions. |
| `solo_peer` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/solo_peer` | `boolean` |  |  |  | Place this peer in its own update group to prevent route sharing with other peers. |
| `ttl_security_hops` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/ttl_security_hops` | `uint8` |  |  | range 1..254 | Maximum number of hops expected for the BGP TTL security mechanism (GTSM). |
| `bfd` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/bfd` | `boolean` |  |  |  | Enable Bidirectional Forwarding Detection ([BFD](../../reference/glossary.md#term-bfd)) for rapid link failure detection on this peer. |
| `bfd_check_ctrl_plane_failure` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/bfd_check_ctrl_plane_failure` | `boolean` |  |  |  | Trigger BGP session reset when a [BFD](../../reference/glossary.md#term-bfd) control plane failure is detected. |
| `capability_dynamic` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/capability_dynamic` | `boolean` |  |  |  | Advertise dynamic capability |
| `dont_negotiate_capability` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/dont_negotiate_capability` | `boolean` |  |  |  | Do not perform capability negotiation |
| `enforce_multihop` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/enforce_multihop` | `boolean` |  |  |  | Enforce EBGP neighbors perform multihop |
| `override_capability` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/override_capability` | `boolean` |  |  |  | Override capability negotiation result |
| `peer_port` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/peer_port` | `uint16` |  |  |  | Peer port number |
| `shutdown_message` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/shutdown_message` | `string` |  |  | length 1..127 | Human-readable message sent in the BGP NOTIFICATION when administratively shutting down the peer. |
| `strict_capability_match` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/strict_capability_match` | `boolean` |  |  |  | Require exact match of capabilities; tear down session if capabilities do not match. |
| `admin_status` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/admin_status` | `stypes:admin_status` |  |  |  | Administrative status to enable or disable this BGP peer. |
| `local_as_no_prepend` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/local_as_no_prepend` | `boolean` |  |  |  | Do not prepend the local AS number to updates received from eBGP peers. |
| `local_as_replace_as` | `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/local_as_replace_as` | `boolean` |  |  |  | Replace the real AS number with the local AS number in outbound updates. |
| `vrf_name` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/vrf_name` | `leafref` | yes |  | /bgpg:sonic-bgp-global/bgpg:BGP_GLOBALS/bgpg:BGP_GLOBALS_LIST/bgpg:vrf_name | Network-instance/[VRF](../../reference/glossary.md#term-vrf) name |
| `neighbor` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/neighbor` | `leafref` | yes |  | ../../../BGP_NEIGHBOR/BGP_NEIGHBOR_LIST[vrf_name=current()/../vrf_name]/neighbor | BGP Neighbor, it will be neighbor address or interface name |
| `afi_safi` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/afi_safi` | `string` |  |  |  | Address family |
| `admin_status` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/admin_status` | `stypes:admin_status` |  |  |  | Indicates address family active/inactive status |
| `send_default_route` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/send_default_route` | `boolean` |  |  |  | Originate a default route to this neighbor. |
| `default_rmap` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/default_rmap` | `leafref` |  |  | /rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name | Route map applied when originating a default route to this neighbor. |
| `max_prefix_limit` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/max_prefix_limit` | `uint32` |  |  |  | Maximum number of prefixes accepted from this neighbor before taking action. |
| `max_prefix_warning_only` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/max_prefix_warning_only` | `boolean` |  |  |  | Only log a warning instead of tearing down the session when the maximum prefix limit is exceeded. |
| `max_prefix_warning_threshold` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/max_prefix_warning_threshold` | `uint8` |  |  | range 1..100 | Percentage of the maximum prefix limit at which a warning is generated. |
| `max_prefix_restart_interval` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/max_prefix_restart_interval` | `uint16` |  |  | range 1..65535 | Time in seconds to wait before re-establishing the session after a max-prefix limit shutdown. |
| `route_map_in` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/route_map_in` | `leafref` |  |  | /rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name | Route-map filter for incoming routes |
| `route_map_out` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/route_map_out` | `leafref` |  |  | /rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name | Route-map filter for outgoing routes |
| `soft_reconfiguration_in` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/soft_reconfiguration_in` | `boolean` |  |  |  | Enable storing of inbound updates to allow route refresh without resetting the session. |
| `unsuppress_map_name` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/unsuppress_map_name` | `leafref` |  |  | /rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name | Route map used to selectively unsuppress suppressed routes to this neighbor. |
| `rrclient` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/rrclient` | `boolean` |  |  |  | Configure this neighbor as a route reflector client. |
| `weight` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/weight` | `uint16` |  |  | range 0..65535 | Default weight assigned to routes received from this neighbor for best-path selection. |
| `as_override` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/as_override` | `boolean` |  |  |  | Replace the peer AS number with the local AS in outbound updates to prevent loops in dual-homed networks. |
| `send_community` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/send_community` | `bgp_community_type` |  |  |  | Send Community attribute to this neighbor |
| `tx_add_paths` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/tx_add_paths` | `bgp_tx_add_paths_type` |  |  |  | Advertise all paths or best path per AS using add path |
| `unchanged_as_path` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/unchanged_as_path` | `boolean` |  |  |  | Propagate the AS path attribute unchanged to this neighbor. |
| `unchanged_med` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/unchanged_med` | `boolean` |  |  |  | Propagate the MED attribute unchanged to this neighbor. |
| `unchanged_nexthop` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/unchanged_nexthop` | `boolean` |  |  |  | Propagate the nexthop attribute unchanged to this neighbor. |
| `filter_list_in` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/filter_list_in` | `leafref` |  |  | /rpolsets:sonic-routing-policy-sets/rpolsets:AS_PATH_SET/rpolsets:AS_PATH_SET_LIST/rpolsets:name | AS-path access list name for filtering inbound routes. |
| `filter_list_out` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/filter_list_out` | `leafref` |  |  | /rpolsets:sonic-routing-policy-sets/rpolsets:AS_PATH_SET/rpolsets:AS_PATH_SET_LIST/rpolsets:name | AS-path access list name for filtering outbound routes. |
| `nhself` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/nhself` | `boolean` |  |  |  | Nexthop is self, no nexthop calculation |
| `nexthop_self_force` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/nexthop_self_force` | `boolean` |  |  |  | Force nexthop to be self for reflected routes |
| `prefix_list_in` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/prefix_list_in` | `leafref` |  |  | /rpolsets:sonic-routing-policy-sets/rpolsets:PREFIX_SET/rpolsets:PREFIX_SET_LIST/rpolsets:name | Prefix list name for filtering inbound routes. |
| `prefix_list_out` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/prefix_list_out` | `leafref` |  |  | /rpolsets:sonic-routing-policy-sets/rpolsets:PREFIX_SET/rpolsets:PREFIX_SET_LIST/rpolsets:name | Prefix list name for filtering outbound routes. |
| `remove_private_as_enabled` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/remove_private_as_enabled` | `boolean` |  |  |  | Remove private AS numbers from the AS path in outbound updates. |
| `replace_private_as` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/replace_private_as` | `boolean` |  |  |  | Replace private AS numbers with the local AS number in outbound updates. |
| `remove_private_as_all` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/remove_private_as_all` | `boolean` |  |  |  | Remove all private AS numbers (including in the middle of the path) from outbound updates. |
| `allow_as_in` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/allow_as_in` | `boolean` |  |  |  | Accept inbound routes even when the local AS number appears in the AS path. |
| `allow_as_count` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/allow_as_count` | `uint8` |  |  |  | Maximum number of times the local AS number may appear in a received AS path. |
| `allow_as_origin` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/allow_as_origin` | `boolean` |  |  |  | Accept routes that originated from the local AS. |
| `cap_orf` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/cap_orf` | `sonic_bgp_orf` |  |  |  | Outbound Route Filtering (ORF) prefix-list capability to negotiate with this neighbor. |
| `route_server_client` | `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/route_server_client` | `boolean` |  |  |  | Configure this neighbor as a route server client, disabling attribute modification. |

## leafref / 依存

- `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/vrf_name` → `/bgpg:sonic-bgp-global/bgpg:BGP_GLOBALS/bgpg:BGP_GLOBALS_LIST/bgpg:vrf_name`
- `sonic-bgp-neighbor/BGP_NEIGHBOR/BGP_NEIGHBOR_LIST/peer_group_name` → `/bgppg:sonic-bgp-peergroup/bgppg:BGP_PEER_GROUP/bgppg:BGP_PEER_GROUP_LIST[bgppg:vrf_name=current()/../vrf_name]/bgppg:peer_group_name`
- `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/vrf_name` → `/bgpg:sonic-bgp-global/bgpg:BGP_GLOBALS/bgpg:BGP_GLOBALS_LIST/bgpg:vrf_name`
- `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/neighbor` → `../../../BGP_NEIGHBOR/BGP_NEIGHBOR_LIST[vrf_name=current()/../vrf_name]/neighbor`
- `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/default_rmap` → `/rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name`
- `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/route_map_in` → `/rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name`
- `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/route_map_out` → `/rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name`
- `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/unsuppress_map_name` → `/rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name`
- `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/filter_list_in` → `/rpolsets:sonic-routing-policy-sets/rpolsets:AS_PATH_SET/rpolsets:AS_PATH_SET_LIST/rpolsets:name`
- `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/filter_list_out` → `/rpolsets:sonic-routing-policy-sets/rpolsets:AS_PATH_SET/rpolsets:AS_PATH_SET_LIST/rpolsets:name`
- `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/prefix_list_in` → `/rpolsets:sonic-routing-policy-sets/rpolsets:PREFIX_SET/rpolsets:PREFIX_SET_LIST/rpolsets:name`
- `sonic-bgp-neighbor/BGP_NEIGHBOR_AF/BGP_NEIGHBOR_AF_LIST/prefix_list_out` → `/rpolsets:sonic-routing-policy-sets/rpolsets:PREFIX_SET/rpolsets:PREFIX_SET_LIST/rpolsets:name`

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- [CONFIG_DB](../../reference/glossary.md#term-config_db): `BGP_NEIGHBOR`
- [CONFIG_DB](../../reference/glossary.md#term-config_db): `BGP_NEIGHBOR_AF`
- CLI: `config bgp`

<!-- yang-sibling -->
### 関連 YANG モジュール

意味的に関連する SONiC YANG モジュール (slug prefix / curated group / frontmatter `related.yang` から自動抽出):

- [`sonic-bgp-global`](sonic-bgp-global.md)
- [`sonic-bgp-peergroup`](sonic-bgp-peergroup.md)
- [`sonic-route-map`](sonic-route-map.md)
- [`sonic-port`](sonic-port.md)
- [`sonic-bgp-aggregate-address`](sonic-bgp-aggregate-address.md)
<!-- /yang-sibling -->

<!-- ref-triangle:start -->

## 関連リファレンス

- [CONFIG_DB](../../reference/glossary.md#term-config_db): [`BGP_NEIGHBOR`](../config-db/bgp-neighbor.md) / [`BGP_NEIGHBOR_AF`](../config-db/bgp-neighbor-af.md)
- CLI: [`config bgp`](../cli/config-bgp.md)

<!-- ref-triangle:end -->

<!-- ops-hint -->
## 運用ヒント

### 典型的なデプロイ位置

- BGP neighbor の静的設定。`BGP_NEIGHBOR|<addr>` を [bgpcfgd](../../reference/glossary.md#term-bgpcfgd) が [FRR](../../reference/glossary.md#term-frr) neighbor stanza に展開。

### よくある落とし穴

- `peer_group_name` leafref 解決失敗で commit がサイレントに無視されるケースあり。先に peer-group を定義すること。

### 関連する config / show コマンド

```bash
sonic-db-cli CONFIG_DB keys 'BGP_NEIGHBOR|*'
show ip bgp summary
```
<!-- /ops-hint -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-bgp-neighbor.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`

<!-- glossary-links-injected: 26ca9e81c971 -->
