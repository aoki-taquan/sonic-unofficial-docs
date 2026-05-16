# VLAN_SUB_INTERFACE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-vlan-sub-interface)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース:
- `sonic-net/sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-net/sonic-swss/orchagent/intfsorch.cpp`

`intfmgrd`（`intfmgr.cpp`）が VLAN_SUB_INTERFACE を設定する際に発生しうる失敗パターンを整理する。

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログレベル | evidence |
|---|---|---|---|---|
| short-name 形式で `vlan` フィールドが `"0"` または空 | `doTask()` L936-939 | `return false`（リトライ待ち）。kernel 操作なし | `SWSS_LOG_INFO` ("Vlan ID not configured for sub interface %s") | `intfmgr.cpp:936-939` |
| `ip link add` 失敗（`addHostSubIntf()` 内 `swss::exec()` 非ゼロ） | `doTask()` L942-948 | `runtime_error` → catch → `return false`（リトライ待ち） | `SWSS_LOG_NOTICE` ("Sub interface ip link add failure. Runtime error: %s") | `intfmgr.cpp:947` |
| `ip link set mtu` 失敗（`setHostSubIntfMtu()` 内 `swss::exec()` 非ゼロ） | `doTask()` L963-969 | `runtime_error` → catch → `return false`（リトライ待ち） | `SWSS_LOG_NOTICE` ("Sub interface ip link set mtu failure. Runtime error: %s") | `intfmgr.cpp:968` |
| `ip link set up/down` 失敗（`setHostSubIntfAdminStatus()` 内 `swss::exec()` 非ゼロ） | `doTask()` L990-999 | `runtime_error` → catch → `return false`（リトライ待ち） | `SWSS_LOG_NOTICE` ("Sub interface ip link set admin status %s failure. Runtime error: %s") | `intfmgr.cpp:998` |
| `isIntfStateOk(alias)` が false（netdev 削除済み競合） | `setHostSubIntfMtu()` L451-455 | `SWSS_LOG_WARN` 記録後 `runtime_error` を throw しない（silent skip） | `SWSS_LOG_WARN` | `intfmgr.cpp:451-455` |
| SAI `create_router_interface()` が非 SUCCESS | `addSubPort()` L1297-1304 | `SWSS_LOG_ERROR` → `handleSaiCreateStatus` 判定 → リトライ不可なら `throw runtime_error` | `SWSS_LOG_ERROR` ("Failed to create router interface %s, rv:%d") | `intfsorch.cpp:1297-1304` |
| SAI `remove_router_interface()` が非 SUCCESS | `removeRouterIntfs()` L1350-1354 | `SWSS_LOG_ERROR` → `handleSaiRemoveStatus` 判定 → リトライ不可なら `throw runtime_error` | `SWSS_LOG_ERROR` | `intfsorch.cpp:1349-1354` |
| `ref_count > 0` 状態で削除試行 | `removeRouterIntfs()` L1327-1331 | `return false`（RIF 削除スキップ）。IP アドレスや VRF binding 残存が原因 | なし | `intfsorch.cpp:1327-1331` |

### 失敗パターン要約

| 失敗種別 | トリガー | ログレベル | 挙動 |
|---|---|---|---|
| VLAN tag 不正（`vlan == "0"` または空） | short-name 形式で `vlan` 未設定 | `SWSS_LOG_INFO` | リトライ待ち（kernel 操作なし） |
| kernel netlink 失敗（ip link add） | `swss::exec()` 非ゼロ返却 | `SWSS_LOG_NOTICE` | リトライ待ち（`return false`） |
| kernel netlink 失敗（ip link set mtu） | `swss::exec()` 非ゼロ返却 | `SWSS_LOG_NOTICE` | リトライ待ち（`return false`） |
| kernel netlink 失敗（ip link set admin） | `swss::exec()` 非ゼロ返却 | `SWSS_LOG_NOTICE` | リトライ待ち（`return false`） |
| SAI sub-port RIF 生成失敗 | `create_router_interface()` 非 SUCCESS | `SWSS_LOG_ERROR` | `handleSaiCreateStatus` 判定 → `task_need_retry` or `throw` |
| SAI sub-port RIF 削除失敗 | `remove_router_interface()` 非 SUCCESS | `SWSS_LOG_ERROR` | `handleSaiRemoveStatus` 判定 → `task_need_retry` or `throw` |
| ref_count 残存での削除 | IP/VRF binding が残存 | なし | RIF 削除スキップ（`return false`） |

<!-- /failure -->
