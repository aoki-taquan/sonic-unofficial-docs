# gnmi-counter — Phase G pubsub 調査メモ

## 調査対象

`sonic-gnmi` の gNMI カウンタ周辺で Redis pub/sub (keyspace notification) が使われる箇所を特定する。

## 1. dialout_client — TELEMETRY_CLIENT keyspace 購読

**ファイル**: `dialout/dialout_client/dialout_client.go:686-740`

```go
pattern := "__keyspace@" + strconv.Itoa(int(dbn)) + "__:TELEMETRY_CLIENT" + separator
prefixLen := len(pattern)
pattern += "*"

pubsub := redisDb.PSubscribe(context.Background(), pattern)
defer pubsub.Close()
// ...
for {
    msgi, err := pubsub.ReceiveTimeout(context.Background(), time.Millisecond*1000)
    // ...
    if subscr.Payload == "del" || subscr.Payload == "hdel" {
        processTelemetryClientConfig(ctx, redisDb, dbkey, "hdel")
    } else if subscr.Payload == "hset" {
        processTelemetryClientConfig(ctx, redisDb, dbkey, "hset")
    }
}
```

`dialout_client` は CONFIG_DB の `TELEMETRY_CLIENT|*` キーに対して Redis keyspace notification を `PSubscribe` する。`hset` / `hdel` / `del` を受信するたびに `processTelemetryClientConfig` でサブスクリプション設定を動的に更新する。これにより、`telemetryd` の再起動なしに dial-out 宛先の追加・変更・削除がリアルタイムに反映される。

- DB: CONFIG_DB (DB 4)
- パターン: `__keyspace@4__:TELEMETRY_CLIENT|*`
- 受信イベント: `hset`、`hdel`、`del`
- タイムアウト: 1000 ms (timeout は再試行のみ、エラーとして扱わない)

## 2. DbJournal — keyspace/keyevent 全 DB 購読

**ファイル**: `gnmi_server/db_journal.go:67-70`

```go
keyspace := fmt.Sprintf("__keyspace@%d__:*", dbNum)
keyevent := fmt.Sprintf("__keyevent@%d__:*", dbNum)
journal.ps = journal.rc.PSubscribe(context.Background(), keyspace, keyevent)
```

`DbJournal` は CONFIG_DB または STATE_DB の全キーを対象にした keyspace + keyevent 通知を `PSubscribe` する。これは gNMI の journal 機能（DB 変更のファイル記録）で使われており、直接カウンタの増分とは関係しないが、`gnmi_server` の内部メカニズムとして記録する。

- DB: CONFIG_DB (DB 4) または STATE_DB (DB 6)（設定次第）
- パターン: `__keyspace@N__:*` + `__keyevent@N__:*`
- チャネル方式: `ps.Channel()` で goroutine が受信
- 用途: DB 変更のジャーナルファイル書き込み

## 3. gRPC Subscribe — gNMI データソース側の keyspace 購読

`sonic_data_client` の `db_client.go` は gNMI Subscribe RPC のデータストリームとして CONFIG_DB / STATE_DB / COUNTERS_DB 等に keyspace notification を設定する。これは gNMI カウンタ（共有メモリ）の増分とは独立している。

## 4. カウンタ共有メモリと pub/sub の非接続性

`IncCounter` / `InitCounters` (`common_utils/context.go`) は Redis に一切アクセスしない。カウンタはプロセス内の `globalCounters [COUNTER_SIZE]uint64` 配列と SysV 共有メモリのみで完結する。つまり **カウンタ増分が Redis pub/sub をトリガーすることはない**。

## まとめ

| 方向 | 購読元 | DB | パターン | 用途 |
|------|--------|-----|---------|------|
| dialout が受信 | CONFIG_DB | 4 | `__keyspace@4__:TELEMETRY_CLIENT|*` | dial-out 設定変更をリアルタイム反映 |
| DbJournal が受信 | CONFIG_DB or STATE_DB | 4 or 6 | `__keyspace@N__:*` + `__keyevent@N__:*` | DB 変更のジャーナルファイル記録 |
| カウンタ自体 | — | — | なし | SysV 共有メモリのみ。Redis 通知なし |
