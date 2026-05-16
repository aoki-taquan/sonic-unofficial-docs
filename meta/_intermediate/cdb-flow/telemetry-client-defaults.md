# TELEMETRY_CLIENT フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14  
対象テーブル: CONFIG_DB `TELEMETRY_CLIENT`

## 調査対象ファイル

- `sonic-gnmi/dialout/dialout_client/dialout_client.go` — `processTelemetryClientConfig()` / `DialOutRun()` / `clientSubscription` struct
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-telemetry_client.yang` — YANG モデル

---

## フィールド別 暗黙デフォルト

### `unidirectional` (TELEMETRY_CLIENT|Global)

**YANG デフォルト**: `true`

```yang
# sonic-telemetry_client.yang L87-89
leaf unidirectional {
    type boolean;
    default true;
    ...
}
```

**コード由来**: `dialout_client.go` L501-505 で `encoding` / `unidirectional` フィールドはどちらも値を強制上書き（実装が未対応のため）。

```go
// dialout_client.go L501-505
case "encoding":
    //Flexible encoding Not supported yet
    clientCfg.Encoding = gpb.Encoding_JSON_IETF
case "unidirectional":
    // No PublishResponse supported yet
    clientCfg.Unidirectional = true
```

**結論**: `unidirectional` は DB の値に関わらずランタイムで常に `true` に固定される（実装上 `false` は無効）。

---

### `encoding` (TELEMETRY_CLIENT|Global)

**コード由来デフォルト**: `JSON_IETF` (gpb.Encoding_JSON_IETF = 0)

```go
// dialout_client.go L501-503
case "encoding":
    //Flexible encoding Not supported yet
    clientCfg.Encoding = gpb.Encoding_JSON_IETF
```

**結論**: YANG では `JSON_IETF`/`ASCII`/`BYTES`/`PROTO` を定義するが、現実装では DB の値を無視して常に `JSON_IETF` が使用される（"Not supported yet" コメント）。

---

### `report_interval` (TELEMETRY_CLIENT_LIST — Subscription)

**YANG デフォルト**: `5000` (ms)

```yang
# sonic-telemetry_client.yang L132-135
leaf report_interval {
    type uint64;
    description "report_interval unit ms";
    default 5000;
}
```

**コード由来デフォルト**: `5000` ms

```go
// dialout_client.go L581-583
cs := clientSubscription{
    interval: 5000, // default to 5000 milliseconds
    name:     name,
```

**結論**: YANG とコード両方が `5000` ms = 5 秒をデフォルトと定義。一致している。

---

### `retry_interval` (TELEMETRY_CLIENT|Global)

**YANG デフォルト**: なし (optional leaf)

**コード由来**: 省略時は `ClientConfig.RetryInterval` が `DialOutRun()` 呼び出し元 (`dialout_client_cli.go` など) が渡す `ccfg` の値を使用する。フィールドが設定されていれば `time.Second * time.Duration(itvl)` に変換。

```go
// dialout_client.go L493-499
case "retry_interval":
    itvl, err := strconv.ParseUint(value, 10, 64)
    if err != nil {
        log.V(2).Infof("Invalid retry_interval %v %v", value, err)
        continue
    }
    clientCfg.RetryInterval = time.Second * time.Duration(itvl)
```

**結論**: DB に値がなければ呼び出し元 CLI オプションのデフォルトに依存。コード内でのゼロ値は「タイムアウトなし」となり接続タイムアウトが発生しない可能性あり。

---

### `src_ip` (TELEMETRY_CLIENT|Global)

**YANG デフォルト**: なし (optional leaf)

**コード由来**: 省略時は `ClientConfig.SrcIp = ""` のまま。gRPC DialContext の送信元は OS のルーティングに委ねられる。

---

### `dst_addr` (TELEMETRY_CLIENT_LIST — DestinationGroup)

**YANG デフォルト**: なし

**コード由来**: 省略または空文字列の場合 `Destination.Validate()` が `"Destination.Addrs is empty"` を返してエントリを拒否。必須フィールド扱い。

---

### `report_type` (TELEMETRY_CLIENT_LIST — Subscription)

**YANG デフォルト**: なし

**コード由来**: 省略時は `clientSubscription.reportType = 0 = Unknown`。`publishRun()` の switch で `default:` ケースに落ち `"Unsupported report type"` をログして処理を行わない（サイレント無効）。

---

## まとめ

| フィールド | コード由来デフォルト | YANG デフォルト | 備考 |
|-----------|-------------------|----------------|------|
| `unidirectional` | `true` (強制固定) | `true` | 実装未対応で DB 値を無視 |
| `encoding` | `JSON_IETF` (強制固定) | なし | 実装未対応で DB 値を無視 |
| `report_interval` | `5000` ms | `5000` | YANG・コード一致 |
| `retry_interval` | 呼び出し元依存 | なし | 未設定時は CLI デフォルト |
| `src_ip` | `""` (OS依存) | なし | 省略可 |
| `dst_addr` | (必須) | なし | 空なら拒否 |
| `report_type` | `Unknown` (無効) | なし | 省略するとサイレント無効 |

## evidence

- `sonic-gnmi/dialout/dialout_client/dialout_client.go` L97-104 (ClientConfig struct), L464-644 (processTelemetryClientConfig), L581-583 (interval default), L501-505 (encoding/unidirectional forced)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-telemetry_client.yang` L87-90 (unidirectional default), L132-135 (report_interval default)
