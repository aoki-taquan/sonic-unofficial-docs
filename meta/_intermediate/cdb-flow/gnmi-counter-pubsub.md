# gNMI 内部リクエストカウンタ — 通信メカニズム (Phase G) 解析メモ

対象: `telemetryd` (sonic-gnmi) の共有メモリカウンタ（SysV SHM key=7749）とその周辺通信経路。

ソース確認:
- `sonic-gnmi/common_utils/context.go` — `IncCounter` / `InitCounters` / `SetMemCounters` 呼び出し
- `sonic-gnmi/common_utils/shareMem.go` — `SetMemCounters` / `GetMemCounters` SysV SHM I/O
- `sonic-gnmi/gnmi_dump/gnmi_dump.go` — `GetMemCounters` ポーリング読み取り
- `sonic-gnmi/common_utils/notification_producer.go` — `NotificationProducer.Send()` → Redis `PUBLISH`
- `sonic-gnmi/gnmi_server/gnoi_system.go` — `sendRebootReqOnNotifCh()` / `Reboot_Request_Channel` / `Reboot_Response_Channel`

## 1. カウンタ本体の通信方式 — SysV 共有メモリ (Redis pub/sub 非使用)

共有メモリカウンタは Redis を **全く使わない**:

| 操作 | 関数 | 方式 |
|------|------|------|
| カウンタ増分 | `IncCounter()` → `atomic.AddUint64` → `SetMemCounters()` | SysV SHM `shmget` + `shmat` 直書き |
| カウンタ初期化 | `InitCounters()` → `SetMemCounters()` | 同上 |
| カウンタ読み取り | `gnmi_dump` の `GetMemCounters()` | SysV SHM `shmget` + `shmat` 直読み |

`SetMemCounters` / `GetMemCounters` は `syscall.SYS_SHMGET` / `syscall.SYS_SHMAT` を直接呼ぶ純粋な Go 実装であり、`redis.Publish` / `redis.Subscribe` は一切使わない (`shareMem.go`)。

`gnmi_dump` は 1 回の `GetMemCounters` → 全 32 スロットを標準出力に出力して終了する。継続購読・keyspace 通知のリスンは行わない。

## 2. gNOI Reboot 通知経路 — NotificationProducer → STATE_DB

カウンタ自体とは独立して、`telemetryd` が gNOI Reboot RPC (`Reboot` / `RebootStatus` / `CancelReboot`) を処理する際に Redis の `PUBLISH` / `SUBSCRIBE` を使う唯一の経路がある。

```
gNOI クライアント ──gRPC Reboot RPC──▶ telemetryd (gnoi_system.go)
                                             │
                          NewNotificationProducer("Reboot_Request_Channel")
                                             │
                                             ▼
                                  STATE_DB PUBLISH Reboot_Request_Channel
                                       [JSON payload: op / data / MESSAGE=reqStr]
                                             │
                                             ▼
                              sonic-host-services / hostcfgd
                                  (Reboot_Response_Channel に応答)
                                             │
                          sc.Subscribe(ctx, "Reboot_Response_Channel")
                                             │
                                             ▼
                                telemetryd が応答を受信して gRPC 応答を返す
```

### 定数 (`gnoi_system.go:23-31`)

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `rebootReqCh` | `"Reboot_Request_Channel"` | `NotificationProducer` で PUBLISH するチャンネル名 |
| `rebootRespCh` | `"Reboot_Response_Channel"` | `redis.Subscribe` で購読するレスポンスチャンネル名 |
| `dataMsgFld` | `"MESSAGE"` | JSON ペイロードのフィールドキー |
| `notificationTimeout` | `10 * time.Second` | レスポンス待機タイムアウト |

操作ごとのチャンネルキー (`rebootKey` / `rebootStatusKey` / `rebootCancelKey`) は JSON ペイロードの `op` フィールドで区別され、チャンネル名は `Reboot_Request_Channel` 固定 (`gnoi_system.go:148`)。

### このパスとカウンタの関係

- `GNOI_REBOOT` カウンタ (index 5) は **dead counter** — `Reboot()` RPC 実装内に `IncCounter(GNOI_REBOOT)` が存在しないため、Reboot 送受信があっても 0 のまま (`gnoi_system.go` 全体確認)。
- Notification 送受信が成功・失敗しても `GNMI_GET_FAIL` / `GNMI_SET_FAIL` は増分されない（Reboot は gNOI RPC のため `Get()` / `Set()` カウンタと無関係）。

## 3. TELEMETRY_CONNECTIONS — 直接 HSET/DEL (pub/sub なし)

Subscribe セッション管理で使う STATE_DB `TELEMETRY_CONNECTIONS` テーブルも Redis `PUBLISH` を使わない。`HSet(table, key, "active")` / `HDel(table, key)` の直接操作のみ (`connection_manager.go:116,127`)。詳細は `gnmi-counter-side-effects.md` 参照。

## 4. ConfigSave 連鎖 (`GNMI|gnmi.save_on_set=true` 時)

`Set()` RPC 処理後に `ConfigSave()` → `dbus_client.go` 経由で systemd DBus API を呼ぶ (`server.go:1057`)。これは DBus (IPC) であって Redis pub/sub ではない。`DBUS_CONFIG_SAVE` カウンタが増分されるのみ。

## 5. サマリ

| 観点 | 内容 |
|------|------|
| カウンタ書込方式 | SysV 共有メモリ直書き（Redis pub/sub 非使用） |
| カウンタ読取方式 | SysV 共有メモリ直読み（`gnmi_dump` polling、継続購読なし） |
| Redis PUBLISH | gNOI Reboot のみ: `Reboot_Request_Channel` へ JSON メッセージを送信 |
| Redis SUBSCRIBE | gNOI Reboot のみ: `Reboot_Response_Channel` を `10s` タイムアウトで待機 |
| keyspace 通知 | 未使用（書き手・読み手ともに keyspace notification を利用しない） |
| ProducerStateTable / ConsumerStateTable | 未使用 |
| SubscriberStateTable | 未使用 |
| TELEMETRY_CONNECTIONS 書込 | 直接 HSET/HDel（Subscribe セッション管理用、pub/sub なし） |
| 書き手 DB | STATE_DB（`Reboot_Request_Channel` 送信先） |
| 読み手 DB | STATE_DB（`Reboot_Response_Channel` 受信元） |

## 6. Evidence

- `sonic-gnmi/common_utils/shareMem.go` — `SetMemCounters` / `GetMemCounters`: `syscall.SYS_SHMGET` / `SYS_SHMAT` 直接呼び出し、Redis なし
- `sonic-gnmi/common_utils/context.go:173-183` — `InitCounters` / `IncCounter`: `SetMemCounters` を呼ぶのみ、戻り値無視
- `sonic-gnmi/gnmi_dump/gnmi_dump.go:17-24` — `GetMemCounters` 1 回読み出して標準出力、継続なし
- `sonic-gnmi/common_utils/notification_producer.go:91` — `n.rc.Publish(ctx, n.ch, val)` — STATE_DB への PUBLISH
- `sonic-gnmi/gnmi_server/gnoi_system.go:27-31` — 定数 `rebootReqCh = "Reboot_Request_Channel"`, `rebootRespCh = "Reboot_Response_Channel"`, `notificationTimeout = 10s`
- `sonic-gnmi/gnmi_server/gnoi_system.go:116-129` — `sendRebootReqOnNotifCh()`: `NewNotificationProducer(rebootReqCh)` + `sc.Subscribe(ctx, rebootRespCh)` の Request/Response パターン
- `sonic-gnmi/gnmi_server/connection_manager.go:116,127` — `HSet` / `HDel` 直接操作（`TELEMETRY_CONNECTIONS`、pub/sub なし）
