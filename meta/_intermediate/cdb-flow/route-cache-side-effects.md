# route-cache-side-effects.md — Phase F: APPL_STATE_DB ROUTE_TABLE 副作用スキャン

調査日: 2026-05-19
対象テーブル: APPL_STATE_DB `ROUTE_TABLE`（route offload cache）
Writer: `orchagent RouteOrch::publishRouteState()` → `ResponsePublisher::publish()`
Consumer: `fpmsyncd RouteSync::onRouteResponse()`、`route_check.py`
スキャン範囲: routeorch.cpp L57-58, L3185-3201; response_publisher.cpp L96-220; fpmsyncd.cpp L78-302; routesync.cpp L3100-3310; sonic-utilities/scripts/route_check.py L755-778

---

## 1. fpmsyncd → FRR zebra（RTM_NEWROUTE + RTM_F_OFFLOAD）

APPL_STATE_DB `ROUTE_TABLE` への書き込み（ResponsePublisher 経由の RESPONSE_CHANNEL 通知）を受信した `fpmsyncd` の `onRouteResponse()` が FRR zebra へ **RTM_NEWROUTE with RTM_F_OFFLOAD** を送出する。

```cpp
// routesync.cpp:3174-3177
void RouteSync::onRouteResponse(const std::string &opName,
                                 const std::vector<FieldValueTuple>& fieldValues)
{
    if (!isSuppressionEnabled())
        return;
    ...
}
```

- **条件**: `suppress-fib-pending = enabled` が CONFIG_DB に設定されていること（`fpmsyncd.cpp:113-118`）
- **送信先**: FRR zebra（FPM ソケット経由）
- **内容**: SAI プログラミング成功経路に対して `sendOffloadReply()` が `RTM_NEWROUTE` + `RTM_F_OFFLOAD` フラグを送出
- **効果**: zebra 側で経路の offload フラグが立ち、FRR が当該経路を「HW にプログラム済み」として扱う

evidence: `routesync.cpp:3100-3131` (`sendOffloadReply`), `routesync.cpp:3174-3177`, `fpmsyncd.cpp:113-118`

---

## 2. Warm Restart: markRoutesOffloaded() の一括読み出し → FRR offload 通知

Warm restart 完了時 (`onWarmStartEnd()`)、`fpmsyncd` が `markRoutesOffloaded()` を実行して APPL_STATE_DB `ROUTE_TABLE` の**全エントリ**を読み出し、一括で FRR zebra に RTM_NEWROUTE offload 通知を送出する。

```cpp
// routesync.cpp:3291-3295
void RouteSync::onWarmStartEnd(swss::DBConnector& applStateDb)
{
    if (isSuppressionEnabled())
        markRoutesOffloaded(applStateDb);
    ...
}
```

```cpp
// routesync.cpp:3285
fieldValues.emplace_back("err_str", "SWSS_RC_SUCCESS");
```

- **読み出し元**: APPL_STATE_DB `ROUTE_TABLE`（全キー `ROUTE_TABLE:*`）
- **出力**: FRR zebra への RTM_NEWROUTE（FPM ソケット）
- **条件**: `isSuppressionEnabled()` が true の場合のみ
- **タイミング**: orchagent の warm restart 完了後に自動実行（一度のみ）
- **効果**: orchagent 再起動後も FRR が保持している経路の offload フラグが復元される

evidence: `routesync.cpp:3291-3310`

---

## 3. route_check.py → RESPONSE_CHANNEL 注入（recovery パス）

`route_check.py` は APPL_STATE_DB `ROUTE_TABLE` を読み出して FRR・ASIC_DB との整合を確認し、FRR に存在するが offload フラグが立っていない経路を検出した場合に `mitigate_installed_not_offloaded_frr_routes()` を実行する。

```python
# sonic-utilities/scripts/route_check.py:767-771
def mitigate_installed_not_offloaded_frr_routes(routes):
    producer = swss.NotificationProducer(db, APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL)
    for prefix in routes:
        fvs = swss.FieldValuePairs([("err_str", "SWSS_RC_SUCCESS"),
                                     ("protocol", "")])
        producer.send(SET_COMMAND, prefix, fvs)
```

- **読み出し元**: APPL_STATE_DB `ROUTE_TABLE`
- **書き込み先**: `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL`（Redis Pub/Sub）
- **効果**: fpmsyncd が `onRouteResponse()` を再実行し、FRR zebra への offload 通知を再送する
- **条件**: `route_check.py` の定期実行または手動実行時のみ（自動定期 cron: 毎分）
- **注意**: APPL_STATE_DB エントリを直接書き換えるのではなく、RESPONSE_CHANNEL に再注入してフロー全体を再起動する recovery 手法

evidence: `scripts/route_check.py:767-771`

---

## 副作用サマリ

| 副作用先 | トリガ | 書き手 | 条件 |
|---------|-------|--------|------|
| FPM (RTM_NEWROUTE + RTM_F_OFFLOAD) → FRR zebra | RESPONSE_CHANNEL 受信 | fpmsyncd RouteSync::sendOffloadReply() | suppress-fib-pending=enabled 時のみ |
| FPM (RTM_NEWROUTE + RTM_F_OFFLOAD) → FRR zebra（一括） | Warm Restart 完了 | fpmsyncd RouteSync::markRoutesOffloaded() | suppress-fib-pending=enabled + warm restart 時 |
| `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` | route_check.py 実行 | route_check.py NotificationProducer | FRR offload フラグ未設定経路が検出された場合 |
