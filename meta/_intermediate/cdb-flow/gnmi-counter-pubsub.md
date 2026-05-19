# gnmi-counter — Phase G pubsub 調査メモ

## 調査対象

`sonic-gnmi` の内部リクエストカウンタ（SysV 共有メモリ key=7749）に関する
Redis pub/sub・swsscommon Publisher/Consumer パターンの有無を確認する。

## 結論

**gNMI 内部カウンタには Redis pub/sub 機構が存在しない。**

カウンタは SysV 共有メモリに格納されるため、Redis キースペース通知・
swsscommon `SubscriberStateTable` / `ConsumerStateTable` / `NotificationConsumer`
などの仕組みは一切介在しない。`gnmi_dump` ツールがカウンタを読む際も
SysV SHM (`shmget` → `shmat`) に直接アクセスするだけで、Redis は経由しない。

## ソースグレップ結果

### PSUBSCRIBE / SubscriberStateTable (sonic-gnmi 全体)

```
$ grep -rn "PSUBSCRIBE\|SubscriberStateTable\|ConsumerStateTable\|keyspace" sonic-gnmi/ \
    --include="*.go" | grep -v "_test.go"
```

該当なし（common_utils/ および gnmi_dump/ ディレクトリ内）。

keyspace 通知を使うコードは以下の 3 箇所のみで、いずれもカウンタとは無関係:

| ファイル | 対象テーブル | 用途 |
|--------|-----------|------|
| `dialout/dialout_client/dialout_client.go:686` | `TELEMETRY_CLIENT|*` | dial-out 設定変更の追従 |
| `gnmi_server/db_journal.go:67-69` | `__keyspace@<dbNum>__:*` | gNMI Set の CONFIG_DB ジャーナル記録 |
| `sonic_data_client/mixed_db_client.go:2093` | `__keyspace@<dbNum>__:<path>` | gNMI Subscribe ON_CHANGE 変更検知 |

### NotificationProducer (sonic-gnmi/common_utils/notification_producer.go)

`NotificationProducer` は存在するが、gNMI カウンタ増分経路（`IncCounter` → `SetMemCounters`）
では使用されない。カウンタ値を Redis Channel に publish するコードはない。

### gnmi_dump のカウンタ読み出し経路

```go
// gnmi_dump/gnmi_dump.go:17-24
func main() {
    cnt, err := common_utils.GetMemCounters()
    if err != nil {
        fmt.Printf("Error: Fail to read counters, syscall error, err: %v\n", err)
        return
    }
    fmt.Printf("Dump GNMI counters\n")
    for i := 0; i < int(common_utils.COUNTER_SIZE); i++ {
        fmt.Printf("%s---%d\n", common_utils.CounterName[i], cnt[i])
    }
}
```

`GetMemCounters` は `syscall.SYS_SHMGET` → `SYS_SHMAT` の SysV IPC 呼び出しのみ。
Redis 接続コードは一切含まない（`shareMem.go:38-54`）。

## 外部監視ツールからの読み出し

外部 Prometheus exporter 等が gNMI カウンタを収集したい場合の唯一の方法は
`gnmi_dump` を定期実行してテキスト出力をパースすることである。
Redis Subscribe / GET による取得パスは提供されていない。
