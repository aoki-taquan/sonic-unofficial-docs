# APPL_DB ROUTE_TABLE — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-15 (Task F Phase F / cdb_q67_f)

## 調査対象

`docs/reference/config-db/app-route.md` が表す `APPL_DB:ROUTE_TABLE` (IPv4/IPv6 ユニキャストルート) の SET/DEL に伴って、主購読者 `routeorch` および関連 orch (`CrmOrch`, `FlowCounterRouteOrch`) が **APPL_STATE_DB / STATE_DB / COUNTERS_DB / その他副次 DB** へ書き込むエントリを特定する。

## 走査範囲

- `.cache/sonic-sources/sonic-swss/orchagent/routeorch.cpp` (主購読者 `RouteOrch::doRouteTask()` / `publishRouteState()` / `updateDefRouteState()`)
- `.cache/sonic-sources/sonic-swss/orchagent/routeorch.h`
- `.cache/sonic-sources/sonic-swss/orchagent/orch.h` (`ResponsePublisher m_publisher`)
- `.cache/sonic-sources/sonic-swss/orchagent/response_publisher.{h,cpp}` (publisher 出力先)
- `.cache/sonic-sources/sonic-swss/orchagent/crmorch.cpp` (CRM カウンタ)
- `.cache/sonic-sources/sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp` (ルート flow counter)

## 走査コマンドと結果

### 1. `routeorch.cpp` 内の副次 DB 名前空間

```bash
grep -n -E "APPL_STATE_DB|STATE_DB|COUNTERS_DB|FLEX_COUNTER_DB" routeorch.cpp
```

- L126 `m_stateDb = new DBConnector("STATE_DB", 0)`
- L1049 コメント "to keep APPL_DB and APPL_STATE_DB consistent"
- L3192 コメント "remove the state entry from APPL_STATE_DB"

### 2. publisher / state table 利用箇所

```bash
grep -n -E "m_publisher|m_stateDefaultRouteTb|publishRouteState" routeorch.cpp
```

- L57–L58 `m_publisher.setBuffered(true); m_publisher.m_directDbWrite = true;` ← `ResponsePublisher` (`orch.h:382` で `{"APPL_STATE_DB"}` 固定)
- L127 `m_stateDefaultRouteTb = new Table(m_stateDb.get(), STATE_ROUTE_TABLE_NAME)`
- L294 `m_stateDefaultRouteTb->set(ip, tuples)` ← `STATE_DB:ROUTE_TABLE|<ip>` に `state=ok/na`
- L923 / L1050 / L1090 / L2729 / L2970 `publishRouteState(ctx)` 呼出 (各 route SET/DEL/失敗パス)
- L3185–L3201 `RouteOrch::publishRouteState()` 実装。`m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace)` で `APPL_STATE_DB:ROUTE_TABLE|<key>` を更新 (DEL 時は空 fvs で削除、SET 時は `protocol` を書く)

### 3. CRM (COUNTERS_DB)

```bash
grep -n "CRM_IPV4_ROUTE\|CRM_IPV6_ROUTE\|CrmRes" routeorch.cpp
```

- L148 / L257 / L2481 / L2532 `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_IPV4_ROUTE | CRM_IPV6_ROUTE)`
- L168 / L280 / L2884 / L2888 `gCrmOrch->decCrmResUsedCounter(...)`
- 書込先: `crmorch.cpp:400-401` `m_countersDb(new DBConnector("COUNTERS_DB", 0))` → `m_countersCrmTable(new Table(... COUNTERS_CRM_TABLE))` (`COUNTERS_DB:CRM:STATS` の `crm_stats_ipv4_route_used` / `crm_stats_ipv6_route_used` を周期的に更新)

### 4. FlowCounterRouteOrch (COUNTERS_DB ルート名マップ)

```bash
grep -n -E "mPrefixToCounterTable|onAddMiscRouteEntry|COUNTERS_ROUTE_NAME_MAP|COUNTERS_ROUTE_TO_PATTERN_MAP" flex_counter/flowcounterrouteorch.cpp
```

- L33 `mPrefixToCounterTable(new Table(mCounterDb.get(), COUNTERS_ROUTE_NAME_MAP))` ← `COUNTERS_DB:COUNTERS_ROUTE_NAME_MAP`
- L34 `mPrefixToPatternTable(new Table(mCounterDb.get(), COUNTERS_ROUTE_TO_PATTERN_MAP))` ← `COUNTERS_DB:COUNTERS_ROUTE_TO_PATTERN_MAP`
- L152 `mPrefixToCounterTable->set("", prefixToCounterMap)` / L157 `mPrefixToPatternTable->set(...)`
- L921–L922 `hdel("", nameMapKey)` でルート削除時にフィールド削除
- `routeorch.cpp:282` `gFlowCounterRouteOrch->onRemoveMiscRouteEntry(...)` 等、route の add/remove ごとに呼ばれる
- L178 `capability_table.set(FLOW_COUNTER_ROUTE_KEY, fvs)` ← `STATE_DB:FLOW_COUNTER_CAPABILITY_TABLE|route` (起動時のケーパビリティ広告)

## 結論

CONFIG_DB ではなく **APPL_DB:ROUTE_TABLE** の SET/DEL に伴って、`routeorch` および同居する `CrmOrch` / `FlowCounterRouteOrch` が以下の副次 DB に書き込む:

| 副次 DB | テーブル/キー | 書込内容 | 根拠 |
|---|---|---|---|
| **APPL_STATE_DB** | `ROUTE_TABLE\|<key>` | SET 時 `protocol=<value>`、DEL 時はキー削除 (空 fvs) | `routeorch.cpp:3185-3201` `publishRouteState()` + `orch.h:382` `ResponsePublisher{"APPL_STATE_DB"}` |
| **STATE_DB** | `ROUTE_TABLE\|<default-ip>` | `state=ok` / `state=na` (デフォルトルート (`0.0.0.0/0` / `::/0`) の到達性状態) | `routeorch.cpp:127, 287-295` `updateDefRouteState()` |
| **COUNTERS_DB** | `CRM:STATS` | `crm_stats_ipv4_route_used` / `crm_stats_ipv6_route_used` (周期更新) | `routeorch.cpp:148/168/...` `incCrmResUsedCounter` → `crmorch.cpp:400-401, 1067-1091` |
| **COUNTERS_DB** | `COUNTERS_ROUTE_NAME_MAP`, `COUNTERS_ROUTE_TO_PATTERN_MAP` | flow-counter 有効時にルート↔counter OID マッピングを set/hdel | `flex_counter/flowcounterrouteorch.cpp:33-34, 152-157, 921-922`、`routeorch.cpp:282 onRemoveMiscRouteEntry` 連動 |
| **STATE_DB** (起動時 1 回) | `FLOW_COUNTER_CAPABILITY_TABLE\|route` | `support`, `counter_type` (フロー集計ケーパビリティ広告) | `flex_counter/flowcounterrouteorch.cpp:169-178` |
| **ASIC_DB** | SAI `route_entry` | SAI Route API 経由のハード書き込み (副次ではなく主作用) | `routeorch.cpp` 全般 (本ページ「データフロー」参照) |

それ以外 (FLEX_COUNTER_DB, LOGLEVEL_DB, CONFIG_DB) への書込みは検出されなかった。
