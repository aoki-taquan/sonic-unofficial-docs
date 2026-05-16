# DASH_ENI_TABLE — Phase B ordering 調査メモ

調査対象ソース:
- `sonic-swss/orchagent/dash/dashorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## 書込み順依存の一覧

### 1. DASH_APPLIANCE_TABLE が先行必須

`addEniObject()` (dashorch.cpp:578-582):
```cpp
if (appliance_entries_.empty())
{
    SWSS_LOG_INFO("Retry as no appliance table entry found");
    return false;
}
```
アプライアンスエントリが存在しない場合は `false` を返し、orchagent がリトライキューに戻す。
DASH_ENI_TABLE を書く前に DASH_APPLIANCE_TABLE の登録が完了している必要がある。

### 2. DASH_VNET_TABLE が先行必須

`addEniObject()` (dashorch.cpp:570-576):
```cpp
if (!vnet.empty() && gVnetNameToId.find(vnet) == gVnetNameToId.end())
{
    SWSS_LOG_INFO("Retry as vnet %s not found", vnet.c_str());
    return false;
}
```
ENI の `vnet` フィールドに指定した VNET が DASH_VNET_TABLE に未登録の場合リトライ。

### 3. DASH_METER_POLICY_TABLE が先行必須 (v4/v6 meter policy 使用時)

`addEniObject()` (dashorch.cpp:584-607):
`v4_meter_policy_id` / `v6_meter_policy_id` が指定されている場合、DashMeterOrch 経由で OID を取得できなければリトライ。

### 4. ENI 本体 → ENI ether address map entry の順

`addEni()` (dashorch.cpp:861-881):
```cpp
if (!addEniObject(eni, entry) || !addEniAddrMapEntry(eni, entry))
{
    return false;
}
```
① `sai_dash_eni_api->create_eni()` → ② `sai_dash_eni_api->create_eni_ether_address_map_entry()` の順序が強制される。
ENI SAI オブジェクトの OID が確定してから ether address map entry に参照される。

### 5. ENI ether address map entry → trusted VNI エントリの順

`addEni()` (dashorch.cpp:869-878):
```cpp
eni_entries_[eni] = entry;
eni_entries_[eni].metadata.clear_trusted_vnis_list();

if (!entry.metadata.trusted_vnis_list().empty())
{
    bool all_trusted_vnis_added = addEniTrustedVnis(eni, entry);
```
ENI オブジェクトと ether address map entry が成功した後にのみ trusted VNI エントリを追加。
失敗時は `removeEni()` を呼び出して全体をロールバック。

### 6. DASH_ENI_TABLE → DASH_ENI_ROUTE_TABLE の順

`setEniRoute()` (dashorch.cpp:1186-1189):
```cpp
if (eni_entries_.find(eni) == eni_entries_.end())
{
    SWSS_LOG_INFO("ENI %s not yet created, not programming ENI route entry", eni.c_str());
    return false;
}
```
ENI オブジェクトが存在しない場合は ENI Route の設定をリトライ。

### 7. DASH_ROUTE_GROUP_TABLE → DASH_ENI_ROUTE_TABLE の順

`setEniRoute()` (dashorch.cpp:1192-1198):
```cpp
sai_object_id_t route_group_oid = dash_route_orch->getRouteGroupOid(entry.group_id());
if (route_group_oid == SAI_NULL_OBJECT_ID)
{
    SWSS_LOG_INFO("Route group not yet created, skipping route entry for ENI %s", entry.group_id().c_str());
    return false;
}
```
ルートグループが未作成の場合もリトライ。

### 8. SAI 内部順序: ENI 削除時は address map → ENI object

`removeEni()` (dashorch.cpp:1035):
```cpp
if (!removeEniAddrMapEntry(eni) || !removeEniObject(eni))
```
削除は作成の逆順: ① ether address map entry 削除 → ② ENI SAI オブジェクト削除。
ENI object が使用中 (`SAI_STATUS_OBJECT_IN_USE`) の場合は削除をリトライ (dashorch.cpp:911-913)。

### 9. orchagent 内の処理キュー順序

`orchdaemon.cpp` の `addOrchList` 登録順:
```
dash_acl_orch → dash_vnet_orch → dash_route_orch → dash_orch → dash_tunnel_orch → dash_meter_orch → dash_ha_orch → dash_port_map_orch → dash_ha_flow_orch
```
DashOrch (DASH_ENI_TABLE 処理) は DashAclOrch / DashVnetOrch / DashRouteOrch の後にキュー処理される。
ただし DASH は ZMQ 経由の受信なので、各メッセージは受信タイミングで即時 doTask() を経由する。

### 10. Warm-reboot 時の動作

`warmRestoreAndSyncUp()` (orchdaemon.cpp:1095-1170):
- Warm start 検出時は `bake()` で既存 APP_DB エントリを toSync キューに積んでから 3 イテレーション `doTask()` を実行する
- DASH 系 Orch は ZMQ Consumer であり、warm-reboot 時に orchagent を再起動すると ZMQ 経由の再送をコントローラが担当する設計
- orchagent 単体の warm-reboot では `DASH_ENI_TABLE` の既存エントリは APP_DB から `bake()` で読み直されるが、依存テーブル (VNET, APPLIANCE) も同様に再処理されるため、3 イテレーション内で依存解決が完了する前提
- `WarmStart::RECONCILED` 状態への遷移は全 Orch の `doTask()` 完了かつペンディングタスクが空になった時点 (orchdaemon.cpp:1187-1205)
