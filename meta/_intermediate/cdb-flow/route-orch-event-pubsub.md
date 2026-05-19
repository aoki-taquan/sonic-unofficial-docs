# route-orch-event — Phase G Redis 通知メカニズム スキャンノート

## 対象ソース

- `orchagent/routeorch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/response_publisher.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `fpmsyncd/fpmsyncd.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `fpmsyncd/routesync.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/mirrororch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/natorch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `orchagent/orchdaemon.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 1. APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL (ResponsePublisher)

### チャネル名の生成

```cpp
// fpmsyncd.cpp L78
const auto routeResponseChannelName =
    std::string("APPL_DB_") + APP_ROUTE_TABLE_NAME + "_RESPONSE_CHANNEL";
// → "APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL"
```

### 送信側 (orchagent)

`ResponsePublisher::publish()` は `swss::NotificationProducer::send()` を呼び出し、
Redis `PUBLISH` コマンドでチャネルへ送信する (`response_publisher.cpp` L93–148)。

`setBuffered(true)` 設定により、送信は `flush()` まで Redis パイプラインにバッファされる:

```cpp
// routeorch.cpp コンストラクタ
m_publisher.setBuffered(true);

// routeorch.cpp doTask() 末尾
m_publisher.flush();  // L1231
```

### 受信側 (fpmsyncd)

`fpmsyncd` は起動時に `suppress-fib-pending` フラグを確認して購読を決定する:

```cpp
// fpmsyncd.cpp L78–120
deviceMetadataTable.hget("localhost", "suppress-fib-pending", suppressionEnabledStr);
if (suppressionEnabledStr == "enabled")
{
    routeResponseChannel = std::make_unique<NotificationConsumer>(
        &applStateDb, routeResponseChannelName);
    sync.setSuppressionEnabled(true);
}
```

`suppress-fib-pending != "enabled"` の場合、`routeResponseChannel` は `nullptr` のまま。
主ループでは `nullptr` チェックをして `select()` に登録しないため購読しない。

### メッセージ形式

`routesync.cpp` L3156–3190 の `RedisFpmSyncd::onRouteResponse()` が受信を処理:

```
(op_code, prefix_key, [(err_str, <value>), (protocol, <value>)])
```

---

## 2. NextHopObserver — プロセス内コールバック

Redis を使わない orchagent 内部の通知機構。

### attach/detach API (routeorch.cpp L308–350, L352–390)

```cpp
void RouteOrch::attach(Observer *observer, const IpAddress& dstAddr,
                       sai_object_id_t vrf_id = gVirtualRouterId);
void RouteOrch::detach(Observer *observer, const IpAddress& dstAddr,
                       sai_object_id_t vrf_id = gVirtualRouterId);
```

`attach()` 呼び出し時に最長プレフィックスマッチが存在すれば即時通知:

```cpp
auto route = observerEntry->second.routeTable.rbegin();
if (route != observerEntry->second.routeTable.rend())
{
    NextHopUpdate update = { vrf_id, dstAddr, route->first, route->second.nhg_key };
    observer->update(SUBJECT_TYPE_NEXTHOP_CHANGE, static_cast<void *>(&update));
}
```

### Observer 一覧

| Observer | attach() 箇所 | 対象 IP |
|---------|--------------|---------|
| `MirrorOrch` | `mirrororch.cpp` L517 | ミラーセッションの `dst_ip` |
| `NatOrch` | `natorch.cpp` L414 (SNAT), L458 (DNAT), L504, L591 (TWICE) | NAT 変換先 IP |
| `NeighOrch` | ネイバー解決処理内 | ネイバー IP |
| `TunnelDecapOrch` | トンネル設定時 | トンネルエンドポイント IP |

---

## 3. orchagent select ループ

`orchdaemon.cpp` L23:
```cpp
const int SELECT_TIMEOUT = 1000;  // ms
```

主ループ: `orchDaemon->doTask()` → `m_orchList` 全走査 → ResponsePublisher `flush()`

各バッチサイクルの終わりに RESPONSE_CHANNEL へ通知がまとめて送出される。
個別ルートごとの flush はない（`setBuffered(true)` の効果）。
