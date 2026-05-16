# gnmi-counter — Phase A デフォルト調査メモ

## 調査対象

- `sonic-gnmi/common_utils/context.go` — CounterType 定義・IncCounter/InitCounters 実装
- `sonic-gnmi/common_utils/shareMem.go` — 共有メモリ読み書き実装
- `sonic-gnmi/gnmi_dump/gnmi_dump.go` — カウンタ読み出しツール
- `sonic-gnmi/gnmi_server/server.go` — GNMI_GET/SET/BYPASS カウンタ増減箇所
- `sonic-gnmi/sonic_service_client/dbus_client.go` — DBUS/GNOI/GNSI カウンタ増減箇所
- `sonic-gnmi/pkg/bypass/bypass.go` — GNMI_SET_BYPASS 発生条件
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-gnmi.yang` — CONFIG_DB YANG 定義

## CounterType 列挙型（context.go, iota 順）

| index | 定数名 | String() |
|-------|-------|---------|
| 0 | `GNMI_GET` | "GNMI get" |
| 1 | `GNMI_GET_FAIL` | "GNMI get fail" |
| 2 | `GNMI_SET` | "GNMI set" |
| 3 | `GNMI_SET_FAIL` | "GNMI set fail" |
| 4 | `GNMI_SET_BYPASS` | "GNMI set bypass" |
| 5 | `GNOI_REBOOT` | "GNOI reboot" |
| 6 | `GNOI_FACTORY_RESET` | "GNOI Factory Reset" |
| 7 | `GNOI_OS_INSTALL` | "GNOI OS Install" |
| 8 | `GNOI_HEALTHZ_ACK` | "GNOI Healthz Ack" |
| 9 | `GNOI_HEALTHZ_CHECK` | "GNOI Healthz Check" |
| 10 | `GNOI_HEALTHZ_COLLECT` | "GNOI Healthz Collect" |
| 11 | `GNSI_CREDZ_SET` | "GNSI Credz Set" |
| 12 | `GNSI_CREDZ_CHECKPOINT` | "GNSI Credz Checkpoint" |
| 13 | `DBUS` | "DBUS" |
| 14 | `DBUS_FAIL` | "DBUS fail" |
| 15 | `DBUS_APPLY_PATCH_DB` | "DBUS apply patch db" |
| 16 | `DBUS_APPLY_PATCH_YANG` | "DBUS apply patch yang" |
| 17 | `DBUS_CREATE_CHECKPOINT` | "DBUS create checkpoint" |
| 18 | `DBUS_DELETE_CHECKPOINT` | "DBUS delete checkpoint" |
| 19 | `DBUS_CONFIG_SAVE` | "DBUS config save" |
| 20 | `DBUS_CONFIG_RELOAD` | "DBUS config reload" |
| 21 | `DBUS_STOP_SERVICE` | "DBUS stop service" |
| 22 | `DBUS_RESTART_SERVICE` | "DBUS restart service" |
| 23 | `DBUS_FILE_STAT` | "DBUS file stat" |
| 24 | `DBUS_FILE_DOWNLOAD` | "DBUS file download" |
| 25 | `DBUS_FILE_REMOVE` | "DBUS file remove" |
| 26 | `DBUS_IMAGE_DOWNLOAD` | "DBUS image download" |
| 27 | `DBUS_IMAGE_INSTALL` | "DBUS image install" |
| 28 | `DBUS_IMAGE_LIST` | "DBUS image list" |
| 29 | `DBUS_IMAGE_ACTIVATE` | "DBUS image activate" |
| 30 | `DBUS_DOCKER_LOAD` | "DBUS docker load" |
| 31 | `DBUS_CONFIG_REPLACE` | "DBUS config replace" |
| 32 | `COUNTER_SIZE` | （番兵、配列サイズ指定用） |

## 共有メモリ仕様（shareMem.go）

- `memKey = 7749`（SysV IPC キー、固定値）
- `memSize = 1024`（バイト。uint64 × 128 カウンタ分まで格納可能）
- `memMode = 0x380`（O_RDWR | IPC_CREAT）
- 現在の `COUNTER_SIZE = 32`（index 0-31）。残り 96 スロット空き
- 初期化: `InitCounters()` がサーバー起動時（`NewServer` L528）に全カウンタを 0 にクリア → 共有メモリに書き込み
- 更新: `IncCounter(cnt)` は `atomic.AddUint64` で増分後、`SetMemCounters` で全カウンタを共有メモリに同期書き込み（ロックなし、uint64 アトミック保証）

## IncCounter 呼び出し箇所一覧

### server.go（gnmi_server）

| 行 | カウンタ | 発生条件 |
|----|---------|---------|
| 121, 128, 136 | `GNMI_GET_FAIL` | `handleOperationalGet` 内エラー（3 経路） |
| 930 | `GNMI_GET` | `Get()` RPC 受信時（成否に関わらず） |
| 933, 955, 1015, 1022, 1027 | `GNMI_GET_FAIL` | `Get()` 内各エラー経路（5 箇所） |
| 1075 | `GNMI_SET` | `Set()` RPC 受信時（成否に関わらず） |
| 1077, 1130, 1138, 1150, 1158, 1165, 1206 | `GNMI_SET_FAIL` | `Set()` 内各エラー経路（7 箇所） |
| 1141 | `GNMI_SET_BYPASS` | bypass 高速パス適用成功時 |

### dbus_client.go（sonic_service_client）

| カウンタ | 発生条件 |
|---------|---------|
| `DBUS` | `systemctlAction` 開始時 |
| `DBUS_FAIL` | `systemctlAction` 各エラー経路（9 箇所） |
| `DBUS_CONFIG_RELOAD` | `ConfigReload()` 開始時 |
| `DBUS_CONFIG_REPLACE` | `ConfigReplace()` 開始時 |
| `DBUS_CONFIG_SAVE` | `ConfigSave()` 開始時 |
| `DBUS_APPLY_PATCH_YANG` | `ApplyPatchYang()` 開始時 |
| `DBUS_APPLY_PATCH_DB` | `ApplyPatchDb()` 開始時 |
| `DBUS_CREATE_CHECKPOINT` | `CreateCheckPoint()` 開始時 |
| `DBUS_DELETE_CHECKPOINT` | `DeleteCheckPoint()` 開始時 |
| `DBUS_STOP_SERVICE` | `StopService()` 開始時 |
| `DBUS_RESTART_SERVICE` | `RestartService()` 開始時 |
| `DBUS_FILE_STAT` | `GetFileStat()` 開始時 |
| `DBUS_FILE_DOWNLOAD` | `DownloadFile()` 開始時 |
| `DBUS_FILE_REMOVE` | `RemoveFile()` 開始時 |
| `DBUS_IMAGE_DOWNLOAD` | `DownloadImage()` 開始時 |
| `DBUS_IMAGE_INSTALL` | `InstallImage()` 開始時 |
| `DBUS_IMAGE_LIST` | `GetDockerImages()` 開始時 |
| `DBUS_IMAGE_ACTIVATE` | `ActivateImage()` 開始時 |
| `DBUS_DOCKER_LOAD` | `LoadDocker()` 開始時 |
| `GNOI_FACTORY_RESET` | `FactoryReset()` 開始時 |
| `GNOI_OS_INSTALL` | `InstallOS()` 開始時 |
| `GNOI_HEALTHZ_CHECK` | `HealthzGet()` 開始時 |
| `GNOI_HEALTHZ_COLLECT` | `HealthzArtifact()` 開始時 |
| `GNOI_HEALTHZ_ACK` | `HealthzAcknowledgeAlarm()` 開始時 |
| `GNSI_CREDZ_SET` | `CanaryPush/CanaryRollback/CredentialInstall` 開始時（3 箇所） |
| `GNSI_CREDZ_CHECKPOINT` | `CanaryActivate/CanaryRevert/SaveCheckpoint` 開始時（3 箇所） |

## Dead Counter（定義されているが未使用）

| 定数名 | 理由 |
|--------|------|
| `GNOI_REBOOT` | `gnoi_system.go` に Reboot 実装はあるが `IncCounter(GNOI_REBOOT)` は呼ばれない（コードギャップ） |

## GNMI_SET_BYPASS 発生条件詳細（bypass.go）

bypass 高速パスが適用される条件（ALL が true の場合のみ）:
1. gRPC メタデータに `x-sonic-ss-bypass-validation: true` が存在
2. `DEVICE_METADATA|localhost.hwsku` が許可プレフィクスと前方一致: `Cisco-8102`, `Cisco-8101`, `Cisco-8223`
3. 操作対象テーブルが allowlist に存在: `VNET`, `VNET_ROUTE_TUNNEL`, `VLAN_SUB_INTERFACE`, `ACL_RULE`, `BGP_PEER_RANGE`

## 初期値・リセット挙動

| 種類 | 内容 |
|------|------|
| 起動時初期値 | `InitCounters()` で全 32 カウンタを `uint64(0)` にリセット |
| 永続化 | なし。共有メモリは揮発性（プロセス再起動・システム再起動でクリア） |
| warm-reboot | `telemetryd` 再起動時に `NewServer` → `InitCounters` → 全カウンタ 0 リセット |
| counter オーバーフロー | `uint64` の最大値（約 1.8 × 10^19）に達すると 0 にラップアラウンド。実運用でのオーバーフローはほぼ発生しない |
| 読み取り方法 | `gnmi_dump` ツール（`gnmi_dump.go`）が `GetMemCounters` で読み出し、key=CounterType.String()、value=uint64 で表示 |
