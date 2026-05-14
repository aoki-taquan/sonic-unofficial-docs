# Phase 10 Named Identifier Extraction — Summary

Date: 2026-05-14

## 対象 4 ページ

1. `docs/reference/config-db/device-metadata.md` (tier_high)
2. `docs/reference/config-db/acl-rule.md` (tier_high)
3. `docs/reference/config-db/acl-table.md` (tier_mid)
4. `docs/reference/config-db/wred-profile.md` (tier_mid)

## 確認 row 数

| ページ | value-behavior row 数 | derivation row 数 | 合計 |
|--------|----------------------|-------------------|------|
| device-metadata | ~50 (type 35値 + 他 enum) | ~20 | ~70 |
| acl-rule | 25 | — | 25 |
| acl-table | 18 | — | 18 |
| wred-profile | 16 | — | 16 |
| **合計** | | | **~129** |

## 識別子追加 row 数: 約 25 行

## 抽出識別子サンプル (before → after の主要差分)

### 1. device-metadata.md — `LeafRouter` type 行
**before**: `下流 ToR ネイバーとの uplink/downlink バッファ・QoS 設定`
**after**: `uplink ポートへ \`dscp_to_tc_map: "AZURE_UPLINK"\` / \`tc_to_queue_map: "AZURE_UPLINK"\` 適用; ダウンリンク \`PORT_DOWNLINK\` / アップリンク \`PORT_UPLINK\` リストで分岐`

### 2. device-metadata.md — `UpstreamLC` subtype 行
**before**: `voq_chassis/policies.conf.j2:19,54 で fallback community を deny する route-map 設定`
**after**: `route-map \`FROM_VOQ_CHASSIS_V4_PEER\` / \`FROM_VOQ_CHASSIS_V6_PEER\` の deny 節を挿入し \`DEVICE_INTERNAL_FALLBACK_COMMUNITY\` を deny`

### 3. acl-rule.md — PACKET_ACTION lookup 行
**before**: `実装 lookup: \`aclPacketActionLookup\` (aclorch.cpp:145-147)`
**after**: `実装 lookup map: \`aclPacketActionLookup\` (aclorch.cpp:143)。マクロ定数: \`PACKET_ACTION_FORWARD\` / \`PACKET_ACTION_DROP\` / \`PACKET_ACTION_COPY\` / \`PACKET_ACTION_REDIRECT\` / \`PACKET_ACTION_DO_NOT_NAT\` / \`PACKET_ACTION_DISABLE_TRIM\` (aclorch.h:83-88)`

### 4. acl-table.md — type 値テーブル
**before**: `実装定義 (acltable.h:26-42): 14 種以上`
**after**: `実装定義マクロ (acltable.h:26-42): \`TABLE_TYPE_L3\` / \`TABLE_TYPE_L3V6\` / ... / \`TABLE_TYPE_UNDERLAY_SET_DSCPV6\` (全 16 定数を列挙)`

### 5. device-metadata.md — 複合条件 #3
**before**: `BGP peer-group に SELECTIVE_ROUTE_DOWNLOAD table-map 適用`
**after**: `BGP peer-group に \`table-map SELECTIVE_ROUTE_DOWNLOAD_V4\` / \`SELECTIVE_ROUTE_DOWNLOAD_V6\` 適用`

## 追加した主要識別子一覧

- `AZURE_UPLINK`, `PORT_DOWNLINK`, `PORT_UPLINK` (qos_config.j2)
- `FROM_VOQ_CHASSIS_V4_PEER`, `FROM_VOQ_CHASSIS_V6_PEER` (voq_chassis/policies.conf.j2)
- `FROM_BGP_INTERNAL_PEER_V4`, `FROM_BGP_INTERNAL_PEER_V6` (internal/policies.conf.j2)
- `DEVICE_INTERNAL_FALLBACK_COMMUNITY` (voq_chassis/policies.conf.j2)
- `SELECTIVE_ROUTE_DOWNLOAD_V4`, `SELECTIVE_ROUTE_DOWNLOAD_V6` (peer-group.conf.j2)
- `CHASSIS_CARD_VOQ ('VoQ')`, `BACKEND_ASIC_SUB_ROLE ('BackEnd')`, `FABRIC_ASIC_SUB_ROLE ('Fabric')` (minigraph.py)
- `disagg_t2`, `disagg_rh` (bgpd.main.conf.j2 template-local vars)
- `filter_acl_table_for_backend()`, `backend_device_types` (minigraph.py/ipinip.json.j2)
- `STATE_BFD_SOFTWARE_SESSION_TABLE_NAME` (bgpcfgd/main.py)
- `PACKET_ACTION_FORWARD/DROP/COPY/REDIRECT/DO_NOT_NAT/DISABLE_TRIM` (aclorch.h)
- `aclPacketActionLookup`, `aclIpTypeLookup` (aclorch.cpp)
- `IP_TYPE_ANY/IP/NON_IP/IPv4ANY/NON_IPv4/IPv6ANY/NON_IPv6/ARP/ARP_REQUEST/ARP_REPLY` (aclorch.h)
- `TABLE_TYPE_L3/L3V6/L3V4V6/MIRROR/MIRRORV6/MIRROR_DSCP/PFCWD/CTRLPLANE/MCLAG/MUX/DROP/MARK_META/MARK_META_V6/EGR_SET_DSCP/UNDERLAY_SET_DSCP/UNDERLAY_SET_DSCPV6` (acltable.h)
- `STAGE_INGRESS`, `STAGE_EGRESS` (acltable.h)
- `aclStageLookUp` (aclorch.cpp)
- `ecn_field_name = "ecn"`, `wred_green_enable_field_name`, `wred_yellow_enable_field_name`, `wred_red_enable_field_name` (qosorch.h)
- `ecn_map` (qosorch.cpp)
