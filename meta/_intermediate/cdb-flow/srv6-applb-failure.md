# APPL_DB SRV6 テーブル — Phase D 失敗挙動スキャンノート

対象テーブル: `SRV6_MY_SID_TABLE` / `SRV6_SID_LIST_TABLE` (APPL_DB)
Consumer: `Srv6Orch` (`sonic-swss/orchagent/srv6orch.cpp`)
スキャン範囲: `createUpdateMysidEntry()`, `doTaskMySidTable()`, `createUpdateSidList()`, `deleteSidList()`, `doTaskSidTable()` 全行精読

---

## 検出した失敗経路

### 1. SRV6_MY_SID_TABLE: 不正な action 文字列 → 即時拒否・自動回復なし

`createUpdateMysidEntry()` (`srv6orch.cpp:1473-1477`) は `sidEntryEndpointBehavior(end_action, ...)` を呼び出す。
`end_behavior_map` に登録されていない action 文字列の場合、`false` を返す。

- **結果**: `doTaskMySidTable()` が `SWSS_LOG_ERROR("Failed to create/update my_sid entry for sid %s", ...)` を出力して `return`。エントリは ASIC に登録されない。`m_toSync` retry にも入らない（破棄）。
- **自動回復**: なし。APPL_DB に正しい `action` 値で再 SET が必要。
- **ログ出力**: `SWSS_LOG_ERROR("Invalid my_sid action %s", end_action.c_str())` (`srv6orch.cpp:1475`)

evidence: `srv6orch.cpp:1473-1477`, `srv6orch.cpp:2230-2234`

### 2. SRV6_MY_SID_TABLE: VRF 未存在 → 即時拒否・自動回復なし

`end.dt*`/`udt*` 行動で `vrf` フィールドに非デフォルト VRF を指定した場合、`m_vrfOrch->isVRFexists(dt_vrf)` が `false` なら即時拒否される (`srv6orch.cpp:1498-1502`)。また `isVRFexists()` が `true` でも `getVRFid()` が `SAI_NULL_OBJECT_ID` を返す場合も拒否される (`srv6orch.cpp:1492-1495`)。

- **結果**: MySID エントリは SAI に登録されない。retry キューに入らない（破棄）。
- **自動回復**: なし。VRF が後から CONFIG_DB に作成されても APPL_DB イベントの再発火はなく、fpmsyncd が再 SET を行うまで未解決のまま。
- **ログ出力**: `SWSS_LOG_ERROR("VRF %s doesn't exist in DB", dt_vrf.c_str())` (`srv6orch.cpp:1500`) または `SWSS_LOG_ERROR("VRF object not created for DT VRF %s", ...)` (`srv6orch.cpp:1494`)

evidence: `srv6orch.cpp:1480-1506`

### 3. SRV6_MY_SID_TABLE: adj Neighbor 未解決 → pending（自動回復あり）

`end.x`/`ua`/`udx4`/`udx6` 等の行動で `adj` フィールドの Neighbor が未解決の場合、エントリは `m_pendingSRv6MySIDEntries[nexthop]` に保留される (`srv6orch.cpp:1532-1542`)。

- **結果**: MySID エントリは SAI に登録されない。pending 状態で自動再試行待ち。
- **自動回復**: `updateNeighbor()` の ADD 通知（`srv6orch.cpp:1224-1259`）で pending エントリが自動再処理される。
- **ログ出力**: `SWSS_LOG_INFO("Nexthop for adjacency %s doesn't exist in DB yet", adj.c_str())` (`srv6orch.cpp:1539`) — INFO レベルのみ（silent に近い）

evidence: `srv6orch.cpp:1511-1543`, `srv6orch.cpp:1224-1259`

### 4. SRV6_MY_SID_TABLE: ECMP adj → 即時拒否

`adj` フィールドにカンマ区切りで複数の隣接（ECMP）が指定された場合、`adjv.size() > 1` で即時拒否される (`srv6orch.cpp:1516-1519`)。

- **結果**: MySID エントリは SAI に登録されない。破棄。
- **自動回復**: なし。単一 adj に修正して再 SET が必要。
- **ログ出力**: `SWSS_LOG_ERROR("Failed to create my_sid entry %s adj %s: ECMP adjacency not yet supported", ...)` (`srv6orch.cpp:1518`)

evidence: `srv6orch.cpp:1515-1519`

### 5. SRV6_SID_LIST_TABLE: path 空文字列 → サイレントスキップ（SAI 未作成）

`createUpdateSidList()` (`srv6orch.cpp:1052-1055`) は `segment_list.count == 0` の場合に `SWSS_LOG_ERROR("segment list count is zero, skip")` を出力して `true` を返す。

- **結果**: SID リストは SAI に作成されない。`doTaskSidTable()` は `task_success` として処理を終了する（エラー扱いにならない）。
- **自動回復**: なし。APPL_DB に正しい `path` で再 SET が必要。
- **ログ出力**: `SWSS_LOG_ERROR("segment list count is zero, skip")` (`srv6orch.cpp:1054`) — 名前が ERROR だがタスクは成功として処理継続

evidence: `srv6orch.cpp:1052-1056`, `srv6orch.cpp:1166-1170`

### 6. SRV6_SID_LIST_TABLE: SAI create/update 失敗 → task_failed

`sai_srv6_api->create_srv6_sidlist()` が `SAI_STATUS_SUCCESS` 以外を返した場合 (`srv6orch.cpp:1092-1096`)、または `set_srv6_sidlist_attribute()` が失敗した場合 (`srv6orch.cpp:1109-1113`)、`createUpdateSidList()` は `false` を返す。

- **結果**: `doTaskSidTable()` が `task_failed` を返す。`doTask()` の Consumer ループでこのエントリは `m_toSync` から削除される（retry なし）。
- **自動回復**: なし。
- **ログ出力**: `SWSS_LOG_ERROR("Failed to create srv6 sidlist object, rv %d", status)` または `SWSS_LOG_ERROR("Failed to set srv6 sidlist object with new segments, rv %d", status)`

evidence: `srv6orch.cpp:1091-1095`, `srv6orch.cpp:1108-1113`, `srv6orch.cpp:1166-1169`

### 7. SRV6_SID_LIST_TABLE DEL: nexthop 参照残存 → task_need_retry（自動再試行）

`deleteSidList()` (`srv6orch.cpp:1129-1133`) は `sid_table_[sid_name].nexthops.size() > 0` の場合、削除を拒否して `task_need_retry` を返す。

- **結果**: SID リストは削除されない。`doTask()` ループで `it++; continue` されエントリは `m_toSync` に保留。
- **自動回復**: nexthop が DEL されると nexthops カウントが 0 になり、次回 Consumer ループで deleteSidList() が再試行されて削除される。
- **ログ出力**: `SWSS_LOG_NOTICE("segment object %s referenced by other nexthops: count %zu, not deleting", ...)` (`srv6orch.cpp:1131`)

evidence: `srv6orch.cpp:1119-1133`, `srv6orch.cpp:2364-2369`

---

## 失敗経路サマリ

| # | テーブル | 失敗条件 | 検出箇所 | 結果 | 自動回復 | ログ種別 |
|---|----------|----------|----------|------|----------|----------|
| 1 | `SRV6_MY_SID_TABLE` | 不正な `action` 値 | `sidEntryEndpointBehavior():1473` | SAI 登録失敗・破棄 | なし | `SWSS_LOG_ERROR` |
| 2 | `SRV6_MY_SID_TABLE` | `vrf` 未存在（dt系行動） | `createUpdateMysidEntry():1498-1502` | SAI 登録失敗・破棄 | なし | `SWSS_LOG_ERROR` |
| 3 | `SRV6_MY_SID_TABLE` | `adj` Neighbor 未解決 | `createUpdateMysidEntry():1532-1542` | pending 保留 | あり (Neighbor ADD) | `SWSS_LOG_INFO` |
| 4 | `SRV6_MY_SID_TABLE` | `adj` ECMP 複数指定 | `createUpdateMysidEntry():1516-1519` | SAI 登録失敗・破棄 | なし | `SWSS_LOG_ERROR` |
| 5 | `SRV6_SID_LIST_TABLE` | `path` 空文字列 | `createUpdateSidList():1052-1055` | SAI 未作成・silent | なし | `SWSS_LOG_ERROR` (誤称) |
| 6 | `SRV6_SID_LIST_TABLE` | SAI create/update 失敗 | `createUpdateSidList():1091-1113` | task_failed | なし | `SWSS_LOG_ERROR` |
| 7 | `SRV6_SID_LIST_TABLE` | DEL 時 nexthop 参照残存 | `deleteSidList():1129-1133` | task_need_retry | あり (nexthop DEL後) | `SWSS_LOG_NOTICE` |
