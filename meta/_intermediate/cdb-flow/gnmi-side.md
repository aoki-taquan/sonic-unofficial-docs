# gnmi 副次 DB 書込調査メモ (Phase F)

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/gnmi.md`
フェーズ: Phase F (副次 DB 書込 / side-effects)

## 調査対象ファイル

| ファイル | リポジトリ | SHA | 役割 |
|---------|-----------|-----|------|
| `gnmi_server/connection_manager.go` | sonic-net/sonic-gnmi | eb635b76 | TELEMETRY_CONNECTIONS テーブルへの書き込みロジック |
| `gnmi_server/server.go` | sonic-net/sonic-gnmi | eb635b76 | NewServer, InitCounters 呼び出し |
| `common_utils/context.go` | sonic-net/sonic-gnmi | eb635b76 | CounterType, IncCounter, InitCounters |
| `common_utils/shareMem.go` | sonic-net/sonic-gnmi | eb635b76 | SysV IPC 共有メモリ操作 |
| `gnmi_dump/gnmi_dump.go` | sonic-net/sonic-gnmi | eb635b76 | カウンタ読み取りツール |

## STATE_DB 書込 — TELEMETRY_CONNECTIONS

### テーブル仕様

- Redis Database: STATE_DB (db index 6)
- Key: `TELEMETRY_CONNECTIONS` (単一 Hash)
- Hash field: connection key = `<peer_ip:port>|<target_1>|...|<RFC3339_timestamp>`
- Hash value: `"active"` (ハードコード固定)

### ライフサイクル

| タイミング | 操作 | ソース |
|-----------|------|--------|
| `PrepareRedis()` 呼び出し (デーモン起動時) | `HGetAll` 後 `HDel` で全既存エントリ削除 | `connection_manager.go:52-60` |
| Subscribe RPC 開始 (`Add()`) | `HSet(table, key, "active")` | `connection_manager.go:116` |
| Subscribe RPC 終了 (`Remove()`) | `HDel(table, key)` | `connection_manager.go:127` |

### threshold との関係

`GNMI|gnmi.threshold` (デフォルト 100) が `len(cm.connections) >= cm.threshold` を満たすと新規接続を拒否し、STATE_DB への HSet は行わない (`connection_manager.go:65`)。
`threshold = 0` は無制限を意味する (コメント: `0 is defined as no threshold`)。

### nil ガード (フォールトトレラント)

```go
// connection_manager.go:111-115
if rclient == nil {
    log.V(1).Infof("Redis client is nil, cannot store connection key")
    return
}
```

STATE_DB が利用不可能でも `telemetry` サーバは継続動作する。

## カウンタ統計 — 共有メモリ (SysV IPC)

### 仕様

- `memKey = 7749` (SysV IPC キー)
- `memSize = 1024` バイト (uint64 × 128 スロット確保)
- 現在 `COUNTER_SIZE = 32` カウンタ使用中

### CounterType 一覧

```
GNMI_GET=0, GNMI_GET_FAIL=1, GNMI_SET=2, GNMI_SET_FAIL=3, GNMI_SET_BYPASS=4
GNOI_REBOOT=5(未使用), GNOI_FACTORY_RESET=6, GNOI_OS_INSTALL=7
GNOI_HEALTHZ_ACK=8, GNOI_HEALTHZ_CHECK=9, GNOI_HEALTHZ_COLLECT=10
GNSI_CREDZ_SET=11, GNSI_CREDZ_CHECKPOINT=12
DBUS=13, DBUS_FAIL=14, DBUS_APPLY_PATCH_DB=15, DBUS_APPLY_PATCH_YANG=16
DBUS_CREATE_CHECKPOINT=17, DBUS_DELETE_CHECKPOINT=18, DBUS_CONFIG_SAVE=19
DBUS_CONFIG_RELOAD=20, DBUS_STOP_SERVICE=21, DBUS_RESTART_SERVICE=22
DBUS_FILE_STAT=23, DBUS_FILE_DOWNLOAD=24, DBUS_FILE_REMOVE=25
DBUS_IMAGE_DOWNLOAD=26, DBUS_IMAGE_INSTALL=27, DBUS_IMAGE_LIST=28
DBUS_IMAGE_ACTIVATE=29, DBUS_DOCKER_LOAD=30, DBUS_CONFIG_REPLACE=31
COUNTER_SIZE=32
```

### 操作フロー

1. `NewServer()` → `InitCounters()`: 全 32 カウンタを uint64(0) に初期化して共有メモリ書き込み
2. RPC 処理中に `IncCounter(cnt)` → `atomic.AddUint64` → `SetMemCounters` (全カウンタ共有メモリ同期)
3. `gnmi_dump` ツール: `GetMemCounters` で共有メモリ読み取り → 標準出力

### GNOI_REBOOT の dead counter

`GNOI_REBOOT` (index 5) は定義されているが、`gnoi_system.go` の Reboot 実装で `IncCounter(GNOI_REBOOT)` が呼ばれていない。コードギャップ。

### Redis COUNTERS_DB への書込

**なし**。カウンタは共有メモリのみで管理される。Redis (`redis-cli`) から見えない。

## その他 DB

| DB | 書込有無 | 根拠 |
|---|---|---|
| APPL_DB | なし | `gnmi_server/server.go` に ProducerStateTable / NotificationProducer の書込なし |
| COUNTERS_DB | なし | カウンタは SysV 共有メモリのみ |
| ASIC_DB | なし | SAI 非経由 |
| FLEX_COUNTER_DB | なし | 参照なし |

## 証跡

- `gnmi_server/connection_manager.go:52-60` — PrepareRedis HGetAll/HDel
- `gnmi_server/connection_manager.go:65` — threshold チェック (0 = 無制限)
- `gnmi_server/connection_manager.go:94-108` — createKey フォーマット
- `gnmi_server/connection_manager.go:111-116` — nil ガード + HSet "active"
- `gnmi_server/connection_manager.go:127` — HDel 接続終了時
- `common_utils/context.go` — CounterType iota, IncCounter, InitCounters
- `common_utils/shareMem.go` — memKey=7749, memSize=1024
- `gnmi_server/server.go:528` — NewServer で InitCounters
- `gnmi_dump/gnmi_dump.go` — GetMemCounters 読み取り
