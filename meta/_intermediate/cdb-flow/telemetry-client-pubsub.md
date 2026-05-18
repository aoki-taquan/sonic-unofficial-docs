# TELEMETRY_CLIENT — Phase G 通信メカニズムスキャンノート

対象テーブル: `TELEMETRY_CLIENT`
Consumer: `sonic-gnmi` (`dialout/dialout_client/dialout_client.go`) の `DialOutRun()`
スキャン範囲: `DialOutRun()` 全行（L670-755）、`processTelemetryClientConfig()` L464-640
スキャン日: 2026-05-18

---

## 購読 API 方式

`DialOutRun()` は `swsscommon.ConfigDBConnector` を使用せず、`go-redis` クライアントの `PSubscribe` を直接呼び出す。

```go
// dialout_client.go:L686-690
pattern := "__keyspace@" + strconv.Itoa(int(dbn)) + "__:TELEMETRY_CLIENT" + separator
prefixLen := len(pattern)
pattern += "*"

pubsub := redisDb.PSubscribe(context.Background(), pattern)
```

- `separator` は CONFIG_DB の table key separator（通常 `|`）を `sdc.GetTableKeySeparator()` で取得。
- `PSubscribe` でワイルドカード pattern `__keyspace@4__:TELEMETRY_CLIENT|*` を購読。
- CONFIG_DB 番号は `sdc.GetDbNum("CONFIG_DB")` で動的に取得（通常 DB4）。

## 起動時スナップショット読み込み

`PSubscribe` 確立後、`redisDb.Keys()` で `TELEMETRY_CLIENT|*` に一致する全キーを取得して一括処理する。

```go
// dialout_client.go:L705-715
dbkeys, err = redisDb.Keys(context.Background(), dbkey_prefix+"*").Result()
for _, dbkey := range dbkeys {
    dbkey = dbkey[len(dbkey_prefix):]
    processTelemetryClientConfig(ctx, redisDb, dbkey, "hset")
}
```

pubsub 購読確立と `Keys()` 呼び出しの間に短い time window が存在するが、実装上の競合対策はない。`PSubscribe` を先に確立してから `Keys` を呼ぶため、その window で届いた通知はイベントループで処理される。

## イベントループ受信

```go
// dialout_client.go:L718-743
msgi, err := pubsub.ReceiveTimeout(context.Background(), time.Millisecond*1000)
// ...
subscr := msgi.(*redis.Message)
dbkey := subscr.Channel[prefixLen:]
if subscr.Payload == "del" || subscr.Payload == "hdel" {
    processTelemetryClientConfig(ctx, redisDb, dbkey, "hdel")
} else if subscr.Payload == "hset" {
    processTelemetryClientConfig(ctx, redisDb, dbkey, "hset")
}
```

- `ReceiveTimeout` は 1000 ms（1 秒）タイムアウト。タイムアウトは `net.Error.Timeout()` で判定して `continue`。
- payload が `"del"` または `"hdel"` → DEL 操作として処理。
- payload が `"hset"` → SET 操作として処理（`HGETALL` で最新値を再取得）。
- 上記以外の payload（`"expire"` 等）は `log.V(2)` ログのみでスキップ。

## 書き込み側（Producer）

CONFIG_DB への書き込みは `sonic-db-cli`、`init_cfg.json` ロード、`minigraph.py` 生成等が行う通常の `HSET`。明示的な `PUBLISH` は行わない。Redis の keyspace notification 機能が `HSET` / `DEL` を自動的に `__keyspace@4__:TELEMETRY_CLIENT|*` チャネルへ通知する。

## ConsumerStateTable / NotificationProducer 非使用

`TELEMETRY_CLIENT` テーブルは `ConsumerStateTable`（channel ベース）および `NotificationProducer` を使用しない。`swsscommon` の `Table`、`ConfigDBConnector` も使用せず、`go-redis` による keyspace notification を直接消費する設計。

## keyspace 通知パターンまとめ

| Redis 通知 channel | payload | 処理 |
|-------------------|---------|------|
| `__keyspace@4__:TELEMETRY_CLIENT\|Global` | `hset` | `processTelemetryClientConfig("Global", "hset")` → 全 DestinationGroup gRPC 再起動 |
| `__keyspace@4__:TELEMETRY_CLIENT\|Global` | `del` / `hdel` | `"Invalid delete operation"` を返してスキップ |
| `__keyspace@4__:TELEMETRY_CLIENT\|DestinationGroup_<n>` | `hset` | `dst_addr` を更新し gRPC セッション再確立 |
| `__keyspace@4__:TELEMETRY_CLIENT\|DestinationGroup_<n>` | `del` | DestinationGroup を削除（参照中なら拒否） |
| `__keyspace@4__:TELEMETRY_CLIENT\|Subscription_<n>` | `hset` | Subscription を更新し gRPC send goroutine 再起動 |
| `__keyspace@4__:TELEMETRY_CLIENT\|Subscription_<n>` | `del` | Subscription を削除し gRPC goroutine 停止 |
