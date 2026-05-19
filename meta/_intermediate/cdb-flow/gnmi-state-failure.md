# gnmi-state — Phase D failure-behavior 調査メモ

## 対象ファイル
`docs/reference/config-db/gnmi-state.md` (`TELEMETRY_CONNECTIONS` テーブル)

## Phase D: 失敗挙動

### 調査ソース
- `sonic-net/sonic-gnmi` @ eb635b7679b260c3fd0786a6d0734fc8e82c9a22
  - `gnmi_server/connection_manager.go`
  - `gnmi_server/client_subscribe.go`

### 主要な失敗パターン

1. **PrepareRedis() 失敗**: `GetDbTcpAddr()` / `GetDbId()` エラー時に `rclient = nil` のまま early return。以降の HSet / HDel はすべて silent no-op。

2. **rclient == nil ガード**: `storeKeyRedis()` (L112-114) と `deleteKeyRedis()` (L122-124) が `rclient == nil` を検出した場合、`log.V(1).Infof` のみ出力して return。gNMI RPC の動作には影響しない。

3. **HSet エラー**: Redis 高負荷・接続切断時に `HSet` が失敗しても `log.V(1).Infof` のみで継続。TELEMETRY_CONNECTIONS にエントリが追加されない。

4. **閾値超過**: `Add()` (L65-69) で `len(cm.connections) >= cm.threshold && cm.threshold != 0` 時は `("", false)` を返す。`storeKeyRedis()` 未呼び出し。

5. **STATE_DB とメモリの乖離**: メモリ更新が常に Redis 操作より先に行われるため、Redis 失敗時に STATE_DB だけが古い状態になる。

### best-effort 設計の意図
STATE_DB への記録は可視化用途のみであり、制御パスに含まれない。したがってすべてのエラーは best-effort で処理され、デーモン本体（gNMI RPC の送受信）には影響しない。
