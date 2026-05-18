# route-orch Phase F: 副作用テーブル書き込み調査メモ

## 対象ファイル
- `orchagent/flex_counter/flowcounterrouteorch.cpp` (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/flex_counter/flex_counter_manager.cpp`
- `common/schema.h` (sonic-swss-common, sha: 158de8d3463ff4b841653f6d57190bb142b80d9c)

## 調査結果

### DB 接続初期化 (L31-34)
```cpp
mCounterDb(std::shared_ptr<DBConnector>(new DBConnector("COUNTERS_DB", 0))),
mPrefixToCounterTable(std::unique_ptr<Table>(new Table(mCounterDb.get(), COUNTERS_ROUTE_NAME_MAP))),
mPrefixToPatternTable(std::unique_ptr<Table>(new Table(mCounterDb.get(), COUNTERS_ROUTE_TO_PATTERN_MAP))),
```
- `COUNTERS_ROUTE_NAME_MAP` = "COUNTERS_ROUTE_NAME_MAP" (schema.h:252)
- `COUNTERS_ROUTE_TO_PATTERN_MAP` = "COUNTERS_ROUTE_TO_PATTERN_MAP" (schema.h:253)

### STATE_DB 書き込み (L174-178, initRouteFlowCounterCapability)
```cpp
swss::DBConnector state_db("STATE_DB", 0);
swss::Table capability_table(&state_db, STATE_FLOW_COUNTER_CAPABILITY_TABLE_NAME);
fvs.emplace_back(FLOW_COUNTER_SUPPORT_FIELD, mRouteFlowCounterSupported ? "true" : "false");
capability_table.set(FLOW_COUNTER_ROUTE_KEY, fvs);
```
- `STATE_FLOW_COUNTER_CAPABILITY_TABLE_NAME` = "FLOW_COUNTER_CAPABILITY_TABLE" (schema.h:498)
- `FLOW_COUNTER_ROUTE_KEY` = "route"
- コンストラクタから呼ばれ起動時 1 回のみ実行

### COUNTERS_DB 書き込み (L152, L157, doTask(SelectableTimer))
```cpp
mPrefixToCounterTable->set("", prefixToCounterMap);   // L152
mPrefixToPatternTable->set("", prefixToPatternMap);   // L157
```
- バインド保留キュー `mPendingAddToFlexCntr` からの VID 解決済みエントリをバッチ書き込み
- 1 秒周期タイマーで処理される

### COUNTERS_DB 削除 (L920-922, removeRouteFlowCounterFromDB)
```cpp
mPrefixToPatternTable->hdel("", nameMapKey);  // L921
mPrefixToCounterTable->hdel("", nameMapKey);  // L922
```

### FLEX_COUNTER_DB 書き込み (flex_counter_manager.cpp:225)
- `FlexCounterManager::setCounterIdList()` → `startFlexCounterPolling()` 経由で FLEX_COUNTER_DB に書き込み
- グループ名: `ROUTE_FLOW_COUNTER_FLEX_COUNTER_GROUP` = "ROUTE_FLOW_COUNTER"
- キー: `FLEX_COUNTER_TABLE|ROUTE_FLOW_COUNTER|<counter_oid>`
