# gnmi-counter — Phase D failure 調査メモ

調査対象:
- `sonic-gnmi/common_utils/shareMem.go` (SetMemCounters / GetMemCounters)
- `sonic-gnmi/common_utils/context.go` (InitCounters / IncCounter)
- `sonic-gnmi/gnmi_dump/gnmi_dump.go` (main — GetMemCounters failure path)
- `sonic-gnmi/gnmi_server/server.go` (NewServer — InitCounters)

## SetMemCounters の失敗パターン

```go
// shareMem.go:21-36
func SetMemCounters(counters *[int(COUNTER_SIZE)]uint64) error {
    shmid, _, err := syscall.Syscall(syscall.SYS_SHMGET, uintptr(memKey), uintptr(memSize), uintptr(memMode))
    if int(shmid) == -1 {
        return fmt.Errorf("syscall error, err: %v\n", err)
    }
    shmaddr, _, err := syscall.Syscall(syscall.SYS_SHMAT, shmid, 0, 0)
    if int(shmaddr) == -1 {
        return fmt.Errorf("syscall error, err: %v\n", err)
    }
    defer syscall.Syscall(syscall.SYS_SHMDT, shmaddr, 0, 0)
    ...
}
```

`SetMemCounters` はエラーを返すが、呼び出し元の `InitCounters` と `IncCounter` はこの戻り値を**無視**する。

## InitCounters の失敗無視

```go
// context.go:173-178
func InitCounters() {
    for i := 0; i < int(COUNTER_SIZE); i++ {
        globalCounters[i] = 0
    }
    SetMemCounters(&globalCounters)  // 戻り値を無視
}
```

`NewServer()` (server.go:528) は `InitCounters()` を呼ぶが、SysV 共有メモリの初期化が失敗しても `NewServer` はエラーを返さず起動を継続する。

## IncCounter の失敗無視

```go
// context.go:180-183
func IncCounter(cnt CounterType) {
    atomic.AddUint64(&globalCounters[cnt], 1)
    SetMemCounters(&globalCounters)  // 戻り値を無視
}
```

RPC 受信ごとに呼ばれる `IncCounter` も `SetMemCounters` の失敗を無視する。goroutine セーフな `globalCounters` は in-memory で正しくカウントされ続けるが、共有メモリへの反映は失敗する（`gnmi_dump` は古い値または未初期化値を返す）。

## GetMemCounters (gnmi_dump) の失敗パターン

```go
// gnmi_dump.go:20-24
err := common_utils.GetMemCounters(&counters)
if err != nil {
    fmt.Printf("Error: Fail to read counters, %v", err)
    return
}
```

telemetryd 未起動 (`shmget` で `ENOENT`) の場合、`gnmi_dump` は `"Error: Fail to read counters, syscall error, err: ..."` を標準出力に出力して終了コード 0 で返る（非ゼロ exit なし）。

## 影響範囲

| 失敗シナリオ | カウンタ動作 | gnmi_dump 影響 | ログ出力 |
|------------|-----------|--------------|---------|
| SHM 作成失敗 (telemetryd 起動時 `shmget` ENOMEM) | in-memory では 0 にリセット、SHM 未初期化 | `Fail to read counters` | なし（InitCounters エラー無視） |
| SHM アタッチ失敗 (IncCounter 時 ENOMEM) | in-memory は正常増加、SHM 更新なし | 古い値を返す | なし（IncCounter エラー無視） |
| telemetryd 未起動で gnmi_dump 実行 | 対象外 | `Fail to read counters` + exit 0 | stderr なし |
| COUNTER_SIZE 変更後 telemetryd と gnmi_dump のバイナリ不一致 | インデックスずれ（配列範囲内は Go panic なし、範囲外は panic） | 誤ったカウンタを出力 | panic の場合 panic ログ |
