# subscription-config-defaults — Phase A 調査メモ

対象ページ: `docs/reference/config-db/subscription-config.md`
対象テーブル: `TELEMETRY_CLIENT|Subscription|*` / `TELEMETRY_CLIENT|DestinationGroup|*` / `TELEMETRY_CLIENT|Global`

調査日: 2026-05-14

---

## コード由来デフォルト一覧

### 1. `report_interval` — YANG default 5000 ms / コード hardcode 5000 ms

**YANG 定義** (`sonic-telemetry_client.yang` L134-135):
```yang
leaf report_interval {
    type uint64;
    description "report_interval unit ms";
    default 5000;
}
```

**Go 実装** (`sonic-gnmi/dialout/dialout_client/dialout_client.go` L582):
```go
cs := clientSubscription{
    interval: 5000, // default to 5000 milliseconds
    name:     name,
    cancel:   cancel,
}
```

YANG と実装が一致。CONFIG_DB に `report_interval` が省略された場合、`clientSubscription.interval` は 5000 ms (5 秒) となる。

証跡: `sonic-gnmi/dialout/dialout_client/dialout_client.go:582`

---

### 2. `unidirectional` — YANG default true / 実装は常に true に固定 (discrepancy)

**YANG 定義** (`sonic-telemetry_client.yang` L88-89):
```yang
leaf unidirectional {
    type boolean;
    default true;
    description "Whether the dial-out connection is unidirectional.";
}
```

**Go 実装** (`dialout_client.go` L503-505):
```go
case "unidirectional":
    // No PublishResponse supported yet
    clientCfg.Unidirectional = true
```

設定値に関わらず **常に `true`** が代入される (コメント: "No PublishResponse supported yet")。`false` を CONFIG_DB に書いても動作は変わらない。

**YANG-実装 discrepancy**: YANG 上は `false` 設定可能だが、実装は `false` を無視する。

証跡: `sonic-gnmi/dialout/dialout_client/dialout_client.go:503-505`

---

### 3. `encoding` — YANG enum あり / 実装は常に JSON_IETF に固定 (discrepancy)

**YANG 定義** (`sonic-telemetry_client.yang` L45-53): enum `JSON_IETF`/`ASCII`/`BYTES`/`PROTO`

**Go 実装** (`dialout_client.go` L500-502):
```go
case "encoding":
    //Flexible encoding Not supported yet
    clientCfg.Encoding = gpb.Encoding_JSON_IETF
```

設定値に関わらず **常に `JSON_IETF`** が代入される (コメント: "Flexible encoding Not supported yet")。

**YANG-実装 discrepancy**: YANG は 4 値の enum を許容するが、実装は `JSON_IETF` のみ有効。

証跡: `sonic-gnmi/dialout/dialout_client/dialout_client.go:500-502`

---

### 4. `retry_interval` — YANG optional / デフォルト値なし (コードも初期値なし)

YANG に `default` なし。Go の `ClientConfig.RetryInterval` (`time.Duration`) はゼロ値 (0)。
ゼロ値の場合、`newClient` が `context.WithTimeout(ctx, 0)` を使うため即タイムアウトする可能性があるが、実装コメントには明示なし。

実用的には `retry_interval` の設定が推奨される (例: `30` 秒)。

証跡: `dialout_client.go:99,260,400`

---

### 5. `report_type` — YANG enum のみ / コードデフォルトなし

`report_type` は `clientSubscription.reportType` に格納。初期値は `reportType` のゼロ値。
`NewReportType(value)` の実装で `""` (空文字) がどの値にマップされるかは `dialout_client.go` 内の `NewReportType` 関数による。

省略時はゼロ値となり、periodic/stream/once のいずれかに相当するが、空値での動作は未定義。実用上は必須フィールドと扱うべき。

---

### 6. `path_target` — 省略時は空 Target → エラー (mandatory 相当)

```go
target := cs.prefix.GetTarget()
if target == "" {
    return fmt.Errorf("Empty target data not supported yet")
}
```

`path_target` が省略されると `cs.prefix` が nil または `Target=""` となり、`NewInstance()` で即エラー。事実上 mandatory。

証跡: `dialout_client.go:187-189`

---

### 7. `dst_group` 省略時 — Subscription は無効化

```go
if cs.destGroupName == "" {
    // not destination configured, just return
    return nil
}
```

`dst_group` が空の Subscription は登録されずに無視される (エラーなしで return)。

証跡: `dialout_client.go:622-625`

---

## サマリ表

| フィールド | YANG default | コード実装値 | 備考 |
|-----------|-------------|------------|------|
| `report_interval` | `5000` (ms) | `5000` (ms) | 一致 |
| `unidirectional` | `true` | 常に `true` | discrepancy: `false` 設定不可 |
| `encoding` | なし | 常に `JSON_IETF` | discrepancy: 他の enum 値は無視 |
| `retry_interval` | なし | ゼロ値 (0) | 未設定時は即タイムアウト可能性 |
| `report_type` | なし | ゼロ値 (未定義) | 省略時動作は未定義 |
| `path_target` | なし | 省略不可 (エラー) | 実質 mandatory |
| `dst_group` | なし | 省略時は Subscription 無視 | エラーなし・サイレント無効化 |

---

## 参照ファイル

- `sonic-net/sonic-buildimage@9ea932ec`: `src/sonic-yang-models/yang-models/sonic-telemetry_client.yang`
- `sonic-net/sonic-gnmi@eb635b76`: `dialout/dialout_client/dialout_client.go`
