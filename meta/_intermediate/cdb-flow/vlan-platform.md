# VLAN テーブル — プラットフォーム差 (Phase H)

調査日: 2026-05-15
調査対象:
- sonic-swss/orchagent/portsorch.cpp
- sonic-swss/orchagent/orch.h (PLATFORM_SUBSTRING 定数群)
- sonic-sairedis/vslib/SwitchStateBase.cpp
- sonic-swss/cfgmgr/vlanmgr.cpp

---

## 検出したプラットフォーム差

### 1. SAI Flood control capability — `SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED` 非対応 ASIC

**検出箇所**: `portsorch.cpp:900-931`, `portsorch.cpp:7517-7524`

```cpp
// portsorch.cpp:900-911 (初期化時)
if (sai_query_attribute_enum_values_capability(gSwitchId, SAI_OBJECT_TYPE_VLAN,
                                               SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_CONTROL_TYPE,
                                               &values) != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_NOTICE("This device does not support unknown unicast flood control types");
}
else
{
    for (uint32_t idx = 0; idx < values.count; idx++)
    {
        uuc_sup_flood_control_type.insert(...);
    }
}

// portsorch.cpp:7517-7524 (VLAN メンバ追加時)
if ((uuc_sup_flood_control_type.find(SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED)
     == uuc_sup_flood_control_type.end()) ||
    (bc_sup_flood_control_type.find(SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED)
     == bc_sup_flood_control_type.end()))
{
    SWSS_LOG_ERROR("Flood group with end point ip is not supported");
    return false;
}
```

- 起動時に `sai_query_attribute_enum_values_capability()` で UUC/BC の flood control タイプを問い合わせ、`COMBINED` をサポートしない ASIC では VXLAN EVPN エンドポイントを用いた flood group 設定が **エラー終了**
- VS (virtual switch) SAI は `SAI_VLAN_FLOOD_CONTROL_TYPE_ALL`, `NONE`, `L2MC_GROUP` の 3 種のみ返す (`SwitchStateBase.cpp:4145-4147`)。`COMBINED` を返さないため、VS 環境では EVPN flood group は設定不可
- Broadcom TD3/TH 系 SAI は `COMBINED` をサポートするケースあり。Mellanox SAI は SAI バージョン依存

**影響フィールド**: VLAN テーブル自体でなく `VLAN_MEMBER` の `end_point_ip` 設定が対象。ただし VLAN の flood 動作全体に影響

### 2. SAI create_vlan() 属性最小化 — ベンダー SAI のデフォルト依存

**検出箇所**: `portsorch.cpp:7387-7410`

```cpp
sai_vlan_id_t vlan_id = (uint16_t)stoi(vlan_alias.substr(4));
sai_attribute_t attr;
attr.id = SAI_VLAN_ATTR_VLAN_ID;
attr.value.u16 = vlan_id;

sai_status_t status = sai_vlan_api->create_vlan(&vlan_oid, gSwitchId, 1, &attr);
// ...
vlan.m_vlan_info.uuc_flood_type = SAI_VLAN_FLOOD_CONTROL_TYPE_ALL;
vlan.m_vlan_info.bc_flood_type = SAI_VLAN_FLOOD_CONTROL_TYPE_ALL;
```

- `create_vlan()` は `SAI_VLAN_ATTR_VLAN_ID` **1 属性のみ**で呼び出す
- flooding control (`SAI_VLAN_ATTR_UNKNOWN_UNICAST_FLOOD_CONTROL_TYPE` 等) はデフォルト (`ALL`) のまま SAI に委ねる
- プラットフォームによっては SAI デフォルトが `ALL` と異なるケースがあり、VLAN 作成直後の flooding 挙動がベンダー SAI 実装依存になる

### 3. SAI_HOSTIF_VLAN_TAG — ベンダー間の段階的サポート

**検出箇所**: `portsorch.cpp:3043-3045`, `portsorch.cpp:438-440`

```cpp
/*
 * Before SAI_HOSTIF_VLAN_TAG_ORIGINAL is supported by libsai from all asic vendors,
 * the VLAN tag on hostif is explicitly controlled with SAI_HOSTIF_VLAN_TAG_STRIP &
 * SAI_HOSTIF_VLAN_TAG_KEEP attributes.
 */
```

コード定義:
```cpp
[SAI_HOSTIF_VLAN_TAG_STRIP]     = "SAI_HOSTIF_VLAN_TAG_STRIP",
[SAI_HOSTIF_VLAN_TAG_KEEP]      = "SAI_HOSTIF_VLAN_TAG_KEEP",
[SAI_HOSTIF_VLAN_TAG_ORIGINAL]  = "SAI_HOSTIF_VLAN_TAG_ORIGINAL"
```

- `SAI_HOSTIF_VLAN_TAG_ORIGINAL` は全ベンダー SAI で未サポートの期間があり、コメントに明記
- 現状 orchagent は VLAN メンバ追加時に `STRIP` / `KEEP` を条件で切り替える方式で回避している
- これにより CPU ポートへのパケット受信時の VLAN タグ有無がベンダー実装で異なる可能性がある

### 4. Mellanox/NVIDIA — isMlnxPlatform() 分岐 (VLAN 間接影響)

**検出箇所**: `portsorch.cpp:689-704`, `orch.h:42`

```cpp
#define MLNX_PLATFORM_SUBSTRING "mellanox"

static bool isMlnxPlatform()
{
    const auto *platform = std::getenv("platform");
    if (platform == nullptr) return false;
    return std::strstr(platform, MLNX_PLATFORM_SUBSTRING) != nullptr;
}
```

- `isMlnxPlatform()` はポートトリム統計 (`SAI_PORT_STAT_TRIM_PACKETS`) の有無判定に使われる
- VLAN 直接の分岐ではないが、`platform` 環境変数による分岐の仕組みは VLAN 周辺コードでも潜在的に適用される

定義済みプラットフォーム識別子:

| 定数 | 値 |
|------|----|
| `MLNX_PLATFORM_SUBSTRING` | `"mellanox"` |
| `BRCM_PLATFORM_SUBSTRING` | `"broadcom"` |
| `BRCM_DNX_PLATFORM_SUBSTRING` | `"broadcom-dnx"` |
| `BFN_PLATFORM_SUBSTRING` | `"barefoot"` |
| `VS_PLATFORM_SUBSTRING` | `"vs"` |
| `NPS_PLATFORM_SUBSTRING` | `"nephos"` |
| `CISCO_8000_PLATFORM_SUBSTRING` | `"cisco-8000"` |
| `XS_PLATFORM_SUBSTRING` | `"xsight"` |
| `CLX_PLATFORM_SUBSTRING` | `"clounix"` |
| `MRVL_PRST_PLATFORM_SUBSTRING` | `"marvell-prestera"` |
| `MRVL_TL_PLATFORM_SUBSTRING` | `"marvell-teralynx"` |

### 5. VS (Virtual Switch) — VLAN flood capability が COMBINED を含まない

**検出箇所**: `sonic-sairedis/vslib/SwitchStateBase.cpp:4134-4149`

```cpp
sai_status_t SwitchStateBase::queryVlanfloodTypeCapability(
               _Inout_ sai_s32_list_t *enum_values_capability)
{
    enum_values_capability->count = 3;
    enum_values_capability->list[0] = SAI_VLAN_FLOOD_CONTROL_TYPE_ALL;
    enum_values_capability->list[1] = SAI_VLAN_FLOOD_CONTROL_TYPE_NONE;
    enum_values_capability->list[2] = SAI_VLAN_FLOOD_CONTROL_TYPE_L2MC_GROUP;
    return SAI_STATUS_SUCCESS;
}
```

- VS SAI が返す flood control タイプは 3 種のみ (`ALL`, `NONE`, `L2MC_GROUP`)
- `SAI_VLAN_FLOOD_CONTROL_TYPE_COMBINED` が含まれないため、VS 上では EVPN BUM flooding のための flood group 設定が不可
- テスト環境 (VS) と実機 (Broadcom/Mellanox) で EVPN 動作が異なる根拠となるコード

---

## 結論

| 差の性質 | 対象 ASIC | 影響 |
|---------|---------|------|
| `COMBINED` flood control 非対応 | VS SAI / 一部 ASIC | EVPN flood group (`end_point_ip`) 設定不可 |
| `create_vlan()` の属性最小化 | 全 ASIC | 初期 flooding 挙動がベンダー SAI デフォルト依存 |
| `SAI_HOSTIF_VLAN_TAG_ORIGINAL` 未対応 | 旧世代 ASIC / 未実装ベンダー | CPU ポートの VLAN タグ有無がベンダー実装依存 |
| `platform` 環境変数分岐 | 識別済み 11 プラットフォーム | VLAN 周辺動作でベンダー特殊処理の潜在的差異 |
| VS flood capability 制限 | VS (Virtual Switch) | EVPN 関連 VLAN メンバ操作が実機と異なる |
