---
title: SONiC-DASH 運用（CLI / 設定例 / トラブルシュート）
description: SONiC-DASH の CLI コマンド（show dash eni / vnet / route-types / qos、sonic-clear dash）、APP_DB 投入による設定例（VNet-VNet
  / Service Tunnel / Private Link）、トラブルシュート手順（ENI が active にならない、ACL が想定通り効かない、メータリングが進まない、DPU
  切り離し）をまとめる。
area: overlay
verification: code-verified
last_verified: 2026-05-26
page_kind: split-child
sources:
- repo: sonic-net/SONiC
  path: doc/dash/dash-sonic-hld.md
  ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06
related:
  config_db:
  - DASH_VNET
  - DASH_ENI
  - DASH_ROUTE
  - DASH_ROUTE_GROUP
  - DASH_VNET_MAPPING_TABLE
  - DASH_ACL_GROUP
  - DASH_ACL_RULE
  - DASH_METER_POLICY
  - DASH_METER
  - DASH_TUNNEL
  cli:
  - show dash eni
  - show dash vnet
  - show dash route-types
  - show dash qos
  - sonic-clear dash
  yang:
  - sonic-dash
---

# SONiC-DASH 運用

このページは [SONiC-DASH 概観](sonic-dash-hld.md) の派生ページで、**CLI / 設定例 / トラブルシュート** に絞る。概念は [sonic-dash-hld-concepts.md](sonic-dash-hld-concepts.md)、内部実装は [sonic-dash-hld-internals.md](sonic-dash-hld-internals.md) を参照。

## 1. CLI

[HLD](../reference/glossary.md#term-hld) §3.4 で規定される CLI[^1]:

```bash
# 表示系
show dash eni <eni>
show dash eni <eni> routes all
show dash eni <eni> acls stage <ingress/egress/all>
show dash vnet <vnet>
show dash vnet <vnet> mappings
show dash vnet brief
show dash route-types
show dash qos

# クリア系
sonic-clear dash all
sonic-clear dash eni <eni>
sonic-clear dash vnet <vnet>
```

[DASH](../reference/glossary.md#term-dash) のオブジェクトは **コントローラ ([gNMI](../reference/glossary.md#term-gnmi)) から投入されるのが基本** であり、CLI は `show`/`clear` のみで `config dash` 系の作成 CLI は HLD 範囲外である[^1]。手動投入する場合は `redis-cli -n 0` で APP_DB を直接編集するか、`sonic-cfggen` の DASH 拡張を使う（ベンダー実装依存）。

## 2. DEVICE_METADATA（DPU 起動の前提）

DASH を有効化するには [CONFIG_DB](../reference/glossary.md#term-config_db) の `DEVICE_METADATA` で `switch_type=dpu` / `subtype=SmartSwitch` を指定する[^1]:

```json
"DEVICE_METADATA": {
    "localhost": {
        "type": "SmartSwitchDPU",
        "subtype": "SmartSwitch",
        "switch_type": "dpu",
        "sub_role": "None"
    }
}
```

この指定により SWSS Lite が起動し、[teamd](../reference/glossary.md#term-teamd-teamsyncd-teammgrd) / nat / sflow 等が disabled、`dashorch` が enable される。詳細 container 一覧は [sonic-dash-hld-internals.md §6](sonic-dash-hld-internals.md#6-swss-lite-と-underlay) を参照。

## 3. 設定例

### 3.1 VNet ↔ VNet 基本（HLD §3.6.1）

[ENI](../reference/glossary.md#term-eni) 1 つに対し outbound route と CA-PA mapping、inbound route rule を投入する最小構成[^1]:

```json
[
    { "DASH_VNET_TABLE:Vnet1": {
        "vni": "45654", "guid": "559c6ce8-26ab-4193-b946-ccc6e8f930b2", "version": "1"
      }, "OP": "SET" },

    { "DASH_ENI_TABLE:F4939FEFC47E": {
        "eni_id": "497f23d7-f0ac-4c99-a98f-59b470e8c7bd",
        "mac_address": "F4-93-9F-EF-C4-7E",
        "underlay_ip": "25.1.1.1",
        "admin_state": "enabled",
        "vnet": "Vnet1",
        "v4_meter_policy_id": "245bea34-1000-0000-0000-0000082764ac"
      }, "OP": "SET" },

    { "DASH_ROUTING_TYPE_TABLE:vnet":
        { "name": "action1", "action_type": "maprouting" }, "OP": "SET" },
    { "DASH_ROUTING_TYPE_TABLE:vnet_encap":
        { "name": "action1", "action_type": "staticencap", "encap_type": "vxlan" }, "OP": "SET" },

    { "DASH_ENI_ROUTE_TABLE:F4939FEFC47E":
        { "group_id": "group_id_1" }, "OP": "SET" },
    { "DASH_ROUTE_GROUP_TABLE:group_id_1":
        { "guid": "group_id_1-test", "version": "1" }, "OP": "SET" },

    { "DASH_ROUTE_TABLE:group_id_1:10.1.0.0/16":
        { "action_type": "vnet", "vnet": "Vnet1" }, "OP": "SET" },
    { "DASH_ROUTE_TABLE:group_id_1:30.0.0.0/16":
        { "action_type": "direct" }, "OP": "SET" },
    { "DASH_ROUTE_TABLE:group_id_1:10.2.5.0/24":
        { "action_type": "drop" }, "OP": "SET" },

    { "DASH_VNET_MAPPING_TABLE:Vnet1:10.1.1.1":
        { "routing_type": "vnet_encap",
          "underlay_ip": "101.1.2.4",
          "mac_address": "C9-22-83-99-22-A2",
          "metering_class": "1001" }, "OP": "SET" },

    { "DASH_ROUTE_RULE_TABLE:F4939FEFC47E:45654:101.1.2.3/32":
        { "action_type": "decap", "priority": 1, "protocol": "0",
          "vnet": "Vnet1", "pa_validation": true }, "OP": "SET" }
]
```

`admin_state: enabled` は **全 ENI 設定が揃ったあと最後に投入** すること（HLD §1.6 #9: admin_state が up でないと ENI へのパケットは drop）[^1]。

### 3.2 Service Tunnel（HLD §3.6.2）

storage 等への ST 経路。`servicetunnel` routing_type で 4to6 + nvgre encap を行う。`underlay_sip` / `underlay_dip` が省略された場合の挙動が rule ごとに異なる点に注意[^1]:

```json
{ "DASH_ROUTING_TYPE_TABLE:servicetunnel": [
    { "name": "action1", "action_type": "4to6" },
    { "name": "action2", "action_type": "staticencap",
      "encap_type": "nvgre", "vni": "100" }
  ], "OP": "SET" }

{ "DASH_ROUTE_TABLE:group_id_2:50.1.2.0/24": {
    "action_type": "servicetunnel",
    "overlay_sip_prefix": "fd00:108:0:d204:0:200::0/96",
    "overlay_dip_prefix": "2603:10e1:100:2::0/96",
    "underlay_sip": "40.1.2.1",
    "metering_class": "50000"
  }, "OP": "SET" }
```

### 3.3 Private Link（HLD §3.6.3）

ENI 側に `pl_sip_encoding` / `pl_underlay_sip` を投入し、`DASH_VNET_MAPPING_TABLE` で `routing_type=privatelink` の mapping を作る[^1]:

```json
{ "DASH_ENI_TABLE:F4939FEFC47E": {
    "eni_id": "497f23d7-f0ac-4c99-a98f-59b470e8c7bd",
    "mac_address": "F4-93-9F-EF-C4-7E",
    "underlay_ip": "25.1.1.1",
    "admin_state": "enabled",
    "vnet": "Vnet1",
    "pl_underlay_sip": "55.1.2.3",
    "pl_sip_encoding": "::cb3a:16e5:ff71:0:0/::ffff:ffff:ffff:0:0"
  }, "OP": "SET" }

{ "DASH_VNET_MAPPING_TABLE:Vnet1:10.1.0.8": {
    "routing_type": "privatelink",
    "mac_address": "F9-22-83-99-22-A2",
    "underlay_ip": "50.1.2.3",
    "overlay_sip_prefix": "fd41:108:20:abc:abc::0/ffff:ffff:ffff:ffff:ffff:ffff::",
    "overlay_dip_prefix": "2603:10e1:100:2::3401:203/ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff",
    "metering_class_or": "0x06"
  }, "OP": "SET" }
```

PL IPv6 transposition の詳細フォーマット（field_value/full_mask）は HLD §3.6.3.2 を参照[^1]。

### 3.4 メータリング

per-policy メータリングを ENI に bind する例[^1]:

```json
{ "DASH_METER_POLICY:245bea34-1000-0000-0000-0000082764ac":
    { "ip_version": "ipv4" }, "OP": "SET" }
{ "DASH_METER_RULE:245bea34-1000-0000-0000-0000082764ac:1":
    { "priority": "0", "ip_prefix": "40.0.0.1/32",
      "metering_class": "20000" }, "OP": "SET" }
{ "DASH_METER:497f23d7-f0ac-4c99-a98f-59b470e8c7bd:20000":
    { "metadata": "ROUTE_DIRECT_POLICY_40000001" }, "OP": "SET" }
```

route table 側で `metering_policy_en: true` を立てると policy lookup が enable され、ヒットすれば policy の class が優先される（policy → route → mapping、ただし mapping `override` で逆転）[^1]。

## 4. 状態確認

### 4.1 redis から DASH オブジェクトを直接見る

```bash
# APP_DB (db 0) の DASH エントリ一覧
redis-cli -n 0 keys 'DASH_*'

# 特定 ENI
redis-cli -n 0 hgetall 'DASH_ENI_TABLE:F4939FEFC47E'

# CA-PA mapping
redis-cli -n 0 keys 'DASH_VNET_MAPPING_TABLE:Vnet1:*'

# STATE_DB (db 6) で programming 状態を確認
redis-cli -n 6 keys 'DASH_*_TABLE_STATE'
redis-cli -n 6 hgetall 'DASH_ENI_TABLE_STATE:F4939FEFC47E'

# protobuf 化されているケース
redis-cli -n 0 hget 'DASH_VNET_TABLE:Vnet1' pb | xxd | head
```

### 4.2 swss / syncd 内部

```bash
docker exec swss orchagent_restart_check 2>&1 | tail
docker exec swss supervisorctl status orchagent
docker logs swss 2>&1 | grep -iE 'dashorch|DashVnet|DashAcl|DashMeter' | tail -50

# ASIC_DB（syncd 側）に SAI DASH オブジェクトが書かれているか
redis-cli -n 1 keys 'ASIC_STATE:SAI_OBJECT_TYPE_ENI:*'
redis-cli -n 1 keys 'ASIC_STATE:SAI_OBJECT_TYPE_OUTBOUND_*'
```

### 4.3 メータカウンタ

`DASH_METER:{eni}:{metering_class_id}` の `tx_counter` / `rx_counter` は read-only。SDN コントローラから gNMI `get` で `(eni, *)` で取得するのが正式手順だが、redis から直接覗ける[^1]:

```bash
redis-cli -n 0 hgetall 'DASH_METER:497f23d7-f0ac-4c99-a98f-59b470e8c7bd:1001'
```

## 5. トラブルシュート

### 5.1 ENI を作ったがトラフィックが流れない

1. `DASH_APPLIANCE_TABLE` の `sip` / `vm_vni` が VM 側と一致しているか確認（vm_vni のミスマッチで direction lookup が外れる）
2. `DASH_ENI_TABLE.admin_state = enabled` か（HLD §1.6 #9: disabled だと完全 drop）
3. `DASH_ENI_TABLE.vnet` が指す `DASH_VNET_TABLE` が先に存在しているか
4. `DASH_ENI_ROUTE_TABLE.group_id` が指す `DASH_ROUTE_GROUP_TABLE` が存在し、その中に該当 prefix の `DASH_ROUTE_TABLE` があるか
5. [STATE_DB](../reference/glossary.md#term-state_db) に `DASH_*_TABLE_STATE` でエラーが書かれていないか

### 5.2 ACL が想定順序で効かない

- DASH [ACL](../reference/glossary.md#term-acl) は **5 stage** あり、より restrictive な結果が選ばれる（HLD §2.1: outbound は 3 stage を combine、most restrictive）。stage 設計ミスがないか確認
- ACL group は **ENI に bind 済みの間は rule 編集不可** で、tag 展開以外は新 group を作って再 bind する必要がある（[sonic-swss#3069](https://github.com/sonic-net/sonic-swss/issues/3069) — 順序依存性バグも参照）[^1]
- tag 関連はそもそも [SAI](../reference/glossary.md#term-sai) 実装が capability `>0` を返している必要がある（戻り 0 は no-tag support）

### 5.3 メータカウンタが進まない

- `DASH_ENI_TABLE.v4_meter_policy_id` / `v6_meter_policy_id` が `DASH_METER_POLICY` を指しているか
- ヒットしている route / mapping エントリに `metering_class_or` 等が設定されているか
- 優先順位: **policy → route → mapping** だが mapping `override` が立つと逆転する。意図と違う bucket に計上されていないか HLD §2.4 表で確認[^1]

### 5.4 inbound パケットが decap されない

- `DASH_ROUTE_RULE_TABLE:{eni}:{vni}:{prefix}:{priority}` の **priority がキーに移動** したのは v2.6 以降。旧形式 `priority` フィールドは deprecated だが残っているため両方の混在に注意[^1]
- `pa_validation: true` の場合、対応 VNet の mapping table に該当 PA が存在しないと drop される（PA validation 失敗）

### 5.5 SmartSwitch で DPU 切り離し

[SmartSwitch](../reference/glossary.md#term-smartswitch) では [NPU](../reference/glossary.md#term-npu) 側から [DPU](../reference/glossary.md#term-dpu) を物理切り離し可能。`DashHaOrch` が peer DPU 状態を同期する設計のため、片肺で運用継続することはできるが、`DASH_*` テーブルは DPU ごとに独立投入される。詳細は [smartswitch-eni-based-forwarding.md](smartswitch-eni-based-forwarding.md) と SmartSwitch HA HLD を参照[^1]。

### 5.6 route group を unbind したあと再利用したい

不可。HLD §1.8 が明記: **全 ENI から unbind された route group は [orchagent](../reference/glossary.md#term-orchagent) と SAI で自動削除** され、route 情報がキャッシュされていないため再 bind 不可。新規 `DASH_ROUTE_GROUP_TABLE` を作って同じ route 群を入れ直すこと[^1]。

## 6. 警告

- **`DASH_ROUTING_APPLIANCE_TABLE` は DEPRECATED**。代わりに `DASH_TUNNEL_TABLE` を使うこと（v2.4 で導入）[^1]
- **`metering_policy_en` は OBSOLETED**。`metering_class_or` / `metering_class_and` で集約フラグを管理する形式に統一[^1]
- **`action_type` フィールドは `routing_type` に改名**（v2.2）、旧フィールドは reserved word として残るが新規設定では `routing_type` を使う[^1]
- **`trusted_vnis` → `trusted_vnis_list`** (v2.6.1)。古い設定スクリプトは要更新[^1]
- DASH は **DPU / SmartSwitch 専用** で、通常の [SONiC](../reference/glossary.md#term-sonic) NPU では動作しない

## 関連ページ

- [SONiC-DASH 概観](sonic-dash-hld.md) — 元 HLD ページ
- [sonic-dash-hld-concepts.md](sonic-dash-hld-concepts.md) — 概念とシナリオ意味論
- [sonic-dash-hld-internals.md](sonic-dash-hld-internals.md) — DASH APP DB スキーマ、Orch / SAI 内部
- [smartswitch-eni-based-forwarding.md](smartswitch-eni-based-forwarding.md)
- [dash-sonic-kvm.md](dash-sonic-kvm.md)

## 引用元

[^1]: `sonic-net/SONiC` `doc/dash/dash-sonic-hld.md` @ `49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06`

<!-- topics-back-ref -->
## 関連 Topics

- [Topics: DASH と SmartSwitch](../topics/13-dash-smartswitch/index.md)

<!-- /topics-back-ref -->

<!-- glossary-links-injected: 2ceca48bcf92 -->
