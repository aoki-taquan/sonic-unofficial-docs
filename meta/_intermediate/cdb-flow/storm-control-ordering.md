# PORT_STORM_CONTROL — Phase B 書込み順序依存 中間ファイル

生成日: 2026-05-16 (Task F Phase B)
ソース: `sonic-swss/orchagent/policerorch.cpp`, `orchdaemon.cpp`

## 依存テーブル

### PORT (必須先行)

`doTask()` 冒頭 (`policerorch.cpp:379-382`):
```cpp
if (!gPortsOrch->allPortsReady())
{
    return;  // 全ポート初期化完了前は doTask 即 return
}
```

`handlePortStormControlTable()` (`policerorch.cpp:138-143`):
```cpp
if (!gPortsOrch->getPort(interface_name, port))
{
    SWSS_LOG_ERROR("Failed to apply storm-control %s to port %s. Port not found",
            storm_type.c_str(), interface_name.c_str());
    return task_process_status::task_success;  // サイレント erase、リトライなし
}
```

PORT が存在しない場合はエントリを erase して `task_success` を返す。リトライなし。

### Ethernet のみ許可

`policerorch.cpp:131-135`:
```cpp
if (strncmp(interface_name.c_str(), ETHERNET_PREFIX, strlen(ETHERNET_PREFIX)))
{
    SWSS_LOG_ERROR("%s: Unsupported / Invalid interface %s", ...);
    return task_process_status::task_success;  // PortChannel / VLAN は silent drop
}
```

LAG (PortChannel) や VLAN インタフェースを指定した場合も同様に erase される。

## storm policer 独立性

policer 名フォーマット: `_<interface_name>_<storm_type>` (`policerorch.cpp:145-146`)

3 種 (broadcast / unknown-unicast / unknown-multicast) は独立して作成・attach・削除される。
相互依存なし。SET/DEL はそれぞれ storm_type 単位で独立処理される。

## orchlist 順序 (orchdaemon.cpp:500)

```
gSwitchOrch → gCrmOrch → gPortsOrch → gBufferOrch → ... → gPolicerOrch → ...
```

`gPortsOrch` は `gPolicerOrch` より先に orchlist に登録されており、`allPortsReady()` が満たされてから PolicerOrch の処理が有効になる。

## 順序サマリ

```
CONFIG_DB|PORT (PortsOrch allPortsReady)
  ↓ (先行必須)
CONFIG_DB|PORT_STORM_CONTROL|<Ethernet ifname>|<storm_type>
  ↓
storm policer (_<ifname>_<storm_type>) 作成
  ↓
SAI create_policer → set_port_attribute (SAI_PORT_ATTR_*_STORM_CONTROL_POLICER_ID attach)
```
