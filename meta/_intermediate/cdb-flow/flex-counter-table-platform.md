# プラットフォーム差異分析: FLEX_COUNTER_TABLE (Phase H)

ソース: `sonic-swss/orchagent/flexcounterorch.cpp`

---

## 1. VOQ シャーシ — キューカウンタの全ポート一括登録

### 根拠コード

```cpp
// flexcounterorch.cpp L544-551
// For VOQ chassis, flexcounterorch adds the Queue Counters for all egress and VOQ queues
// of all front panel and system ports to the FLEX_COUNTER_DB irrespective of BUFFER_QUEUE configuration.
if ((!isCreateOnlyConfigDbBuffers()) || (gMySwitchType == "voq"))
{
    FlexCounterQueueStates flexCounterQueueState(0);
    queuesStateVector.insert(make_pair(createAllAvailableBuffersStr, flexCounterQueueState));
    return queuesStateVector;
}
```

### 挙動の差異

| モード | キューカウンタ登録対象 |
|--------|----------------------|
| 非 VOQ (`create_only_config_db_buffers=false`) | `BUFFER_QUEUE` テーブルに profile が設定されたポート/キューのみ |
| 非 VOQ (`create_only_config_db_buffers=true`) | `BUFFER_QUEUE` テーブルの非ゼロ profile エントリのみ |
| VOQ シャーシ (`gMySwitchType == "voq"`) | 全フロントパネルポート + システムポートの egress / VOQ キュー全部を `createAllAvailableBuffersStr` で一括登録 |

VOQ シャーシでは `create_only_config_db_buffers` 設定に関わらず、全キューが flex counter DB に登録される。

---

## 2. SAI Capability — FLOW_CNT_ROUTE の有効化条件

### 根拠コード

```cpp
// flex_counter/flow_counter_handler.cpp L51-63
bool FlowCounterHandler::queryRouteFlowCounterCapability()
{
    sai_attr_capability_t capability;
    sai_status_t status = sai_query_attribute_capability(
        gSwitchId, SAI_OBJECT_TYPE_ROUTE_ENTRY,
        SAI_ROUTE_ENTRY_ATTR_COUNTER_ID, &capability);
    if (status != SAI_STATUS_SUCCESS)
    {
        SWSS_LOG_WARN("Could not query route entry attribute SAI_ROUTE_ENTRY_ATTR_COUNTER_ID %d", status);
        return false;
    }
    return capability.set_implemented;
}
```

```cpp
// flexcounterorch.cpp L324
if (gFlowCounterRouteOrch && gFlowCounterRouteOrch->getRouteFlowCounterSupported() && key == FLOW_CNT_ROUTE_KEY)
```

### 挙動の差異

`FLOW_CNT_ROUTE` グループの `FLEX_COUNTER_STATUS=enable` は、SAI が `SAI_ROUTE_ENTRY_ATTR_COUNTER_ID` の set 操作をサポートしている場合のみ有効となる。SAI capability クエリが失敗する / `set_implemented=false` の ASIC では `FLOW_CNT_ROUTE` は無操作となる。

---

## 3. DASH / SmartSwitch (DPU) — ENI / DASH_METER / HA_SET グループ

### 根拠コード

```cpp
// flexcounterorch.cpp L162-163, L299-310
DashOrch* dash_orch = gDirectory.get<DashOrch*>();
DashHaOrch* dash_ha_orch = gDirectory.get<DashHaOrch*>();
...
if (dash_orch && (key == ENI_KEY))
    dash_orch->handleFCStatusUpdate((value == "enable"));
if (dash_orch && (key == DASH_METER_KEY))
    dash_orch->handleMeterFCStatusUpdate((value == "enable"));
if (dash_ha_orch && (key == HA_SET_KEY))
    dash_ha_orch->handleHaSetFCStatusUpdate((value == "enable"));
```

`DashOrch` / `DashHaOrch` は DPU OrchDaemon でのみインスタンス化される (`orchdaemon.cpp DpuOrchDaemon::init()`)。非 DPU (通常 NPU) 環境では `gDirectory.get<DashOrch*>()` が nullptr を返すため、`ENI` / `DASH_METER` / `HA_SET` グループの `FLEX_COUNTER_STATUS` 変更は無操作となる。

| プラットフォーム | ENI / DASH_METER / HA_SET グループ動作 |
|-----------------|---------------------------------------|
| DPU (SmartSwitch の DPU サイド) | `DashOrch` / `DashHaOrch` が有効。グループ enable/disable が DashOrch に通知される |
| 通常 NPU / non-SmartSwitch | `dash_orch == nullptr` のためグループ変更は無操作 |

---

## 4. FabricPortsOrch — Fabric ポートキュー統計

### 根拠コード

```cpp
// flexcounterorch.cpp L291-294
if (gFabricPortsOrch)
{
    gFabricPortsOrch->generateQueueStats();
}
```

`gFabricPortsOrch` は Fabric Chassis 向けの OrchDaemon (`FabricOrchDaemon`) およびメイン OrchDaemon で有効化された場合にのみ非 nullptr となる。通常の非 Fabric 構成では `gFabricPortsOrch == nullptr` のため、flex counter enable 時にキュー統計生成コールが skip される。

---

## まとめ

| 差異点 | 条件 | 通常 NPU との違い |
|--------|------|-----------------|
| QUEUE カウンタ登録範囲 | `gMySwitchType == "voq"` | 全ポート・全キューを一括登録 |
| FLOW_CNT_ROUTE 有効化 | SAI `SAI_ROUTE_ENTRY_ATTR_COUNTER_ID` capability | capability なし ASIC では無効 |
| ENI / DASH_METER / HA_SET | DPU (SmartSwitch) のみ | 非 DPU では無操作 |
| Fabric ポートキュー統計 | FabricPortsOrch 有効時 | 非 Fabric 構成では skip |
