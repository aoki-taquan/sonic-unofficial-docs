# PORTCHANNEL_MEMBER 失敗挙動調査 (Phase D)

調査日: 2026-05-15
対象: `docs/reference/config-db/portchannel-member.md`
ソース:
- `sonic-swss/cfgmgr/teammgr.cpp`
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-portchannel.yang`

## 1. YANG スキーマ検証レイヤ

`PORTCHANNEL_MEMBER` の key `(name, port)` は YANG leafref。
参照先の PORTCHANNEL / PORT が存在しない場合は `sonic-cfggen` / `config load` 時点で reject。
エントリは CONFIG_DB に書き込まれない。

## 2. teammgrd レイヤ (addLagMember)

### コード証跡: `teammgr.cpp:769-788`

```cpp
if (exec(cmd.str(), res) != 0)
{
    if (checkPortIffUp(member))
    {
        SWSS_LOG_INFO("Failed to add %s to port channel %s, retry...",
                member.c_str(), lag.c_str());
        return task_need_retry;
    }
    else
    {
        SWSS_LOG_ERROR("Failed to add %s to port channel %s",
                member.c_str(), lag.c_str());
        return task_failed;
    }
}
```

- `teamdctl port add` コマンド失敗 + ポートが `IFF_UP` 状態 → `task_need_retry`（SWSS_LOG_INFO）。portmgrd 等との競合とみなして自動再試行。
- `teamdctl port add` コマンド失敗 + ポートが admin-down → `task_failed`（SWSS_LOG_ERROR）。エントリ破棄、手動介入必要。

### ポート未発見: `teammgr.cpp:741-744`

```cpp
if (exec(cmd.str(), res) != 0)
{
    SWSS_LOG_WARN("Unable to find port %s", member.c_str());
    return task_ignore;
}
```

- `ip link show <member>` が失敗（ポートが kernel netdev として存在しない）→ `task_ignore`（SWSS_LOG_WARN）。エントリは破棄される。

### 既スレーブ状態: `teammgr.cpp:749-752`

```cpp
if (isPortEnslaved(member))
{
    return task_ignore;
}
```

- ポートが既に別 LAG にスレーブ済み → `task_ignore`（ログなし）。べき等処理。

## 3. teammgrd 前提条件チェック (doLagMemberTask)

### コード証跡: `teammgr.cpp:357-366`

```cpp
if (!isPortStateOk(member) || !isLagStateOk(lag))
{
    it++;
    continue;
}
if (isMACsecAttached(member) && !isMACsecIngressSAOk(member))
{
    it++;
    continue;
}
```

| 条件 | 挙動 | ログ |
|---|---|---|
| `STATE_PORT_TABLE[member].state != ok` | 暗黙 continue（次ループで再試行） | なし |
| `STATE_LAG_TABLE[lag]` 未登録 | 暗黙 continue（次ループで再試行） | なし |
| MACsec 有効 + Ingress SA 未確立 | 暗黙 continue（次ループで再試行） | SWSS_LOG_INFO |

- リトライ上限なし。依存状態が解消されれば自然に成功する設計。

## 4. orchagent (PortsOrch) レイヤ

### ポート型チェック: `portsorch.cpp:6290-6295`

```cpp
if (!isValidPortTypeForLagMember(port))
{
    SWSS_LOG_ERROR("LAG member port has to be of type PHY or SYSTEM");
    it = consumer.m_toSync.erase(it);
    continue;
}
```

- ポートが PHY / SYSTEM 型以外 → SWSS_LOG_ERROR + エントリ消去。リトライなし。

### chassis switch_id ミスマッチ: `portsorch.cpp:6307-6315`

```cpp
if (port_switch_id != lag_switch_id)
{
    SWSS_LOG_ERROR("System lag switch id mismatch. Lag %s switch id: %d, Member %s switch id: %d",
            lag_alias.c_str(), lag_switch_id, port_alias.c_str(), port_switch_id);
    it = consumer.m_toSync.erase(it);
    continue;
}
```

- chassis 環境でのみ発生。異なる ASIC のスイッチ ID → SWSS_LOG_ERROR + エントリ消去。

### VLAN_MEMBER 競合（skip ≠ error）: `portsorch.cpp:6337-6343`

```cpp
if (m_portVlanMember[port.m_alias].size() > 0)
{
    SWSS_LOG_DEBUG("Port %s is still a member of %zu VLAN(s), skipping adding port to port channel.", ...);
    it++;
    continue;
}
```

- ポートが VLAN_MEMBER に残存 → SWSS_LOG_DEBUG + 暗黙 skip（エラーではない）。VLAN_MEMBER が DEL されるまでループし続ける。

### SAI LAG member add 失敗: `portsorch.cpp:8174-8182`

```cpp
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_ERROR("Failed to add member %s to LAG %s lid:%" PRIx64 " pid:%" PRIx64, ...);
    task_process_status handle_status = handleSaiCreateStatus(SAI_API_LAG, status);
    if (handle_status != task_success)
    {
        return parseHandleSaiStatusFailure(handle_status);
    }
}
```

- `sai_lag_api->create_lag_member()` 失敗 → SWSS_LOG_ERROR。SAI ステータスに応じて `handleSaiCreateStatus` でリトライ判定。

### SAI LAG member remove 失敗: `portsorch.cpp:8223-8231`

- `sai_lag_api->remove_lag_member()` 失敗 → SWSS_LOG_ERROR。同様に `handleSaiRemoveStatus` でリトライ判定。

### DEL で存在しないメンバー: `portsorch.cpp:6399-6404`

```cpp
if (!port.m_lag_id || !port.m_lag_member_id)
{
    SWSS_LOG_WARN("Member %s not found in LAG %s lid:%" PRIx64 " lmid:%" PRIx64 ",", ...);
    it = consumer.m_toSync.erase(it);
    continue;
}
```

- DEL 時にメンバーが既存でない → SWSS_LOG_WARN + エントリ消去（べき等）。

## 5. 起動時失敗

### DEVICE_METADATA MAC アドレス欠如: `teammgr.cpp:61`

```cpp
throw runtime_error("Failed to get MAC address from configuration database");
```

- `DEVICE_METADATA|localhost|mac` が存在しない場合、teammgrd 起動時に例外をスロー → コンテナ停止。

## まとめ

| 失敗シナリオ | 戻り値/挙動 | ログレベル | リカバリ |
|---|---|---|---|
| YANG leafref 違反 (name/port 参照先なし) | config-load reject | - | エントリ作成前に拒否 |
| STATE_PORT_TABLE 未準備 | 暗黙 continue | なし | 自動再試行 |
| STATE_LAG_TABLE 未準備 | 暗黙 continue | なし | 自動再試行 |
| MACsec Ingress SA 未確立 | 暗黙 continue | INFO | 自動再試行 |
| `ip link show` 失敗（netdev なし） | `task_ignore` | WARN | エントリ破棄 |
| ポートが既スレーブ | `task_ignore` | なし | べき等処理 |
| `teamdctl port add` 失敗 + admin-up | `task_need_retry` | INFO | 自動再試行 |
| `teamdctl port add` 失敗 + admin-down | `task_failed` | ERROR | 手動介入必要 |
| ポート型 PHY/SYSTEM 以外 | エントリ消去 | ERROR | 型修正後に再投入 |
| chassis switch_id ミスマッチ | エントリ消去 | ERROR | 設計見直し必要 |
| VLAN_MEMBER 競合（ポート在籍中） | 暗黙 skip | DEBUG | VLAN_MEMBER DEL 後に自動解消 |
| SAI create_lag_member 失敗 | SAI ステータス依存 | ERROR | SAI 依存 |
| SAI remove_lag_member 失敗 | SAI ステータス依存 | ERROR | SAI 依存 |
| DEL で未存在メンバー | エントリ消去 | WARN | べき等 |
| DEVICE_METADATA mac 欠如 | 例外スロー → 停止 | - | MAC 設定後に再起動 |
