# subscription-config — Phase C 暗黙テーブル参照スキャンノート

対象テーブル: `TELEMETRY_CLIENT|Global` / `TELEMETRY_CLIENT|DestinationGroup_<name>` / `TELEMETRY_CLIENT|Subscription_<name>`
Consumer: `dialout_client.go` (`sonic-gnmi/dialout/dialout_client/dialout_client.go`)
スキャン範囲: `DialOutRun()`, `processTelemetryClientConfig()`, `NewInstance()`, `sonic_db_config/db_config.go` 全行精読

---

## 検出した暗黙参照

### 1. `/var/run/redis/sonic-db/database_config.json` — DB 接続情報ソース

`DialOutRun()` は `sdcfg.GetDbId("CONFIG_DB", ns)`, `sdcfg.GetDbSock("CONFIG_DB", ns)`, `sdcfg.GetDbTcpAddr("CONFIG_DB", ns)`
を呼び出してRedis接続情報を取得する (`dialout_client.go:650-674`)。

`sdcfg` パッケージ (`sonic_db_config/db_config.go:14`) は `SONIC_DB_CONFIG_FILE = "/var/run/redis/sonic-db/database_config.json"`
を参照してDB ID・ソケットパスを解決する。

- **依存**: `database_config.json` が存在・正常でなければ `DialOutRun()` 起動時にエラー終了する。
- **影響範囲**: `CONFIG_DB` 接続と、Subscription の `path_target` による各DB接続の双方に影響。

### 2. `path_target` — 購読先 DB の暗黙参照

`Subscription_<name>` の `path_target` フィールドは接続先 Redis DB 名を示す (`dialout_client.go:599-603`)。

```go
case "path_target":
    cs.prefix = &gpb.Path{
        Target: value,
    }
```

`NewInstance()` (`dialout_client.go:193-201`) で `target` 値に応じて以下のクライアントが選択される:

| `path_target` 値 | 使用クライアント | 暗黙参照 DB |
|---|---|---|
| `"OTHERS"` | `sdc.NewNonDbClient` | Redis DB 非経由（ファイル等） |
| `"OC_YANG"` | `sdc.NewTranslClient` | `database_config.json` 経由で適切な DB |
| それ以外（`APPL_DB`, `CONFIG_DB`, `COUNTERS_DB`, `STATE_DB` 等） | `sdc.NewDbClient` | `database_config.json` で対応する Redis DB |

YANG (`sonic-telemetry_client.yang`) が enum として宣言する値は `APPL_DB / CONFIG_DB / COUNTERS_DB / STATE_DB / OTHERS` の 5 種類。
`APPL_DB` / `CONFIG_DB` / `COUNTERS_DB` / `STATE_DB` はいずれも `sdc.NewDbClient` 経由で `database_config.json` を参照する。

### 3. `paths` フィールド — 購読先テーブル/パスの暗黙依存

`paths` フィールド (`dialout_client.go:604-617`) には購読対象のデータパスをカンマ区切りで指定する。
`ygot.StringToPath` でパース後、`sdc.NewDbClient` の `populateAllDbtablePath` がパスを
実際の Redis テーブルキーに展開する。

- パスで参照するテーブル（例: `COUNTERS/Ethernet*`, `COUNTERS_PORT_NAME_MAP`）が
  対象 DB に存在しない場合、`ValidatePaths()` がエラーを返す可能性がある。
- `paths` の値は `TELEMETRY_CLIENT` テーブルに保持されるが、
  最終的に参照する実データは `path_target` で指定した DB の各テーブルにある。

### 4. `TELEMETRY` テーブル — 姉妹テーブル（dial-in 側）

`TELEMETRY` テーブルは gnmi-server (dial-in) の設定を保持し、`TELEMETRY_CLIENT` テーブル (dial-out) とは独立して動作する。
両テーブルは同一 CONFIG_DB に存在するが、`dialout_client.go` は `TELEMETRY` を直接読まない。

| 参照関係 | 内容 |
|---|---|
| 設計上の姉妹関係 | `TELEMETRY` (dial-in) と `TELEMETRY_CLIENT` (dial-out) は対をなすが、互いに直接参照しない |
| 共通 DB 接続設定 | `database_config.json` を共有するが、設定エントリは独立 |

### 5. 外部 gRPC コレクタ — `dst_addr` が示すエンドポイント

`DestinationGroup_<name>` の `dst_addr` フィールドはダイアルアウト先の gRPC コレクタ (`host:port`) を指定する
(`dialout_client.go:531-543`)。CONFIG_DB の範囲外のネットワークエンドポイントへの暗黙依存であり、
コレクタが到達不能の場合は `NewInstance()` の gRPC 接続フェーズでエラーが発生する。

---

## 暗黙参照サマリ

| 参照先 | 参照機構 | 条件 | evidence |
|---|---|---|---|
| `/var/run/redis/sonic-db/database_config.json` | `sdcfg.GetDbId/GetDbSock/GetDbTcpAddr` | 常時（DB 接続確立に必須） | `db_config.go:14`, `dialout_client.go:650-674` |
| `path_target` 指定の Redis DB（APPL_DB 等） | `sdc.NewDbClient` → `database_config.json` | Subscription の `path_target` が `OTHERS`/`OC_YANG` 以外の場合 | `dialout_client.go:199-200`, `db_client.go:186-207` |
| `paths` で指定するテーブルの実データ | `populateAllDbtablePath` → 対象 DB | Subscription が接続済みの場合 | `db_client.go:204` |
| 外部 gRPC コレクタ (`dst_addr`) | TCP/gRPC ネットワーク接続 | DestinationGroup が有効な場合 | `dialout_client.go:531-543` |
| `TELEMETRY` テーブル（CONFIG_DB） | なし（直接参照なし）; 姉妹テーブルとして設計上関連 | — | YANG 設計 |
