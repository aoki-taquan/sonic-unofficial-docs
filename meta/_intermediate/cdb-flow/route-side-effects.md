# ROUTE_TABLE 副次 DB 書込 分析 (Phase F — side-effects)

対象ドキュメント: `docs/reference/config-db/route.md`  
対象テーブル: APPL_DB `ROUTE_TABLE`  
調査対象ソース:
- `sonic-swss/orchagent/routeorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp`
- `sonic-swss/orchagent/crmorch.cpp`

> このファイルは `meta/_intermediate/cdb-flow/route-side.md` の内容と同一の分析を
> Phase F 標準命名規則 `<slug>-side-effects.md` に従ってまとめたものです。
> `route.md` の `<!-- side-effects -->` ブロックに反映済み。

---

## 1. STATE_DB への書込み

### 1-A. STATE_DB `ROUTE_TABLE` — デフォルト経路の有無 (routeorch.cpp:287-294)

`RouteOrch::updateDefRouteState(string ip, bool add)` が書き込む:

```cpp
void RouteOrch::updateDefRouteState(string ip, bool add)
{
    vector<FieldValueTuple> tuples;
    string state = add ? "ok" : "na";
    FieldValueTuple tuple("state", state);
    tuples.push_back(tuple);
    m_stateDefaultRouteTb->set(ip, tuples);
}
```

- DB: `STATE_DB`
- テーブル: `ROUTE_TABLE` (STATE_ROUTE_TABLE_NAME, schema.h:494)
- キー: `"0.0.0.0/0"` (IPv4 デフォルト経路) または `"::/0"` (IPv6 デフォルト経路)
- フィールド: `state` = `"ok"` (経路追加時) / `"na"` (経路削除時)

呼び出しポイント:
- 起動時 (`routeorch.cpp:130, 156`): `"0.0.0.0/0"` と `"::/0"` に `state="na"` で初期化
- デフォルト経路 SET 成功時 (`routeorch.cpp:2703`): `state="ok"` で書き込み
- デフォルト経路 DEL 時 (`routeorch.cpp:2856`): `state="na"` で書き込み

**重要**: 個別経路エントリ（非デフォルト経路）のステータスは STATE_DB に書き込まれない。

---

## 2. APPL_STATE_DB への書込み

### 2-A. APPL_STATE_DB `ROUTE_TABLE` — 経路処理ステータス (routeorch.cpp:3185-3201)

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
- テーブル: `ROUTE_TABLE`
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

## 3. ASIC_DB / SAI route_entry への書込み

`RouteOrch` が SAI API を呼び出すことで `syncd` 経由で ASIC_DB に反映される。直接の DB 書込みではなく SAI オブジェクト操作。

- オブジェクト型: `SAI_OBJECT_TYPE_ROUTE_ENTRY` (`sai_route_entry_t`)
- 操作関数:
  - `sai_route_api->create_route_entry()` — 経路追加
  - `sai_route_api->remove_route_entry()` — 経路削除
  - `sai_route_api->set_route_entry_attribute()` — 経路更新
- ASIC_DB キー形式: `ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY:{"dest":"<prefix>","switch_id":"<oid>","vr_id":"<vrf_oid>"}`

バルク操作: `sai_route_api->create_route_entries()` / `remove_route_entries()` が使用される
(routeorch.cpp の BulkContext 系関数)。

---

## 4. NEXTHOP_GROUP_TABLE 関連の副作用

### 4-A. NhgOrch リファレンスカウント管理 (routeorch.cpp)

`nexthop_group` フィールドを持つ ROUTE_TABLE エントリを追加・削除する際、`NhgOrch` のリファレンスカウントが増減する:

- SET 時: `gNhgOrch->getNhg(nhg_index).getKey()` でカウント増加
- DEL 時: `nhgEntry.dec_ref_count()` でカウント減少

NHG エントリのリファレンスカウントが 0 になるまで `NEXTHOP_GROUP_TABLE` の削除はブロックされる。

---

## 5. COUNTERS_DB への書込み

### 5-A. COUNTERS_DB `CRM` テーブル — 使用中リソース数 (crmorch.cpp)

`CrmOrch` が定期タイマー `CRM_COUNTERS_POLL` で `updateCrmCountersTable()` を呼び出す:

- DB: `COUNTERS_DB`
- テーブル: `CRM` (COUNTERS_CRM_TABLE, schema.h:237)
- キー: `STATS`
- フィールド:
  - `crm_stats_ipv4_route_used`: IPv4 経路の使用数 (routeorch.cpp:2481, 2532, 2884, 2888)
  - `crm_stats_ipv6_route_used`: IPv6 経路の使用数 (routeorch.cpp:2485, 2536, 2884, 2888)

### 5-B. COUNTERS_DB Flow Counter マッピング (flowcounterrouteorch.cpp)

フロウカウンタが有効な場合のみ書き込む:

- `COUNTERS_ROUTE_NAME_MAP` (schema.h:252): プレフィックス → カウンタ OID マッピング
- `COUNTERS_ROUTE_TO_PATTERN_MAP` (schema.h:253): プレフィックス → パターンマッピング

---

## 6. STATE_DB `FLOW_COUNTER_CAPABILITY_TABLE` — 起動時 1 回のみ

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
- フィールド: `support` = `"true"` / `"false"`
- タイミング: orchagent 初期化時に `initRouteFlowCounterCapability()` が 1 回のみ実行

---

## 副作用サマリ

| DB | テーブル | キー形式 | SET | DEL | 条件 |
|----|---------|---------|-----|-----|------|
| STATE_DB | `ROUTE_TABLE` | `0.0.0.0/0` / `::/0` | `state=ok` | `state=na` | デフォルト経路のみ |
| APPL_STATE_DB | `ROUTE_TABLE` | `<prefix>` / `<vrf>:<prefix>` | `protocol=<proto>` 書込 | エントリ削除 | SAI 操作後 常時 |
| ASIC_DB | `ASIC_STATE:SAI_OBJECT_TYPE_ROUTE_ENTRY` | `{"dest":"<pfx>","switch_id":"<oid>","vr_id":"<oid>"}` | route_entry 作成 | route_entry 削除 | syncd 経由 |
| COUNTERS_DB | `CRM` | `STATS` | `crm_stats_ipv{4,6}_route_used` 増加 | 減少 | 定期タイマー経由 |
| COUNTERS_DB | `COUNTERS_ROUTE_NAME_MAP` | `""` | プレフィックス→OID マップ追加 | マップ削除 | フロウカウンタ有効時のみ |
| COUNTERS_DB | `COUNTERS_ROUTE_TO_PATTERN_MAP` | `""` | プレフィックス→パターン追加 | マップ削除 | フロウカウンタ有効時のみ |
| STATE_DB | `FLOW_COUNTER_CAPABILITY_TABLE` | `route` | `support=true/false` | — | 起動時 1 回のみ |
