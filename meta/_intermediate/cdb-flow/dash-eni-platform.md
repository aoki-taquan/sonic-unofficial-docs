# dash-eni-platform.md — Phase H 調査メモ

> 調査日: 2026-05-17  
> ソース: `sonic-net/sonic-swss` @ 4305596156d70e9797e8a881b3d19b46de0bce0d  
> 主要ファイル: `orchagent/dash/dashorch.cpp`, `orchagent/dash/dashorch.h`, `orchagent/main.cpp`, `orchagent/orchdaemon.cpp`

## 1. 動作条件: switch_type=dpu のみ

`main.cpp:990-994` で `gMySwitchType == "dpu"` の場合のみ `DpuOrchDaemon` が生成される。`DashOrch` は `DpuOrchDaemon::init()` (`orchdaemon.cpp:1322-1418`) で `m_dpu_appDb`（`DPU_APPL_DB`）・`m_dpu_appstateDb`（`DPU_APPL_STATE_DB`）を引数として登録される。

```
gMySwitchType は CONFIG_DB:DEVICE_METADATA:localhost:switch_type から取得
getCfgSwitchType() — main.cpp:242-268
```

| switch_type | DashOrch 起動 | 備考 |
|-------------|--------------|------|
| `"dpu"` | **起動** | SmartSwitch の DPU ロール。DPU_APPL_DB を購読 |
| `""` / `"switch"` / `"voq"` / `"fabric"` / `"chassis-packet"` | **不起動** | 通常 T0/T1 / VOQ chassis / fabric blade |
| SmartSwitch NPU 側 (`sub_type=SmartSwitch` かつ `switch_type=switch`) | **不起動** | NPU は orchdaemon.cpp:613 で DashEniFwdOrch のみ登録 |

## 2. SmartSwitch NPU 側: DashEniFwdOrch

SmartSwitch 構成では NPU 側 (`gMySwitchSubType == "SmartSwitch"`) に `DashEniFwdOrch` が別途起動する（`orchdaemon.cpp:613-615`）。これは `DASH_ENI_TABLE` ではなく `APP_DASH_ENI_FORWARD_TABLE` を処理し、ENI を DPU に転送するための ACL ルールをインストールする。`DashOrch` / `DASH_ENI_TABLE` への直接関与はない。

## 3. SAI DASH ENI API — ベンダー分岐なし

`dashorch.cpp:39` で `extern sai_dash_eni_api_t* sai_dash_eni_api;` を参照。`addEniObject()` は `sai_dash_eni_api->create_eni(&eni_id, gSwitchId, ...)` を呼び出すのみで、ベンダー固有の環境変数（`platform` / `sub_platform` 等）参照は一切存在しない。SAI DASH Extension API がベンダー差を抽象化している。

## 4. SAI capability クエリ: SAI_ENI_ATTR_IS_HA_FLOW_OWNER

`dashorch.cpp:102-125` — `isHaFlowOwnerAttrSupported()` が `sai_query_attribute_capability()` で SAI ASIC の HA flow owner 属性サポートを実行時検出する。

```cpp
std::call_once(m_ha_flow_owner_attr_once_flag, [this]() {
    sai_attr_capability_t capability;
    sai_status_t status = sai_query_attribute_capability(
            gSwitchId,
            (sai_object_type_t)SAI_OBJECT_TYPE_ENI,
            SAI_ENI_ATTR_IS_HA_FLOW_OWNER,
            &capability);

    if (status != SAI_STATUS_SUCCESS) {
        m_ha_flow_owner_attr_supported = false;
    } else {
        m_ha_flow_owner_attr_supported = capability.set_implemented || capability.create_implemented;
    }
});
```

これが **唯一の SAI capability 条件分岐**であり、ベンダーによって実装状況が異なり得る。`isHaFlowOwnerAttrSupported()` が `false` の場合、ENI 作成時に `SAI_ENI_ATTR_IS_HA_FLOW_OWNER` を push しない（`dashorch.cpp:692-715`）。

## 5. SAI_DASH_APPLIANCE_ATTR_LOCAL_REGION_ID capability クエリ

`dashorch.cpp:141-148` — appliance 作成時に `SAI_DASH_APPLIANCE_ATTR_LOCAL_REGION_ID` の capability を問い合わせ、`create_implemented` の場合のみ属性を push する。ENI 作成に直接影響するのは appliance 経由（`appliance_entries_` を ENI が参照）。

## 6. FlexCounter ポーリング間隔（ハードコード）

`dashorch.h:30, 33` の `10000 ms` はすべての DPU ベンダー共通。動的変更機能なし。

## 7. IPv4 / IPv6 差異

CRM カウンタは `CRM_DASH_ENI` と `CRM_DASH_ENI_ETHER_ADDRESS_MAP` のみで、アドレスファミリ分岐なし。ENI のアンダーレイ IP は protobuf `IpAddress` 型で IPv4/IPv6 を内包するが、orchagent コードは `to_sai()` に委任するだけでアドレスファミリの独自分岐はしない。

## 8. gMaxBulkSize / バルク処理

`dashorch.cpp` の SET/DEL 処理にバルク処理（`bulker_`）は使用していない。`ZmqConsumerStateTable` の `gBatchSize=128` が一度に処理するエントリ数の上限。DPU ベンダー別のデフォルト差なし。

## 結論

- 伝統的な ASIC ベンダー（mellanox / broadcom / barefoot 等）の条件分岐は dashorch.cpp に一切存在しない
- 唯一のプラットフォーム差: `SAI_ENI_ATTR_IS_HA_FLOW_OWNER` の実行時 capability 検出（ベンダー SAI 実装依存）
- `switch_type=dpu` 専用起動。T0/T1 では DashOrch は登録されない
- SmartSwitch NPU 側は `DashEniFwdOrch` のみ（DASH_ENI_TABLE は処理しない）
