# BUFFER_PORT_EGRESS_PROFILE_LIST 暗黙参照スキャン (Phase C)

`docs/reference/config-db/buffer-port-egress-profile-list.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソースは `sonic-net/sonic-swss/cfgmgr/buffermgrdyn.cpp` および `sonic-net/sonic-swss/orchagent/bufferorch.cpp`。
`BUFFER_PORT_EGRESS_PROFILE_LIST` テーブル処理時にコードが暗黙的に読み出す CONFIG_DB / APPL_DB テーブルを列挙する。

## スキャン手順

```bash
# buffermgrdyn.cpp の egress profile list ハンドラ
grep -n "BUFFER_PROFILE\|BUFFER_POOL\|getPort\|PORT\|m_bufferProfileLookup\|m_bufferPoolReady\|profile_list\|checkBufferProfile" \
    .cache/sonic-sources/sonic-swss/cfgmgr/buffermgrdyn.cpp | grep -E "3[23456789][0-9]{2}|47[0-9]"

# bufferorch.cpp の processEgressBufferProfileList
grep -n "processEgressBufferProfileList\|resolveFieldRefArray\|getPort\|BUFFER_PROFILE\|BUFFER_POOL" \
    .cache/sonic-sources/sonic-swss/orchagent/bufferorch.cpp | grep -E "processEgress|resolveFieldRef|getPort"
```

## 検出された暗黙参照テーブル

### BUFFER_PROFILE — buffermgrd 段（dynamic model）

`handleSingleBufferPortProfileListEntry` 内の `checkBufferProfileDirection` が SET 時に
`profile_list` の各プロファイル名を `m_bufferProfileLookup` で検索する。

- **evidence**: `buffermgrdyn.cpp:3281-3296`
- **未解決時**: `task_need_retry`（BUFFER_PROFILE 到着後に自動再処理）
- **方向違反時**: `task_failed`（ingress profile を egress list に指定した場合）

```cpp
// buffermgrdyn.cpp:3281
auto profileSearchRef = m_bufferProfileLookup.find(profileName);
if (profileSearchRef == m_bufferProfileLookup.end())
{
    SWSS_LOG_INFO("Profile %s doesn't exist, need retry", profileName.c_str());
    return task_process_status::task_need_retry;
}
// 方向検証
if (dir != profileObj.direction)
{
    SWSS_LOG_ERROR("Profile %s's direction is %s but %s is expected...", ...);
    return task_process_status::task_failed;
}
```

### BUFFER_PROFILE — orchagent 段

`processEgressBufferProfileList` 内の `resolveFieldRefArray` が
`m_buffer_type_maps[APP_BUFFER_PROFILE_TABLE_NAME]` を検索して各プロファイルの SAI OID を解決する。

- **evidence**: `bufferorch.cpp:1870-1879`
- **未解決時**: `task_need_retry`（自動リトライ）
- **解決失敗時**: `task_failed`

```cpp
// bufferorch.cpp:1870
ref_resolve_status resolve_status = resolveFieldRefArray(m_buffer_type_maps, buffer_profile_list_field_name,
                                                         buffer_to_ref_table_map.at(buffer_profile_list_field_name), tuple,
                                                         profile_list, profile_name_list);
if (ref_resolve_status::success != resolve_status)
{
    if(ref_resolve_status::not_resolved == resolve_status)
    {
        SWSS_LOG_INFO("Missing or invalid egress buffer profile reference specified for:%s", key.c_str());
        return task_process_status::task_need_retry;
    }
    ...
}
```

### PORT — orchagent 段

`processEgressBufferProfileList` の末尾で `gPortsOrch->getPort(port_name, port)` を実行する。
PortsOrch のポートマップに指定ポートが存在しない場合は `task_invalid_entry` を返し、エントリが**永続的に破棄**される。

- **evidence**: `bufferorch.cpp:1952-1956`
- **未解決時**: `task_invalid_entry`（**retry なし**、エントリ破棄）

```cpp
// bufferorch.cpp:1952
if (!gPortsOrch->getPort(port_name, port))
{
    SWSS_LOG_ERROR("Port with alias:%s not found", port_name.c_str());
    return task_process_status::task_invalid_entry;
}
```

### BUFFER_POOL — buffermgrd 段の間接依存

`handleSingleBufferPortProfileListEntry` は `m_bufferPoolReady` フラグを確認する。
BUFFER_POOL が APPL_DB に反映されていない場合は、エントリを APPL_DB に書き込まず保留する。

- **evidence**: `buffermgrdyn.cpp:3408-3415`
- **未準備時**: `m_bufferObjectsPending=true` を立て `task_success` 返却（pool 準備完了後に一括再処理）

```cpp
// buffermgrdyn.cpp:3408
if (!m_bufferPoolReady)
{
    const auto &direction = m_bufferDirectionNames[dir];
    SWSS_LOG_NOTICE("Buffer pools are not ready when configuring buffer %s profile list %s, pending", direction.c_str(), key.c_str());
    m_bufferObjectsPending = true;
    return task_process_status::task_success;
}
```

## YANG leafref との対比

| 参照先テーブル | YANG leafref | コードレベル参照 | 差異 |
|---|---|---|---|
| `BUFFER_PROFILE` | あり（`profile_list` フィールド） | あり（2 段階: buffermgrd + orchagent） | YANG は静的 validation のみ。コードは追加で方向検証・trim 制約を実施 |
| `PORT` | あり（key の leafref） | あり（`gPortsOrch->getPort()`） | YANG: 設定時 validate、コード: ランタイム解決（未解決でエントリ永続破棄） |
| `BUFFER_POOL` | 直接なし（BUFFER_PROFILE 経由） | あり（`m_bufferPoolReady` フラグ） | コードのみで存在する間接依存。YANG には表現されない |

## 検出結果サマリ

暗黙参照 3 件を検出:

1. **BUFFER_PROFILE** (buffermgrd): `m_bufferProfileLookup` 検索 + 方向検証 — `buffermgrdyn.cpp:3281-3296`
2. **BUFFER_PROFILE** (orchagent): `resolveFieldRefArray` で SAI OID 解決 — `bufferorch.cpp:1870-1879`
3. **PORT** (orchagent): `gPortsOrch->getPort()` でポート解決 — `bufferorch.cpp:1952-1956`
4. **BUFFER_POOL** (buffermgrd): `m_bufferPoolReady` フラグによる間接依存 — `buffermgrdyn.cpp:3408-3415`

YANG leafref で明示されている `BUFFER_PROFILE` および `PORT` は、コードレベルでは**より厳格な検証**（方向制約・trim 制約・リトライ有無の差異）が追加されている。`BUFFER_POOL` への間接依存は YANG には表現されておらず、コードのみで規定される。
