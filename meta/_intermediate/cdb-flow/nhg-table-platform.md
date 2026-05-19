# NEXTHOP_GROUP_TABLE / CLASS_BASED_NEXT_HOP_GROUP_TABLE — プラットフォーム差調査

調査日: 2026-05-19
フェーズ: Phase H

## 調査対象ファイル

- `sonic-swss/orchagent/routeorch.cpp` (`RouteOrch` コンストラクタ: L40-L130)
- `sonic-swss/orchagent/routeorch.h` (`getMaxNhgCount()`: L267)
- `sonic-swss/orchagent/nhgorch.cpp` (`NhgOrch::doTask()` 上限チェック: L252, L320)
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp` (`CbfNhgOrch::doTask()` 上限チェック: L100)
- `sonic-swss/orchagent/cbf/nhgmaporch.cpp` (`NhgMapOrch` コンストラクタ: L24-L33)
- `sonic-swss/orchagent/orch.h` (プラットフォーム識別文字列定数: L40-L49)
- `sonic-swss/orchagent/nhgbase.h` (`getSyncedCount()` assert: L449)

---

## 1. Mellanox ASIC 限定: ECMP グループ数の補正

`RouteOrch` コンストラクタ (`routeorch.cpp:61-88`) が `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` を取得後、`getenv("platform")` 文字列に `MLNX_PLATFORM_SUBSTRING == "mellanox"` が含まれる場合のみ:

```cpp
// routeorch.cpp:83-87
char *platform = getenv("platform");
if (platform && strstr(platform, MLNX_PLATFORM_SUBSTRING))
{
    m_maxNextHopGroupCount /= DEFAULT_MAX_ECMP_GROUP_SIZE; // 32
}
```

定数定義 (`routeorch.cpp:37-38`):
```cpp
#define DEFAULT_NUMBER_OF_ECMP_GROUPS   128
#define DEFAULT_MAX_ECMP_GROUP_SIZE     32
```

**意味**: Mellanox 上の SAI は「ECMP グループサイズ = 1 (単一メンバ)」を前提として総 NHG 数を返す。実際の運用では 1 グループ最大 32 メンバが使われるため、戻り値を 32 で割って実際の最大グループ数に補正する。SAI 取得失敗時はデフォルト 128 にフォールバック。

この補正後の `m_maxNextHopGroupCount` が `NhgOrch::doTask()` L252 / L320 および `CbfNhgOrch::doTask()` L100 の上限チェックに使われる。これを超えると temporary NHG 作成または `success=false` での再試行が発動する。

**他プラットフォームへの影響なし**: Broadcom / Marvell / Cisco Silicon One / VS / xsight 等では SAI が返した値をそのまま採用する。

---

## 2. VOQ chassis: ECMP メンバ数を 128 に強制

`routeorch.cpp:95-124` で `SAI_SWITCH_ATTR_MAX_ECMP_MEMBER_COUNT` を取得し、`gMySwitchType == "voq"` かつ取得値 >= 128 のとき `SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT` を 128 に **書き戻す**:

```cpp
// routeorch.cpp:109-122
if (gMySwitchType == "voq" && maxEcmpGroupSize >= 128)
{
    maxEcmpGroupSize = 128;
    attr.id = SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT;
    attr.value.s32 = maxEcmpGroupSize;
    status = sai_switch_api->set_switch_attribute(gSwitchId, &attr);
    ...
}
```

`gMySwitchType` は `CONFIG_DB:DEVICE_METADATA|localhost:switch_type` 由来。値は `switch` (fixed pizzabox) / `voq` (distributed VOQ chassis) / `chassis-packet` / `dpu`。T0/T1 fixed (switch_type=switch) では本書き換えは発生しない。

VOQ chassis では各 line card の `NEXTHOP_GROUP_TABLE` エントリが 128 メンバを超えると SAI が切り詰める可能性があるが、`NhgOrch` 側に追加ガードは存在せず、SAI が返すエラーに委ねられる。

---

## 3. CBF NHG マップ: SAI capability 依存

`NhgMapOrch` コンストラクタ (`nhgmaporch.cpp:24-33`) で `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS` の代わりに `SAI_NEXT_HOP_GROUP_ATTR_TYPE` 系の能力 (`SAI_OBJECT_TYPE_NEXT_HOP_GROUP_MAP`) の最大数を SAI に問い合わせる:

```cpp
// nhgmaporch.cpp:24-33
sai_status_t status = sai_switch_api->get_switch_attribute(
    gSwitchId, 1, &attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_WARN("Switch does not support NHG maps");
    m_max_nhg_map_count = 0;
}
```

**SAI がサポートしない場合 `m_max_nhg_map_count = 0`** → `nhgmaporch.cpp:105` の上限チェック `m_syncdMaps.size() >= m_max_nhg_map_count` が常に true となり、`FC_TO_NHG_INDEX_MAP_TABLE` の SET が全件 reject される。`CLASS_BASED_NEXT_HOP_GROUP_TABLE` は `selection_map` 参照がこのマップを前提とするため、CBF NHG 機能全体が使用不可となる。

この制限はプラットフォーム識別文字列による静的分岐ではなく、**実行時 SAI 問い合わせ**による動的判断であるため、community SAI がサポートを宣言するかどうかで変わる。

---

## 4. SRv6 NHG: ASIC SAI capability 依存

`nhgorch.cpp:200-201` で SRv6 NHG (`srv6_nh=true`) の場合に `NextHopGroupKey` を `overlay_nh=false, srv6_nh=true` で構築し、SAI に `SAI_NEXT_HOP_TYPE_SRV6_SIDLIST` のネクストホップを作成する。SAI 実装がこの type をサポートしない場合、`sai_next_hop_api->create_next_hop` が `SAI_STATUS_NOT_SUPPORTED` を返す。

また、SRv6 NHG は temporary NHG 作成ロジックを経由せず `++it` でスキップされる (`nhgorch.cpp:257-261`):
```cpp
// nhgorch.cpp:257-261  
if (nhg_key.is_srv6_nexthop()) {
    ++it;
    continue;
}
```
このため SRv6 NHG は上限到達時に temporary NHG へ降格できず、SAI リソースが解放されるまで pending のままになる。

community master 実装では Broadcom DNX / Mellanox Spectrum-4 (SN5xxx) の一部 SKU で SRv6 が動作し、VS/vpp はスタブ実装。

---

## 5. VS / VPP プラットフォーム

`VS_PLATFORM_SUBSTRING="vs"` の場合、SAI シム (libsaivs) が ECMP グループ作成を常に成功させるが ASIC へは反映しない。`m_maxNextHopGroupCount` 補正は Mellanox 限定のため VS では SAI が返す既定値 (多くは 128 や 1024) がそのまま採用される。CBF NHG は SAI が `m_max_nhg_map_count > 0` を返せば動作する (VS では通常 0 以外)。

---

## まとめ

| 差異 | 対象プラットフォーム / 条件 | NHG テーブルへの影響 |
|------|---------------------------|----------------------|
| ECMP グループ数の補正 (`/= 32`) | Mellanox のみ (`MLNX_PLATFORM_SUBSTRING`) | `m_maxNextHopGroupCount` が SAI 生値 / 32 に縮小 → temp NHG 発動閾値が低くなる |
| ECMP メンバ数を 128 に強制 | VOQ chassis (`switch_type=voq`) | 128 メンバ超の NEXTHOP_GROUP_TABLE エントリは SAI で切り詰めの可能性 |
| CBF NHG マップ上限 = 0 | SAI が NHG map type 未サポートの ASIC | FC_TO_NHG_INDEX_MAP_TABLE の SET 全件 reject → CBF NHG 全体が無効 |
| SRv6 NHG の temp NHG 非対応 | SRv6 NHG を持つ全プラットフォーム | 上限到達時に temporary NHG に降格できず、SAI リソース解放まで pending |
| SRv6 NHG SAI 非サポート | SRv6 未対応 ASIC | `SAI_STATUS_NOT_SUPPORTED` → `SWSS_LOG_ERROR` + NHG 作成失敗 |

## 証拠リンク

- `sonic-swss/orchagent/routeorch.cpp:37-38` — 定数定義
- `sonic-swss/orchagent/routeorch.cpp:61-124` — `RouteOrch` コンストラクタ (Mellanox 補正 / VOQ 書き戻し)
- `sonic-swss/orchagent/routeorch.h:267` — `getMaxNhgCount()`
- `sonic-swss/orchagent/nhgorch.cpp:252,320` — NhgOrch 上限チェック
- `sonic-swss/orchagent/cbf/cbfnhgorch.cpp:100-104` — CbfNhgOrch 上限チェック
- `sonic-swss/orchagent/cbf/nhgmaporch.cpp:24-33,105` — NHG マップ上限取得
- `sonic-swss/orchagent/nhgorch.cpp:257-261` — SRv6 NHG の temp NHG スキップ
- `sonic-swss/orchagent/orch.h:41-49` — プラットフォーム識別文字列定数
