# APPL_DB ROUTE_TABLE — プラットフォーム差調査

Task F Phase H: `APPL_DB:ROUTE_TABLE` 適用時のプラットフォーム/構成差を `sonic-swss/orchagent/routeorch.cpp` / `crmorch.cpp` / `saihelper.cpp` から精読した結果。

## 結論

**プラットフォーム差あり**。ECMP の最大グループ数・最大メンバ数が ASIC 種別と switch_type で分岐し、SRv6 / EVPN overlay ネクストホップは ASIC SAI が当該機能をサポートしていることを前提とする。
multi-asic / VOQ chassis では `asicN` namespace ごとに独立した routeorch インスタンスが ASIC 単位で APPL_DB を購読する。

## 根拠

### 1. Mellanox ASIC 限定: ECMP グループ数の補正

`routeorch.cpp` L73-L88 の `RouteOrch` コンストラクタで `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` を取得後、`getenv("platform")` の文字列に `MLNX_PLATFORM_SUBSTRING == "mellanox"` (`orchagent/orch.h` L42) が含まれる場合のみ:

```cpp
// orchagent/routeorch.cpp:84-87
if (platform && strstr(platform, MLNX_PLATFORM_SUBSTRING))
{
    m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE; // 32
}
```

`DEFAULT_NUMBER_OF_ECMP_GROUPS` は 128、`DEFAULT_MAX_ECMP_GROUP_SIZE` は 32 (`routeorch.cpp` L37-L38)。
SAI 取得失敗時はデフォルト 128 にフォールバック。
Mellanox 以外（Broadcom / Marvell / Cisco silicon-one / VS / xsight 等）は SAI が返した値をそのまま採用する。
得られた `MAX_NEXTHOP_GROUP_COUNT` は `m_switchOrch->set_switch_capability()` で STATE_DB `SWITCH_CAPABILITY` テーブルへ公開され、`ROUTE_TABLE` の `nexthop_group` 採用可否はこの値で決まる。

### 2. VOQ chassis: ECMP メンバ数を 128 に強制

`routeorch.cpp` L95-L124 で `SAI_SWITCH_ATTR_MAX_ECMP_MEMBER_COUNT` を取得し、`gMySwitchType == "voq"` かつ取得値が 128 以上のとき `SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT` を 128 に **書き戻す**:

```cpp
// orchagent/routeorch.cpp:109-122
if (gMySwitchType == "voq" && maxEcmpGroupSize >= 128)
{
    maxEcmpGroupSize = 128;
    attr.id = SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT;
    attr.value.s32 = maxEcmpGroupSize;
    status = sai_switch_api->set_switch_attribute(gSwitchId, &attr);
    ...
}
```

`gMySwitchType` は CONFIG_DB `DEVICE_METADATA|localhost:switch_type` 由来。値は `switch`（fixed pizzabox）/ `voq`（distributed VOQ chassis）/ `chassis-packet`（packet chassis）/ `dpu`。
T0/T1 fixed (`switch_type=switch`) や `chassis-packet` の line card では本書き換えは発生しない。

### 3. CRM 集計: ROUTE_ENTRY 利用可能数の SAI 取得

`crmorch.cpp` L76-L77 で:

```cpp
{ CrmResourceType::CRM_IPV4_ROUTE, SAI_SWITCH_ATTR_AVAILABLE_IPV4_ROUTE_ENTRY },
{ CrmResourceType::CRM_IPV6_ROUTE, SAI_SWITCH_ATTR_AVAILABLE_IPV6_ROUTE_ENTRY },
```

`SAI_SWITCH_ATTR_AVAILABLE_*_ROUTE_ENTRY` は SAI の任意属性で、ASIC SAI 実装が未対応のとき `crm_stats_ipv4_route_available` / `ipv6_route_available` が STATE_DB `CRM` に出ない。VS プラットフォーム (`VS_PLATFORM_SUBSTRING == "vs"` / `orch.h` L46) と vpp/xsight プラットフォーム (`XS_PLATFORM_SUBSTRING == "xsight"` / `orch.h` L49) では一部値がダミーになる。

### 4. SRv6 / EVPN overlay ネクストホップは ASIC capability 依存

`routeorch.cpp` L736-L795 で APPL_DB の `vni_label` / `segment` / `seg_src` フィールドを検出して `overlay_nh` / `srv6_nh` フラグを立てるが、SAI 側で `SAI_NEXT_HOP_TYPE_TUNNEL_ENCAP` / `SAI_NEXT_HOP_TYPE_SRV6_SIDLIST` および `SAI_OBJECT_TYPE_MY_SID_ENTRY` が未対応の ASIC では create_next_hop / create_my_sid_entry が `SAI_STATUS_NOT_SUPPORTED` を返し routeorch がエラーログを残す（L2130 / L2136 など）。community master では Broadcom DNX / Mellanox SN5xxx の一部 SKU で SRv6 が動作し、VS / vpp はスタブ実装。

### 5. multi-asic / VOQ chassis での namespace 分離

`routeorch` は `db` 引数の `DBConnector` namespace で APPL_DB に接続するため、`swss@asicN` Docker ごとに 1 つの routeorch が起動し、それぞれ独立した `ROUTE_TABLE` を購読する。fpmsyncd も `asicN` namespace 単位で動作し、line card 内 ASIC 間で `nexthop_group` / `route_entry` 名前空間が交わらない。
chassis 全体での集中ルーティングは `chassis_app_db` (`CHASSIS_APP_DB` index 12, redis `chassisdb.sock`) を介した別経路（`voqorch` / `BgpGlobalStateOrch`）であり、`APPL_DB:ROUTE_TABLE` 自体には chassis 跨ぎの自動同期機構はない。

### 6. VS / VPP プラットフォーム

`VS_PLATFORM_SUBSTRING="vs"` / `XS_PLATFORM_SUBSTRING="xsight"` の場合、SAI シム（libsaivs / libsaivpp）が ECMP / SRv6 / overlay nexthop の create を成功させるが ASIC へは反映しない。CRM 値もダミー。routeorch の `m_maxNextHopGroupCount` 補正は Mellanox 限定なので VS では SAI 既定値（多くは 128 や 1024）がそのまま採用される。

## まとめ

APPL_DB:ROUTE_TABLE 経路自体（fpmsyncd 書込 → routeorch 購読）はプラットフォーム共通だが、

- ECMP 容量: Mellanox は `m_maxNextHopGroupCount /= 32` の補正、VOQ は最大メンバ数を 128 に強制
- SRv6 / EVPN: ASIC SAI capability に依存（NOT_SUPPORTED 戻りでエラー）
- multi-asic / chassis: `asicN` namespace ごとに routeorch + fpmsyncd が独立、chassis-wide 同期は別経路
- VS / VPP: 機能的に no-op だが API は成功

の 4 軸で挙動差が出る。
