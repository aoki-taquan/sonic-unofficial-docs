# CRM 順序依存分析 (Phase B)

ソース: `sonic-swss/orchagent/crmorch.cpp`

## 1. CrmOrch ポーリング起動順序

`CrmOrch::CrmOrch()` コンストラクタが実行する初期化ステップ（L398-L419）:

1. **`Orch(db, tableName)` 基底クラス初期化** — CONFIG_DB コンシューマー登録（L398-399）
2. **`m_countersDb` / `m_countersCrmTable` 生成** — COUNTERS_DB コネクション確立（L400-401）
3. **`m_timer` 生成（SelectableTimer）** — デフォルト間隔 `CRM_POLLING_INTERVAL_DEFAULT = 300秒` でタイマーオブジェクト生成（L402）
4. **`m_pollingInterval` 設定** — `chrono::seconds(300)` をメンバ変数にコピー（L406）
5. **`m_resourcesMap` 全リソース初期化** — `crmResTypeNameMap` を走査して全リソース種別を `CrmResourceEntry(name, PERCENTAGE, 70, 85)` でエントリ登録（L408-411）。`crmResTypeNameMap` の定義順（L28-72）は `std::map` のキー昇順（`CrmResourceType` 列挙値順）で反復される
6. **COUNTERS_DB の既存 CRM 統計削除** — `m_countersCrmTable->del("STATS")` で古いキャッシュをクリア（L414）
7. **`ExecutableTimer` 生成・登録** — `Orch::addExecutor(executor)` でポーリングループへ紐付け（L417-418）
8. **`m_timer->start()`** — タイマー起動。これ以後、`polling_interval` 経過ごとに `doTask(SelectableTimer&)` → `getResAvailableCounters()` → `updateCrmCountersTable()` → `checkCrmThresholds()` の順で呼ばれる（L419、L751-758）

> **重要**: リソースエントリの登録（ステップ 5）はタイマー起動（ステップ 8）より必ず先に完了する。タイマーコールバックが先走ってリソースマップが空の状態でカウンタ取得を試みることはない。

## 2. リソース種別ごとの初期化順序

`crmResTypeNameMap`（`std::map<CrmResourceType, string>`）は列挙値の昇順でイテレートされる。コンストラクタの `for (const auto &res : crmResTypeNameMap)` ループで `m_resourcesMap` へのエントリ追加順は以下の通り（`crmorch.cpp` L28-72 の列挙値順）:

| 順 | CrmResourceType | リソース名 |
|----|----------------|-----------|
| 1 | CRM_IPV4_ROUTE | IPV4_ROUTE |
| 2 | CRM_IPV6_ROUTE | IPV6_ROUTE |
| 3 | CRM_IPV4_NEXTHOP | IPV4_NEXTHOP |
| 4 | CRM_IPV6_NEXTHOP | IPV6_NEXTHOP |
| 5 | CRM_IPV4_NEIGHBOR | IPV4_NEIGHBOR |
| 6 | CRM_IPV6_NEIGHBOR | IPV6_NEIGHBOR |
| 7 | CRM_NEXTHOP_GROUP_MEMBER | NEXTHOP_GROUP_MEMBER |
| 8 | CRM_NEXTHOP_GROUP | NEXTHOP_GROUP |
| 9 | CRM_ACL_TABLE | ACL_TABLE |
| 10 | CRM_ACL_GROUP | ACL_GROUP |
| 11 | CRM_ACL_ENTRY | ACL_ENTRY |
| 12 | CRM_ACL_COUNTER | ACL_COUNTER |
| 13 | CRM_FDB_ENTRY | FDB_ENTRY |
| 14 | CRM_IPMC_ENTRY | IPMC_ENTRY |
| 15 | CRM_SNAT_ENTRY | SNAT_ENTRY |
| 16 | CRM_DNAT_ENTRY | DNAT_ENTRY |
| 17 | CRM_MPLS_INSEG | MPLS_INSEG |
| 18 | CRM_MPLS_NEXTHOP | MPLS_NEXTHOP |
| 19 | CRM_SRV6_MY_SID_ENTRY | SRV6_MY_SID_ENTRY |
| 20 | CRM_SRV6_NEXTHOP | SRV6_NEXTHOP |
| 21 | CRM_NEXTHOP_GROUP_MAP | NEXTHOP_GROUP_MAP |
| 22 | CRM_EXT_TABLE | EXTENSION_TABLE |
| 23 | CRM_DASH_VNET | DASH_VNET |
| 24 | CRM_DASH_ENI | DASH_ENI |
| 25 | CRM_DASH_ENI_ETHER_ADDRESS_MAP | DASH_ENI_ETHER_ADDRESS_MAP |
| 26 | CRM_DASH_IPV4_INBOUND_ROUTING | DASH_IPV4_INBOUND_ROUTING |
| 27 | CRM_DASH_IPV6_INBOUND_ROUTING | DASH_IPV6_INBOUND_ROUTING |
| 28 | CRM_DASH_IPV4_OUTBOUND_ROUTING | DASH_IPV4_OUTBOUND_ROUTING |
| 29 | CRM_DASH_IPV6_OUTBOUND_ROUTING | DASH_IPV6_OUTBOUND_ROUTING |
| 30 | CRM_DASH_IPV4_PA_VALIDATION | DASH_IPV4_PA_VALIDATION |
| 31 | CRM_DASH_IPV6_PA_VALIDATION | DASH_IPV6_PA_VALIDATION |
| 32 | CRM_DASH_IPV4_OUTBOUND_CA_TO_PA | DASH_IPV4_OUTBOUND_CA_TO_PA |
| 33 | CRM_DASH_IPV6_OUTBOUND_CA_TO_PA | DASH_IPV6_OUTBOUND_CA_TO_PA |
| 34 | CRM_DASH_IPV4_ACL_GROUP | DASH_IPV4_ACL_GROUP |
| 35 | CRM_DASH_IPV6_ACL_GROUP | DASH_IPV6_ACL_GROUP |
| 36 | CRM_DASH_IPV4_ACL_RULE | DASH_IPV4_ACL_RULE |
| 37 | CRM_DASH_IPV6_ACL_RULE | DASH_IPV6_ACL_RULE |
| 38 | CRM_DASH_IPV4_METER_POLICY | DASH_IPV4_METER_POLICY |
| 39 | CRM_DASH_IPV4_METER_RULE | DASH_IPV4_METER_RULE |
| 40 | CRM_DASH_IPV6_METER_POLICY | DASH_IPV6_METER_POLICY |
| 41 | CRM_DASH_IPV6_METER_RULE | DASH_IPV6_METER_RULE |
| 42 | CRM_TWAMP_ENTRY | TWAMP_ENTRY |

全エントリはデフォルト値 `thresholdType=PERCENTAGE`, `lowThreshold=70`, `highThreshold=85` で初期化される。

## 3. SAI sai_switch_attr 読取り順序（ポーリング時）

`getResAvailableCounters()` (L878-) が毎ポーリングで各リソースを走査する際の SAI 属性読取りロジック:

### 優先順位 1: `sai_object_type_get_availability()` 経由（objType != NULL の場合）

以下のリソースはまず `sai_object_type_get_availability(gSwitchId, objType, attrCount, &attr, &availCount)` を呼ぶ（L801）。attrCount=1 で追加属性を渡すリソースあり:

| リソース | sai_object_type | 追加属性 |
|---------|----------------|---------|
| CRM_IPV4_ROUTE | SAI_OBJECT_TYPE_ROUTE_ENTRY | SAI_ROUTE_ENTRY_ATTR_IP_ADDR_FAMILY = IPv4 |
| CRM_IPV6_ROUTE | SAI_OBJECT_TYPE_ROUTE_ENTRY | SAI_ROUTE_ENTRY_ATTR_IP_ADDR_FAMILY = IPv6 |
| CRM_IPV4_NEIGHBOR | SAI_OBJECT_TYPE_NEIGHBOR_ENTRY | SAI_NEIGHBOR_ENTRY_ATTR_IP_ADDR_FAMILY = IPv4 |
| CRM_IPV6_NEIGHBOR | SAI_OBJECT_TYPE_NEIGHBOR_ENTRY | SAI_NEIGHBOR_ENTRY_ATTR_IP_ADDR_FAMILY = IPv6 |
| CRM_NEXTHOP_GROUP | SAI_OBJECT_TYPE_NEXT_HOP_GROUP | なし (attrCount=0) |
| CRM_FDB_ENTRY | SAI_OBJECT_TYPE_FDB_ENTRY | なし (attrCount=0) |
| CRM_MPLS_NEXTHOP | SAI_OBJECT_TYPE_NEXT_HOP | SAI_NEXT_HOP_ATTR_TYPE = SAI_NEXT_HOP_TYPE_MPLS |
| CRM_SRV6_NEXTHOP | SAI_OBJECT_TYPE_NEXT_HOP | SAI_NEXT_HOP_ATTR_TYPE = SAI_NEXT_HOP_TYPE_SRV6_SIDLIST |
| CRM_SRV6_MY_SID_ENTRY | SAI_OBJECT_TYPE_MY_SID_ENTRY | なし (attrCount=0) |
| CRM_MPLS_INSEG | SAI_OBJECT_TYPE_INSEG_ENTRY | なし (attrCount=0) |
| CRM_NEXTHOP_GROUP_MAP | SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MAP | なし (attrCount=0) |
| CRM_EXT_TABLE | SAI_OBJECT_TYPE_GENERIC_PROGRAMMABLE | なし (attrCount=0) |

### 優先順位 2: `sai_switch_api->get_switch_attribute()` へフォールバック

`sai_object_type_get_availability()` が失敗、または objType が NULL の場合（IPV4_NEXTHOP / IPV6_NEXTHOP / NEXTHOP_GROUP_MEMBER 等）、`crmResSaiAvailAttrMap` に存在するリソースは `sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr)` で代替取得（L809）:

| リソース | SAI_SWITCH_ATTR |
|---------|----------------|
| CRM_IPV4_ROUTE | SAI_SWITCH_ATTR_AVAILABLE_IPV4_ROUTE_ENTRY |
| CRM_IPV6_ROUTE | SAI_SWITCH_ATTR_AVAILABLE_IPV6_ROUTE_ENTRY |
| CRM_IPV4_NEXTHOP | SAI_SWITCH_ATTR_AVAILABLE_IPV4_NEXTHOP_ENTRY |
| CRM_IPV6_NEXTHOP | SAI_SWITCH_ATTR_AVAILABLE_IPV6_NEXTHOP_ENTRY |
| CRM_IPV4_NEIGHBOR | SAI_SWITCH_ATTR_AVAILABLE_IPV4_NEIGHBOR_ENTRY |
| CRM_IPV6_NEIGHBOR | SAI_SWITCH_ATTR_AVAILABLE_IPV6_NEIGHBOR_ENTRY |
| CRM_NEXTHOP_GROUP_MEMBER | SAI_SWITCH_ATTR_AVAILABLE_NEXT_HOP_GROUP_MEMBER_ENTRY |
| CRM_NEXTHOP_GROUP | SAI_SWITCH_ATTR_AVAILABLE_NEXT_HOP_GROUP_ENTRY |
| CRM_ACL_TABLE | SAI_SWITCH_ATTR_AVAILABLE_ACL_TABLE |
| CRM_ACL_GROUP | SAI_SWITCH_ATTR_AVAILABLE_ACL_TABLE_GROUP |
| CRM_FDB_ENTRY | SAI_SWITCH_ATTR_AVAILABLE_FDB_ENTRY |
| CRM_IPMC_ENTRY | SAI_SWITCH_ATTR_AVAILABLE_IPMC_ENTRY |
| CRM_SNAT_ENTRY | SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY |
| CRM_DNAT_ENTRY | SAI_SWITCH_ATTR_AVAILABLE_DNAT_ENTRY |
| CRM_TWAMP_ENTRY | SAI_SWITCH_ATTR_AVAILABLE_TWAMP_SESSION |

### ACL_TABLE / ACL_GROUP: 特殊リスト取得

`CRM_ACL_TABLE` / `CRM_ACL_GROUP` は `sai_acl_resource_t` のリスト形式で取得。初期 `CRM_ACL_RESOURCE_COUNT=256` サイズのベクタを割り当て、`SAI_STATUS_BUFFER_OVERFLOW` の場合は返却された count でリサイズしてリトライ（L943-L980）。これは他リソースにはない 2-phase 取得パターン。

### DASH 系: gMySwitchType="dpu" ガード

DASH 系リソース（CRM_DASH_* 全種別）は `gMySwitchType != "dpu"` のとき `CRM_RES_NOT_SUPPORTED` にセットしてスキップ（L933-936）。

## 4. ポーリングループ内呼び出し順

`doTask(SelectableTimer&)` から呼ばれる関数の順序（L751-758）:

```
1. getResAvailableCounters()  — SAI から available counter を取得・更新
2. updateCrmCountersTable()   — COUNTERS_DB の CRM:STATS テーブルを更新
3. checkCrmThresholds()       — 閾値超過チェック・アラート syslog 送信
```

この順序は固定。`checkCrmThresholds()` が `updateCrmCountersTable()` より先に動くことはなく、最新の available counter でチェックが行われることが保証される。
