# APPL_DB ROUTE_TABLE (appl-db-route) — プラットフォーム差調査

Task F Phase H: `APPL_DB:ROUTE_TABLE` 適用時のプラットフォーム/構成差を `sonic-swss/orchagent/routeorch.cpp` と `nhgorch.cpp` (+ 周辺 `crmorch.cpp` / `orch.h`) から精読した結果。`docs/reference/config-db/appl-db-route.md` 1 ページに反映する。

## 結論

**プラットフォーム差あり**。`fpmsyncd` → APPL_DB 書込み自体は ASIC 非依存だが、`routeorch` 側で

1. Mellanox ASIC 限定の ECMP グループ数補正（`m_maxNextHopGroupCount /= 32`）
2. VOQ chassis での ECMP メンバ数 128 強制書き戻し
3. SRv6 / EVPN overlay nexthop の SAI capability 依存（NOT_SUPPORTED 戻り）

の 3 軸で挙動が分岐する。`nhgorch.cpp` 自体には platform / switch_type の分岐は無く、`routeorch` が算出した `m_maxNextHopGroupCount` と SAI capability に従って動作する。

## 根拠

### 1. Mellanox ASIC 限定: ECMP グループ数を 32 で除算

`orchagent/routeorch.cpp` L73-L88 の `RouteOrch` コンストラクタで `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` を取得後、`getenv("platform")` の値に `MLNX_PLATFORM_SUBSTRING == "mellanox"` (`orchagent/orch.h` L42) が含まれる場合のみ補正:

```cpp
// orchagent/routeorch.cpp:84-87
char *platform = getenv("platform");
if (platform && strstr(platform, MLNX_PLATFORM_SUBSTRING))
{
    m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE;  // 32
}
```

- `DEFAULT_NUMBER_OF_ECMP_GROUPS = 128`（L37）— SAI 取得失敗時のフォールバック
- `DEFAULT_MAX_ECMP_GROUP_SIZE = 32`（L38）— Mellanox 補正の除数
- 算出値は `m_switchOrch->set_switch_capability()` 経由で STATE_DB `SWITCH_CAPABILITY:MAX_NEXTHOP_GROUP_COUNT` に公開される（L90-L92）

Broadcom / Marvell / Cisco silicon-one / VS / xsight 等は SAI 戻り値をそのまま採用する。`nhgorch` はこの公開値をもとに `nexthop_group` の登録可否を判定するが、`nhgorch.cpp` 自体に platform 分岐は無い。

### 2. VOQ chassis: ECMP メンバ数を 128 に強制書き戻し

`orchagent/routeorch.cpp` L95-L124 で `SAI_SWITCH_ATTR_MAX_ECMP_MEMBER_COUNT` を取得し、`gMySwitchType == "voq"` かつ取得値が 128 以上のとき `SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT` を 128 に書き戻す:

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

`gMySwitchType` は CONFIG_DB `DEVICE_METADATA|localhost:switch_type` 由来（`switch` / `voq` / `chassis-packet` / `dpu`）。`switch_type=switch` (T0/T1 fixed pizzabox) や `chassis-packet` の line card では発火しない。マジック数 `128` は `#define` ではなくインラインリテラル。

### 3. SRv6 / EVPN overlay ネクストホップは ASIC SAI capability 依存

`routeorch.cpp` L736-L795 で APPL_DB の `vni_label` / `segment` / `seg_src` フィールドを検出し `overlay_nh` / `srv6_nh` フラグを立てるが、SAI 側で以下が未実装の ASIC は create に失敗する:

- `SAI_NEXT_HOP_TYPE_TUNNEL_ENCAP`（EVPN VxLAN encap）
- `SAI_NEXT_HOP_TYPE_SRV6_SIDLIST`（SRv6 SID-list）
- `SAI_OBJECT_TYPE_MY_SID_ENTRY`（SRv6 MY_SID）

未対応時は `create_next_hop` / `create_my_sid_entry` が `SAI_STATUS_NOT_SUPPORTED` を返し routeorch がエラーログを残す（L2130 / L2136 など）。community master では Broadcom DNX / Mellanox 一部 SKU で SRv6 が機能、VS / vpp はスタブ実装。

### 4. CRM 集計: SAI 任意属性

`crmorch.cpp` L76-L77 で `CRM_IPV4_ROUTE` / `CRM_IPV6_ROUTE` を `SAI_SWITCH_ATTR_AVAILABLE_IPV4_ROUTE_ENTRY` / `_IPV6_ROUTE_ENTRY` に紐付けるが、これらは SAI の任意属性。古い SDK / VS / VPP の一部では実装されておらず STATE_DB `CRM` の `crm_stats_ipv4_route_available` / `ipv6_route_available` が欠落する。

### 5. multi-asic / VOQ chassis での namespace 分離

`routeorch` は `DBConnector` の namespace に従って `swss@asicN` Docker ごとに 1 インスタンス起動し、それぞれ独立した APPL_DB `ROUTE_TABLE` を購読する。fpmsyncd も `asicN` namespace 単位で動作し、ASIC 間で `route_entry` / `next_hop_group` の名前空間は交わらない。chassis 全体の VOQ ルーティングは `CHASSIS_APP_DB`（redis index 12、`chassisdb.sock`）+ `voqorch` / `BgpGlobalStateOrch` 経由で同期されるため、`APPL_DB:ROUTE_TABLE` 自体に chassis-wide 同期機構はない。

### 6. VS / VPP プラットフォーム

`VS_PLATFORM_SUBSTRING="vs"` / `XS_PLATFORM_SUBSTRING="xsight"`（`orch.h` L46 / L49）では SAI シム（libsaivs / libsaivpp）が ECMP / SRv6 / overlay nexthop の create を SUCCESS で返すが ASIC は無く実機転送はない。Mellanox 補正は走らず、SAI 既定値（多くは 128〜1024）が `m_maxNextHopGroupCount` になる。CRM の available 値もダミー。

### 7. nhgorch には platform 分岐なし

`orchagent/nhgorch.cpp` / `nhgbase.cpp` を `MLNX_PLATFORM|VS_PLATFORM|XS_PLATFORM|gMySwitchType|getenv\("platform"\)|voq|chassis` で grep しても 0 ヒット。nhgorch は `SAI_NEXT_HOP_GROUP_TYPE_ECMP` （L771-L772）と `SAI_NEXT_HOP_GROUP_MEMBER_ATTR_WEIGHT`（L611, L1116）などを共通 API で発行するだけで、platform/switch_type の if 分岐を持たない。プラットフォーム差は routeorch が公開する `MAX_NEXTHOP_GROUP_COUNT` と SAI capability 経由で間接的に効く。

## まとめ

APPL_DB:ROUTE_TABLE 経路自体（fpmsyncd 書込 → routeorch 購読 → nhgorch 経由 SAI 反映）はプラットフォーム共通だが:

- **ECMP 容量**: Mellanox は `m_maxNextHopGroupCount /= 32`、VOQ は最大メンバ数 128 強制
- **SRv6 / EVPN**: ASIC SAI capability に依存（NOT_SUPPORTED 戻りでエラーログ）
- **multi-asic / chassis**: `asicN` namespace ごとに routeorch + fpmsyncd が独立、chassis-wide 同期は別経路
- **VS / VPP**: 機能的に no-op だが API は成功

nhgorch には platform 分岐が無く、上記差は routeorch の起動時補正と STATE_DB `SWITCH_CAPABILITY` を通じて間接的に反映される。
