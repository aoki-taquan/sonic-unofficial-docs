# gnmi-counter — Phase C 暗黙参照テーブル分析 (cross-refs)

対象ドキュメント: `docs/reference/config-db/gnmi-counter.md`
解析日: 2026-05-19
根拠ソース:
- `sonic-gnmi/pkg/bypass/bypass.go` (master)
- `sonic-gnmi/gnmi_server/connection_manager.go` (master)
- `sonic-gnmi/pkg/interceptors/dpuproxy/resolver.go` (master)
- `sonic-gnmi/gnmi_server/server.go` (master)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-gnmi.yang` (master)

---

## 目的

`gnmi-counter` ページが扱う telemetryd (sonic-gnmi) が、カウンタ増分ロジックに連動して
**暗黙的に** 参照する他テーブル・データストアを網羅する。

---

## 1. CONFIG_DB: DEVICE_METADATA|localhost.hwsku

### 参照箇所

`pkg/bypass/bypass.go:156` — `checkSKU()` 関数

```go
hwsku, err := rclient.HGet(context.Background(), "DEVICE_METADATA|localhost", "hwsku").Result()
...
for _, prefix := range AllowedSKUPrefixes {
    if strings.HasPrefix(hwsku, prefix) {
        return true
    }
}
```

### 依存内容

| 参照側 | 参照先テーブル/キー | 参照フィールド | 参照タイミング |
|--------|------------------|--------------|--------------|
| `bypass.checkSKU()` | `DEVICE_METADATA\|localhost` | `hwsku` | `Set()` RPC で bypass 高速パス判定時（毎リクエスト） |

### 特記事項

- `hwsku` が `Cisco-8102` / `Cisco-8101` / `Cisco-8223` のいずれかの前方一致で `GNMI_SET_BYPASS` カウンタが増分される。
- 読み取りは CONFIG_DB (DB 4) への直接 Redis `HGet`（sonic-gnmi 独自クライアント。SWSSCommon の DbInterface は不使用）。
- `checkSKU()` は `GNMI_SET_BYPASS` が増分されるたびに毎回 CONFIG_DB を参照する（キャッシュなし）。

---

## 2. STATE_DB: TELEMETRY_CONNECTIONS

### 参照箇所

`gnmi_server/connection_manager.go:52` — `ConnectionManager.PrepareRedis()` と `storeKeyRedis()`

```go
res, _ := rclient.HGetAll(context.Background(), "TELEMETRY_CONNECTIONS").Result()
...
rclient.HDel(context.Background(), table, key)   // 起動時に既存エントリをクリア
rclient.HSet(context.Background(), table, key, value)  // 接続追加時
rclient.HDel(context.Background(), table, key)          // 接続削除時
```

### 依存内容

| 参照側 | 参照先 DB | テーブル/キー | 参照タイミング |
|--------|----------|-------------|--------------|
| `ConnectionManager.PrepareRedis()` | STATE_DB | `TELEMETRY_CONNECTIONS` | `telemetryd` 起動時（古いエントリ掃除） |
| `ConnectionManager.Add()` 経由 `storeKeyRedis()` | STATE_DB | `TELEMETRY_CONNECTIONS` | gRPC 接続確立時 |
| `ConnectionManager.Remove()` 経由 `deleteKeyRedis()` | STATE_DB | `TELEMETRY_CONNECTIONS` | gRPC 接続切断時 |

### 特記事項

- `TELEMETRY_CONNECTIONS` は CONFIG_DB ではなく **STATE_DB** (DB 6) に格納される。
- キーは `<remote-addr>:<port>:<query>` 形式の文字列。telemetryd 起動時に HGetAll でクリア済みエントリを掃除する。
- このテーブルの読み書きはカウンタの増分とは独立しているが、同一の `telemetryd` プロセスが管理する接続状態として gnmi-counter ページと密接に関連する。

---

## 3. CONFIG_DB: DPU|dpuN (SmartSwitch 環境のみ)

### 参照箇所

`pkg/interceptors/dpuproxy/resolver.go:91-98` — `DPUResolver.GetDPUInfo()`

```go
configKey := fmt.Sprintf("%s%s", DPUConfigTablePrefix, dpuIndex)  // "DPU|dpu<N>"
configFields, err := r.configClient.HGetAll(ctx, configKey)
gnmiPort, ok := configFields["gnmi_port"]
```

### 依存内容

| 参照側 | 参照先テーブル/キー | 参照フィールド | 参照タイミング |
|--------|------------------|--------------|--------------|
| `DPUResolver.GetDPUInfo()` | `DPU\|dpu<N>` (CONFIG_DB) | `gnmi_port` | DPU proxy 経由 gRPC リクエスト転送時 |
| `DPUResolver.GetDPUInfo()` | `CHASSIS_MIDPLANE_TABLE\|DPU<N>` (STATE_DB) | `ip_address`, `access` | DPU proxy 経由 gRPC リクエスト転送時 |

### 特記事項

- SmartSwitch 構成（`pkg/interceptors/dpuproxy/`）でのみ使用。通常の SONiC では不使用。
- `gnmi_port` 未設定時はデフォルト `8080` が使用される。
- `CHASSIS_MIDPLANE_TABLE` は STATE_DB に格納（DB 6）。CONFIG_DB の `DPU|dpu<N>` とセットで参照される。

---

## 4. CONFIG_DB: GNMI テーブル（間接参照）

### 参照箇所

`telemetry/telemetry.go` — `prepareTelemetryConfig()` が起動フラグとして受け取るが、
CONFIG_DB `GNMI` テーブル自体は `hostcfgd` の `GnmiCfg` ハンドラ
（`sonic-buildimage/src/sonic-host-services/host_modules/gnmi.py`）が supervisord / telemetry コンテナの
起動パラメータとして変換する。

### 依存内容

| CONFIG_DB テーブル | 参照フィールド | 用途 |
|-------------------|--------------|------|
| `GNMI\|certs` | `ca_crt`, `server_crt`, `server_key` | TLS 証明書パス（telemetryd 起動引数 `-ca_crt`, `-server_crt`, `-server_key`） |
| `GNMI\|gnmi` | `client_auth`, `log_level`, `port`, `save_on_set`, `enable_crl`, `crl_expire_duration`, `user_auth` | gNMI サーバ動作パラメータ（telemetryd 起動引数） |
| `GNMI_CLIENT_CERT` | `cert_cname`, `role` | クライアント証明書ごとの RBAC ロール（cert 認証時） |

### 特記事項

- `GNMI` テーブルへの参照は telemetryd 自身がランタイムに直接 CONFIG_DB を読むのではなく、
  `hostcfgd` がテーブル変化を検知 → supervisord.conf 書き換え → telemetry コンテナ再起動という
  間接的なパターン。
- `GNMI|gnmi.save_on_set = true` 時、`Set()` RPC 処理後に `/etc/sonic/config_db.json` への保存
  (`server.go:1057`) が走り、`DBUS_CONFIG_SAVE` カウンタが増分される（`dbus_client.go`）。
  つまり `GNMI` テーブルの設定がカウンタ増分挙動に間接影響する。

---

## 範囲外（誤解されやすい隣接テーブル）

- `COUNTERS_DB` — sonic-gnmi の `sonic_data_client` が gNMI Get/Subscribe の**データソース**として
  読み出す先だが、gnmi-counter（共有メモリカウンタ）の増分ロジックとは無関係。
- `APPL_DB` — gNMI Set で書き込み先になりうるが、カウンタ自体はテーブルを問わず増分される。
