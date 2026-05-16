# app-counter — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/flexcounterorch.cpp` (FlexCounterOrch ディスパッチ層)
- `sonic-swss/orchagent/flex_counter/flex_counter_manager.cpp` (StatsMode 文字列マッピング)
- `sonic-swss/orchagent/flex_counter/flow_counter_handler.cpp` (SAI generic counter stat リスト・capability query)
- `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp` (Route flow counter 既定値・タイマー)
- `sonic-swss/orchagent/copporch.cpp` (Trap flow counter ポーリング既定値)

---

## 1. CONFIG_DB key 定数 (`flexcounterorch.cpp` L58-59, `flowcounterrouteorch.cpp` L22)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `FLOW_CNT_TRAP_KEY` | `"FLOW_CNT_TRAP"` | `FLEX_COUNTER_TABLE` の trap 用 key 文字列 | flexcounterorch.cpp:58 |
| `FLOW_CNT_ROUTE_KEY` | `"FLOW_CNT_ROUTE"` | `FLEX_COUNTER_TABLE` の route 用 key 文字列 | flexcounterorch.cpp:59 |
| `FLOW_COUNTER_ROUTE_KEY` | `"route"` | `STATE_DB FLOW_COUNTER_CAPABILITY_TABLE` のキー (`support` フィールドを格納) | flowcounterrouteorch.cpp:22 |
| `FLOW_COUNTER_SUPPORT_FIELD` | `"support"` | capability テーブルの値フィールド名 | flowcounterrouteorch.cpp:23 |
| `ROUTE_PATTERN_MAX_MATCH_COUNT_FIELD` | `"max_match_count"` | `FLOW_COUNTER_ROUTE_PATTERN` のフィールド名 | flowcounterrouteorch.cpp:24 |

---

## 2. ポーリング間隔の既定値 (10 秒, ms 単位)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `HOSTIF_TRAP_COUNTER_POLLING_INTERVAL_MS` | `10000` | `FLEX_COUNTER_TABLE\|FLOW_CNT_TRAP` の `POLL_INTERVAL` 未設定時にコンストラクタへ渡される値 | copporch.cpp:189 |
| `ROUTE_FLOW_COUNTER_POLLING_INTERVAL_MS` | `10000` | `FLEX_COUNTER_TABLE\|FLOW_CNT_ROUTE` の `POLL_INTERVAL` 未設定時にコンストラクタへ渡される値 | flowcounterrouteorch.cpp:26 |

両者は FlexCounterManager コンストラクタ第 3 引数として固定値で渡され、CONFIG_DB に `POLL_INTERVAL` が現れて初めて上書きされる。

---

## 3. 非同期タイマー定数 (1 秒)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `FLEX_COUNTER_UPD_INTERVAL` | `1` (秒) | `FlowCounterRouteOrch` 内部の `SelectableTimer` 周期。pending route の counter binding 再試行間隔 | flowcounterrouteorch.cpp:21, L43 |
| `"FLEX_COUNTER_UPD_TIMER"` | (タイマー名) | `ExecutableTimer` の identifier 文字列。`select()` ループ上で識別される | flowcounterrouteorch.cpp:45 |

`route flow counter` を `enable` にしてからカウンタが COUNTERS_DB に出現するまで最大数秒のラグが生じる根拠。

---

## 4. `max_match_count` のデフォルト (30)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT` | `30` | `FLOW_COUNTER_ROUTE_PATTERN` に `max_match_count` 未指定時の既定。`0` を設定した場合も silent fallback でこの値 | flowcounterrouteorch.cpp:25, L73, L84 |

CLI の `config flowcnt-route pattern add --max` のデフォルト (`config/flow_counters.py:29`) も 30 で一致。

---

## 5. Warm restart 遅延 (60 秒)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `FLEX_COUNTER_DELAY_SEC` | `60` | warm-restart 後、FlexCounterOrch が `doTask(Consumer&)` を 60 秒間 no-op にする `SelectableTimer` 周期 | flexcounterorch.cpp:44, L127 |

`FLOW_CNT_TRAP` / `FLOW_CNT_ROUTE` の `enable/disable` 反映が warm boot 直後 60 秒遅れる根拠。コールド起動時は遅延なし。`FlowCounterRouteOrch` 側には同等の遅延ガードは無い。

---

## 6. 内部 group 定数 (CONFIG_DB key → flex_counter group 名)

`flexCounterGroupMap` (`flexcounterorch.cpp:65-99`) による静的マップ。ユーザは変更不可。

| CONFIG_DB key | 内部 group constant (FLEX_COUNTER_DB 上のグループ名) | ソース |
|---|---|---|
| `FLOW_CNT_TRAP` | `HOSTIF_TRAP_COUNTER_FLEX_COUNTER_GROUP` | flexcounterorch.cpp:87 |
| `FLOW_CNT_ROUTE` | `ROUTE_FLOW_COUNTER_FLEX_COUNTER_GROUP` | flexcounterorch.cpp:88 |

これらの実体文字列定義は `swss-common` の `schema.h` 側にあり、`FLEX_COUNTER_DB` の `FLEX_COUNTER_GROUP_TABLE|<group>` キーとして syncd が参照する。

---

## 7. CONFIG_DB フィールド名定数

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `FLEX_COUNTER_STATUS_FIELD` | `"FLEX_COUNTER_STATUS"` | enable/disable トグルのフィールド名 | flexcounterorch.cpp:225 (swss-common schema.h で定義) |
| `POLL_INTERVAL_FIELD` | `"POLL_INTERVAL"` | ポーリング間隔フィールド名 | flexcounterorch.cpp:200 (同上) |

これらは `sonic-swss-common/common/schema.h` 由来でユーザ側からの変更手段なし。

---

## 8. SAI generic counter stat リスト (固定 2 種)

`flow_counter_handler.cpp` L10-13 で `std::vector<sai_counter_stat_t>` として定数定義。trap / route 両グループで共通。

| stat | 意味 | ソース |
|------|------|--------|
| `SAI_COUNTER_STAT_PACKETS` | パケット数 | flow_counter_handler.cpp:12 |
| `SAI_COUNTER_STAT_BYTES` | バイト数 | flow_counter_handler.cpp:13 |

ユーザは項目を増減できない。capability ゲートでは `SAI_OBJECT_TYPE_ROUTE_ENTRY` の `SAI_ROUTE_ENTRY_ATTR_COUNTER_ID` のみ問い合わせる (`flow_counter_handler.cpp:54-61`)。

---

## 9. StatsMode 文字列マッピング (`flex_counter_manager.cpp` L25-29)

| StatsMode enum | 文字列定数 | ソース |
|---|---|---|
| `StatsMode::READ` | `STATS_MODE_READ` (`"STATS_MODE_READ"`) | flex_counter_manager.cpp:27 |
| `StatsMode::READ_AND_CLEAR` | `STATS_MODE_READ_AND_CLEAR` | flex_counter_manager.cpp:28 |

`FLOW_CNT_TRAP` / `FLOW_CNT_ROUTE` 両グループとも `StatsMode::READ` 固定でコンストラクタに渡される (`copporch.cpp:198`, `flowcounterrouteorch.cpp:35`)。CONFIG_DB から変更する手段はない。

---

## まとめ

`FLEX_COUNTER_TABLE|FLOW_CNT_TRAP` / `FLOW_CNT_ROUTE` / `FLOW_COUNTER_ROUTE_PATTERN` 周辺のハードコード定数はすべて C++ ソース直書きで、CONFIG_DB / YANG / 環境変数のいずれからも変更できない。ユーザ可変なのは `FLEX_COUNTER_STATUS`・`POLL_INTERVAL`・`max_match_count`・`FLOW_COUNTER_ROUTE_PATTERN` のキー (prefix / vrf) のみ。
