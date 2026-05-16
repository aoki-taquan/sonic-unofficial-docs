# ROUTE_TABLE 副次 DB 書込 分析 (Phase F)

対象テーブル: APPL_DB `ROUTE_TABLE`  
調査対象コード:
- `sonic-swss/orchagent/routeorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp`
- `sonic-swss/orchagent/crmorch.cpp`
- `sonic-swss-common/common/schema.h` (ref: 158de8d3463ff4b841653f6d57190bb142b80d9c)

---

## 1. STATE_DB への書込み

### 1-A. STATE_DB `ROUTE_TABLE` — デフォルト経路の有無 (routeorch.cpp:287-294)

`RouteOrch::updateDefRouteState(string ip, bool add)` が書き込む:

```cpp
void RouteOrch::updateDefRouteState(string ip, bool add)
{
    vector<FieldValueTuple> tuples;
    string state = add?"ok":"na";
    FieldValueTuple tuple("state", state);
    tuples.push_back(tuple);
    m_stateDefaultRouteTb->set(ip, tuples);
}
```

- テーブル定義: `schema.h:494` `STATE_ROUTE_TABLE_NAME = "ROUTE_TABLE"`
- DB: `STATE_DB`
- キー: `"0.0.0.0/0"` (IPv4 デフォルト) または `"::/0"` (IPv6 デフォルト)
- フィールド: `state` = `"ok"` (追加時) / `"na"` (削除時)

呼び出しポイント:
- 起動時 (`routeorch.cpp:130, 156`): `"0.0.0.0/0"` と `"::/0"` に `state="na"` で初期化
- デフォルト経路 SET 成功時 (`routeorch.cpp:2703`): `state="ok"` で書き込み
- デフォルト経路 DEL 時 (`routeorch.cpp:2856`): `state="na"` で書き込み

個別経路エントリ（非デフォルト）のステータスは STATE_DB に書き込まれない。

---

## 2. APPL_STATE_DB への書込み

### 2-A. APPL_STATE_DB `ROUTE_TABLE` — 経路ステータス (routeorch.cpp:3185-3201)

`RouteOrch::publishRouteState(const RouteBulkContext& ctx, const ReturnCode& status)` が書き込む:

```cpp
void RouteOrch::publishRouteState(const RouteBulkContext& ctx, const ReturnCode& status)
{
    std::vector<FieldValueTuple> fvs;
    /* Leave the fvs empty if the operation type is "DEL".
     * An empty fvs makes ResponsePublisher::publish() remove the state entry from APPL_STATE_DB */
    if (ctx.is_set)
    {
        fvs.emplace_back("protocol", ctx.protocol);
    }
    const bool replace = false;
    m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace);
}
```

`m_publisher` は `ResponsePublisher{"APPL_STATE_DB"}` (orchagent/orch.h:382)。

- DB: `APPL_STATE_DB`
- キー: `ROUTE_TABLE:<prefix>` または `ROUTE_TABLE:<vrf_name>:<prefix>`
- SET 操作: フィールド `protocol` = ctx.protocol (`"bgp"`, `"static"`, `"kernel"` 等)
- DEL 操作: fvs 空 → エントリ削除

呼び出しポイント (routeorch.cpp):
- `923`: SET 成功時 (normal path)
- `1050`: APPL_DB と APPL_STATE_DB の整合性確保 (force publish)
- `1090`: retry 成功時
- `2729`: SAI route 作成成功後
- `2970`: SAI route 削除成功後

---

## 3. COUNTERS_DB への書込み

### 3-A. COUNTERS_DB `CRM` テーブル — 使用中/利用可能リソース数 (crmorch.cpp)

`CrmOrch` が定期的に `updateCrmCountersTable()` を呼び出し COUNTERS_DB `CRM` テーブルを更新する。

- DB: `COUNTERS_DB`
- テーブル: `CRM` (`COUNTERS_CRM_TABLE = "CRM"`, schema.h:237)
- キー: `STATS`
- 経路関連フィールド:
  - `crm_stats_ipv4_route_used`: IPv4 経路の使用数 (routeorch.cpp:2481, 2532, 2884, 2888)
  - `crm_stats_ipv4_route_available`: IPv4 経路の残容量 (SAI ポーリング)
  - `crm_stats_ipv6_route_used`: IPv6 経路の使用数 (routeorch.cpp:2485, 2536, 2884, 2888)
  - `crm_stats_ipv6_route_available`: IPv6 経路の残容量 (SAI ポーリング)

`incCrmResUsedCounter` / `decCrmResUsedCounter` はメモリ内カウンタを増減するのみ。COUNTERS_DB への実際の書込みは定期タイマー (`CRM_COUNTERS_POLL`) が `updateCrmCountersTable()` を呼び出す際に行われる。

### 3-B. COUNTERS_DB `COUNTERS_ROUTE_NAME_MAP` — Flow Counter マッピング (flowcounterrouteorch.cpp)

`FlowCounterRouteOrch` がルートパターンに合致した経路に対してフロウカウンタをバインドする際に書き込む。

- DB: `COUNTERS_DB`
- テーブル: `COUNTERS_ROUTE_NAME_MAP` (schema.h:252)
- キー: `""`（ハッシュフィールドとしてプレフィックス→カウンタ OID を格納）
- 書込み条件: `FLEX_COUNTER_TABLE` でルートパターンが有効化されている場合のみ。デフォルトでは無効。

### 3-C. COUNTERS_DB `COUNTERS_ROUTE_TO_PATTERN_MAP` — Flow Counter パターンマップ (flowcounterrouteorch.cpp)

- DB: `COUNTERS_DB`
- テーブル: `COUNTERS_ROUTE_TO_PATTERN_MAP` (schema.h:253)
- キー: `""`
- 書込み条件: ルートフロウカウンタが有効な場合のみ (`3-B` と同タイミング)

---

## 4. STATE_DB `FLOW_COUNTER_CAPABILITY_TABLE` への書込み (flowcounterrouteorch.cpp:174-178)

orchagent 起動時に一度だけ書き込む:

```cpp
swss::DBConnector state_db("STATE_DB", 0);
swss::Table capability_table(&state_db, STATE_FLOW_COUNTER_CAPABILITY_TABLE_NAME);
std::vector<FieldValueTuple> fvs;
fvs.emplace_back(FLOW_COUNTER_SUPPORT_FIELD, mRouteFlowCounterSupported ? "true" : "false");
capability_table.set(FLOW_COUNTER_ROUTE_KEY, fvs);
```

- DB: `STATE_DB`
- テーブル: `FLOW_COUNTER_CAPABILITY_TABLE` (schema.h:498)
- キー: `"route"` (FLOW_COUNTER_ROUTE_KEY)
- フィールド: `support` = `"true"` / `"false"` (プラットフォームサポート有無)
- タイミング: orchagent 初期化時に `initRouteFlowCounterCapability()` が 1 回のみ実行

---

## 副作用サマリ

| DB | テーブル | キー形式 | SET | DEL | 条件 |
|----|---------|---------|-----|-----|------|
| STATE_DB | `ROUTE_TABLE` | `0.0.0.0/0` / `::/0` | `state=ok` | `state=na` | デフォルト経路のみ |
| APPL_STATE_DB | `ROUTE_TABLE` | `<prefix>` または `<vrf>:<prefix>` | `protocol=<proto>` 書込 | エントリ削除 | SAI 操作後 常時 |
| COUNTERS_DB | `CRM` | `STATS` | `crm_stats_ipv{4,6}_route_used` 増加 | 減少 | 定期タイマー経由 |
| COUNTERS_DB | `COUNTERS_ROUTE_NAME_MAP` | `""` | プレフィックス→OID マップ | マップ削除 | フロウカウンタ有効時のみ |
| COUNTERS_DB | `COUNTERS_ROUTE_TO_PATTERN_MAP` | `""` | プレフィックス→パターン | マップ削除 | フロウカウンタ有効時のみ |
| STATE_DB | `FLOW_COUNTER_CAPABILITY_TABLE` | `route` | `support=true/false` | — | 起動時 1 回のみ |
