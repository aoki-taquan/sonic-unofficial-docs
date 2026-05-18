# subscription-config — Phase E ハードコード定数スキャンノート

対象テーブル: `TELEMETRY_CLIENT|Global` / `TELEMETRY_CLIENT|DestinationGroup_<name>` / `TELEMETRY_CLIENT|Subscription_<name>`
Consumer: `dialout_client.go` (`sonic-gnmi/dialout/dialout_client/dialout_client.go`)
スキャン範囲: 全行精読（const ブロック、数値リテラル、time.Duration 定数、queue パラメータ）

---

## 検出したハードコード定数

### 1. `report_interval` デフォルト — 5000 ms

```go
// dialout_client.go:582
cs := clientSubscription{
    interval: 5000, // default to 5000 milliseconds
    name:     name,
    cancel:   cancel,
}
```

CONFIG_DB に `report_interval` が設定されていない場合、`clientSubscription.interval` は **5000 ms (5 秒)** に固定される。
この値は YANG `default 5000` と一致するため、YANG-実装 discrepancy はない。

---

### 2. Stream モード — 100 ms sleep（収束待ち）

```go
// dialout_client.go:392
time.Sleep(100 * time.Millisecond)
```

Stream モードで `cs.dc.StreamRun()` を goroutine として起動した直後、メインループが 100 ms 待機する。
これは StreamRun の初期化完了を待つための経験則的な値であり、CONFIG_DB フィールドでは制御できない。

---

### 3. pubsub ReceiveTimeout — 1000 ms (ポーリング間隔)

```go
// dialout_client.go:693 (初回確認)
msgi, err := pubsub.ReceiveTimeout(context.Background(), time.Second)

// dialout_client.go:718 (メインループ)
msgi, err := pubsub.ReceiveTimeout(context.Background(), time.Millisecond*1000)
```

`DialOutRun()` のメインイベントループは Redis keyspace 通知を最大 **1000 ms (1 秒)** 待機する。
タイムアウトした場合は `neterr.Timeout() == true` を検出して `continue` し、次のポーリングへ移行する。
この値は CONFIG_DB で変更できない。CONFIG_DB 変更への最悪応答遅延が約 1 秒になることを示す。

---

### 4. PriorityQueue 容量 — 1 (送信キュー)

```go
// dialout_client.go:298
cs.q = queue.NewPriorityQueue(1, false)
```

各 Subscription の送信キュー (`PriorityQueue`) は容量 **1** で生成される。
キューが満杯の場合、新しいデータは破棄される（`queue.PriorityQueue` の `blocking=false` 設定）。
これは CONFIG_DB フィールドでは変更できない。

---

### 5. reportType 定数マッピング (const iota)

```go
// dialout_client.go:27-35
const (
    Unknown  reportType = iota  // 0
    Once                        // 1
    Periodic                    // 2
    Stream                      // 3
)
```

YANG の `report_type` enum (`once`/`periodic`/`stream`) は、以下の文字列→整数マッピングで変換される。

```go
// dialout_client.go:63-70
typeConst = map[string]reportType{
    "unknown":  Unknown,   // 0
    "once":     Once,      // 1
    "periodic": Periodic,  // 2
    "stream":   Stream,    // 3
}
```

`NewReportType("")`（空文字列）は `Unknown (0)` を返す。`Unknown` の場合、`publishRun` の
`switch cs.reportType` でデフォルトブランチに落ち、動作が未定義になる。

---

### 6. grpc.DialTimeout — 0 (タイムアウトなし)

```go
// dialout_client.go:666, 678
DialTimeout: 0,
```

gRPC 接続オプションの `DialTimeout` は **0**（タイムアウトなし）が設定される。
実際の接続タイムアウトは `ClientConfig.RetryInterval` を `context.WithTimeout` に渡す形で制御される
（`dialout_client.go:260-261`）。`RetryInterval = 0` の場合は即タイムアウトになる。

---

## 定数サマリ表

| 定数 | 値 | 制御方法 | 影響 |
|------|----|---------|------|
| `report_interval` デフォルト | 5000 ms | CONFIG_DB `report_interval` で上書き可 | 未設定時の報告周期 |
| Stream モード起動待ち | 100 ms | 変更不可（ハードコード） | StreamRun goroutine の収束待ち |
| pubsub ReceiveTimeout | 1000 ms | 変更不可（ハードコード） | CONFIG_DB 変更への最悪応答遅延 |
| PriorityQueue 容量 | 1 | 変更不可（ハードコード） | 送信キューが 1 エントリ超過すると破棄 |
| gRPC DialTimeout | 0 | 変更不可（ハードコード） | 接続タイムアウトは RetryInterval に依存 |
| `Unknown` reportType | 0 (iota) | YANG `report_type` フィールドで制御 | 空・未知値は Unknown → 動作未定義 |

---

## 参照ファイル

- `sonic-net/sonic-gnmi@eb635b76`: `dialout/dialout_client/dialout_client.go`
  - L27-35: const iota ブロック
  - L63-70: typeConst マップ
  - L298: PriorityQueue(1, false)
  - L392: time.Sleep(100 * time.Millisecond)
  - L582: interval: 5000
  - L666, 678: DialTimeout: 0
  - L693, 718: pubsub.ReceiveTimeout(... time.Second / time.Millisecond*1000)
