# PORTCHANNEL_INTERFACE 失敗挙動調査 (Phase D)

調査日: 2026-05-16
対象: `docs/reference/config-db/portchannel-interface.md`
ソース: `sonic-swss/cfgmgr/intfmgr.cpp`, `sonic-swss/orchagent/intfsorch.cpp`

## 1. intfmgrd (IntfMgr) の失敗・retry パターン

### 1.1 STATE_LAG_TABLE 未登録 → 暗黙 retry

コード根拠: `intfmgr.cpp:833-836`

```cpp
if (!isIntfStateOk(parentAlias.empty() ? alias : parentAlias))
{
    SWSS_LOG_DEBUG("Interface is not ready, skipping %s", alias.c_str());
    return false;
}
```

`isIntfStateOk()` は `PortChannel` プレフィクスに対して `m_stateLagTable.get(alias, temp)` を確認する (`intfmgr.cpp:661-667`)。
LAG が STATE_DB に存在しない場合、`doIntfGeneralTask()` は `false` を返し、呼び出し元 `doTask()` は `it++` してエントリを `m_toSync` に残し次ループで再試行する。**ログは DEBUG レベルのみ**。

### 1.2 VRF 未登録 → 暗黙 retry

コード根拠: `intfmgr.cpp:839-842`

```cpp
if (!vrf_name.empty() && !isIntfStateOk(vrf_name))
{
    SWSS_LOG_DEBUG("VRF is not ready, skipping %s", vrf_name.c_str());
    return false;
}
```

`vrf_name` 指定時に `m_stateVrfTable.get(vrf_name, temp)` が false なら retry。
vrfmgrd が STATE_VRF_TABLE を書き込むまで PORTCHANNEL_INTERFACE の VRF binding は保留される。

### 1.3 VRF 直接変更 → ERROR ログ + skip (エントリ削除)

コード根拠: `intfmgr.cpp:846-849`

```cpp
if (isIntfChangeVrf(alias, vrf_name))
{
    SWSS_LOG_ERROR("%s can not change to %s directly, skipping", alias.c_str(), vrf_name.c_str());
    return true;  // true = エントリを m_toSync から消去
}
```

既存 VRF binding を別 VRF に直接変更しようとした場合、エラーログを出力してエントリを破棄する (`return true` → `m_toSync.erase`)。
**自動リカバリなし**。VRF 変更は一度 `vrf_name` を削除（DEL）してから再設定（SET）する必要がある。

### 1.4 MPLS 設定失敗 → ERROR ログ + return false (retry)

コード根拠: `intfmgr.cpp:901-904`

```cpp
if (!setIntfMpls(alias, mpls))
{
    SWSS_LOG_ERROR("Failed to set MPLS to \"%s\" for the \"%s\" interface", mpls.c_str(), alias.c_str());
    return false;
}
```

`setIntfMpls()` は `sysctl` コマンドで `net.mpls.conf.<alias>.input` を設定する。コマンド失敗時は SWSS_LOG_ERROR を出力して `false` を返し retry。
MPLS モジュールがカーネルにロードされていない環境 (`mpls_router` / `mpls_iptunnel` カーネルモジュール未ロード) で発生する可能性がある。

### 1.5 IP prefix 処理での STATE_INTERFACE_TABLE 未登録 → 暗黙 retry

コード根拠: `intfmgr.cpp:1115`

```cpp
if (!isIntfStateOk(alias) || !isIntfCreated(alias))
{
    SWSS_LOG_DEBUG("Interface is not ready, skipping %s", alias.c_str());
    return false;
}
```

IP プレフィクスロウ (`PORTCHANNEL_INTERFACE|<name>|<ip_prefix>`) は、対応する属性ロウ (`PORTCHANNEL_INTERFACE|<name>`) が先に処理されて STATE_INTERFACE_TABLE に登録されるまで保留される。
`isIntfCreated(alias)` が false → retry。

### 1.6 DEL 時の IP アドレス残存チェック → 暗黙 retry

コード根拠: `intfmgr.cpp:1060-1063`

```cpp
if (getIntfIpCount(alias))
{
    return false;
}
```

属性ロウへの DEL 操作時、当該インタフェースに IP アドレスが残存していれば `false` を返して retry する。
IP プレフィクスロウを先に削除してから属性ロウを削除する順序が必要。

## 2. orchagent (IntfsOrch) の失敗・retry パターン

### 2.1 LAG オブジェクト未生成 → 暗黙 retry

コード根拠: `intfsorch.cpp:905-924`

```cpp
Port port;
if (!gPortsOrch->getPort(alias, port))
{
    /* TODO: Resolve the dependency relationship and add ref_count to port */
    it++;
    continue;
}
```

APP_DB の `INTF_TABLE` 更新を受信した orchagent が `gPortsOrch->getPort(alias, port)` で LAG オブジェクトを取得できない場合、`m_toSync` にエントリを残して retry。
`PortsOrch` が teamd の通知で LAG を生成するまで待つ。**ログなし**。

### 2.2 SAI RIF 作成失敗 → 例外 (throw) + 起動停止

コード根拠: `intfsorch.cpp:1297-1304`

```cpp
sai_status_t status = sai_router_intfs_api->create_router_interface(&port.m_rif_id, gSwitchId, attrs.size(), attrs.data());
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create router interface %s, rv:%d", port.m_alias.c_str(), status);
    if (handleSaiCreateStatus(SAI_API_ROUTER_INTERFACE, status) != task_success)
    {
        throw runtime_error("Failed to create router interface.");
    }
}
```

SAI `create_router_interface` が失敗すると `SWSS_LOG_ERROR` + `runtime_error` をスロー。orchagent は例外を catch しないため **プロセスがクラッシュ**する。`supervisord` が orchagent を再起動するが、再起動後も同じ SAI エラーが続く場合はハードウェア/SAI 実装の問題。

### 2.3 SAI RIF 削除失敗 → 例外 (throw) + 起動停止

コード根拠: `intfsorch.cpp:1352-1355`

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to remove router interface for port %s, rv:%d", port.m_alias.c_str(), status);
    throw runtime_error("Failed to remove router interface.");
}
```

`removeRouterIntfs()` の SAI 削除失敗も同様に例外スロー → orchestagent クラッシュ。

### 2.4 mac_addr 設定失敗 → task_need_retry

コード根拠: `intfsorch.cpp:1017-1025`

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to set router interface mac %s for port %s, rv:%d", ...);
    if (handleSaiSetStatus(SAI_API_ROUTER_INTERFACE, status) == task_need_retry)
    {
        it++;
        continue;
    }
}
```

`mac_addr` の SAI SET が失敗し `handleSaiSetStatus` が `task_need_retry` を返すと retry。
`task_failed` や `task_success` の場合はループを継続（エントリ消去）。

### 2.5 loopback_action 設定失敗 → ERROR ログ + 処理継続 (非 retry)

コード根拠: `intfsorch.cpp:444-454`

```cpp
sai_status_t status = sai_router_intfs_api->set_router_interface_attribute(port.m_rif_id, &attr);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Loopback action [%s] set failed, interface [%s], rc [%d]", ...);
    task_process_status handle_status = handleSaiSetStatus(SAI_API_ROUTER_INTERFACE, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

`setIntfLoopbackAction()` の失敗は `parseHandleSaiStatusFailure()` の戻り値で判断。`task_need_retry` の場合は `it++; continue;` だが、設定がベストエフォートに留まる実装も多い。

### 2.6 IP2me ルート作成失敗 → 例外スロー

コード根拠: `intfsorch.cpp:1400-1403`

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to create IP2me route ip:%s, rv:%d", ...);
    throw runtime_error("Failed to create IP2me route.");
}
```

IP prefix 追加時の IP2me (Host Entry) ルート作成失敗も例外スロー → orchagent クラッシュ。

## 3. 失敗シナリオ一覧

| 失敗シナリオ | 発生箇所 | 戻り値 / 動作 | ログ | リカバリ |
|---|---|---|---|---|
| STATE_LAG_TABLE 未登録 (LAG 未起動) | `intfmgr.cpp:833-836` | `false` → retry | SWSS_LOG_DEBUG | lagmgrd が STATE_LAG_TABLE 書込み後に自動再試行 |
| STATE_VRF_TABLE 未登録 (VRF 未生成) | `intfmgr.cpp:839-842` | `false` → retry | SWSS_LOG_DEBUG | vrfmgrd が STATE_VRF_TABLE 書込み後に自動再試行 |
| VRF 直接変更 | `intfmgr.cpp:846-849` | `true` → エントリ破棄 | SWSS_LOG_ERROR | 手動: DEL → SET の順序で再設定 |
| MPLS sysctl 設定失敗 | `intfmgr.cpp:901-904` | `false` → retry | SWSS_LOG_ERROR | mpls カーネルモジュールのロード後に自動再試行 |
| IP prefix: 属性ロウ未登録 | `intfmgr.cpp:1115` | `false` → retry | SWSS_LOG_DEBUG | 属性ロウ処理完了後に自動再試行 |
| DEL 時の IP アドレス残存 | `intfmgr.cpp:1060-1063` | `false` → retry | なし | IP prefix DEL 後に自動再試行 |
| orchagent: LAG オブジェクト未生成 | `intfsorch.cpp:905-924` | retry | なし | PortsOrch が LAG 生成後に自動再試行 |
| orchagent: SAI RIF 作成失敗 | `intfsorch.cpp:1297-1304` | 例外スロー | SWSS_LOG_ERROR | supervisord による orchagent 再起動 |
| orchagent: SAI RIF 削除失敗 | `intfsorch.cpp:1352-1355` | 例外スロー | SWSS_LOG_ERROR | supervisord による orchagent 再起動 |
| orchagent: mac_addr SAI SET 失敗 | `intfsorch.cpp:1017-1025` | `task_need_retry` or 継続 | SWSS_LOG_ERROR | SAI 状態回復後に自動再試行 |
| orchagent: IP2me ルート作成失敗 | `intfsorch.cpp:1400-1403` | 例外スロー | SWSS_LOG_ERROR | supervisord による orchagent 再起動 |
