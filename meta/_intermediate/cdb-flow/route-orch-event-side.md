# route-orch-event — Phase F 副次 DB 書き込みスキャンノート

## 対象ソース

- `orchagent/routeorch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/response_publisher.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `common/schema.h` @ sonic-swss-common (STATE_ROUTE_TABLE_NAME = "ROUTE_TABLE")

---

## 調査対象: RouteOrch 通知機構の副次 DB 書き込み

RouteOrch の通知機構は 3 種類の副次 DB 書き込みを生成する。

---

## 1. APPL_STATE_DB — ROUTE_TABLE (ResponsePublisher 経由)

`publishRouteState()` が `m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace)` を呼ぶ。
`response_publisher.cpp` L96-148 により以下の書き込みが行われる。

```cpp
// response_publisher.cpp: publish()
// SAI 成功 (status.ok()) の場合: intent_attrs = state_attrs として APPL_STATE_DB に書き込む
// SAI 失敗の場合: state_attrs = {} となり APPL_STATE_DB には書き込まれない
```

| テーブル | キー形式 | フィールド | 値 | 書き込み元 | タイミング |
|---|---|---|---|---|---|
| `APPL_STATE_DB ROUTE_TABLE` | `ROUTE_TABLE\|<prefix>` | `err_str` | `"SWSS_RC_SUCCESS"` または `"[SAI] ..."` | `ResponsePublisher::writeToDB()` | SAI プログラミング完了後、`doTask()` 末尾の `m_publisher.flush()` 時 |
| `APPL_STATE_DB ROUTE_TABLE` | `ROUTE_TABLE\|<prefix>` | `protocol` | `""` またはソースプロトコル文字列 | 同上 | 同上 (SET 操作時のみ; DEL 時は空 fvs でエントリ削除) |

**書き込み条件**:
- SAI 操作成功 (SET): `err_str` + `protocol` を書き込む
- SAI 操作失敗 (SET): `RESPONSE_CHANNEL` 通知のみ。APPL_STATE_DB には書き込まれない
- DEL 操作: 空 `fvs` で `writeToDB` が呼ばれ、APPL_STATE_DB からエントリが削除される (`response_publisher.cpp` L133-136)

証跡:
- `routeorch.cpp` L923, L1050, L1090, L2729, L2970 (`publishRouteState(ctx)` 呼び出し箇所)
- `routeorch.cpp` L3185-3201 (`publishRouteState()` 本体)
- `response_publisher.cpp` L96-148 (`publish()` 本体)

---

## 2. STATE_DB — ROUTE_TABLE (デフォルトルート状態)

`updateDefRouteState()` が `m_stateDefaultRouteTb->set(ip, tuples)` を呼ぶ。
`STATE_DB ROUTE_TABLE` に `state = "ok"` または `state = "na"` を書き込む。

```cpp
// routeorch.cpp L287-295
void RouteOrch::updateDefRouteState(string ip, bool add)
{
    vector<FieldValueTuple> tuples;
    string state = add?"ok":"na";
    FieldValueTuple tuple("state", state);
    tuples.push_back(tuple);
    m_stateDefaultRouteTb->set(ip, tuples);
}
```

| テーブル | キー形式 | フィールド | 値 | 書き込み元 | タイミング |
|---|---|---|---|---|---|
| `STATE_DB ROUTE_TABLE` | `ROUTE_TABLE\|0.0.0.0/0` | `state` | `"ok"` | `RouteOrch::updateDefRouteState("0.0.0.0/0", true)` | デフォルトルート SAI 書き込み成功後 (routeorch.cpp L2703) |
| `STATE_DB ROUTE_TABLE` | `ROUTE_TABLE\|0.0.0.0/0` | `state` | `"na"` | `RouteOrch::updateDefRouteState("0.0.0.0/0", false)` | デフォルトルート DEL 後 (routeorch.cpp L2856) |
| `STATE_DB ROUTE_TABLE` | `ROUTE_TABLE\|::/0` | `state` | `"ok"` | `RouteOrch::updateDefRouteState("::/0", true)` | IPv6 デフォルトルート SAI 書き込み成功後 |
| `STATE_DB ROUTE_TABLE` | `ROUTE_TABLE\|::/0` | `state` | `"na"` | `RouteOrch::updateDefRouteState("::/0", false)` | IPv6 デフォルトルート DEL 後 |

**起動時初期化**: RouteOrch コンストラクタ (routeorch.cpp L130, L156) で `state = "na"` として初期化される。

証跡: `routeorch.cpp` L126-127 (テーブル初期化), L287-295 (関数本体), L2703, L2856 (呼び出し箇所)

---

## 3. Redis Pub/Sub — RESPONSE_CHANNEL (SAI 結果通知)

`APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` に通知を送出する。DB への永続書き込みではなく一時的なメッセージングチャネル。

```cpp
// response_publisher.cpp: publish() L107-114
std::string response_channel = "APPL_DB_" + table + "_RESPONSE_CHANNEL";
// → "APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL"
swss::NotificationProducer notificationProducer{m_ntf_pipe.get(), response_channel, m_buffered};
notificationProducer.send(status.codeStr(), key, intent_attrs_copy);
```

| チャネル | メッセージ形式 | 購読者 | 条件 |
|---|---|---|---|
| `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` | `(status_code, prefix_key, [(err_str, val), (protocol, val)])` | `fpmsyncd` (`routesync.cpp` L3156-3190) | `suppress-fib-pending = enabled` かつ fpmsyncd 稼働中のみ |

通知は `doTask()` 末尾の `m_publisher.flush()` (routeorch.cpp L1231) まではバッファされる。

---

## 副次 DB 書き込みサマリ

| 書き込み先 | テーブル | 条件 | 書き込み元 |
|---|---|---|---|
| APPL_STATE_DB | `ROUTE_TABLE` | SAI SET 成功時のみ。DEL 時はエントリ削除 | `ResponsePublisher::writeToDB()` via `publishRouteState()` |
| STATE_DB | `ROUTE_TABLE` | デフォルトルート (0.0.0.0/0, ::/0) の追加/削除時のみ | `RouteOrch::updateDefRouteState()` |
| Redis Pub/Sub | `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` | `suppress-fib-pending = enabled` 時。バッファ後 `flush()` で発火 | `ResponsePublisher::publish()` |
