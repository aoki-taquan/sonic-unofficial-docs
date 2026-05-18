# telemetry-client — Phase F 副次 DB 書込スキャンノート

## 調査対象

- `sonic-net/sonic-gnmi` `dialout/dialout_client/dialout_client.go` @ eb635b7679b260c3fd0786a6d0734fc8e82c9a22

## 調査手順

1. `dialout_client.go` 全行を通読し、CONFIG_DB 以外の Redis DB への書込を探索
2. `SetEntry` / `set(` / `publish` / `STATE_DB` / `APPL_DB` / `BMP_STATE` / `COUNTERS_DB` をキーワード検索
3. go-redis `client.Set` / `client.HSet` / `client.Del` の呼び出しを探索

## 結果

**副次 DB 書込なし。**

`dialout_client.go` は CONFIG_DB への書込を行わない（読み取り専用）。
他の Redis DB (`STATE_DB`, `APPL_DB`, `COUNTERS_DB`, `BMP_STATE_DB` 等) への書込も検出されなかった。

同プロセスの動作:
- CONFIG_DB の `TELEMETRY_CLIENT|*` キースペース通知を受信 (PSubscribe)
- gRPC dial-out でリモートコレクタへデータを Push（Redis 外のネットワーク I/O）
- Redis への Write 操作は一切なし

## 根拠コード断片

```go
// DialOutRun() — CONFIG_DB keyspace を PSubscribe するが書き込みはしない
pubsub := redisDb.PSubscribe(context.Background(), pattern)
// ...
dbkeys, err = redisDb.Keys(context.Background(), dbkey_prefix+"*").Result()
// ...
fv, err := redisDb.HGetAll(context.Background(), tableKey).Result()
```

すべて読み取り系メソッド (`PSubscribe`, `Keys`, `HGetAll`) のみ。`Set`, `HSet`, `Del` の呼び出しは存在しない。

## 結論

`<!-- side-effects -->` ブロックの内容: 副次 DB 書込なし。
dial-out クライアントの "副作用" はネットワーク (gRPC ストリーム to コレクタ) であり Redis DB 上には現れない。
