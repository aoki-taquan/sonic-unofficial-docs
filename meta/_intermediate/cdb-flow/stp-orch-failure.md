# stp-orch — 失敗挙動・リトライ・リカバリ調査メモ

## 調査対象

`docs/reference/config-db/stp-orch.md` Phase D 追加分。
ソース: `sonic-swss/orchagent/stporch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## SAI API 失敗時の挙動

### 1. `STP_VLAN_INSTANCE_TABLE` SET — SAI 失敗 → it++ 残置

`addVlanToStpInstance()` (stporch.cpp:115-163) の SAI 失敗パターン:

```cpp
// create_stp 失敗
if (sai_status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create STP instance for Vlan %s rv:%d", vlan_alias.c_str(), sai_status);
    return false;
}

// set_vlan_attribute(SAI_VLAN_ATTR_STP_INSTANCE) 失敗
if (sai_status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to set SAI_VLAN_ATTR_STP_INSTANCE for Vlan %s rv:%d", vlan_alias.c_str(), sai_status);
    task_process_status handle_status = handleSaiSetStatus(SAI_API_VLAN, sai_status);
    // handleSaiSetStatus で SAI_STATUS_SUCCESS 以外なら false を返す
    return false;
}
```

`doStpTask()` (stporch.cpp:410-414) では:
```cpp
if(!addVlanToStpInstance(vlan_alias, instance))
{
    it++;
    continue;
}
```
失敗時は `it++` で残置し、後続エントリの処理は継続する。エントリは次ポーリングサイクルで自動再試行される。

### 2. `STP_VLAN_INSTANCE_TABLE` — `stp_instance` フィールド欠落 → エラーログ + it++ 残置

stporch.cpp:395-408 で `stp_instance` フィールドが存在しない場合:
```cpp
if (!found)
{
    SWSS_LOG_ERROR("Failed to parse STP instance from SET message for Vlan %s", vlan_alias.c_str());
    it++;
    continue;
}
```
フィールド欠落はエラーログを出力し `it++` で残置。stpmgrd が正しいフィールドで再度 SET するまで再試行され続ける。

### 3. `STP_PORT_STATE_TABLE` SET — ポート未登録 → return (コンシューマ全体ブロック)

`doStpPortStateTask()` (stporch.cpp:449-453):
```cpp
if (!gPortsOrch->getPort(port_alias, port))
{
    SWSS_LOG_ERROR("Failed to get port for STP port state entry %s", key.c_str());
    return;
}
```
`it++` でなく `return` するため、同一コンシューマの後続エントリも全てブロックされる。PortsOrch へのポート登録後に自動再開する。

### 4. `STP_PORT_STATE_TABLE` SET — Bridge Port 作成失敗 → it++ 残置

`addStpPort()` (stporch.cpp:218-227):
```cpp
if(port.m_bridge_port_id == SAI_NULL_OBJECT_ID)
{
    gPortsOrch->addBridgePort(port);
    if(port.m_bridge_port_id == SAI_NULL_OBJECT_ID)
    {
        SWSS_LOG_ERROR("Failed to add STP port %s invalid bridge port id ...", port_alias.c_str());
        return SAI_NULL_OBJECT_ID;
    }
}
```
`SAI_NULL_OBJECT_ID` 返却 → `updateStpPortState()` が false → `doStpPortStateTask()` が `it++` で残置。SAI リカバリ後に自動再試行される。

### 5. `STP_PORT_STATE_TABLE` SET — SAI `create_stp_port` 失敗 → it++ 残置

`addStpPort()` (stporch.cpp:249-257):
```cpp
if (sai_status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create STP port %s for STP instance %d rv:%d", ...);
    return SAI_NULL_OBJECT_ID;
}
```
`SAI_NULL_OBJECT_ID` 返却 → 同上、`it++` 残置。

### 6. `STP_PORT_STATE_TABLE` SET — `set_stp_port_attribute` 失敗 → it++ 残置

`updateStpPortState()` (stporch.cpp:314-335):
```cpp
if (sai_status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to set STP port state for %s rv:%d", port_alias.c_str(), sai_status);
    task_process_status handle_status = handleSaiSetStatus(SAI_API_STP, sai_status);
    return false;
}
```
false 返却 → `doStpPortStateTask()` が `it++` 残置。

### 7. `STP_FASTAGEING_FLUSH_TABLE` SET — VLAN 未登録 → fail-silent (即消去)

`stpVlanFdbFlush()` (stporch.cpp:369-372) が false を返しても `doStpFastageTask()` (stporch.cpp:488-519) は戻り値をチェックしない。エントリは常に `erase()` される。FDB フラッシュが実行されなくてもエラーログは出力されない。

### 8. `STP_INST_PORT_FLUSH_TABLE` SET — インスタンス未登録 → no-op (即消去)

`doMstInstPortFlushTask()` (stporch.cpp:553-561) で `m_vlanAliasToStpInstanceMap` にインスタンスが存在しない場合はフラッシュなしで `erase()` のみ実行される。エラーログなし。

### 9. `STP_VLAN_INSTANCE_TABLE` DEL — VLAN 未登録 → it++ 残置

`removeVlanFromStpInstance()` (stporch.cpp:164-206) でも `gPortsOrch->getPort()` を呼ぶ。未登録なら false を返し `doStpTask()` の DEL 分岐が `it++` 残置する。

### 10. コンストラクタ SAI クエリ失敗 → 未初期化のまま動作継続

`StpOrch::StpOrch()` (stporch.cpp:17-43) で SAI Switch 属性 (`DEFAULT_STP_INST_ID` / `MAX_STP_INSTANCE`) の取得に失敗した場合は `SWSS_LOG_WARN` のみで `m_defaultStpId` と `m_maxStpInstance` が未初期化のまま動作を継続する。この状態では:
- VLAN 削除時に `SAI_VLAN_ATTR_STP_INSTANCE` を `m_defaultStpId` (=0) に戻そうとして SAI エラーが発生しうる
- STATE_DB への `max_stp_inst` 書き込みも行われない

## リトライ・リカバリメカニズム

| 失敗種別 | 残置方法 | リカバリトリガ |
|---------|---------|-------------|
| SAI 操作失敗 (create/set STP) | `it++` 残置 | SAI リカバリ後の次ポーリングサイクル |
| `stp_instance` フィールド欠落 | `it++` 残置 | stpmgrd が正しい SET で上書き |
| ポート未登録 (`STP_PORT_STATE_TABLE`) | `return` コンシューマ全体ブロック | PortsOrch へのポート登録後に自動再開 |
| VLAN 未登録 (`STP_VLAN_INSTANCE_TABLE`) | `it++` 残置 | PortsOrch への VLAN 登録後に自動再試行 |
| Bridge port 作成失敗 | `it++` 残置 | 次ポーリングで再試行 |
| VLAN 未登録 (`FASTAGEING_FLUSH`) | fail-silent | リトライなし (フラッシュ機会を消失) |
| インスタンス未登録 (`INST_PORT_FLUSH`) | no-op | リトライなし |
| コンストラクタ SAI クエリ失敗 | 未初期化継続 | orchagent 再起動のみ |

## Warm Restart

StpOrch には専用の Warm Restart reconciliation 機構が実装されていない。`doTask()` は `allPortsReady()` ガードのみ持ち、再起動後は `m_toSync` への再投入に依存する。
