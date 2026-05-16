# APPL_DB VRF_TABLE — 副次 DB 書込 (Phase F) 中間スキャン

調査対象: `sonic-swss/orchagent/vrforch.cpp` (ref `4305596156d70e9797e8a881b3d19b46de0bce0d`)
関連ファイル: `vrforch.h`、`flex_counter/flowcounterrouteorch.cpp`、`sonic-swss-common/common/schema.h`
スコープ: APPL_DB `VRF_TABLE` (※ `VNET_TABLE` 経路は `VnetOrch` 別ページ扱い。本ページでは VRF_TABLE 経路の副次書込のみを対象とし、VNET 経路は参照リンクで触れる)

## grep 結果サマリ

`vrforch.cpp` 全文に対するスキャン:

```
grep -nE "(StateDB|state_db|STATE_|CountersDB|COUNTERS_|counters_db|m_state|m_app|producerTable|ProducerStateTable|Table\\(|hset|publish|notification)" vrforch.cpp
→
120:        m_stateVrfObjectTable.hset(vrf_name, "state", "ok");
150:        m_stateVrfObjectTable.hset(vrf_name, "state", "ok");
193:    m_stateVrfObjectTable.del(vrf_name);
```

`vrforch.h`:

```
52:    VRFOrch(swss::DBConnector *appDb, const std::string& appTableName, swss::DBConnector *stateDb, const std::string& stateTableName) :
54:        m_stateVrfObjectTable(stateDb, stateTableName)
182:    swss::Table m_stateVrfObjectTable;
```

→ `VRFOrch` が保持する書込先 swss Table は `m_stateVrfObjectTable` ただ 1 つ。APPL_DB / COUNTERS_DB / FLEX_COUNTER_DB / ASIC_DB / LOGLEVEL_DB への直接書込ハンドルは存在しない。

## 直接書込 — STATE_DB `VRF_OBJECT_TABLE`

| トリガ | コード位置 | 書込内容 |
|---|---|---|
| `addOperation` create 成功後 | `vrforch.cpp:120` | `m_stateVrfObjectTable.hset(vrf_name, "state", "ok")` |
| `addOperation` update 成功後 | `vrforch.cpp:150` | `m_stateVrfObjectTable.hset(vrf_name, "state", "ok")` |
| `delOperation` 成功後 | `vrforch.cpp:193` | `m_stateVrfObjectTable.del(vrf_name)` |

テーブル名は `orchdaemon.cpp` で `VRFOrch` を構築する際に `STATE_VRF_OBJECT_TABLE_NAME` (`schema.h` の `STATE_VRF_OBJECT_TABLE_NAME = "VRF_OBJECT_TABLE"`) が渡される。

購読側: `vrfmgrd::isVrfObjExist()` が VRF 削除のタイミング制御に使用 (`sonic-swss/cfgmgr/vrfmgr.cpp`)。

## 間接書込 — COUNTERS_DB / FLEX_COUNTER_DB (条件付き)

`vrforch.cpp:110` と `:184` で `gFlowCounterRouteOrch->onAddVR(router_id)` / `onRemoveVR(router_id)` を呼ぶ。

```cpp
// vrforch.cpp:110
gFlowCounterRouteOrch->onAddVR(router_id);
// vrforch.cpp:184
gFlowCounterRouteOrch->onRemoveVR(router_id);
```

`FlowCounterRouteOrch::onAddVR` (`flex_counter/flowcounterrouteorch.cpp:401-432`) はガード `mRouteFlowCounterSupported == false` の場合に即 return する。`true` の場合、`mRoutePatternSet` の中で `vrf_name` 一致する `RoutePattern` が存在する場合に限り `createRouteFlowCounterByPattern()` を呼ぶ。

`FlowCounterRouteOrch` が保持する DB:

```
flowcounterrouteorch.cpp:31  mCounterDb(new DBConnector("COUNTERS_DB", 0))
flowcounterrouteorch.cpp:33  mPrefixToCounterTable(... COUNTERS_ROUTE_NAME_MAP)
flowcounterrouteorch.cpp:34  mPrefixToPatternTable(... COUNTERS_ROUTE_TO_PATTERN_MAP)
flowcounterrouteorch.cpp:35  mRouteFlowCounterMgr(ROUTE_FLOW_COUNTER_FLEX_COUNTER_GROUP, ...)
```

つまり VRF_TABLE への SET/DEL が、以下の条件すべてを満たす場合に限り間接的に COUNTERS_DB / FLEX_COUNTER_DB に副次書込みが発火する:

1. プラットフォームが `mRouteFlowCounterSupported == true` (`FlexCounterOrch::getRouteFlowCountersState()` 由来、デフォルト無効)
2. CONFIG_DB `FLOW_COUNTER_ROUTE_PATTERN_TABLE` に当該 `vrf_name` を含むパターンが登録済み

通常運用（ROUTE フローカウンタ未使用）では **発火しない**。

## その他 DB スキャン

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB (他テーブルへの fan-out) | なし | `VRFOrch` は `Orch2(appDb, appTableName, ...)` で APP_VRF_TABLE_NAME を購読側として使うのみ。`appDb` への producer hands は持たない (`vrforch.h:52-56`) |
| ASIC_DB | なし (SAI 経由) | `sai_virtual_router_api->create_virtual_router()` が syncd → ASIC_DB に流すが、これは SAI 通常経路。VRFOrch が直接 ASIC_DB Table を持つことはない |
| LOGLEVEL_DB | なし | grep ヒットなし |
| FLEX_COUNTER_DB (直接) | なし | `VRFOrch` 自身は FLEX_COUNTER_DB Table を保持しない。間接経路は上記 `FlowCounterRouteOrch` のみ |
| Notification channel | なし | `vrforch.cpp` に `NotificationProducer` / `publish` の呼出なし |

## 結論

- **直接副次書込**: STATE_DB `VRF_OBJECT_TABLE` 1 系統のみ（既にページ本文「購読者」「STATE_DB 書き戻し」節に明記済み）。
- **間接副次書込**: `FlowCounterRouteOrch` 経由で COUNTERS_DB `COUNTERS_ROUTE_NAME_MAP` / `COUNTERS_ROUTE_TO_PATTERN_MAP` / FLEX_COUNTER_DB に条件付き発火。デフォルト無効。
- **VNET_TABLE 経路**: 本ページは VRF_TABLE スコープ。VNET_TABLE 側の副次書込（`STATE_VNET_RT_TUNNEL_TABLE`、`STATE_ADVERTISE_NETWORK_TABLE` 等）は `VnetOrch` の責務であり、別ページで扱う。
