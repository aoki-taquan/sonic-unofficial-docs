# subscription-config — Phase G: Redis 通知メカニズム

## 調査対象

- `sonic-net/sonic-gnmi` `dialout/dialout_client/dialout_client.go` (ref: eb635b7679b260c3fd0786a6d0734fc8e82c9a22)
- 関数: `DialOutRun()` (L647–L745)、`processTelemetryClientConfig()` (L464–L643)

## CONFIG_DB 購読メカニズム

`DialOutRun()` は起動時に直接 Redis クライアント (`redisDb`) を生成し、Redis keyspace notification を **PSUBSCRIBE** で購読する。
swss-common の `SubscriberStateTable` / `ConsumerStateTable` ではなく、Go の `go-redis` クライアントが直接 PSUBSCRIBE する独自実装である。

### PSUBSCRIBE パターン

```
__keyspace@<CONFIG_DB_ID>__:TELEMETRY_CLIENT|*
```

- `CONFIG_DB_ID` は `sdcfg.GetDbId("CONFIG_DB", ns)` で実行時に解決 (通常 4)
- セパレータは `sdc.GetTableKeySeparator("CONFIG_DB", ns)` で解決 (通常 `|`)
- ワイルドカード `*` で `TELEMETRY_CLIENT|Global`、`TELEMETRY_CLIENT|DestinationGroup_<name>`、`TELEMETRY_CLIENT|Subscription_<name>` の全エントリを一括購読

実装箇所: `dialout_client.go:682-690`

```go
pattern := "__keyspace@" + strconv.Itoa(int(dbn)) + "__:TELEMETRY_CLIENT" + separator
prefixLen := len(pattern)
pattern += "*"
pubsub := redisDb.PSubscribe(context.Background(), pattern)
```

### 初回ブルスキャン + イベント駆動の 2 フェーズ

1. **ブルスキャン** (L707-L715): `redisDb.Keys(ctx, "TELEMETRY_CLIENT|*")` で既存エントリを全取得し、各キーに対して `processTelemetryClientConfig(..., "hset")` を呼ぶ
2. **イベントループ** (L718-L745): 1000 ms タイムアウトの `pubsub.ReceiveTimeout()` で常時ポーリング。受信ペイロードに応じて処理:
   - `"hset"` → `processTelemetryClientConfig(..., "hset")`（新規 or 更新）
   - `"del"` or `"hdel"` → `processTelemetryClientConfig(..., "hdel")`（削除）
   - その他 → スキップ (`log.V(2)` のみ)

タイムアウトは `net.Error.Timeout()` で判定し、タイムアウト時は `continue`（エラー扱いしない）。

### イベントループの poll 間隔

明示的な sleep は存在しない。`ReceiveTimeout(ctx, 1000ms)` が poll 間隔を兼ねる。
Redis サーバーからのプッシュがあれば即時処理される（最大 1 秒の遅延）。

## 通知受信後の処理

`processTelemetryClientConfig()` は受信したキーのサフィックス (`key`) をもとに 3 種類の処理に分岐する:

| キープレフィックス | 処理内容 |
|------------------|---------|
| `Global` | `clientCfg` (グローバル設定) を更新し、全既存 gRPC 接続を `closeDestGroupClient()` + `setupDestGroupClients()` で再接続 |
| `DestinationGroup_<name>` | `destGrpNameMap` にデスティネーション情報を登録し、`setupDestGroupClients()` で gRPC 接続を確立 |
| `Subscription_<name>` | `ClientSubscriptionNameMap` に `clientSubscription` 構造体を登録し、`cs.NewInstance(ctx)` でデータ送信ゴルーチンを起動 |

`Global` の `hdel` は不正操作として `fmt.Errorf` を返す（削除不可）。

## 購読元・対象テーブルまとめ

| DB | DB ID | テーブル | PSUBSCRIBE パターン | 実装箇所 |
|----|-------|---------|-------------------|---------|
| CONFIG_DB | 動的取得 | `TELEMETRY_CLIENT\|*` | `__keyspace@<ID>__:TELEMETRY_CLIENT\|*` | `dialout_client.go:686-690` |

他の DB (APPL_DB / STATE_DB / COUNTERS_DB) への通知購読は存在しない。
