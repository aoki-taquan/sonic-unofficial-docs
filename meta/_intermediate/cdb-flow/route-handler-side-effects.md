# route-handler — Phase F: 副作用・連鎖変更 調査証跡

生成日: 2026-05-18
対象ページ: `docs/reference/config-db/route-handler.md`

## 訪問ファイル一覧

| ファイル | 関数 / セクション | 目的 |
|---------|----------------|------|
| `sonic-swss/fpmsyncd/routesync.cpp` | `setRouteWithWarmRestart()` L172-189 | APPL_DB 書き込みと warm-restart 中の遅延挙動 |
| `sonic-swss/fpmsyncd/routesync.cpp` | `delWithWarmRestart()` L198-206 | DEL と warm-restart 中遅延挙動 |
| `sonic-swss/fpmsyncd/routesync.cpp` | `onRouteResponse()` L3165-3270 | オフロード応答構築・FPM 送出 |
| `sonic-swss/fpmsyncd/routesync.cpp` | `sendOffloadReply(nlmsghdr*)` L3100-3131 | RTM_F_OFFLOAD フラグ付加・zebra への FPM 送出 |
| `sonic-swss/fpmsyncd/routesync.cpp` | `markRoutesOffloaded()` L3291-3295 | warm-restart 終了時の一括オフロード応答 |
| `sonic-swss/orchagent/routeorch.cpp` | コンストラクタ L126-127 | STATE_DB:ROUTE_TABLE テーブル初期化 |
| `sonic-swss/orchagent/routeorch.cpp` | `updateDefRouteState()` L287-295 | STATE_DB:ROUTE_TABLE デフォルト経路状態更新 |
| `sonic-swss/orchagent/routeorch.cpp` | `publishRouteState()` L3185-3201 | APPL_STATE_DB:ROUTE_TABLE 更新 |
| `sonic-swss/orchagent/routeorch.cpp` | `doTask()` L605-1114 | 副作用呼出しポイント一覧 |

## 副作用詳細

### 1. APPL_DB:ROUTE_TABLE (fpmsyncd が書き手)

`setRouteWithWarmRestart()` は通常時 `ProducerStateTable::set()` で書き込む。
warm-restart 中は `m_warmStartHelper.insertRefreshMap()` に積み、reconcile 後に一括書き込む。

証跡:
```cpp
// routesync.cpp:172-189
void RouteSync::setRouteWithWarmRestart(FieldValueTupleWrapperBase & fvw,
                                        ProducerStateTable & table )
{
    bool warmRestartInProgress = m_warmStartHelper.inProgress();
    if (!warmRestartInProgress)
    {
        table.set(fvw.KeyOpFieldsValuesTupleVector());
    }
    else
    {
        if(isNbZmqEnabled()) {
            m_warmStartHelper.insertRefreshMap(fvw.KeyOpFieldsValuesTupleVector()[0]);
        } else {
            m_warmStartHelper.insertRefreshMap(fvw.KeyOpFieldsValuesTupleVector()[1]);
        }
    }
}
```

### 2. APPL_STATE_DB:ROUTE_TABLE (orchagent が書き手)

`publishRouteState()` が `ResponsePublisher::publish()` 経由で書き込む。

証跡:
```cpp
// routeorch.cpp:3185-3201
void RouteOrch::publishRouteState(const RouteBulkContext& ctx, const ReturnCode& status)
{
    std::vector<FieldValueTuple> fvs;
    if (ctx.is_set)
    {
        fvs.emplace_back("protocol", ctx.protocol);
    }
    const bool replace = false;
    m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace);
}
```

呼出しポイント:
- L923: `addRoute()` 後（excp_intfs_flag の場合）
- L1050,1090: 重複エントリ受信時
- L2729: `addRoute()` 成功時
- L2970: `removeRoute()` 成功時

### 3. STATE_DB:ROUTE_TABLE (orchagent が書き手、デフォルト経路のみ)

```cpp
// routeorch.cpp:287-295
void RouteOrch::updateDefRouteState(string ip, bool add)
{
    vector<FieldValueTuple> tuples;
    string state = add ? "ok" : "na";
    FieldValueTuple tuple("state", state);
    tuples.push_back(tuple);
    m_stateDefaultRouteTb->set(ip, tuples);
}
```

`STATE_ROUTE_TABLE_NAME = "ROUTE_TABLE"` (sonic-swss-common/common/schema.h:494)

呼出しポイント:
- コンストラクタ L130: `updateDefRouteState("0.0.0.0/0")` — 初期化 (state=na)
- コンストラクタ L156: `updateDefRouteState("::/0")` — 初期化 (state=na)
- L2703: `addRoute()` 内でデフォルト経路追加時 (state=ok)
- L2856: `removeRoute()` 内でデフォルト経路削除時 (state=na)

### 4. FPM (zebra へのオフロード確認応答)

```cpp
// routesync.cpp:3100-3131
bool RouteSync::sendOffloadReply(struct nlmsghdr* hdr)
{
    if (hdr->nlmsg_type != RTM_NEWROUTE)
        return false;
    hdr->nlmsg_flags |= NLM_F_REQUEST;
    rtmsg *rtm = static_cast<rtmsg*>(NLMSG_DATA(hdr));
    rtm->rtm_flags |= RTM_F_OFFLOAD;
    if (!m_fpmInterface)
    {
        SWSS_LOG_ERROR("Cannot send offload reply to zebra: FPM is disconnected");
        return false;
    }
    if (!m_fpmInterface->send(hdr))
    {
        SWSS_LOG_ERROR("Failed to send reply to zebra");
        return false;
    }
    return true;
}
```

route suppression 無効時は `onRouteResponse()` が即 return し、オフロード応答は送出されない:
```cpp
// routesync.cpp:3174-3177
if (!isSuppressionEnabled())
{
    return;
}
```

warm-restart 終了時の一括応答:
```cpp
// routesync.cpp:3291-3295
void RouteSync::markRoutesOffloaded(swss::DBConnector& db)
{
    sendOffloadReply(db, APP_ROUTE_TABLE_NAME);
}
```

## 結論

`route-handler` ページ（fpmsyncd の RouteSync handler 分岐）の副作用は 4 種類:
1. **APPL_DB:ROUTE_TABLE** — 直接書き込み（warm-restart 中は遅延）
2. **APPL_STATE_DB:ROUTE_TABLE** — orchagent が ResponsePublisher 経由で書き込み
3. **STATE_DB:ROUTE_TABLE** — orchagent がデフォルト経路 (`0.0.0.0/0`, `::/0`) のみ書き込み
4. **FPM (RTM_F_OFFLOAD)** — route suppression 有効時のみ zebra へオフロード確認応答
