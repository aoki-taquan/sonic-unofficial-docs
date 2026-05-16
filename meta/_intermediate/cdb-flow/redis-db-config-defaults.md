# redis-db-config フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象: `database_config.json` / Redis DB インスタンス・データベース設定

## 調査対象ファイル

- `sonic-swss-common/common/database_config.json` — 配布デフォルト JSON
- `sonic-swss-common/common/dbconnector.h` — DEFAULT_SONIC_DB_CONFIG_FILE 定数、SonicDBConfig クラス
- `sonic-swss-common/common/dbconnector.cpp` — parseDatabaseConfig(), initialize(), initializeGlobalConfig()
- `sonic-buildimage/dockers/docker-database/database_config.json.j2` — Jinja2 テンプレート (実環境)
- `sonic-buildimage/dockers/docker-database/database_global.json.j2` — グローバル設定テンプレート
- `sonic-buildimage/dockers/docker-database/docker-database-init.sh` — 起動スクリプト

---

## ファイルパス デフォルト

### `DEFAULT_SONIC_DB_CONFIG_FILE`

**コード由来デフォルト**: `/var/run/redis/sonic-db/database_config.json`

```cpp
// dbconnector.h:90
static constexpr const char *DEFAULT_SONIC_DB_CONFIG_FILE = "/var/run/redis/sonic-db/database_config.json";
```

`SonicDBConfig::initialize()` 無引数呼び出し時のデフォルトパス。
実体は `docker-database-init.sh` が起動時に `$REDIS_DIR/sonic-db/database_config.json` として生成する（`/etc/sonic/database_config.json` が存在する場合はそれをコピー）。

### `DEFAULT_SONIC_DB_GLOBAL_CONFIG_FILE`

**コード由来デフォルト**: `/var/run/redis/sonic-db/database_global.json`

```cpp
// dbconnector.h:91
static constexpr const char *DEFAULT_SONIC_DB_GLOBAL_CONFIG_FILE = "/var/run/redis/sonic-db/database_global.json";
```

マルチ ASIC / SmartSwitch 環境でのみ生成される。INCLUDES セクションで各 namespace の database_config.json を参照。

### `DEFAULT_UNIXSOCKET`

**コード由来デフォルト**: `/var/run/redis/redis.sock`

```cpp
// dbconnector.h:169 (RedisContext), dbconnector.h:206 (DBConnector)
static constexpr const char *DEFAULT_UNIXSOCKET = "/var/run/redis/redis.sock";
```

---

## INSTANCES フィールド デフォルト

### `redis` インスタンス (通常ノード)

| フィールド | デフォルト値 | 出典 |
|-----------|-------------|------|
| `hostname` | `"127.0.0.1"` | `database_config.json.j2:5` / `docker-database-init.sh:20` |
| `port` | `6379` | `docker-database-init.sh:20` |
| `unix_socket_path` | `/var/run/redis/redis.sock` | `database_config.json.j2:7` |
| `persistence_for_warm_boot` | `"yes"` | `database_config.json.j2:8` |

**注意**: `hostname` は `docker-database-init.sh` が `lo` (グローバル namespace) または `eth0` (サブ namespace) の IP から取得する。取得失敗時は `127.0.0.1` にフォールバック。

### `redis_chassis` インスタンス (VoQ Chassis 専用)

| フィールド | デフォルト値 | 出典 |
|-----------|-------------|------|
| `hostname` | `"redis_chassis.server"` | `database_config.json.j2:13` |
| `port` | `6380` | `database_config.json.j2:14` |
| `unix_socket_path` | `/var/run/redis-chassis/redis_chassis.sock` | `database_config.json.j2:15` |
| `persistence_for_warm_boot` | `"yes"` | `database_config.json.j2:17` |

### `redis_bmp` インスタンス (BMP 専用、非 DPU/BMC)

| フィールド | デフォルト値 | 出典 |
|-----------|-------------|------|
| `hostname` | `"127.0.0.1"` (HOST_IP と同値) | `database_config.json.j2:31` |
| `port` | `6400` (BMP_DB_PORT) | `docker-database-init.sh:49`, `database_config.json.j2:33` |
| `unix_socket_path` | `/var/run/redis/redis_bmp.sock` | `database_config.json.j2:33` |
| `persistence_for_warm_boot` | `"yes"` | `database_config.json.j2:34` |

**DPU デバイス**: `redis_bmp` なし。代わりに `remote_redis` が存在する場合あり (REMOTE_DB_IP/REMOTE_DB_PORT 定義時)。

---

## DATABASES フィールド デフォルト

全 DATABASES エントリは `database_config.json.j2` で固定定義される。各エントリの必須フィールドは `id`, `separator`, `instance` の 3 つ。

### 標準データベース (通常ノード共通)

| DB 名 | id | separator | instance |
|------|----|-----------|----------|
| `APPL_DB` | `0` | `":"` | `redis` |
| `ASIC_DB` | `1` | `":"` | `redis` |
| `COUNTERS_DB` | `2` | `":"` | `redis` |
| `LOGLEVEL_DB` | `3` | `":"` | `redis` |
| `CONFIG_DB` | `4` | `"|"` | `redis` |
| `PFC_WD_DB` | `5` | `":"` | `redis` |
| `FLEX_COUNTER_DB` | `5` | `":"` | `redis` |
| `STATE_DB` | `6` | `"|"` | `redis` |
| `SNMP_OVERLAY_DB` | `7` | `"|"` | `redis` |
| `RESTAPI_DB` | `8` | `"|"` | `redis` |
| `GB_ASIC_DB` | `9` | `":"` | `redis` |
| `GB_COUNTERS_DB` | `10` | `":"` | `redis` |
| `GB_FLEX_COUNTER_DB` | `11` | `":"` | `redis` |
| `CHASSIS_APP_DB` | `12` | `"|"` | `redis_chassis` |
| `CHASSIS_STATE_DB` | `13` | `"|"` | `redis_chassis` |
| `APPL_STATE_DB` | `14` | `":"` | `redis` |

**共有 DB ID**: `PFC_WD_DB` と `FLEX_COUNTER_DB` は共に id=5 を使用 (同一 Redis DB)。

### DPU 追加データベース (DATABASE_TYPE=dpudb 時のみ)

| DB 名 | id | separator | instance | 備考 |
|------|----|-----------|----------|------|
| `DPU_APPL_DB` | `15` | `":"` | `redis` / `remote_redis` | `format: "proto"` 付き |
| `DPU_APPL_STATE_DB` | `16` | `"|"` | `redis` / `remote_redis` | - |
| `DPU_STATE_DB` | `17` | `"|"` | `redis` / `remote_redis` | - |
| `DPU_COUNTERS_DB` | `18` | `":"` | `redis` / `remote_redis` | - |

### BMP データベース (通常ノード、dpudb/bmcdb 以外)

| DB 名 | id | separator | instance |
|------|----|-----------|----------|
| `BMP_STATE_DB` | `20` | `"|"` | `redis_bmp` |

---

## separator の意味

- `":"` — APPL_DB 系、COUNTERS_DB 系等: `TABLE_NAME:ROW_KEY` 形式
- `"|"` — CONFIG_DB, STATE_DB 系等: `TABLE_NAME|ROW_KEY` 形式

`SonicDBConfig::getSeparator()` でアプリが取得する。DB ID でも名前でも取得可能。

---

## parseDatabaseConfig() の必須フィールド検証

```cpp
// dbconnector.cpp:54-55
string hostname = it.value().at("hostname");   // 必須 - なければ domain_error
int port = it.value().at("port");              // 必須 - なければ domain_error
// unix_socket_path はオプション (find() で確認)
auto path = it.value().find("unix_socket_path");
if (path != it.value().end()) { socket = *path; }
```

`unix_socket_path` は任意フィールド。存在しない場合は空文字列となり TCP 接続のみ有効。

---

## 初期化フロー

1. `SonicDBConfig::initialize()` — 単一 DB 設定ファイル読み込み (`m_init` フラグ)
2. `SonicDBConfig::initializeGlobalConfig()` — グローバル設定読み込み (`m_global_init` フラグ)
3. どちらかの初期化前に `getDbInfo()` が呼ばれると `initialize(DEFAULT_SONIC_DB_CONFIG_FILE)` が自動実行

---

## docker-database-init.sh でのデフォルト動作

1. `/etc/sonic/database_config.json` が存在 → そのままコピー
2. 存在しない かつ `/etc/sonic/enable_multidb` あり → `multi_database_config.json.j2` でレンダリング
3. 存在しない かつ `enable_multidb` なし → `database_config.json.j2` でレンダリング

レンダリング変数デフォルト:
- `HOST_IP`: lo の IP アドレス (取得失敗時 `127.0.0.1`)
- `REDIS_PORT`: `6379`
- `BMP_DB_PORT`: `6400`
- `DATABASE_TYPE`: 空文字列 (通常ノード)

---

## 証拠リンク

- `sonic-swss-common/common/dbconnector.h:90-91` — DEFAULT_SONIC_DB_CONFIG_FILE / DEFAULT_SONIC_DB_GLOBAL_CONFIG_FILE
- `sonic-swss-common/common/dbconnector.h:169,206` — DEFAULT_UNIXSOCKET
- `sonic-swss-common/common/dbconnector.cpp:27-87` — parseDatabaseConfig()
- `sonic-swss-common/common/dbconnector.cpp:89-180` — initializeGlobalConfig()
- `sonic-swss-common/common/database_config.json` — 配布デフォルト JSON
- `sonic-buildimage/dockers/docker-database/database_config.json.j2` — 実環境テンプレート
- `sonic-buildimage/dockers/docker-database/docker-database-init.sh` — 初期化スクリプト
