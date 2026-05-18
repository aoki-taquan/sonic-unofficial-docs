# route-state pubsub 調査メモ (Phase G)

## 調査対象

- `orchagent/response_publisher.cpp` (sonic-net/sonic-swss)
- `orchagent/routeorch.cpp` (sonic-net/sonic-swss)
- `fpmsyncd/fpmsyncd.cpp` (sonic-net/sonic-swss)
- `fpmsyncd/routesync.cpp` (sonic-net/sonic-swss)

---

## APPL_STATE_DB ROUTE_TABLE — ResponsePublisher の通知チャンネル

`publishRouteState()` → `ResponsePublisher::publish()` の内部で、APPL_STATE_DB への書き込みと同時に以下のチャンネルへ通知が送出される:

```
チャンネル名: APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL
```

実装 (`response_publisher.cpp:104, 118-120`):
```cpp
std::string response_channel = "APPL_DB_" + table + "_RESPONSE_CHANNEL";
// ...
swss::NotificationProducer notificationProducer{
    m_ntf_pipe.get(), response_channel, m_buffered};
notificationProducer.send(status.codeStr(), key, intent_attrs_copy);
```

- 通知ペイロード: `{err_str, protocol}` (SET 操作時) または `{err_str}` のみ (DEL 操作時)
- DB: APPL_STATE_DB (Redis DB index 14 デフォルト)
- バッファリング: `routeorch.cpp:57` で `m_publisher.setBuffered(true)` が設定されており、`doTask()` 末尾の `m_publisher.flush()` (`routeorch.cpp:1231`) で一括送出

## STATE_DB ROUTE_TABLE — Table::set() で直接書き込み

STATE_DB の `ROUTE_TABLE` は `ResponsePublisher` を使わず `swss::Table::set()` で直接書き込む (`routeorch.cpp:294`)。  
keyspace notification が有効な環境では `__keyspace@6__:ROUTE_TABLE|<ip>` が PUBLISH されるが、これは Redis の keyspace 通知機能であり、アプリケーションレベルの明示的な subscribe はない。

`sonic-linkmgrd` が `SubscriberStateTable` でこのチャンネルを購読する (Phase C で記述済み)。

## fpmsyncd — RESPONSE_CHANNEL の購読

```cpp
// fpmsyncd.cpp:78
const auto routeResponseChannelName = std::string("APPL_DB_") + APP_ROUTE_TABLE_NAME + "_RESPONSE_CHANNEL";
// fpmsyncd.cpp:116 (suppress-fib-pending=enabled 時のみ)
routeResponseChannel = std::make_unique<NotificationConsumer>(&applStateDb, routeResponseChannelName);
```

- `NotificationConsumer` を使用し、主ループ `s.select()` で受信待機
- 受信後 `routeResponseChannel->pops(notifications)` で dequeue
- 各エントリに対し `sync.onRouteResponse(key, fieldValues)` を呼び出す

## onRouteResponse() の処理フロー

`fpmsyncd/routesync.cpp:3165-3261`:

1. `err_str == "SWSS_RC_SUCCESS"` かつ `protocol` フィールドが存在する (SET 操作) の場合のみ処理
2. DEL 操作 (`protocol` フィールドなし) は無視
3. SAI 失敗 (`err_str != "SWSS_RC_SUCCESS"`) は無視（suppress 状態を継続）
4. `protocol` が空文字列の場合も無視（FRR 外経由の経路）
5. 上記条件クリア時: `sendOffloadReply()` → FRR zebra へ `RTM_F_OFFLOAD` フラグ付き netlink メッセージを送信

## suppress-fib-pending の動的切り替え

`CONFIG_DB DEVICE_METADATA|localhost suppress-fib-pending` が実行時に変更された場合:
- `enabled` に変更 → `routeResponseChannel` を生成し `s.addSelectable()` で登録
- 無効化 → 既存 suppress 経路をすべて offloaded にマークしてから `routeResponseChannel.reset()` で破棄  
(`fpmsyncd.cpp:285-302`)

## ResponsePublisher のバッファリング詳細

`routeorch.cpp:57`: `m_publisher.setBuffered(true)` — 通知を即時送出せずパイプラインに貯める  
`routeorch.cpp:1231`: `m_publisher.flush()` — doTask() の最後に一括フラッシュ

コメント (`routeorch.cpp:1228`):
> Without this, notifications stay buffered in the Redis pipeline until the next OrchDaemon periodic flush (up to 1s), delaying the offload reply to fpmsyncd.

## 購読方式まとめ

| チャンネル / テーブル | 購読方式 | 購読主体 | DB |
|---------------------|---------|---------|-----|
| `APPL_DB_ROUTE_TABLE_RESPONSE_CHANNEL` | `NotificationConsumer` | `fpmsyncd` | APPL_STATE_DB |
| `STATE_DB ROUTE_TABLE` (keyspace) | `SubscriberStateTable` | `sonic-linkmgrd` | STATE_DB |
