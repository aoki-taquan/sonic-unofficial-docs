# route — Phase H: プラットフォーム差異

ソース: `orchagent/routeorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 1. ASIC 別 ECMP グループ数上限 (m_maxNextHopGroupCount)

RouteOrch コンストラクタは起動時に `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` を問い合わせて ECMP グループ上限を決定する。

```cpp
// routeorch.cpp:61-91
attr.id = SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS;
sai_status_t status = sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr);
if (status != SAI_STATUS_SUCCESS)
{
    m_maxNextHopGroupCount = DEFAULT_NUMBER_OF_ECMP_GROUPS;  // 128
}
else
{
    m_maxNextHopGroupCount = attr.value.s32;

    // Mellanox 固有補正
    char *platform = getenv("platform");
    if (platform && strstr(platform, MLNX_PLATFORM_SUBSTRING))  // "mellanox"
    {
        m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE;  // ÷ 32
    }
}
```

| プラットフォーム | SAI 返値の解釈 | 有効 m_maxNextHopGroupCount |
|-----------------|---------------|----------------------------|
| Mellanox (mellanox) | SAI が「ECMP size=1 のときの最大グループ数」を返すため ÷32 が必要 | `SAI 返値 / 32` |
| その他 ASIC | SAI 返値をそのまま使用 | `SAI 返値` |
| SAI 失敗時フォールバック | — | `DEFAULT_NUMBER_OF_ECMP_GROUPS = 128` |

この値は `SwitchOrch::set_switch_capability()` で `MAX_NEXTHOP_GROUP_COUNT` として STATE_DB に公開され、CRM 管理の限界値にもなる (routeorch.cpp:90-93)。

---

## 2. VOQ chassis — ECMP メンバー数上限の固定 (voq スイッチタイプ)

`gMySwitchType == "voq"` のとき、ECMP メンバー数を最大 128 に制限する。

```cpp
// routeorch.cpp:95-120
attr.id = SAI_SWITCH_ATTR_MAX_ECMP_MEMBER_COUNT;
status = sai_switch_api->get_switch_attribute(gSwitchId, 1, &attr);
// ...
uint32_t maxEcmpGroupSize = attr.value.u32;
if (gMySwitchType == "voq" && maxEcmpGroupSize >= 128)
{
    maxEcmpGroupSize = 128;
    attr.id = SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT;
    attr.value.s32 = maxEcmpGroupSize;
    sai_switch_api->set_switch_attribute(gSwitchId, &attr);
}
```

**背景**: VOQ (Virtual Output Queue) chassis 構成では、複数の line card が共有 ASIC fabric を通じて経路を同期する。ECMP メンバー数が多すぎると chassis 内部のフォワーディングテーブル同期に支障が出るため、orchagent 側でハードキャップ 128 を設定する。通常の box スイッチや fabric スイッチでは SAI が返す値をそのまま使う。

| スイッチタイプ (`gMySwitchType`) | ECMP メンバー上限 |
|----------------------------------|-----------------|
| `"voq"` | min(ASIC 能力, 128) を SAI に設定 |
| その他 (`"switch"`, `"fabric"` 等) | ASIC 能力値のまま（orchagent から変更しない） |

---

## 3. SAI Bulk API 対応差 (gRouteBulker / gNextHopGroupMemberBulker)

RouteOrch は route / MPLS label route / nexthop group member の 3 種類に Bulker を使用する。

```cpp
// routeorch.cpp:41-43
gRouteBulker(sai_route_api, gMaxBulkSize),             // SAI_ROUTE_ENTRY
gLabelRouteBulker(sai_mpls_api, gMaxBulkSize),          // SAI_LABEL_ROUTE_ENTRY
gNextHopGroupMemberBulker(sai_next_hop_group_api, gSwitchId, gMaxBulkSize),
```

`gMaxBulkSize` のデフォルトは `DEFAULT_MAX_BULK_SIZE = 1000`（orchdaemon.cpp:81-82）。

Bulk API の実体は `sai_bulk_object_create_fn` / `sai_bulk_object_remove_fn` であり、SAI 実装（ASIC ベンダー）が bulk をサポートするか否かで挙動が変わる:

| SAI 実装の bulk 対応 | gRouteBulker.flush() の動作 |
|---------------------|---------------------------|
| bulk 対応 (sai_bulk_create_route_entry 実装済み) | 最大 1000 エントリをまとめて 1 回の SAI 呼び出しで渡す |
| bulk 非対応 (SAI_STATUS_NOT_IMPLEMENTED 等) | Bulker 内部でシングルエントリ呼び出しにフォールバック |

`gRouteBulker.flush()` は `doTask()` ループ末尾（routeorch.cpp:1117）でバッチ単位に呼び出される。ECMP グループが上限に達している場合は pending DEL がある時点で早期 flush が発生する（routeorch.cpp:1094-1097）。

---

## 4. 影響まとめ

| 差異ポイント | 対象プラットフォーム | 実装箇所 |
|-------------|---------------------|---------|
| ECMP グループ数上限の ÷32 補正 | Mellanox (`"mellanox"`) | routeorch.cpp:84-86 |
| ECMP メンバー数キャップ 128 | VOQ chassis (`gMySwitchType=="voq"`) | routeorch.cpp:109-117 |
| SAI Bulk API フォールバック | bulk 非対応 ASIC ベンダー | sai_bulker.h (swss-common) |
| gMaxBulkSize 調整 | 全プラットフォーム (起動引数で変更可) | orchdaemon.cpp:81-82 |
