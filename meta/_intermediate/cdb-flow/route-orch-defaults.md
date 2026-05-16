# RouteOrch / FlowCounterRouteOrch — CONFIG_DB フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `FLOW_COUNTER_ROUTE_PATTERN`  
調査対象ファイル:
- `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.cpp` (FlowCounterRouteOrch::doTask)
- `sonic-swss/orchagent/flex_counter/flowcounterrouteorch.h` (RoutePattern 構造体)
- `sonic-utilities/flow_counter_util/route.py` (テーブル名・フィールド名定数)
- `sonic-swss/orchagent/orchdaemon.cpp` (FlowCounterRouteOrch 初期化)

---

## 概要

`RouteOrch` 本体 (orchagent/routeorch.cpp) は **CONFIG_DB を直接購読しない**。  
CONFIG_DB への接続を持つのは `FlowCounterRouteOrch`（同じ orchagent プロセス内）であり、
CONFIG_DB `FLOW_COUNTER_ROUTE_PATTERN` テーブルを購読してルートフローカウンターのパターンを管理する。

```
orchdaemon.cpp:250-253
static const vector<string> route_pattern_tables = {
    CFG_FLOW_COUNTER_ROUTE_PATTERN_TABLE_NAME,
};
gFlowCounterRouteOrch = new FlowCounterRouteOrch(m_configDb, route_pattern_tables);
```

テーブル名文字列:
```python
# sonic-utilities/flow_counter_util/route.py:20
FLOW_COUNTER_ROUTE_PATTERN_TABLE = 'FLOW_COUNTER_ROUTE_PATTERN'
```

---

## FLOW_COUNTER_ROUTE_PATTERN フィールド別 暗黙デフォルト

### `max_match_count`

**コード由来デフォルト**: `30`

```cpp
// flowcounterrouteorch.cpp:25
#define ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT       30

// flowcounterrouteorch.cpp:73-86
size_t maxMatchCount = ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT;
for (auto valuePair : data)
{
    const auto &field = fvField(valuePair);
    const auto &value = fvValue(valuePair);
    if (field == ROUTE_PATTERN_MAX_MATCH_COUNT_FIELD)
    {
        maxMatchCount = (size_t)std::stoul(value);
        if (maxMatchCount == 0)
        {
            SWSS_LOG_WARN("Max match count for route pattern cannot be 0, set it to default value 30");
            maxMatchCount = ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT;
        }
    }
}
```

- `max_match_count` フィールドが CONFIG_DB エントリに存在しない場合、`30` が使用される。
- `max_match_count = 0` を設定すると警告を発して `30` にフォールバックする（0 は無効値）。
- Python 側でも `DEFAULT_MAX_MATCH = 30` として同値が定義されている (`flow_counter_util/route.py:23`)。

---

## ROUTE_TABLE (APP_DB) フィールド — RouteOrch 消費側デフォルト

RouteOrch は APP_DB `ROUTE_TABLE` を購読し、各フィールドが不在の場合のデフォルト動作をコードで定義している。

### `blackhole`

**コード由来デフォルト**: `false`（フィールド不在 = false として処理）

```cpp
// routeorch.cpp:765-766
if (fvField(i) == "blackhole")
    blackhole = fvValue(i) == "true";
```

変数 `blackhole` は `bool blackhole = false;` と宣言（ローカル変数の初期値）。
フィールドが不在でも `false` のまま使われる。

### `nexthop` / `ifname`

**コード由来デフォルト**: 空文字列 → empty vector

```cpp
// routeorch.cpp:727-729,841-842
string ips;      // デフォルト空文字列
string aliases;  // デフォルト空文字列
...
ipv = tokenize(ips, ',');
alsv = tokenize(aliases, ',');
```

フィールド不在の場合 `ips`/`aliases` は空文字列のまま。`tokenize("", ',')` は空ベクタを返す。
ただし blackhole でも srv6_nh でもない場合、`alsv.size() == 0` はスキップ条件になる:

```cpp
// routeorch.cpp:857-861
if (alsv.size() == 0 && !blackhole && !srv6_nh)
{
    SWSS_LOG_WARN("Skip the route %s, for it has an empty ifname field.", key.c_str());
    it = consumer.m_toSync.erase(it);
    continue;
}
```

### `weight`

**コード由来デフォルト**: APPL_DB 側で書き込まれたフィールドが不在 → orchagent は空のまま処理し、SAI には weight 属性を設定しない。  
fpmsyncd 側では `rtnl_route_nh_get_weight() == 0` の場合に `1` を書き込むため、通常は `"1"` が存在する (`fpmsyncd/routesync.cpp`)。

### `fallback_to_default_route`

**コード由来デフォルト**: `false`（フィールド不在 = false）

```cpp
// routeorch.cpp:744,790-791
bool fallback_to_default_route = false;
...
if (fvField(i) == "fallback_to_default_route")
    fallback_to_default_route = fvValue(i) == "true";
```

### `protocol`

**コード由来デフォルト**: 空文字列（フィールド不在 = ctx.protocol は空のまま）

```cpp
// routeorch.cpp:785-788
if (fvField(i) == "protocol" && fvValue(i) != "")
{
    ctx.protocol = fvValue(i);
}
```

### `nexthop_group` (`nhg_index`)

**コード由来デフォルト**: 空文字列（NhgOrch 管理 NHG を使わない = RouteOrch 自身が NHG を管理）

```cpp
// routeorch.cpp:771-773
if (fvField(i) == "nexthop_group" && fvValue(i) != "")
    nhg_index = fvValue(i);
```

---

## FlowCounterRouteOrch — ポーリングインターバルデフォルト

```cpp
// flowcounterrouteorch.cpp:26
#define ROUTE_FLOW_COUNTER_POLLING_INTERVAL_MS      10000
```

`FlexCounterManager` 初期化時に `10000ms`（10秒）がハードコードされている。  
CONFIG_DB からは設定不可（固定値）。

---

## まとめ

| テーブル | フィールド | コード由来デフォルト | ソース |
|---------|-----------|-------------------|-------|
| `FLOW_COUNTER_ROUTE_PATTERN` | `max_match_count` | `30`（0 を指定すると 30 にフォールバック） | flowcounterrouteorch.cpp:25,83 |
| `ROUTE_TABLE` (APP_DB) | `blackhole` | `false`（フィールド不在） | routeorch.cpp:737,765 |
| `ROUTE_TABLE` (APP_DB) | `fallback_to_default_route` | `false`（フィールド不在） | routeorch.cpp:744,790 |
| `ROUTE_TABLE` (APP_DB) | `protocol` | `""`（フィールド不在） | routeorch.cpp:734,785 |
| `ROUTE_TABLE` (APP_DB) | `nexthop`/`ifname` | `""`（blackhole/srv6_nh でなければスキップ） | routeorch.cpp:727,857 |
| `ROUTE_TABLE` (APP_DB) | `nexthop_group` | `""`（RouteOrch 自身が NHG 管理） | routeorch.cpp:733,771 |
| 内部定数 | polling interval | `10000ms`（固定） | flowcounterrouteorch.cpp:26 |
