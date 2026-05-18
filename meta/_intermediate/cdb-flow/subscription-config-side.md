# subscription-config — Phase F: 副次 DB 書込スキャン中間ファイル

生成日: 2026-05-18

## 調査対象

`docs/reference/config-db/subscription-config.md` 対象テーブル
`TELEMETRY_CLIENT|Global` / `TELEMETRY_CLIENT|DestinationGroup_<name>` / `TELEMETRY_CLIENT|Subscription_<name>`
変更時に `dialout_client.go` (`sonic-gnmi/dialout/dialout_client/dialout_client.go`) が
APPL_DB / STATE_DB / COUNTERS_DB / その他副次 DB へ何らかの書き込みを行うかを調査する。

## 走査範囲

- `sonic-gnmi/dialout/dialout_client/dialout_client.go` 全行
- `sonic-gnmi/` 全体 (`TELEMETRY_CLIENT` / `STATE_DB` / `APPL_DB` / `COUNTERS_DB` の grep)
- `sonic-gnmi/sonic_data_client/` (DB クライアント層)

## 走査コマンドと結果

### 1. dialout_client.go で DB 書込操作を検索

```bash
grep -n -E "\.Set\(|\.HSet\(|\.Publish\(|STATE_DB|APPL_DB|COUNTERS_DB|Producer|Notification" \
  sonic-gnmi/dialout/dialout_client/dialout_client.go
```

結果:
- `line 320`: `c.client.Publish(ctx)` — これは外部 gRPC コレクタへの `Publish` RPC であり、Redis Publish ではない
- `STATE_DB` / `APPL_DB` / `COUNTERS_DB` / `HSet` / `Producer` / `Notification` — **マッチ 0 件**

### 2. redisDb に対する操作を全列挙

```bash
grep -n "redisDb\." sonic-gnmi/dialout/dialout_client/dialout_client.go
```

結果（3 件のみ、すべて読み取り操作）:
- `L471`: `redisDb.HGetAll(...)` — CONFIG_DB から TELEMETRY_CLIENT エントリを読み取る（読み取り専用）
- `L690`: `redisDb.PSubscribe(...)` — CONFIG_DB キースペース通知を購読（読み取り専用）
- `L707`: `redisDb.Keys(...)` — CONFIG_DB 内の TELEMETRY_CLIENT キーを列挙（読み取り専用）

**書き込み操作は 0 件。** `dialout_client.go` は CONFIG_DB を読み取るのみで、いかなる DB にも書き込まない。

### 3. sonic-gnmi 全体で STATE_DB / APPL_DB への書き込みが TELEMETRY_CLIENT に連動するか

```bash
grep -rn "TELEMETRY_CLIENT" sonic-gnmi/ --include="*.go" | grep -v "_test.go"
```

結果: `dialout_client.go` および `dialout_client_cli.go` のみにヒット。
`gnmi_server/` や `sonic_data_client/` には TELEMETRY_CLIENT 処理なし。

## 結論

`TELEMETRY_CLIENT` テーブルの変更に伴い、`dialout_client.go` は副次 DB への書き込みを一切行わない。

| 副次 DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | `redisDb.HGetAll` / `PSubscribe` / `Keys` 以外の Redis 操作なし |
| STATE_DB | なし | `dialout_client.go` に `STATE_DB` 参照・接続なし |
| COUNTERS_DB | なし | `dialout_client.go` に `COUNTERS_DB` 参照・接続なし |
| ASIC_DB / FLEX_COUNTER_DB | なし | dialout は SAI 非経由、ORchagent とは無関係 |

副作用は外部 gRPC コレクタ (`dst_addr` の `host:port`) へのテレメトリデータ送信のみ。
これは Redis DB への書き込みではなく、ネットワーク I/O である。
