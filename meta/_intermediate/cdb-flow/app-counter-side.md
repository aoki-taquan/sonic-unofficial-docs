# app-counter — Phase F: 副次 DB 書込ノート

**対象ページ**: `docs/reference/config-db/app-counter.md`

**対象テーブル**: `FLEX_COUNTER_TABLE|FLOW_CNT_TRAP` / `FLEX_COUNTER_TABLE|FLOW_CNT_ROUTE` / `FLOW_COUNTER_ROUTE_PATTERN`

## 概要

これらの CONFIG_DB エントリを `enable` にすると、orchagent (`FlexCounterOrch` / `CoppOrch` / `FlowCounterRouteOrch`) が **COUNTERS_DB / STATE_DB / FLEX_COUNTER_DB** に副次的に書き込みを行う。CONFIG_DB は readonly な input、書き込みは副作用として実装側で行われ、ユーザー側からは `show flowcnt-*` / `counterpoll show` / SONiC counters API 経由で観測される。

## 1. COUNTERS_DB への副次書込

### 1-a. `COUNTERS_TRAP_NAME_MAP` (HSET)

| 項目 | 値 |
|---|---|
| DB | COUNTERS_DB |
| key | `COUNTERS_TRAP_NAME_MAP` (単一 hash) |
| field | trap 名 (例 `bgp`, `lldp`, `arp_request`) |
| value | SAI generic counter OID (`oid:0x...`) |
| トリガ | `FLOW_CNT_TRAP=enable` → `CoppOrch::bindTrapCounter()` |
| evidence | `copporch.cpp:196, 1452-1456`, `m_counter_table->set("", nameMapFvs)` |
| クリア | `unbindTrapCounter()` で `hdel`、`copporch.cpp:1494-1496` |

### 1-b. `COUNTERS_ROUTE_NAME_MAP` (HSET)

| 項目 | 値 |
|---|---|
| DB | COUNTERS_DB |
| key | `COUNTERS_ROUTE_NAME_MAP` (単一 hash) |
| field | `<vrf_name>\|<prefix>` または `<prefix>` (デフォルト VRF) |
| value | SAI generic counter OID |
| トリガ | `FLOW_CNT_ROUTE=enable` + `FLOW_COUNTER_ROUTE_PATTERN` 登録 → 1 秒タイマー bind 成功時 |
| evidence | `flowcounterrouteorch.cpp:33, 150-153` (`mPrefixToCounterTable->set("", prefixToCounterMap)`) |
| クリア | `removeRouteFlowCounterFromDB()`、`flowcounterrouteorch.cpp:921-922` |

### 1-c. `COUNTERS_ROUTE_TO_PATTERN_MAP` (HSET)

| 項目 | 値 |
|---|---|
| DB | COUNTERS_DB |
| key | `COUNTERS_ROUTE_TO_PATTERN_MAP` (単一 hash) |
| field | 個別ルートの `<vrf>\|<prefix>` |
| value | マッチした `FLOW_COUNTER_ROUTE_PATTERN` key (パターン側 prefix) |
| トリガ | route bind 成功時 |
| evidence | `flowcounterrouteorch.cpp:34, 155-158` (`mPrefixToPatternTable->set`) |
| クリア | `flowcounterrouteorch.cpp:921` (`hdel`) |

### 1-d. `COUNTERS:<oid>` (syncd 側書込、間接副作用)

orchagent → FLEX_COUNTER_DB 経由で syncd が 10 秒周期に `SAI_COUNTER_STAT_PACKETS` / `_BYTES` を `COUNTERS_DB` の `COUNTERS:<counter_oid>` ハッシュに HSET する。orchagent 自身は書かない。

## 2. STATE_DB への副次書込

### 2-a. `FLOW_COUNTER_CAPABILITY_TABLE|route` (HSET)

| 項目 | 値 |
|---|---|
| DB | STATE_DB |
| key | `FLOW_COUNTER_CAPABILITY_TABLE\|route` (`STATE_FLOW_COUNTER_CAPABILITY_TABLE_NAME` + `FLOW_COUNTER_ROUTE_KEY`) |
| field | `support` |
| value | `"true"` / `"false"` |
| トリガ | `FlowCounterRouteOrch` ctor 時 1 回。`FlowCounterHandler::queryRouteFlowCounterCapability()` の結果 |
| evidence | `flowcounterrouteorch.cpp:166-179` |
| クリア | なし (orch 寿命中固定) |

trap 側には capability エントリは書かれない。

## 3. FLEX_COUNTER_DB への副次書込

### 3-a. `FLEX_COUNTER_GROUP_TABLE|HOSTIF_TRAP_FLOW_COUNTER` / `|ROUTE_FLOW_COUNTER` (HSET)

| 項目 | 値 |
|---|---|
| DB | FLEX_COUNTER_DB |
| key | `FLEX_COUNTER_GROUP_TABLE\|HOSTIF_TRAP_FLOW_COUNTER` または `\|ROUTE_FLOW_COUNTER` |
| field | `FLEX_COUNTER_STATUS`, `POLL_INTERVAL`, `STATS_MODE` |
| トリガ | `FLEX_COUNTER_STATUS` 変更 / `POLL_INTERVAL` 変更 |
| evidence | `flexcounterorch.cpp:202-214, 380-392` → `saihelper.cpp:868-885,918-962` 経由で `ProducerTable` / SAI redis switch attr |

### 3-b. `FLEX_COUNTER_TABLE:<counter_oid>` (HSET)

| 項目 | 値 |
|---|---|
| DB | FLEX_COUNTER_DB |
| key | `FLEX_COUNTER_TABLE:oid:0x...` (per counter OID) |
| field | `COUNTER_IDS` = `SAI_COUNTER_STAT_PACKETS,SAI_COUNTER_STAT_BYTES`, `COUNTER_TYPE` |
| トリガ | trap/route → counter 紐付け時 (`setCounterIdList`) |
| evidence | `flex_counter_manager.cpp:200-260`, `flow_counter_handler.cpp:10-13` |

## まとめ

| 副次 DB | テーブル | 書込タイミング | 主体 |
|---|---|---|---|
| COUNTERS_DB | `COUNTERS_TRAP_NAME_MAP` | trap bind 時 | CoppOrch |
| COUNTERS_DB | `COUNTERS_ROUTE_NAME_MAP` | route bind 時 (1 秒タイマー) | FlowCounterRouteOrch |
| COUNTERS_DB | `COUNTERS_ROUTE_TO_PATTERN_MAP` | route bind 時 | FlowCounterRouteOrch |
| COUNTERS_DB | `COUNTERS:<oid>` | 10 秒周期 | syncd (FlexCounter) |
| STATE_DB | `FLOW_COUNTER_CAPABILITY_TABLE\|route` | orch 起動時 1 回 | FlowCounterRouteOrch |
| FLEX_COUNTER_DB | `FLEX_COUNTER_GROUP_TABLE\|<group>` | enable/disable, interval 変更時 | FlexCounterOrch |
| FLEX_COUNTER_DB | `FLEX_COUNTER_TABLE:<oid>` | counter 紐付け時 | FlexCounterManager |

## 不可逆 / 残置リスク

- `COUNTERS_TRAP_NAME_MAP` / `COUNTERS_ROUTE_NAME_MAP` は **disable で `hdel` される**が、SAI `remove_counter` 失敗時は OID リーク (`flow_counter_handler.cpp:32-38`)。
- `STATE_DB FLOW_COUNTER_CAPABILITY_TABLE\|route` は **orchagent プロセス再起動でしか再評価されない**。
