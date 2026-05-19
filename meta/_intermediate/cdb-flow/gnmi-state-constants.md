# TELEMETRY_CONNECTIONS (gnmi-state) — Phase E ハードコード定数調査メモ

調査日: 2026-05-19
調査対象:
- `sonic-net/sonic-gnmi/gnmi_server/connection_manager.go`
- `sonic-net/sonic-gnmi/gnmi_server/client_subscribe.go`
- `sonic-net/sonic-gnmi/telemetry/telemetry.go`

## 検出された定数

### テーブル名定数 (connection_manager.go:16)

```go
const table = "TELEMETRY_CONNECTIONS"
```

STATE_DB の Redis Hash キー名。`HSet` / `HDel` / `HGetAll` のすべての呼び出しでこの定数を使用。

### STATE_DB 参照先固定文字列

`PrepareRedis()` (connection_manager.go:34,39) で以下の固定文字列を使用:

```go
addr, err := sdcfg.GetDbTcpAddr("STATE_DB", ns)
db, err := sdcfg.GetDbId("STATE_DB", ns)
```

DB 名 `"STATE_DB"` はハードコード。設定変更不可。

### Hash value 固定値 (connection_manager.go:116)

```go
rclient.HSet(context.Background(), table, key, "active")
```

接続登録時の value は常に文字列 `"active"` 固定。接続状態の種類 (`established`, `idle` 等) は存在せず、エントリの存在自体を接続中の証拠とする設計。

### threshold デフォルト値 (telemetry.go:187)

```go
Threshold: fs.Int("threshold", 100, "max number of client connections"),
```

threshold の CLI デフォルト値は `100`。`threshold = 0` は無制限を意味する。

### connection key 生成の正規表現 (connection_manager.go:95)

```go
regexStr := "(?:target|element):\"([a-zA-Z0-9-_*]*)\""
```

Subscribe リクエストの gNMI query 文字列から `target` / `element` フィールド値を抽出するための正規表現。取得対象文字種は `[a-zA-Z0-9-_*]` に限定されており、その他の文字はキーから除外される。

### connection key タイムスタンプ形式 (connection_manager.go:107)

```go
connectionKey += time.Now().UTC().Format(time.RFC3339)
```

タイムスタンプフォーマットは Go 標準ライブラリの `time.RFC3339`（`"2006-01-02T15:04:05Z07:00"` 形式、秒精度）。UTC タイムゾーン固定。

### ログ verbosity レベル (connection_manager.go:66, 72, 85, 113, 117, 123, 129)

STATE_DB 書き込み失敗・接続管理のログはすべて `log.V(1).Infof()` で出力。verbosity `1` でのみ可視。
デーモン起動時のエラー系ログのみ `log.Errorf()` (verbosity 0) で出力される。
