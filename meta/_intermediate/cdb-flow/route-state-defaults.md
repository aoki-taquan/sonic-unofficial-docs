# route-state-defaults.md — Phase A: STATE_DB ROUTE_TABLE コード由来デフォルト

## 対象テーブル

`STATE_DB` の `ROUTE_TABLE`（スキーマ定数: `STATE_ROUTE_TABLE_NAME`）

ソース: `sonic-swss-common/common/schema.h` line 494

```cpp
#define STATE_ROUTE_TABLE_NAME  "ROUTE_TABLE"
```

---

## 書き込み主体

### 1. `RouteOrch::updateDefRouteState()` — デフォルト経路の状態管理

ソース: `sonic-swss/orchagent/routeorch.cpp` lines 287–295

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

書き込まれるフィールド:
- `state`: `"ok"`（デフォルト経路あり）または `"na"`（デフォルト経路なし）

キー例: `0.0.0.0/0`、`::0/0`

### 2. `RouteOrch::publishRouteState()` — APPL_STATE_DB への経路状態書き込み

ソース: `sonic-swss/orchagent/routeorch.cpp` lines 3185–3202

```cpp
void RouteOrch::publishRouteState(const RouteBulkContext& ctx, const ReturnCode& status)
{
    std::vector<FieldValueTuple> fvs;

    /* Leave the fvs empty if the operation type is "DEL".
     * An empty fvs makes ResponsePublisher::publish() remove the state entry from APPL_STATE_DB
     */
    if (ctx.is_set)
    {
        fvs.emplace_back("protocol", ctx.protocol);
    }

    const bool replace = false;

    m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace);
}
```

これは **APPL_STATE_DB** の `ROUTE_TABLE` に書き込む（STATE_DB とは別 DB）。

書き込まれるフィールド（SET操作時）:
- `protocol`: `ctx.protocol`（フィールド不在時は空文字列 `""`）
- `err_str`: `ResponsePublisher::publish()` が自動付与 — `PrependedComponent(status) + status.message()`

DEL操作時は fvs が空となり、APPL_STATE_DB のエントリ自体が削除される。

---

## フィールドのデフォルト値まとめ

### STATE_DB ROUTE_TABLE

| フィールド | コード由来デフォルト | 書込み条件 | 出典 |
|-----------|-------------------|-----------|------|
| `state` | なし（明示的にのみ書く） | デフォルト経路の追加/削除時のみ | routeorch.cpp:290–291 |

- `add=true` → `"ok"` を書き込む
- `add=false` → `"na"` を書き込む
- デフォルト経路以外の経路はこのテーブルに書き込まれない

### APPL_STATE_DB ROUTE_TABLE

| フィールド | コード由来デフォルト | 書込み条件 | 出典 |
|-----------|-------------------|-----------|------|
| `protocol` | `""` (空文字列 / フィールド不在) | SET操作 (is_set=true) のみ。DEL時はエントリ削除 | routeorch.cpp:3196 |
| `err_str` | `"SWSS_RC_SUCCESS"` (成功時) | ResponsePublisher が自動付与 | response_publisher.cpp:102 |

---

## ctx.protocol の初期化

`RouteBulkContext::protocol` の暗黙デフォルトは `""`:

```cpp
// routeorch.cpp line 785-787
if (fvField(i) == "protocol" && fvValue(i) != "")
{
    ctx.protocol = fvValue(i);
}
```

APPL_DB の `ROUTE_TABLE` に `protocol` フィールドがなければ `ctx.protocol` は `""` のまま。この場合 APPL_STATE_DB にも `protocol=""` が書き込まれる。

---

## 検出した注意点

1. **STATE_DB の ROUTE_TABLE はデフォルト経路専用**: `updateDefRouteState()` はデフォルト経路（0.0.0.0/0 / ::0/0）のみを対象にする。一般のユニキャスト経路は STATE_DB の ROUTE_TABLE には書き込まれない。

2. **APPL_STATE_DB と STATE_DB は別**: `publishRouteState()` は APPL_STATE_DB に書き込む。STATE_DB の ROUTE_TABLE と混同しやすい。

3. **`"na"` はデフォルト経路削除を意味する**: STATE_DB `ROUTE_TABLE` の `state="na"` はフィールドの「不在」ではなく「デフォルト経路なし」という明示的な状態。

4. **ResponsePublisher の err_str**: APPL_STATE_DB には SAI 操作の結果として `err_str` が常に付与される。成功時は `"SWSS_RC_SUCCESS"` または `"[SAI] SAI_STATUS_SUCCESS"` になる。

---

## ソース参照

- `sonic-swss/orchagent/routeorch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d lines 287–295, 3185–3202
- `sonic-swss/orchagent/response_publisher.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d lines 96–150
- `sonic-swss-common/common/schema.h` @ 158de8d3463ff4b841653f6d57190bb142b80d9c line 494
