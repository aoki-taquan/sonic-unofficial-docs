# gnmi-state ハードコード定数調査 (Phase E)

## 調査対象

- `sonic-net/sonic-gnmi` `gnmi_server/connection_manager.go`
- `sonic-net/sonic-gnmi` `telemetry/telemetry.go`

## 検出定数

### テーブル名・値定数

| 定数 | 値 | ソース |
|------|----|--------|
| `table` 定数 | `"TELEMETRY_CONNECTIONS"` | `connection_manager.go:16` |
| HSet 固定値 | `"active"` | `connection_manager.go:116` |

### 接続閾値デフォルト

| フラグ | デフォルト | ソース |
|--------|-----------|--------|
| `--threshold` | `100` | `telemetry.go:187` |
| threshold=0 の意味 | 上限なし | `connection_manager.go:65` |

### connection key 生成

| 定数 | 値 | ソース |
|------|----|--------|
| regexStr | `"(?:target\|element):\"([a-zA-Z0-9-_*]*)\""` | `connection_manager.go:95` |
| 区切り文字 | `"\|"` | `connection_manager.go:99,105,107` |
| タイムスタンプ形式 | `time.RFC3339` | `connection_manager.go:107` |

### Redis クライアントパラメータ

| フィールド | 値 | ソース |
|------------|-----|--------|
| Network | `"tcp"` | `connection_manager.go:45` |
| Password | `""` | `connection_manager.go:47` |
| DialTimeout | `0` | `connection_manager.go:49` |
