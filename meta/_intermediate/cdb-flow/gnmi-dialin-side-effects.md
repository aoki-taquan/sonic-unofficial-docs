# gnmi-dialin 副次 DB 書込調査メモ (Phase F)

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/gnmi-dialin.md`
フェーズ: Phase F (副次 DB 書込 / side-effects)

## 調査対象ファイル

| ファイル | リポジトリ | SHA | 役割 |
|---------|-----------|-----|------|
| `gnmi_server/connection_manager.go` | sonic-net/sonic-gnmi | eb635b76 | STATE_DB TELEMETRY_CONNECTIONS 書き込みロジック |
| `gnmi_server/server.go` | sonic-net/sonic-gnmi | eb635b76 | NewServer / InitCounters 呼び出し |
| `gnmi_server/client_subscribe.go` | sonic-net/sonic-gnmi | eb635b76 | PrepareRedis 呼び出し |
| `common_utils/context.go` | sonic-net/sonic-gnmi | eb635b76 | CounterType, IncCounter, InitCounters |
| `common_utils/shareMem.go` | sonic-net/sonic-gnmi | eb635b76 | SysV IPC 共有メモリ操作 |

## STATE_DB 書込 — TELEMETRY_CONNECTIONS

`telemetry` デーモン（dial-in gNMI サーバ）は Subscribe RPC の接続状態を STATE_DB の
`TELEMETRY_CONNECTIONS` Hash に記録する。これは `GNMI|gnmi` テーブルの直接の操作起点ではなく、
dial-in セッション確立・切断イベントをトリガとする**副次的な STATE_DB 書込**である。

### テーブル仕様

- Redis Database: STATE_DB (db index 6)
- Key: `TELEMETRY_CONNECTIONS` (単一 Hash)
- Hash field: connection key = `<peer_ip:port>|<target_1>|...|<RFC3339_timestamp>`
- Hash value: `"active"` (ハードコード固定)

### ライフサイクル

| タイミング | 操作 | ソース |
|-----------|------|--------|
| `client_subscribe.go` 起動 (`PrepareRedis()` 呼び出し) | `HGetAll("TELEMETRY_CONNECTIONS")` + 全既存エントリを `HDel` で削除 | `connection_manager.go:32-61`; `client_subscribe.go:84` |
| Subscribe RPC 開始 (`Add()`) | `HSet(table, key, "active")` | `connection_manager.go:116` |
| Subscribe RPC 終了 (`Remove()`) | `HDel(table, key)` | `connection_manager.go:127` |

### threshold との連動

`GNMI|gnmi.threshold`（デフォルト `100`）が `len(connections) >= threshold` を満たすと新規
Subscribe RPC を拒否し、STATE_DB への HSet は行わない (`connection_manager.go:65`)。
`threshold = 0` は無制限を意味する（コメント: `0 is defined as no threshold`）。

### nil ガード（フォールトトレラント）

```go
// connection_manager.go:111-115
if rclient == nil {
    log.V(1).Infof("Redis client is nil, cannot store connection key")
    return
}
```

STATE_DB が利用不可能でも `telemetry` サーバは継続動作する。

## カウンタ統計 — SysV IPC 共有メモリ

`NewServer()` が `InitCounters()` を呼び出し、全 32 カウンタを SysV IPC 共有メモリに初期化する。
Redis COUNTERS_DB への書込は**一切行わない**。

- `memKey = 7749` (SysV IPC キー)
- `memSize = 1024` バイト (uint64 × 128 スロット確保)
- 現在 `COUNTER_SIZE = 32` カウンタ使用中

`gnmi_dump` ツールが `GetMemCounters()` で共有メモリを読み取る（Redis 非経由）。

## その他 DB

| DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | `gnmi_server/server.go` に ProducerStateTable / NotificationProducer の書込なし |
| COUNTERS_DB | なし | カウンタは SysV 共有メモリのみ。`redis-cli` から不可視 |
| ASIC_DB | なし | SAI 非経由 |
| FLEX_COUNTER_DB | なし | 参照なし |

## 証跡

- `gnmi_server/connection_manager.go:32-61` — PrepareRedis: HGetAll + HDel
- `gnmi_server/connection_manager.go:63-70` — Add: threshold チェック (0 = 無制限)
- `gnmi_server/connection_manager.go:94-108` — createKey フォーマット
- `gnmi_server/connection_manager.go:111-116` — nil ガード + HSet "active"
- `gnmi_server/connection_manager.go:127` — HDel 接続終了時
- `gnmi_server/client_subscribe.go:84` — PrepareRedis 呼び出し
- `gnmi_server/server.go:528` — NewServer で InitCounters
- `common_utils/context.go` — CounterType iota, IncCounter, InitCounters
- `common_utils/shareMem.go` — memKey=7749, memSize=1024
