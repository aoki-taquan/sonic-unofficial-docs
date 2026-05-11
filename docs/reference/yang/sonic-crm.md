---
title: sonic-crm YANG
area: reference
verification: code-verified
last_verified: 2026-05-11
sources:
  - repo: sonic-net/sonic-buildimage
    path: src/sonic-yang-models/yang-models/sonic-crm.yang
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: [CRM]
  cli: ["crm config", "crm show"]
  yang: [sonic-device_metadata]
---

# sonic-crm YANG

## 概要

- module: `sonic-crm`
- namespace: `http://github.com/sonic-net/sonic-crm`
- revision: `2020-04-10`
- import: `sonic-types`, `sonic-device_metadata`
- top container: `sonic-crm`

Critical Resource Monitoring (CRM) 設定の YANG モデル[^1]。ASIC 上の各種ハードウェアリソース（ACL カウンタ/エントリ、route、neighbor、nexthop、FDB、NAT、MPLS、SRv6、DASH オブジェクト 等）について `threshold_type` / `high_threshold` / `low_threshold` の 3 リーフをひとセットとして繰り返し定義する大型モジュール。

## ツリー（概略）

```
module: sonic-crm
  +--rw sonic-crm
     +--rw CRM
        +--rw Config
           +--rw polling_interval?                              uint32
           # 各リソースクラスごとに以下 3 リーフ
           +--rw <resource>_threshold_type?                     stypes:crm_threshold_type (PERCENTAGE|USED|FREE)
           +--rw <resource>_high_threshold?                     uint16
           +--rw <resource>_low_threshold?                      uint16
```

すべての `_high_threshold` は対応する `_low_threshold` より大きいことが must 制約で要求される。`PERCENTAGE` 系では値 < 100 制約も付く。

## リソースクラス一覧

CRM が監視する論理リソース（`<class>_threshold_type` / `_high_threshold` / `_low_threshold` の 3 リーフが定義されているもの）:

### ACL 系

`acl_counter`, `acl_entry`, `acl_group`, `acl_table`

### FDB / Neighbor / Nexthop / Route 系

`fdb_entry`, `ipv4_neighbor`, `ipv6_neighbor`, `ipv4_nexthop`, `ipv6_nexthop`, `ipv4_route`, `ipv6_route`, `nexthop_group`, `nexthop_group_member`

### NAT / Multicast

`dnat_entry`, `snat_entry`, `ipmc_entry`

### MPLS / SRv6

`mpls_inseg`, `mpls_nexthop`, `srv6_my_sid_entry`, `srv6_nexthop`

### DASH (SmartSwitch)

`dash_vnet`, `dash_eni`, `dash_eni_ether_address_map`,
`dash_ipv4_inbound_routing`, `dash_ipv6_inbound_routing`,
`dash_ipv4_outbound_routing`, `dash_ipv6_outbound_routing`,
`dash_ipv4_pa_validation`, `dash_ipv6_pa_validation`,
`dash_ipv4_outbound_ca_to_pa`, `dash_ipv6_outbound_ca_to_pa`,
`dash_ipv4_acl_group`, `dash_ipv6_acl_group`,
`dash_ipv4_acl_rule`, `dash_ipv6_acl_rule`

## leaf（特殊なもの）

| leaf | パス | 型 | 必須 | デフォルト | 説明 |
|------|------|----|------|-----------|------|
| `polling_interval` | `sonic-crm/CRM/Config/polling_interval` | `uint32` |  |  | CRM ポーリング間隔（秒） |
| `<resource>_threshold_type` | `sonic-crm/CRM/Config/<resource>_threshold_type` | `stypes:crm_threshold_type` |  |  | 閾値タイプ（PERCENTAGE / USED / FREE） |
| `<resource>_high_threshold` | `sonic-crm/CRM/Config/<resource>_high_threshold` | `uint16` |  |  | THRESHOLD_EXCEEDED アラートを起こす上限値 |
| `<resource>_low_threshold` | `sonic-crm/CRM/Config/<resource>_low_threshold` | `uint16` |  |  | THRESHOLD_CLEAR アラートを起こす下限値 |

完全な leaf 一覧は YANG ソース（37 リソースクラス × 3 + `polling_interval` ＝ 約 112 リーフ）を直接参照のこと。

## must / 制約

- `<resource>_high_threshold > <resource>_low_threshold` を全リソースに対して要求
- `threshold_type = PERCENTAGE` のとき `high_threshold < 100` かつ `low_threshold < 100`

## leafref / 依存

- なし（`sonic-device_metadata` を import するが leafref は使用していない）

## augment / deviation

- なし

## 関連 CONFIG_DB / CLI

- CONFIG_DB: `CRM|Config`
- CLI: `crm config thresholds <type> <resource> ...`, `crm show resources`

<!-- ref-triangle:start -->

## 関連リファレンス

- CONFIG_DB: [`CRM`](../config-db/crm.md)
- CLI: `crm config` / `crm show`

<!-- ref-triangle:end -->

## 引用元

[^1]: `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-crm.yang` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
