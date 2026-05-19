# dpu-orch 副次 DB 書込 (Phase F) — スキャン証跡

調査日: 2026-05-19  
対象: `sonic-net/sonic-swss` HEAD

## 調査方針

`DpuOrchDaemon::init()` が生成する全 DASH Orch の `writeResultToDB()` / `removeResultFromDB()` 呼出し、および追加の DB 書込みを全ファイル精読。

## `writeResultToDB` 定義

`orchagent/saihelper.cpp:1125-1155`

```cpp
void writeResultToDB(const std::unique_ptr<swss::Table>& table, const string& key,
                     uint32_t res, const string& version)
{
    std::vector<FieldValueTuple> fvVector;
    fvVector.emplace_back("result", std::to_string(res));
    if (!version.empty()) { fvVector.emplace_back("version", version); }
    table->set(key, fvVector);
}
```

`res=0` = SAI_STATUS_SUCCESS、`res!=0` = 失敗コード。`version` は `DashRouteOrch::doTaskRouteGroupTable()` のみ付与。

## DPU_APPL_STATE_DB へのテーブル別書込一覧

各 DASH Orch コンストラクタに `m_dpu_appstateDb`（`DPU_APPL_STATE_DB`）が渡され、result table を `swss::Table` として保持する。

### DashVnetOrch (orchdaemon.cpp:1339)

- `result_table_`: `APP_DASH_VNET_TABLE_NAME` = `"DASH_VNET_TABLE"` — `writeResultToDB` at `dashvnetorch.cpp:217,283`
- `dash_vnet_map_result_table_`: `APP_DASH_VNET_MAPPING_TABLE_NAME` = `"DASH_VNET_MAPPING_TABLE"` — at `dashvnetorch.cpp:788,851`

### DashOrch (orchdaemon.cpp:1350)

- `dash_appliance_result_table_`: `APP_DASH_APPLIANCE_TABLE_NAME` = `"DASH_APPLIANCE_TABLE"` — at `dashorch.cpp:419`
- `dash_routing_type_result_table_`: `APP_DASH_ROUTING_TYPE_TABLE_NAME` = `"DASH_ROUTING_TYPE_TABLE"` — at `dashorch.cpp:517`
- `dash_eni_result_table_`: `APP_DASH_ENI_TABLE_NAME` = `"DASH_ENI_TABLE"` — at `dashorch.cpp:1077`
- `dash_qos_result_table_`: `APP_DASH_QOS_TABLE_NAME` = `"DASH_QOS_TABLE"` — at `dashorch.cpp:1159`
- `dash_eni_route_result_table_`: `APP_DASH_ENI_ROUTE_TABLE_NAME` = `"DASH_ENI_ROUTE_TABLE"` — at `dashorch.cpp:1312`

### DashHaOrch (orchdaemon.cpp:1359)

- `dash_ha_set_result_table_`: `APP_DASH_HA_SET_TABLE_NAME` = `"DASH_HA_SET_TABLE"` — at `dashhaorch.cpp:447`
- `dash_ha_scope_result_table_`: `APP_DASH_HA_SCOPE_TABLE_NAME` = `"DASH_HA_SCOPE_TABLE"` — at `dashhaorch.cpp:985`

### DashRouteOrch (orchdaemon.cpp:1368)

- `dash_route_result_table_`: `APP_DASH_ROUTE_TABLE_NAME` = `"DASH_ROUTE_TABLE"` — at `dashrouteorch.cpp:342,403`
- `dash_route_rule_result_table_`: `APP_DASH_ROUTE_RULE_TABLE_NAME` = `"DASH_ROUTE_RULE_TABLE"` — at `dashrouteorch.cpp:644,705`
- `dash_route_group_result_table_`: `APP_DASH_ROUTE_GROUP_TABLE_NAME` = `"DASH_ROUTE_GROUP_TABLE"` — at `dashrouteorch.cpp:874` (version 付与あり)

### DashAclOrch (orchdaemon.cpp:1378)

`DashAclOrch` コンストラクタは `app_state_db` を受け取るが、`DashAclOrch` 自身はこれを result_table に使用しない (`dashaclorch.cpp:77-85` — result_table メンバなし)。`DashAclGroupMgr` / `DashTagMgr` も state_db 書込なし。

### DashTunnelOrch (orchdaemon.cpp:1384)

- `dash_tunnel_result_table_`: `APP_DASH_TUNNEL_TABLE_NAME` = `"DASH_TUNNEL_TABLE"` — at `dashtunnelorch.cpp:142,197,251`

### DashMeterOrch (orchdaemon.cpp:1392)

`app_state_db` を受け取るが result_table メンバを持たない (`dashmeterorch.cpp:27-32`)。`writeResultToDB` 呼出しなし。

### DashPortMapOrch (orchdaemon.cpp:1399)

- `dash_port_map_result_table_`: `APP_DASH_OUTBOUND_PORT_MAP_TABLE_NAME` = `"DASH_OUTBOUND_PORT_MAP_TABLE"` — at `dashportmaporch.cpp:89,149`
- `dash_port_map_range_result_table_`: `APP_DASH_OUTBOUND_PORT_MAP_RANGE_TABLE_NAME` = `"DASH_OUTBOUND_PORT_MAP_RANGE_TABLE"` — at `dashportmaporch.cpp:329,387`
- `removeResultFromDB` 呼出しあり (at `dashportmaporch.cpp:101,156,341,394`)

### DashHaFlowOrch (orchdaemon.cpp:1406)

`app_state_db`（`DPU_APPL_STATE_DB`）を受け取るが使用しない。代わりに自コンストラクタ内で `DBConnector("DPU_STATE_DB", ...)` を新規生成し (`dashhafloworch.cpp:766`)、`FlowApiHandler::m_state_table` として `STATE_DASH_FLOW_SYNC_SESSION_STATE_TABLE_NAME` = `"DASH_FLOW_SYNC_SESSION_STATE_TABLE"` への書込みに使用する (`dashhafloworch.cpp:247,307`)。

これは `DPU_APPL_STATE_DB` ではなく `DPU_STATE_DB` への書込みである点に注意。

## removeResultFromDB の挙動

`saihelper.cpp:1157-1177` — `table->del(key)` を呼ぶ。失敗時は SWSS_LOG_ERROR を出力して return（例外を飲み込む）。`DashPortMapOrch` のみが `removeResultFromDB` を呼ぶ。他の DASH Orch は SET オペレーションで result を `0` (SUCCESS) に上書きする（DEL ではなく result=0 で「削除成功」を表現）。

## ASIC_DB への副次書込

`DashHaFlowOrch` は `registerFlowBulkGetSessionNotifier()` にて SAI switch 属性 `SAI_SWITCH_ATTR_FLOW_BULK_GET_SESSION_EVENT_NOTIFY` を設定し、ASIC_DB NOTIFICATIONS チャンネルを購読する (`dashhafloworch.cpp:782-786`)。これは CONFIG_DB / APPL_DB への書込ではない。

## 結論

`DpuOrchDaemon` 配下の DASH Orch は、SAI API 操作完了後に **`DPU_APPL_STATE_DB`** の 13 テーブルへ `result` フィールドを書き込む。例外として `DashHaFlowOrch` のみが **`DPU_STATE_DB`** の `DASH_FLOW_SYNC_SESSION_STATE_TABLE` へフロー同期セッション状態を書く。`DashAclOrch` と `DashMeterOrch` は `app_state_db` を受け取るが result テーブルへの書込を行わない。
