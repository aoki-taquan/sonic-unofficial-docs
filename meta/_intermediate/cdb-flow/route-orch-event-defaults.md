# route-orch-event — Phase A デフォルト調査メモ

## 対象ソース

- `orchagent/routeorch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/routeorch.h` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/response_publisher.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`

## 対象: RouteOrch event/notification 送出機構

RouteOrch は 2 種類の「通知」を送出する:

1. **ResponsePublisher 経由の APPL_STATE_DB 書き込み + RESPONSE_CHANNEL 通知**
   - `publishRouteState()` → `m_publisher.publish(APP_ROUTE_TABLE_NAME, ...)`
   - フィールド: `protocol`（SET 時のみ）、`err_str`（自動付与）
   - 送信先: APPL_STATE_DB、`APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL`

2. **内部 Observer パターン (`SUBJECT_TYPE_NEXTHOP_CHANGE`)**
   - `notifyNextHopChangeObservers()` → `observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, ...)`
   - `NextHopUpdate` 構造体で vrf_id / destination / prefix / nexthopGroup を伝達
   - 購読者: NeighOrch, MirrorOrch, etc. が `attach()` で登録

---

## 1. `publishRouteState()` — RESPONSE_CHANNEL 通知フィールド

### コード (routeorch.cpp L3185–3202)

```cpp
void RouteOrch::publishRouteState(const RouteBulkContext& ctx, const ReturnCode& status)
{
    SWSS_LOG_ENTER();

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

### フィールド詳細

| フィールド | SET 操作時 | DEL 操作時 |
|-----------|-----------|-----------|
| `protocol` | `ctx.protocol` の値（デフォルト: `""`） | 送信しない（fvs が空） |
| `err_str` | `ResponsePublisher` が自動付与 | 同上 |

### `ctx.protocol` の初期値とセット条件

`RouteBulkContext` の `protocol` フィールド初期値は `""`:

```cpp
// routeorch.cpp L157-177
RouteBulkContext(const std::string& key, bool is_set)
    : key(key), is_set(is_set)
    ...
// clear() 呼び出し時
protocol.clear();  // → ""
```

APPL_DB の SET メッセージから読み取るコード (L785-788):

```cpp
if (fvField(i) == "protocol" && fvValue(i) != "")
{
    ctx.protocol = fvValue(i);
}
```

- APPL_DB の `protocol` フィールドが存在し空でない → その値を使用
- APPL_DB に `protocol` フィールドが存在しない → `ctx.protocol = ""`（空文字列）のまま

### ResponsePublisher.publish() での `err_str` 付与

`response_publisher.cpp` L102-103:

```cpp
swss::FieldValueTuple err_str("err_str", PrependedComponent(status) + status.message());
intent_attrs_copy.insert(intent_attrs_copy.begin(), err_str);
```

`PrependedComponent(status)` の決定ロジック:

```cpp
std::string PrependedComponent(const ReturnCode &status)
{
    constexpr char *kOrchagentComponent = "[OrchAgent] ";
    constexpr char *kSaiComponent = "[SAI] ";
    if (status.ok())
        return "";
    if (status.isSai())
        return kSaiComponent;
    return kOrchagentComponent;
}
```

| 状態 | `err_str` |
|------|-----------|
| SAI 成功 | `"SWSS_RC_SUCCESS"` |
| SAI エラー | `"[SAI] <エラーメッセージ>"` |
| OrchAgent エラー | `"[OrchAgent] <エラーメッセージ>"` |

### APPL_STATE_DB 書き込み条件

`response_publisher.cpp` L133-138:

```cpp
if (m_enable_db_write_and_notify &&
     ((intent_attrs.size() && state_attrs.size()) ||
     (status.ok() && !intent_attrs.size())))
{
    writeToDB(table, key, state_attrs, intent_attrs.size() ? SET_COMMAND : DEL_COMMAND, replace);
}
```

- SET 操作（`intent_attrs.size() > 0`）かつ SAI 成功 → APPL_STATE_DB に `protocol` + `err_str` を書き込む
- DEL 操作（`intent_attrs.size() == 0`）かつ SAI 成功 → APPL_STATE_DB からエントリを削除（DEL_COMMAND）
- SAI 失敗 → APPL_STATE_DB 書き込みなし（RESPONSE_CHANNEL への通知のみ）

### バッファリング設定

RouteOrch コンストラクタ (routeorch.cpp L57-58):

```cpp
m_publisher.setBuffered(true);
m_publisher.m_directDbWrite = true;
```

- `setBuffered(true)`: 通知は Redis パイプライン経由でバッファリング
- `m_directDbWrite = true`: DB への書き込みはパイプライン経由（非スレッド）
- `m_publisher.flush()` は doTask() の最後に必ず呼ばれる (L1231):

```cpp
/* Flush response publisher so route notifications reach fpmsyncd every batch. */
m_publisher.flush();
```

---

## 2. `notifyNextHopChangeObservers()` — 内部 Observer 通知

### `NextHopUpdate` 構造体 (routeorch.h L61-68)

```cpp
struct NextHopUpdate
{
    sai_object_id_t vrf_id;
    IpAddress destination;
    IpPrefix prefix;
    NextHopGroupKey nexthopGroup;
};
```

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `vrf_id` | `sai_object_id_t` | VRF の SAI オブジェクト ID |
| `destination` | `IpAddress` | Observer が追跡しているホスト IP |
| `prefix` | `IpPrefix` | マッチした最長プレフィックス |
| `nexthopGroup` | `NextHopGroupKey` | 新しい nexthop グループキー |

### 通知発火条件 (routeorch.cpp L1270-1340)

```cpp
void RouteOrch::notifyNextHopChangeObservers(
    sai_object_id_t vrf_id, const IpPrefix &prefix,
    const NextHopGroupKey &nexthops, bool add)
```

**ADD 時の発火条件**:
- 新規ルートが追加され、かつそのルートが当該 Observer 宛先の「最長プレフィックスマッチ」である場合
- 既存ルートの nexthopGroup が変化し、かつそのルートが最長プレフィックスマッチである場合

**DEL 時の発火条件**:
- 削除されたルートが最長プレフィックスマッチであった場合（次の最長マッチで再通知）

### `attach()` 時の即時通知 (routeorch.cpp L340-350)

```cpp
// Trigger next hop change for the first time the observer is attached
auto route = observerEntry->second.routeTable.rbegin();
if (route != observerEntry->second.routeTable.rend())
{
    NextHopUpdate update = { vrf_id, dstAddr, route->first, route->second.nhg_key };
    observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, static_cast<void *>(&update));
}
```

Observer が `attach()` した時点で、現在の最長プレフィックスマッチが存在すれば即時通知。

### デフォルトルートは常に存在する保証

`assert(!entry.second.routeTable.empty())` が ADD/DEL 通知の直前に存在:

```cpp
/* Table should not be empty. Default route should always exists. */
assert(!entry.second.routeTable.empty());
```

Observer 追跡テーブルには必ずデフォルトルート (`0.0.0.0/0` / `::/0`) が含まれるため、
最長プレフィックスマッチは必ず 1 件以上存在する。

---

## 3. RESPONSE_CHANNEL の購読者

`APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` の主な購読者:

- **fpmsyncd**: SAI プログラミング結果を FRR (zebra) へフィードバック。
  - `err_str` が `SWSS_RC_SUCCESS` でない場合、FRR は経路を再送信または削除する。

## 4. 呼び出し箇所一覧

`publishRouteState()` の呼び出し箇所 (routeorch.cpp):

| 行番号 | 状況 |
|--------|------|
| L923 | `addRoute()` 内: SAI エラー時（戻り値 false）直後 |
| L1050 | `addRoute()` 内: 既存エントリと一致（re-publish） |
| L1090 | `addRoute()` 内: 重複エントリ追加スキップ時 |
| L2729 | `addRoutePost()` 末尾: SAI 操作完了後 |
| L2970 | `removeRoutePost()` 末尾: SAI 操作完了後 |
