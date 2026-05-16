# APPL_DB ROUTE_TABLE — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-15 (Task F Phase F / cdb_q67_f)
対象ページ: `docs/reference/config-db/appl-db-route.md`
commit ref: `4305596156d70e9797e8a881b3d19b46de0bce0d` (sonic-swss)

## 1. 調査対象

`APPL_DB:ROUTE_TABLE` (IPv4 / IPv6 unicast / blackhole / EVPN / SRv6 経路) の SET/DEL に伴って、主購読者 `routeorch` および同居 orch (`CrmOrch`, `FlowCounterRouteOrch`) が **APPL_STATE_DB / STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB** へ書き込む副次エントリを総覧する。SAI を介する ASIC_DB 反映は本ページの主作用のため除外する。

## 2. 走査範囲

- `.cache/sonic-sources/sonic-swss/orchagent/routeorch.cpp` (主購読者 `RouteOrch`)
- `.cache/sonic-sources/sonic-swss/orchagent/routeorch.h`
- `.cache/sonic-sources/sonic-swss/orchagent/orch.h` (`ResponsePublisher m_publisher{"APPL_STATE_DB"}` 既定)
- `.cache/sonic-sources/sonic-swss/orchagent/crmorch.cpp` (CRM カウンタ用 COUNTERS_DB writer)
- `.cache/sonic-sources/sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp` (route flow counter)

## 3. 走査コマンドと結果

### 3.1 routeorch.cpp 内の副次 DB 名前空間 / Table 生成

```bash
grep -nE "APPL_STATE_DB|STATE_DB|COUNTERS_DB|FLEX_COUNTER_DB|m_publisher|m_stateDb|publishRouteState|updateDefRouteState" routeorch.cpp
```

主要ヒット:

- L57-58 `m_publisher.setBuffered(true); m_publisher.m_directDbWrite = true;` — `ResponsePublisher m_publisher` (Orch 基底, `orch.h:382` で `{"APPL_STATE_DB"}` 固定)
- L126-127 `m_stateDb = new DBConnector("STATE_DB", 0)` / `m_stateDefaultRouteTb = new Table(m_stateDb.get(), STATE_ROUTE_TABLE_NAME)`
- L130 / L156 `updateDefRouteState("0.0.0.0/0")` / `updateDefRouteState("::/0")` (起動時)
- L287-295 `updateDefRouteState(string ip, bool add)` 実装: `m_stateDefaultRouteTb->set(ip, [("state", "ok"|"na")])`
- L923 / L1050 / L1090 / L2729 / L2970 `publishRouteState(ctx)` 呼出 (各 route SET/DEL/loopback パス)
- L2703 / L2856 `updateDefRouteState(ipPrefix.to_string(), true|false)` (デフォルト route SET/DEL の状態反映)
- L3185-3201 `RouteOrch::publishRouteState()` 実装: `m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace=false)` — SET 時 `fvs = [("protocol", ctx.protocol)]`, DEL 時は空 fvs でキー削除

### 3.2 CRM (COUNTERS_DB CRM:STATS)

```bash
grep -n "CRM_IPV4_ROUTE\|CRM_IPV6_ROUTE\|CRM_NEXTHOP_GROUP" routeorch.cpp
```

inc 箇所:

- L148 / L257 / L2481 / L2532 `incCrmResUsedCounter(CRM_IPV4_ROUTE)` / `(CRM_IPV6_ROUTE)`
- L446 / L522 / L1445 / L1580 / L1637 `incCrmResUsedCounter(CRM_NEXTHOP_GROUP[_MEMBER])`

dec 箇所:

- L168 / L280 / L2884 / L2888 `decCrmResUsedCounter(CRM_IPV4_ROUTE|CRM_IPV6_ROUTE)`
- L594 / L1467 / L1746 / L1761 `decCrmResUsedCounter(CRM_NEXTHOP_GROUP[_MEMBER])`

書込み実体: `crmorch.cpp`

- L400-401 `m_countersDb(new DBConnector("COUNTERS_DB", 0))`, `m_countersCrmTable(new Table(m_countersDb.get(), COUNTERS_CRM_TABLE))`
- L414 起動時に `m_countersCrmTable->del(CRM_COUNTERS_TABLE_KEY)` で初期化
- L1063-1113 `updateCrmCountersTable()`: `crmUsedCntsTableMap` / `crmAvailCntsTableMap` を走査して `m_countersCrmTable->set(cnt.first, [(field, value)])` で `crm_stats_*_used` / `crm_stats_*_available` を書く
- polling は `m_timer` (`CRM_POLLING_INTERVAL_DEFAULT`) で `doTask(SelectableTimer)` 経由

### 3.3 FlowCounterRouteOrch (COUNTERS_DB / STATE_DB / FLEX_COUNTER_DB)

```bash
grep -nE "Counter|StateDb|FLEX_COUNTER|NameMap|capability" flex_counter/flowcounterrouteorch.cpp
```

Table 生成:

- L31 `mCounterDb(new DBConnector("COUNTERS_DB", 0))`
- L32 `mVidToRidTable(new Table(mAsicDb.get(), "VIDTORID"))` (ASIC_DB read-only 用; 書込みなし)
- L33 `mPrefixToCounterTable(new Table(mCounterDb.get(), COUNTERS_ROUTE_NAME_MAP))`
- L34 `mPrefixToPatternTable(new Table(mCounterDb.get(), COUNTERS_ROUTE_TO_PATTERN_MAP))`
- L35 `mRouteFlowCounterMgr(ROUTE_FLOW_COUNTER_FLEX_COUNTER_GROUP, READ, 10000ms, false)` (FLEX_COUNTER_DB writer)

書込み箇所:

- L123 `mRouteFlowCounterMgr.setCounterIdList(counter_oid, ROUTE, counter_stats)` — `FLEX_COUNTER_DB:FLEX_COUNTER_TABLE|ROUTE_FLOW_COUNTER:<oid>` に登録
- L152 `mPrefixToCounterTable->set("", prefixToCounterMap)` — `COUNTERS_ROUTE_NAME_MAP` への HSET (バルク)
- L157 `mPrefixToPatternTable->set("", prefixToPatternMap)` — `COUNTERS_ROUTE_TO_PATTERN_MAP` への HSET (バルク)
- L174-178 `swss::DBConnector state_db("STATE_DB", 0); Table capability_table(&state_db, STATE_FLOW_COUNTER_CAPABILITY_TABLE_NAME); capability_table.set(FLOW_COUNTER_ROUTE_KEY, fvs)` — 起動時 `support=true/false` を `STATE_DB:FLOW_COUNTER_CAPABILITY_TABLE|route` に
- L916-923 `removeRouteFlowCounterFromDB()`: `mPrefixToPatternTable->hdel("", nameMapKey)`, `mPrefixToCounterTable->hdel("", nameMapKey)`, `mRouteFlowCounterMgr.clearCounterIdList(counter_oid)`

連動呼出 (`routeorch.cpp` 側):

- L259 `gFlowCounterRouteOrch->onAddMiscRouteEntry(vrf_id, linklocal_prefix.getSubnet())` (link-local route 追加時)
- L282 `gFlowCounterRouteOrch->onRemoveMiscRouteEntry(vrf_id, linklocal_prefix.getSubnet())`
- L2708 `gFlowCounterRouteOrch->handleRouteAdd(vrf_id, ipPrefix)` (route 追加成功時)
- L2996 `gFlowCounterRouteOrch->handleRouteRemove(vrf_id, ipPrefix)` (route 削除成功時)

### 3.4 その他副次 DB の有無

```bash
grep -nE "LOGLEVEL_DB|CHASSIS_APP_DB|SNMP_OVERLAY_DB|ConfigDBConnector" routeorch.cpp crmorch.cpp flex_counter/flowcounterrouteorch.cpp
```

ヒット 0 件。`routeorch` は CONFIG_DB を購読する側のみで、CONFIG_DB への書込みは行わない (Config-validator 等は orch 外)。

## 4. 結論サマリ表

| 副次 DB | テーブル / キー | 書込内容 | 根拠 (file:line) |
|---|---|---|---|
| APPL_STATE_DB | `ROUTE_TABLE\|<key>` | SET 時 `protocol`, DEL 時キー削除 | `routeorch.cpp:57-58,3185-3201` |
| STATE_DB | `ROUTE_TABLE\|0.0.0.0/0` `\|::/0` | `state=ok|na` (default route のみ) | `routeorch.cpp:126-127,287-295,130,156,2703,2856` |
| COUNTERS_DB | `CRM:STATS` | `crm_stats_ipv4/ipv6_route_used` 周期更新 (+ NHG / member) | `routeorch.cpp:148,168,...`; `crmorch.cpp:400-401,1063-1113` |
| COUNTERS_DB | `COUNTERS_ROUTE_NAME_MAP`, `COUNTERS_ROUTE_TO_PATTERN_MAP` | flow-counter bind/unbind | `flowcounterrouteorch.cpp:33-34,152-157,921-922` |
| STATE_DB | `FLOW_COUNTER_CAPABILITY_TABLE\|route` | 起動時 1 回 `support` 広告 | `flowcounterrouteorch.cpp:166-178` |
| FLEX_COUNTER_DB | `FLEX_COUNTER_GROUP_TABLE\|ROUTE_FLOW_COUNTER`, `FLEX_COUNTER_TABLE\|...:<oid>` | flow-counter ポーリング登録 / 解除 | `flowcounterrouteorch.cpp:35,123,923` |

それ以外 (LOGLEVEL_DB, CONFIG_DB, CHASSIS_APP_DB, SNMP_OVERLAY_DB) への書込みは検出されなかった。

## 5. 検証コマンド (実機)

```sh
# APPL_STATE_DB の route protocol mirror
redis-cli -n 14 keys 'ROUTE_TABLE:*' | head
redis-cli -n 14 hgetall 'ROUTE_TABLE:10.0.0.0/24'

# STATE_DB default route reachability
redis-cli -n 6 hgetall 'ROUTE_TABLE|0.0.0.0/0'
redis-cli -n 6 hgetall 'ROUTE_TABLE|::/0'

# COUNTERS_DB CRM
redis-cli -n 2 hgetall 'CRM:STATS' | grep -E 'route_used|route_available'

# COUNTERS_DB flow-counter name maps
redis-cli -n 2 hgetall COUNTERS_ROUTE_NAME_MAP
redis-cli -n 2 hgetall COUNTERS_ROUTE_TO_PATTERN_MAP

# STATE_DB flow-counter capability
redis-cli -n 6 hgetall 'FLOW_COUNTER_CAPABILITY_TABLE|route'

# FLEX_COUNTER_DB route flow counter
redis-cli -n 5 keys 'FLEX_COUNTER_GROUP_TABLE|ROUTE_FLOW_COUNTER*'
redis-cli -n 5 keys 'FLEX_COUNTER_TABLE|ROUTE_FLOW_COUNTER*'
```
