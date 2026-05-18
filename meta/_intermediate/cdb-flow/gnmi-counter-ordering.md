# gnmi-counter — Phase B ordering 調査メモ

## 調査対象

- `sonic-buildimage/dockers/docker-sonic-telemetry/supervisord.conf` — コンテナ内サービス起動順
- `sonic-gnmi/gnmi_server/server.go` — `NewServer()` → `InitCounters()` の呼び出し順序（L528）
- `sonic-gnmi/common_utils/context.go` — `InitCounters()` / `IncCounter()` 実装
- `sonic-gnmi/common_utils/shareMem.go` — SysV 共有メモリ書込み (`SetMemCounters` / `GetMemCounters`)
- `sonic-gnmi/gnmi_dump/gnmi_dump.go` — カウンタ読み出しツール（独立プロセス）

## supervisord.conf 起動順序

| priority | program | wait_for |
|----------|---------|----------|
| 1 | rsyslogd | — |
| 2 | start | rsyslogd:running |
| 3 | telemetry | start:exited |
| 4 | dialout | telemetry:running |

## 順序依存の根拠

### 1. start.sh → telemetry の強制先行

`supervisord.conf` の `dependent_startup_wait_for=start:exited` により、`telemetry` プロセスは `start.sh` が exited 状態になるまで起動しない。

### 2. InitCounters → gRPC Serve の強制先行

`server.go:NewServer()` の逐次実行:
```go
func NewServer(config *Config, tlsOpts []grpc.ServerOption, commonOpts []grpc.ServerOption) (*Server, error) {
    ...
    common_utils.InitCounters()   // L528: 全カウンタを 0 で共有メモリへ初期化
    ...
    s := grpc.NewServer(...)      // L544: gRPC サーバ作成
    ...
}
// その後 srv.Serve() → gRPC リクエスト受け付け開始
```

`InitCounters()` は `NewServer()` の冒頭で同期的に呼ばれるため、共有メモリが初期化される前に gRPC リクエストを受け付けることはない（goroutine 分岐なし）。

### 3. gnmi_dump の独立性と SysV shm の存在前提

`gnmi_dump.go` は `common_utils.GetMemCounters()` → `syscall.SYS_SHMGET` を直接呼ぶ。telemetryd 未起動時（共有メモリ未作成）の場合、`shmget` がエラーを返し「`Fail to read counters`」として終了する。

### 4. dialout と counters の無関係性

`dialout` は `telemetry:running` を待って起動するが、dialout の処理コード（`dialout/` ディレクトリ）は `IncCounter()` を呼ばない。counters はあくまで telemetry の gRPC RPC 受信と DBus 操作のみでカウントされる。

## 結論

- 共有メモリカウンタは `telemetryd` (priority=3) 起動時の `NewServer()` で確実に初期化される
- `gnmi_dump` は telemetryd 起動後でなければカウンタ読み取り不可
- dialout 側にカウンタ更新処理はなく、counters は telemetry 専用
