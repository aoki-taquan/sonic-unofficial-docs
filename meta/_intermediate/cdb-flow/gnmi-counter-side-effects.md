# gnmi-counter — Phase F 副作用調査メモ

## 調査対象

- `sonic-gnmi/gnmi_server/connection_manager.go` (master)
- `sonic-gnmi/gnmi_server/server.go` (master)
- `sonic-gnmi/common_utils/context.go` (master)
- `sonic-gnmi/common_utils/shareMem.go` (master)

## 発見した副作用

### 1. STATE_DB `TELEMETRY_CONNECTIONS` への書き込み

`connection_manager.go:76` — `ConnectionManager.Add()` が `storeKeyRedis(key)` を呼び、STATE_DB `TELEMETRY_CONNECTIONS` に `HSet(key, "active")` を実行。
`connection_manager.go:90` — `ConnectionManager.Remove()` が `deleteKeyRedis(key)` を呼び、`HDel(key)` を実行。
`connection_manager.go:52-60` — `PrepareRedis()` 起動時に `HGetAll` + 全 `HDel` でテーブルをクリア。

```go
// connection_manager.go:111-119
func storeKeyRedis(key string) {
    if rclient == nil { return }
    rclient.HSet(context.Background(), table, key, "active")
}

// connection_manager.go:121-131
func deleteKeyRedis(key string) {
    if rclient == nil { return }
    rclient.HDel(context.Background(), table, key)
}
```

### 2. スタートアップコンフィグ保存（save_on_set 有効時）

`server.go:1207-1208`:
```go
err = dc.Set(req.GetDelete(), req.GetReplace(), req.GetUpdate())
if err != nil {
    common_utils.IncCounter(common_utils.GNMI_SET_FAIL)
} else {
    s.SaveStartupConfig()
}
```

デフォルト (`server.go:551`) は `SaveStartupConfig: saveOnSetDisabled`（no-op）。
`save_on_set = true` の場合、`hostcfgd GnmiCfg` ハンドラが `SaveStartupConfig = SaveOnSetEnabled` に差し替え、DBus `ConfigSave("/etc/sonic/config_db.json")` を発行。これにより `DBUS_CONFIG_SAVE` カウンタが増分される。

### 3. SysV 共有メモリへの書き込み

`context.go:180-183` — `IncCounter` は `atomic.AddUint64` の後に `SetMemCounters(&globalCounters)` を呼ぶ。全 32 カウンタを SysV SHM (key=7749) へ書き直す。CONFIG_DB / STATE_DB への書き込みはなし。

## 副作用のないパス

- `GNMI_GET_FAIL` / `GNMI_SET_FAIL` 増分: SysV SHM への書き込みのみ。他の DB への影響なし。
- `GNMI_SET_BYPASS` 増分: bypass パス (`bypass.go:TrySet`) が直接 Redis (CONFIG_DB) に書き込むが、カウンタ増分自体の副作用は SysV SHM のみ。
- `DBUS_*` カウンタ: DBus 操作の完了/失敗とは独立して増分される。操作の結果自体（DB 変更等）はカウンタとは別経路。
