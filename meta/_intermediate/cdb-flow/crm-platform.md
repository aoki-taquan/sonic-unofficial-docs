# CRM — Phase H: プラットフォーム差異

ソース: `sonic-swss/orchagent/crmorch.cpp`

## 1. ASIC ベンダー別 SAI capability 差 (resource 取得方式)

CRM は各リソースの available カウンタを 2 段階で取得する (`getResAvailability`):

### 優先パス: `sai_object_type_get_availability`

SAI の汎用 object-level availability API。ASIC ベンダーが実装していれば、より細粒度な capacity を返す。  
以下のリソースは `crmResSaiObjAttrMap` で SAI object type が指定されており、最初にこのパスを試みる:

- `CRM_IPV4_ROUTE` / `CRM_IPV6_ROUTE` → `SAI_OBJECT_TYPE_ROUTE_ENTRY` + `SAI_ROUTE_ENTRY_ATTR_IP_ADDR_FAMILY`
- `CRM_IPV4_NEIGHBOR` / `CRM_IPV6_NEIGHBOR` → `SAI_OBJECT_TYPE_NEIGHBOR_ENTRY` + アドレスファミリ属性
- `CRM_MPLS_NEXTHOP` → `SAI_OBJECT_TYPE_NEXT_HOP` + `SAI_NEXT_HOP_ATTR_TYPE=SAI_NEXT_HOP_TYPE_MPLS`
- `CRM_SRV6_NEXTHOP` → `SAI_OBJECT_TYPE_NEXT_HOP` + `SAI_NEXT_HOP_ATTR_TYPE=SAI_NEXT_HOP_TYPE_SRV6_SIDLIST`
- `CRM_NEXTHOP_GROUP` → `SAI_OBJECT_TYPE_NEXT_HOP_GROUP`
- `CRM_FDB_ENTRY` → `SAI_OBJECT_TYPE_FDB_ENTRY`
- `CRM_MPLS_INSEG` → `SAI_OBJECT_TYPE_INSEG_ENTRY`
- `CRM_SRV6_MY_SID_ENTRY` → `SAI_OBJECT_TYPE_MY_SID_ENTRY`

### フォールバックパス: `sai_switch_api->get_switch_attribute`

`sai_object_type_get_availability` が失敗した場合、または `crmResSaiObjAttrMap` で `SAI_OBJECT_TYPE_NULL` が設定されているリソースは `crmResSaiAvailAttrMap` の `SAI_SWITCH_ATTR_AVAILABLE_*` を直接 get する:

- `CRM_IPV4_ROUTE` → `SAI_SWITCH_ATTR_AVAILABLE_IPV4_ROUTE_ENTRY`
- `CRM_NEXTHOP_GROUP_MEMBER` → `SAI_SWITCH_ATTR_AVAILABLE_NEXT_HOP_GROUP_MEMBER_ENTRY`
- `CRM_SNAT_ENTRY` / `CRM_DNAT_ENTRY` → `SAI_SWITCH_ATTR_AVAILABLE_SNAT_ENTRY` / `SAI_SWITCH_ATTR_AVAILABLE_DNAT_ENTRY`
- `CRM_TWAMP_ENTRY` → `SAI_SWITCH_ATTR_AVAILABLE_TWAMP_SESSION`

### SAI_STATUS_NOT_SUPPORTED / NOT_IMPLEMENTED 時の挙動

いずれのパスでも `SAI_STATUS_NOT_SUPPORTED` / `SAI_STATUS_NOT_IMPLEMENTED` / `SAI_STATUS_IS_ATTR_NOT_SUPPORTED` / `SAI_STATUS_IS_ATTR_NOT_IMPLEMENTED` が返ると:

- `res.resStatus = CRM_RES_NOT_SUPPORTED` をセット
- `SWSS_LOG_NOTICE("CRM resource %s not supported")` を出力
- 以降の polling cycle でそのリソースはスキップされる (`resStatus != CRM_RES_SUPPORTED` ガード)

**実用上の意味**: ASIC が特定リソース (e.g. MPLS INSEG, SRv6 MY SID, TWAMP) をサポートしない場合、自動的に monitoring が無効化される。CONFIG_DB への threshold 設定自体は受け入れるが、COUNTERS_DB には統計が書き込まれない。

## 2. ACL リソースの特殊取得 (stage × bind_point 単位)

`CRM_ACL_TABLE` / `CRM_ACL_GROUP` は他リソースと異なる方式で capacity を取得する:

- `SAI_SWITCH_ATTR_AVAILABLE_ACL_TABLE` / `SAI_SWITCH_ATTR_AVAILABLE_ACL_TABLE_GROUP` を `aclresource` 型で取得 (最大 `CRM_ACL_RESOURCE_COUNT=256` エントリ)
- `SAI_STATUS_BUFFER_OVERFLOW` 時は `attr.value.aclresource.count` で返ってきた実際サイズでリサイズして再取得
- 返却値はステージ (`ingress`/`egress`) × バインドポイント (`port`/`lag`/`vlan`/`rif`/`switch`) のマトリクス
- COUNTERS_DB には `ACL_STATS:INGRESS:PORT` のような複合 key で個別に書き込まれる

`CRM_ACL_ENTRY` / `CRM_ACL_COUNTER` は per-ACL table で `sai_acl_api->get_acl_table_attribute` を呼び出す (ACL テーブルが存在しない場合は usedCounter = availableCounter = 0)。

## 3. DASH / DPU 専用リソース (`gMySwitchType != "dpu"` ガード)

`DEVICE_METADATA.localhost.switch_type` が `"dpu"` でない場合、以下のリソースは強制的に `CRM_RES_NOT_SUPPORTED` となり monitoring されない:

- DASH 系リソース全般 (`DASH_VNET`, `DASH_ENI`, `DASH_ENI_ETHER_ADDRESS_MAP`, 全 routing/pa_validation/ca_to_pa エントリ, `DASH_IPV4/6_METER_POLICY/RULE`)
- `DASH_IPV4/6_ACL_GROUP`: `getDashAclGroupResAvailability` が `gMySwitchType != "dpu"` を事前チェックして即 `CRM_RES_NOT_SUPPORTED` を返す

`DASH_IPV4/6_ACL_RULE` は専用の `getDashAclGroupResAvailability` 関数経由で取得し、ACL Group OID ごとに `sai_object_type_get_availability` + `SAI_DASH_ACL_RULE_ATTR_DASH_ACL_GROUP_ID` フィルタで capacity を確認する。

## 4. EXT_TABLE (Generic Programmable) の ASIC-specific 取得

`CRM_EXT_TABLE` は extension テーブル名を `SAI_GENERIC_PROGRAMMABLE_ATTR_OBJECT_NAME` (s8list) で指定し `sai_object_type_get_availability` を呼び出す。テーブル名がそのまま SAI lookup key になるため、ASIC ドライバが対象テーブル名を認識しない場合は `status != SAI_STATUS_SUCCESS` でエラーログが出力される (not_supported フラグは立てない)。

## 5. VOQ chassis での資源差

VOQ chassis では `DEVICE_METADATA.localhost.switch_type = "voq"` となるが、CRM コード上に VOQ 専用パスは存在しない。`gMySwitchType` のチェックは DASH (`"dpu"`) のみ。VOQ システムでも CRM は通常スイッチと同一の FIB/ACL/L2 リソースを監視するが、fabric port 側の resource は CRM 対象外。

## 6. TWAMP リソースの特殊性

`CRM_TWAMP_ENTRY` は `crmResSaiObjAttrMap` で `SAI_OBJECT_TYPE_NULL` が割り当てられているため、`sai_object_type_get_availability` を試みない。常に `SAI_SWITCH_ATTR_AVAILABLE_TWAMP_SESSION` の `get_switch_attribute` フォールバックのみを使用する。ASIC が TWAMP をサポートしない場合は `CRM_RES_NOT_SUPPORTED` に遷移。

## evidence 一覧

| 事象 | ファイル:行 |
|------|------------|
| `getResAvailability` 2段階取得ロジック | `crmorch.cpp:760-834` |
| DASH resources `gMySwitchType != "dpu"` ガード | `crmorch.cpp:933-937` |
| `getDashAclGroupResAvailability` DPU チェック | `crmorch.cpp:839-843` |
| ACL TABLE/GROUP aclresource 取得 | `crmorch.cpp:946-989` |
| ACL ENTRY/COUNTER per-table 取得 | `crmorch.cpp:991-1020` |
| EXT_TABLE generic programmable 取得 | `crmorch.cpp:1022-1047` |
| DASH ACL RULE → `getDashAclGroupResAvailability` | `crmorch.cpp:1049-1054` |
| `CRM_RES_NOT_SUPPORTED` skip ガード | `crmorch.cpp:884-886` |
| `crmResSaiAvailAttrMap` TWAMP → `SAI_OBJECT_TYPE_NULL` | `crmorch.cpp:92` |
