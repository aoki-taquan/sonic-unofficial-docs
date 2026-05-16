# PORT_STORM_CONTROL — Phase B 順序依存中間ファイル

生成日: 2026-05-16 (Task F Phase B)
ソース: `sonic-swss/orchagent/policerorch.cpp`

## PORT 先行制約

`doTask()` 冒頭 (`policerorch.cpp:379-382`):
```cpp
if (!gPortsOrch->allPortsReady())
{
    return;
}
```
全ポート初期化完了前は PORT_STORM_CONTROL 処理がブロックされる。

`handlePortStormControlTable()` (`policerorch.cpp:138-143`):
```cpp
if (!gPortsOrch->getPort(interface_name, port))
{
    SWSS_LOG_ERROR("Failed to apply storm-control %s to port %s. Port not found",
            storm_type.c_str(), interface_name.c_str());
    return task_process_status::task_success;  // サイレント破棄 (erase、リトライなし)
}
```
PORT が存在しない場合は task_success を返しエントリを erase する。

## storm policer 命名・独立性

policer 名: `_<interface_name>_<storm_type>` (`policerorch.cpp:145-146`)

3 種 (broadcast / unknown-unicast / unknown-multicast) は独立して作成・attach・削除される。
相互依存なし。SET/DEL はそれぞれ storm_type 単位で独立処理。

## 順序サマリ

```
PORT (PortsOrch allPortsReady)
  ↓ (前提)
PORT_STORM_CONTROL|<ifname>|<storm_type>
  ↓
storm policer (_<ifname>_<storm_type>) 作成 → SAI_PORT_ATTR_*_STORM_CONTROL_POLICER_ID attach
```
