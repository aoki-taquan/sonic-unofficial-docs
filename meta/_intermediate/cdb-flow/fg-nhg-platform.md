# FG_NHG — Phase H プラットフォーム差異 調査ログ

**調査日**: 2026-05-16  
**ソース**: `sonic-swss/orchagent/fgnhgorch.cpp`  
**フェーズ**: Phase H（プラットフォーム差）

---

## 1. VS プラットフォーム: `real_bucket_size` 省略

### 証拠コード

`fgnhgorch.cpp` の `createFineGrainedNextHopGroup()` 関数 (L257–315):

```cpp
string platform = getenv("platform") ? getenv("platform") : "";
// ...
nhg_attr.id = SAI_NEXT_HOP_GROUP_ATTR_TYPE;
nhg_attr.value.s32 = SAI_NEXT_HOP_GROUP_TYPE_FINE_GRAIN_ECMP;
nhg_attrs.push_back(nhg_attr);

nhg_attr.id = SAI_NEXT_HOP_GROUP_ATTR_CONFIGURED_SIZE;
nhg_attr.value.s32 = fgNhgEntry->configured_bucket_size;
nhg_attrs.push_back(nhg_attr);

// ...NHG 作成後...

if (platform == VS_PLATFORM_SUBSTRING)  // "vs" (orch.h L46)
{
   /* TODO: need implementation for SAI_NEXT_HOP_GROUP_ATTR_REAL_SIZE */
    fgNhgEntry->real_bucket_size = fgNhgEntry->configured_bucket_size;
}
else
{
    nhg_attr.id = SAI_NEXT_HOP_GROUP_ATTR_REAL_SIZE;
    nhg_attr.value.u32 = 0;
    sai_status_t status = sai_next_hop_group_api->get_next_hop_group_attribute(
        next_hop_group_id, 1, &nhg_attr);
    if (status != SAI_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to query next hop group %s SAI_NEXT_HOP_GROUP_ATTR_REAL_SIZE, rv:%d",
                   nextHops.to_string().c_str(), status);
        // ロールバック + return false
    }
    fgNhgEntry->real_bucket_size = nhg_attr.value.u32;
}
```

### VS_PLATFORM_SUBSTRING 定義

`orchagent/orch.h` L46:
```cpp
#define VS_PLATFORM_SUBSTRING   "vs"
```

### 影響

- VS 環境: `real_bucket_size = configured_bucket_size`（設定値をそのまま使用）
- 実 ASIC: SAI クエリにより ASIC の実際のバケット数を取得（ハードウェアアライメントにより設定値より大きくなる場合あり）
- `real_bucket_size` は NHG member のリサイズ・バンク割り当て計算 (`calculateBankHashBucketStartIndices`) に使用されるため、VS と実機で挙動が異なる

---

## 2. SAI Fine-Grained ECMP 未対応 ASIC の動作

### 証拠コード

`routeorch.cpp` の `createFineGrainedNextHopGroup()` (L1420–1448):

```cpp
sai_status_t status = sai_next_hop_group_api->create_next_hop_group(&next_hop_group_id,
                                                  gSwitchId,
                                                  (uint32_t)nhg_attrs.size(),
                                                  nhg_attrs.data());
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create next hop group rv:%d", status);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_NEXT_HOP_GROUP, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- ASIC が `SAI_NEXT_HOP_GROUP_TYPE_FINE_GRAIN_ECMP` をサポートしない場合、`create_next_hop_group` が失敗
- `fgnhgorch.cpp:277` で `"Failed to create next hop group %s"` を SWSS_LOG_ERROR 出力後 `return false`
- CONFIG_DB の FG_NHG エントリは削除されず残存

---

## 3. VRF 制約 — デフォルト VRF のみ対応

### 証拠コード

`fgnhgorch.cpp` の `isRouteFineGrained()` (L1201–1251):

```cpp
if (!isFineGrainedConfigured || (vrf_id != gVirtualRouterId))
{
    SWSS_LOG_DEBUG("Route %s:%s vrf %" PRIx64 " default_vrf %" PRIx64 " NOT fine grained ECMP",
                    ipPrefix.to_string().c_str(), nextHops.to_string().c_str(), vrf_id, gVirtualRouterId);
    return false;
}
```

同様に `syncdContainsFgNhg()` (L1254–1272) でも同チェックあり。

また `doTaskFgNhgPrefix()` (L1850, L1900) での FG prefix 処理は `gVirtualRouterId` をハードコードして使用:
```cpp
sai_object_id_t vrf_id = gVirtualRouterId;
```

### 影響

- 非デフォルト VRF (`ip vrf <name>`) に所属するルートには FG ECMP が適用されない
- `FG_NHG_PREFIX` を設定しても非デフォルト VRF のルートには無視される
- ログ: `SWSS_LOG_DEBUG` レベルのため通常 syslog には出力されない

---

## 4. VOQ / Chassis 構成

### コード調査結果

`fgnhgorch.cpp` 全 2164 行を検索した結果、以下のキーワードは存在しなかった:
- `VOQ`, `voq`, `isVoq`
- `chassis`, `CHASSIS`
- `system_port`, `inband`
- `cpu_port`

→ FgNhgOrch に VOQ chassis 固有の分岐は存在しない。

### 推定される影響

1. **VRF 制約の波及**: VOQ chassis では複数スライスにまたがる VRF が存在する場合があるが、FG ECMP はデフォルト VRF のみ対応のため影響を受ける可能性がある
2. **Port oper-state 追跡**: `fgnhgorch.cpp:1377` で `Port::PHY` 型のみ link 追跡対象としており、chassis 構成でのポート扱いが異なる場合に注意が必要

---

## まとめ

| 差異カテゴリ | 内容 | コード箇所 |
|---|---|---|
| VS プラットフォーム | `real_bucket_size` を SAI クエリせず `configured_bucket_size` を代入 | fgnhgorch.cpp:284–308 |
| SAI 非対応 ASIC | FG NHG 作成失敗 → `return false` (CONFIG_DB エントリは残存) | routeorch.cpp:1431–1442 |
| 非デフォルト VRF | FG ECMP 適用対象外（デフォルト VRF のみ対応） | fgnhgorch.cpp:1205, 1256 |
| VOQ chassis | 明示的分岐なし（動作保証外） | — |
