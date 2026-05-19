# route-cache-pubsub.md — Phase G: APPL_STATE_DB ROUTE_TABLE Redis 通知メカニズム

調査日: 2026-05-19
対象テーブル: APPL_STATE_DB `ROUTE_TABLE`（route offload cache）
Writer: `orchagent RouteOrch::publishRouteState()` → `ResponsePublisher` → `NotificationProducer`
Consumer: `fpmsyncd` → `NotificationConsumer` → `RouteSync::onRouteResponse()`
スキャン範囲: response_publisher.cpp L96-133; routeorch.cpp L57-58, L1231; fpmsyncd.cpp L78-365; routesync.cpp L3160-3310

---

## 通知チャネル名

`APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL`

- orchagent 側: `ResponsePublisher::publish()` が `response_channel = "APPL_DB_" + table + "_RESPONSE_CHANNEL"` を構築 (response_publisher.cpp:104)
- fpmsyncd 側: `const auto routeResponseChannelName = std::string("APPL_DB_") + APP_ROUTE_TABLE_NAME + "_RESPONSE_CHANNEL"` (fpmsyncd.cpp:78)

## 書き込み側: ResponsePublisher の送信フロー

1. `publishRouteState()` → `m_publisher.publish(APP_ROUTE_TABLE_NAME, ctx.key, fvs, status, replace)` (routeorch.cpp:3201)
2. `ResponsePublisher::publish()` が `NotificationProducer` を生成し `notificationProducer.send(status.codeStr(), key, intent_attrs_copy)` を呼び出す (response_publisher.cpp:118-120)
3. `m_publisher` はバッファリングモード: `setBuffered(true)` (routeorch.cpp:57)
4. `m_publisher.flush()` で 1 doTask() サイクル末にまとめて送出 (routeorch.cpp:1231)

メッセージ内容:
- opcode: `status.codeStr()` ("SWSS_RC_SUCCESS" または SAI エラーコード)
- key: 経路プレフィクス (例: "10.0.0.0/24")
- fields: `err_str` + `protocol` (SET 時)、`err_str` のみ (DEL 時)

## 購読側: fpmsyncd の NotificationConsumer

起動時の条件付き有効化 (fpmsyncd.cpp:112-118):
```cpp
deviceMetadataTable.hget("localhost", "suppress-fib-pending", suppressionEnabledStr);
if (suppressionEnabledStr == "enabled")
{
    routeResponseChannel = std::make_unique<NotificationConsumer>(&applStateDb, routeResponseChannelName);
    sync.setSuppressionEnabled(true);
}
```

動的切替 (fpmsyncd.cpp:283-303):
- disabled→enabled: 新規 NotificationConsumer 生成 + s.addSelectable()
- enabled→disabled: markRoutesOffloaded() 後に remove + reset

## イベントループ

fpmsyncd.cpp:186-323:
```cpp
gSelectTimeout = INFINITE;  // デフォルト: ブロッキング
while (true) {
    s.select(&temps, gSelectTimeout);
    if (routeResponseChannel && temps == routeResponseChannel.get()) {
        routeResponseChannel->pops(notifications);
        for (const auto& n: notifications)
            sync.onRouteResponse(kfvKey(n), kfvFieldsValues(n));
    }
}
```

## パイプラインフラッシュ戦略

APPL_DB 書き込みパイプライン (fpmsyncd.cpp:335-365):
- サイズ上限: `ROUTE_SYNC_PPL_SIZE = 50000` (fpmsyncd.h:6)
- フラッシュ閾値: `SMALL_TRAFFIC = 500` エントリ未満 OR `FLUSH_TIMEOUT = 500 ms` 経過
- `onRouteResponse()` 自体は APPL_DB に書き込まないためこのパイプラインには無関係

## orchagent の ConsumerStateTable 待機タイムアウト

orchagent の APPL_DB consumer は `SELECT_TIMEOUT = 1000 ms` で `orchdaemon.cpp:959` の select() を実行する。これは ROUTE_TABLE の書き込み側タイムアウトであり、APPL_STATE_DB の読み出し側（fpmsyncd の NotificationConsumer）とは独立している。

## まとめ

| レイヤ | 方式 | バッファ/タイムアウト |
|--------|------|---------------------|
| RouteOrch → Redis | NotificationProducer (buffered) | flush() で doTask() 末にまとめて送出 |
| Redis → fpmsyncd | NotificationConsumer (SUBSCRIBE) | select(INFINITE) で即時ブロック解除 |
| fpmsyncd → FRR | netlink RTM_NEWROUTE | onRouteResponse() 内で同期送信 |
| fpmsyncd APPL_DB | RedisPipeline (50000) | 500ms / 500エントリ閾値でフラッシュ |
