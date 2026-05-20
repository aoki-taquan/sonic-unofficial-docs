---
title: Redis DB 設定 (database_config.json)
description: "SONiC の Redis インスタンス・データベース構成を定義する database_config.json のリファレンス。インスタンス定義・DB ID マッピング・セパレータ・デフォルト値を網羅する。"
area: reference
verification: code-verified
last_verified: 2026-05-14
sources:
  - repo: sonic-net/sonic-swss-common
    path: common/database_config.json
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
  - repo: sonic-net/sonic-swss-common
    path: common/dbconnector.h
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
  - repo: sonic-net/sonic-swss-common
    path: common/dbconnector.cpp
    ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
  - repo: sonic-net/sonic-buildimage
    path: dockers/docker-database/database_config.json.j2
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
  - repo: sonic-net/sonic-buildimage
    path: dockers/docker-database/docker-database-init.sh
    ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd
related:
  config_db: []
  cli: []
  yang: []
---

# Redis DB 設定 (database_config.json)

## 概要

SONiC は Redis を複数データベースに分割して使用し、その構成を `/var/run/redis/sonic-db/database_config.json` で管理する[^1]。このファイルには **Redis インスタンス定義** (接続先 hostname/port/UNIX ソケット) と **データベース定義** (DB ID・セパレータ・所属インスタンス) が含まれる。

`SonicDBConfig` クラス (`sonic-swss-common`) がこの JSON を解析し、すべての DB 接続を仲介する。アプリケーションは `SonicDBConfig::getDbId()` / `getDbSock()` / `getSeparator()` 等の API を通じて DB 情報を取得する[^2]。

<!-- defaults -->
## コード由来デフォルト値

### ファイルパス定数

| 定数名 | 値 | 出典 |
|-------|----|------|
| `DEFAULT_SONIC_DB_CONFIG_FILE` | `/var/run/redis/sonic-db/database_config.json` | `dbconnector.h:90` |
| `DEFAULT_SONIC_DB_GLOBAL_CONFIG_FILE` | `/var/run/redis/sonic-db/database_global.json` | `dbconnector.h:91` |
| `DEFAULT_UNIXSOCKET` | `/var/run/redis/redis.sock` | `dbconnector.h:169,206` |

`SonicDBConfig::getDbInfo()` 等が初期化前に呼ばれると、`initialize(DEFAULT_SONIC_DB_CONFIG_FILE)` が自動的に実行される[^2]。

### INSTANCES デフォルト値

#### `redis` — 通常ノード主インスタンス

| フィールド | デフォルト値 | 備考 |
|-----------|-------------|------|
| `hostname` | `"127.0.0.1"` | `docker-database-init.sh` が `lo` の IP を取得; 失敗時フォールバック |
| `port` | `6379` | `docker-database-init.sh:20` |
| `unix_socket_path` | `/var/run/redis/redis.sock` | `database_config.json.j2:7` |
| `persistence_for_warm_boot` | `"yes"` | Warm Boot 対応フラグ |

#### `redis_chassis` — VoQ Chassis 専用インスタンス

| フィールド | デフォルト値 | 備考 |
|-----------|-------------|------|
| `hostname` | `"redis_chassis.server"` | VoQ Supervisor の DNS 名 |
| `port` | `6380` | `database_config.json.j2:14` |
| `unix_socket_path` | `/var/run/redis-chassis/redis_chassis.sock` | `database_config.json.j2:15` |

#### `redis_bmp` — BMP 専用インスタンス (通常ノードのみ)

| フィールド | デフォルト値 | 備考 |
|-----------|-------------|------|
| `hostname` | HOST_IP と同値 | `database_config.json.j2:31` |
| `port` | `6400` | `BMP_DB_PORT` 環境変数; `docker-database-init.sh:49` |
| `unix_socket_path` | `/var/run/redis/redis_bmp.sock` | `database_config.json.j2:33` |

`redis_bmp` は `DATABASE_TYPE=dpudb` または `DATABASE_TYPE=bmcdb` の場合は生成されない。

### DATABASES デフォルト定義

すべてのデータベースは `database_config.json.j2` で固定定義される。各エントリに必須のフィールドは `id`、`separator`、`instance` の 3 つ[^2]。

#### 標準データベース (全ノード共通)

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

!!! note "DB ID 共有"
    `PFC_WD_DB` と `FLEX_COUNTER_DB` は共に id=5 を使用し、同一 Redis DB を指す。

#### DPU 追加データベース (`DATABASE_TYPE=dpudb` 時のみ)

| DB 名 | id | separator | instance | 備考 |
|------|----|-----------|----------|------|
| `DPU_APPL_DB` | `15` | `":"` | `redis` / `remote_redis` | `"format": "proto"` 付き |
| `DPU_APPL_STATE_DB` | `16` | `"|"` | `redis` / `remote_redis` | - |
| `DPU_STATE_DB` | `17` | `"|"` | `redis` / `remote_redis` | - |
| `DPU_COUNTERS_DB` | `18` | `":"` | `redis` / `remote_redis` | - |

`REMOTE_DB_IP` / `REMOTE_DB_PORT` が定義されている場合、instance は `remote_redis` に切り替わる。

#### EVENT_DB (通常ノード)

| DB 名 | id | separator | instance |
|------|----|-----------|----------|
| `EVENT_DB` | `19` | `":"` | `redis` |

#### BMP データベース (通常ノード、dpudb/bmcdb 以外)

| DB 名 | id | separator | instance |
|------|----|-----------|----------|
| `BMP_STATE_DB` | `20` | `"|"` | `redis_bmp` |
<!-- /defaults -->

<!-- ordering -->
## 初期化順序依存 (Phase B)

`database_config.json` は CONFIG_DB テーブルではなく、Redis インスタンスと DB ID マッピングを定義するインフラ層ファイルである。ここでの「書込み順依存」は、ファイル生成 → Redis 起動 → アプリ接続 の厳密なシーケンスに関するものである。

### 起動シーケンス

```
docker-database コンテナ起動
  │
  ├─ docker-database-init.sh 実行
  │   ├─ /etc/sonic/database_config.json が存在? → コピー
  │   ├─ /etc/sonic/enable_multidb が存在? → multi_database_config.json.j2 でレンダリング
  │   └─ それ以外 → database_config.json.j2 でレンダリング
  │       └─ 出力: /var/run/redis/sonic-db/database_config.json
  │
  ├─ supervisord が Redis インスタンス起動 (database_config.json のインスタンス定義に基づく)
  │
  └─ 各アプリ (swss / syncd / mgmt 等) が起動
      └─ 最初の DB API 呼び出し時に SonicDBConfig::initialize() が自動実行
          └─ /var/run/redis/sonic-db/database_config.json を読み込む
```

### 検出された順序依存

| # | 依存関係 | 強度 | 根拠 |
|---|----------|------|------|
| 1 | `database_config.json` 生成 → Redis プロセス起動 | **強制先行** | supervisord は `database_config.json` をもとに起動するインスタンスを決定する (`docker-database-init.sh` 全体) |
| 2 | `initialize()` の一度限り実行 → 以降の全 DB API | **強制先行** | `m_init` フラグで二重初期化を防ぐ。再初期化には `reset()` が必要 (`dbconnector.cpp:193-194`) |
| 3 | `initializeGlobalConfig()` → namespace 指定 API | **強制先行** | `validateNamespace()` が `m_global_init` を確認し、未初期化の場合は `SWSS_LOG_THROW` (`dbconnector.cpp:228-231`) |
| 4 | `initialize()` 遅延自動実行 | なし（自動緩和） | `getDbInfo()` / `getDbId()` 等が `m_init == false` のとき自動的に `initialize(DEFAULT_SONIC_DB_CONFIG_FILE)` を呼ぶ (`dbconnector.cpp:253`) |
| 5 | namespace 対応 API: `initializeGlobalConfig()` 要求 | **強制先行** | namespace 非空のとき `m_global_init` が false なら `SWSS_LOG_THROW` で即クラッシュ (`dbconnector.cpp:259`) |
| 6 | VoQ Chassis: `update_chassisdb_config` 実行 → supervisord 設定生成 | **強制先行** | chassis_db を含む/除外した tmp ファイルを経由して supervisord.conf を生成 (`docker-database-init.sh` L67-80) |

### 主要制約詳細

**二重初期化禁止 (依存 #2)**: `SonicDBConfig::initialize()` は `m_init` が真のとき `runtime_error("SonicDBConfig already initialized")` を投げる。アプリがカスタムパスで初期化した後にデフォルト自動初期化が走ることはない（evidence: `dbconnector.cpp:193-194`）。

**グローバル設定未初期化でのクラッシュ (依存 #5)**: マルチ ASIC / SmartSwitch 環境で namespace を指定した API (`getDbId(..., netns)` 等) を `initializeGlobalConfig()` 前に呼ぶと、`SWSS_LOG_THROW` で即座にプロセスが終了する。これはプログラミングエラーを早期に露出させる設計判断（evidence: `dbconnector.cpp:259-261`）。

**database_config.json 生成後の変更は非対応**: `SonicDBConfig` は起動時に一度ファイルを読み込んだあとは再読み込みを行わない。Redis ポートや DB ID を変更する場合はコンテナ再起動が必要（`reset()` + `initialize()` の明示的な再実行、または再起動）。

<!-- evidence: sonic-net/sonic-swss-common/common/dbconnector.cpp L182-204 (initialize()) -->
<!-- evidence: sonic-net/sonic-swss-common/common/dbconnector.cpp L89-180 (initializeGlobalConfig()) -->
<!-- evidence: sonic-net/sonic-swss-common/common/dbconnector.cpp L220-260 (getDbInfo 自動初期化) -->
<!-- evidence: sonic-net/sonic-buildimage/dockers/docker-database/docker-database-init.sh (全体: 生成ロジック) -->

<!-- /ordering -->
<!-- cross-refs -->
## 暗黙参照リソース (Phase C)

`database_config.json` は CONFIG_DB テーブルではなくインフラ層ファイルであるため、
他 CONFIG_DB テーブルへの leafref は存在しない。
ただし `docker-database-init.sh` の起動ロジックおよび `SonicDBConfig` の初期化 API は
以下のファイル・設定を暗黙的に参照する。

| 参照先リソース | 参照タイミング | 依存内容 | 証跡 |
|--------------|--------------|---------|------|
| `/etc/sonic/database_config.json` (オーバーライドファイル) | `docker-database` コンテナ起動時 | 存在する場合はテンプレートレンダリングをスキップしてそのままコピー。存在しない場合のみ `database_config.json.j2` を使用 | `docker-database-init.sh:55-61` |
| `/etc/sonic/enable_multidb` (フラグファイル) | `docker-database` コンテナ起動時 | 存在すると `multi_database_config.json.j2` を使用。複数 ASIC / SmartSwitch 構成を切り替えるスイッチ | `docker-database-init.sh:58-61` |
| `/usr/share/sonic/platform/chassisdb.conf` | `docker-database` コンテナ起動時 | `source` で読み込み、`start_chassis_db` / `chassis_db_address` / `chassis_db_port` を取得。`start_chassis_db=1` 時のみ `CHASSIS_APP_DB` エントリを最終設定に含める | `docker-database-init.sh:77-78`, `docker-database-init.sh:124-127` |
| `/var/run/redis/sonic-db/database_global.json` | `SonicDBConfig::initializeGlobalConfig()` 呼び出し時 | マルチ ASIC / SmartSwitch 環境で namespace 付き API 使用前に必須。未初期化で namespace 付き API を呼ぶと `SWSS_LOG_THROW` で即クラッシュ | `dbconnector.cpp:228-231` |
| `/etc/sonic/database_global.json` (グローバルオーバーライド) | `docker-database` コンテナ起動時 (マルチ ASIC / SmartSwitch のみ) | 存在する場合はテンプレートレンダリングをスキップしてそのままコピー | `docker-database-init.sh:106-109` |
| `NAMESPACE_COUNT` / `NUM_DPU` 環境変数 | `docker-database` コンテナ起動時 | `NAMESPACE_COUNT > 1` または `NUM_DPU > 1` の場合のみ `database_global.json` を生成 | `docker-database-init.sh:104-110` |

### CONFIG_DB テーブルとの間接依存

`database_config.json` 自体は CONFIG_DB に格納されない。ただし `SonicDBConfig` によって
定義された DB ID / インスタンス情報は SONiC の全デーモン (`swss`, `syncd`, `mgmt`, `snmp` 等)
が起動時に依存する基盤層であり、間接的にすべての CONFIG_DB テーブル操作の前提条件となる。

<!-- /cross-refs -->
<!-- failure -->
## 失敗挙動 (Phase D)

`database_config.json` は CONFIG_DB テーブルではなくインフラ層ファイルであり、`SonicDBConfig` クラスが起動時に一度だけ読み込む。読み込み・解析に失敗した場合は例外として呼び出し元に伝播し、キャッチされなければプロセス abort → systemd 再起動という自己回復経路を取る。

### A. ファイル読み込み失敗 (`parseDatabaseConfig`)

| 失敗条件 | 挙動 | evidence |
|---------|------|---------|
| 設定ファイルが存在しない / 開けない (`i.good() == false`) | `SWSS_LOG_ERROR` + `throw runtime_error("Sonic database config file doesn't exist at " + file)` で上位伝播 | `dbconnector.cpp:83-85` |
| `ignore_nonexistent=true` かつファイル不在 (`access() == -1`) | `SWSS_LOG_NOTICE` を出力して `return`（例外なし、エントリ空で続行） | `dbconnector.cpp:33-36` |
| JSON 必須キー欠落 (`domain_error`) | `SWSS_LOG_ERROR` + `throw runtime_error("key doesn't exist in json object ...")` で上位伝播 | `dbconnector.cpp:71-74` |
| その他 JSON 解析例外 | `SWSS_LOG_ERROR` + `throw runtime_error("Sonic database config file syntax error ...")` で上位伝播 | `dbconnector.cpp:76-79` |

### B. 二重初期化 (`initialize`)

`m_init == true` の状態で `initialize()` を呼ぶと `SWSS_LOG_ERROR` + `throw runtime_error("SonicDBConfig already initialized")` が発生する (`dbconnector.cpp:193-194`)。通常の起動フローでは自動初期化 (`m_init == false` のときのみ実行) により二重実行は回避される。

### C. グローバル設定失敗 (`initializeGlobalConfig`)

| 失敗条件 | 挙動 | evidence |
|---------|------|---------|
| グローバル設定ファイルが存在しない | `SWSS_LOG_ERROR` 出力後、**例外なし**で `m_global_init = true` をセットして続行（名前空間情報なしで初期化完了扱い） | `dbconnector.cpp:173-179` |
| `ignore_nonexistent=true` の include ファイルが不在 | `SWSS_LOG_NOTICE` 出力後 `return`（当該エントリをスキップして続行） | `dbconnector.cpp:33-36` |
| 二重初期化 (`m_global_init == true`) | `SWSS_LOG_ERROR` を出力して **早期リターン**（例外なし） | `dbconnector.cpp:96-99` |

### D. DB 名・namespace 解決失敗 (`getDbInfo` / `getRedisInfo` / `getSeparator`)

| 失敗条件 | 挙動 | evidence |
|---------|------|---------|
| namespace 非空かつ `m_global_init == false` | `SWSS_LOG_THROW` でプロセス即 abort（プログラミングエラー扱い） | `dbconnector.cpp:229-231`, `259-260` |
| namespace 名が設定ファイルに存在しない | `SWSS_LOG_THROW("Namespace %s is not a valid namespace ...")` でプロセス即 abort | `dbconnector.cpp:242` |
| DB 名または key が設定ファイルに存在しない | `SWSS_LOG_ERROR` + `throw out_of_range(msg)` で上位伝播 | `dbconnector.cpp:263-275` |

!!! note "SWSS_LOG_THROW vs throw"
    `SWSS_LOG_THROW` は SONiC 独自マクロで `abort()` 相当の即プロセス終了を引き起こす。namespace 解決失敗はこの経路を通り、systemd の `Restart=always` 設定でのみ回復する。

### E. 自己回復経路

- `getDbInfo()` 等のアクセサ API は `m_init == false` のとき自動的に `initialize(DEFAULT_SONIC_DB_CONFIG_FILE)` を呼ぶため、明示的な初期化呼び出しなしでもデフォルトパスからの読み込みが行われる (`dbconnector.cpp:252-253`)。
- `parseDatabaseConfig()` や `initialize()` から `runtime_error` が伝播した場合、各デーモン（`swss`/`syncd`/`mgmt` 等）がキャッチしなければプロセス abort → systemd 再起動 → 再 `initialize()` で自己回復する。
- Redis 接続層（`DBConnector` コンストラクタ）の TCP/UNIX ソケット接続失敗は `system_error` として伝播し、各アプリが個別に処理する (`dbconnector.cpp:589`, `605`)。

> **証跡**: `parseDatabaseConfig()` L27-87、`initialize()` L182-204、`initializeGlobalConfig()` L89-180、`getDbInfo()` L246-278、`getRedisInfo()` L280-310。詳細は `meta/_intermediate/cdb-flow/redis-db-config-failure.md` を参照。

<!-- /failure -->

<!-- constants -->
## ハードコード定数 (Phase E)

実装コードに直接埋め込まれている文字列キー・数値定数・マクロ名を一覧化する。

### JSON 構造キー定数

`parseDatabaseConfig()` が `database_config.json` を解析する際に参照するキー名はすべてハードコードされている (`dbconnector.cpp:45-64`)。

| JSON キー | 用途 | 参照箇所 |
|----------|------|---------|
| `"INSTANCES"` | Redis インスタンス定義ブロック | `dbconnector.cpp:45` |
| `"DATABASES"` | DB ID マッピングブロック | `dbconnector.cpp:59` |
| `"hostname"` | インスタンスの接続先ホスト名 | `dbconnector.cpp:54` |
| `"port"` | インスタンスの TCP ポート番号 | `dbconnector.cpp:55` |
| `"unix_socket_path"` | UNIX ドメインソケットパス (省略可) | `dbconnector.cpp:49-53` |
| `"instance"` | DB エントリが属するインスタンス名 | `dbconnector.cpp:62` |
| `"id"` | Redis DB 番号 (0-20) | `dbconnector.cpp:63` |
| `"separator"` | テーブル名とキーを区切る文字 | `dbconnector.cpp:64` |

`unix_socket_path` は `it.value().find()` で探索されるため省略可能。それ以外の必須フィールドは `at()` で取得されるため、欠落時は `domain_error` が発生する。

### DB ID マクロ定数 (`schema.h`)

`sonic-swss-common/common/schema.h` で定義される DB ID マクロと `database_config.json` の `id` フィールド値の対応。

| マクロ名 | id 値 | `schema.h` 行 |
|---------|-------|--------------|
| `APPL_DB` | `0` | `schema.h:12` |
| `ASIC_DB` | `1` | `schema.h:13` |
| `COUNTERS_DB` | `2` | `schema.h:14` |
| `LOGLEVEL_DB` | `3` | `schema.h:15` |
| `CONFIG_DB` | `4` | `schema.h:16` |
| `PFC_WD_DB` | `5` | `schema.h:17` |
| `FLEX_COUNTER_DB` | `5` | `schema.h:18` (PFC_WD_DB と同 id) |
| `STATE_DB` | `6` | `schema.h:19` |
| `SNMP_OVERLAY_DB` | `7` | `schema.h:20` |
| `RESTAPI_DB` | `8` | `schema.h:21` |
| `GB_ASIC_DB` | `9` | `schema.h:22` |
| `GB_COUNTERS_DB` | `10` | `schema.h:23` |
| `GB_FLEX_COUNTER_DB` | `11` | `schema.h:24` |
| `CHASSIS_APP_DB` | `12` | `schema.h:25` |
| `CHASSIS_STATE_DB` | `13` | `schema.h:26` |
| `APPL_STATE_DB` | `14` | `schema.h:27` |
| `DPU_APPL_DB` | `15` | `schema.h:28` |
| `DPU_APPL_STATE_DB` | `16` | `schema.h:29` |
| `DPU_STATE_DB` | `17` | `schema.h:30` |
| `DPU_COUNTERS_DB` | `18` | `schema.h:31` |
| `EVENT_DB` | `19` | `schema.h:32` |
| `BMP_STATE_DB` | `20` | `schema.h:33` |

### パス・ポート定数 (`dbconnector.h` / `docker-database-init.sh`)

| 定数名 / 変数名 | ハードコード値 | 出典 |
|--------------|-------------|------|
| `SonicDBConfig::DEFAULT_SONIC_DB_CONFIG_FILE` | `/var/run/redis/sonic-db/database_config.json` | `dbconnector.h:90` |
| `SonicDBConfig::DEFAULT_SONIC_DB_GLOBAL_CONFIG_FILE` | `/var/run/redis/sonic-db/database_global.json` | `dbconnector.h:91` |
| `RedisContext::DEFAULT_UNIXSOCKET` | `/var/run/redis/redis.sock` | `dbconnector.h:169,206` |
| `redis_port` (デフォルト) | `6379` | `docker-database-init.sh:20` |
| `redis_port` (DPU インスタンス) | `6381 + DPU_ID` | `docker-database-init.sh:28` |
| `REMOTE_DB_PORT` (DPU リモート) | `6380 + d` | `docker-database-init.sh:40` |
| `BMP_DB_PORT` | `6400` | `docker-database-init.sh:49` |
| `REDIS_DIR` | `/var/run/redis${NAMESPACE_ID}` | `docker-database-init.sh:51` |
| `KEY_DEL_CHUNK_SIZE` | `128` | `dbconnector.cpp:23` (Redis キー一括削除サイズ) |

<!-- evidence: sonic-net/sonic-swss-common/common/schema.h L12-33 (DB ID マクロ定義) -->
<!-- evidence: sonic-net/sonic-swss-common/common/dbconnector.h L90-91,169,206 (パス・ソケット定数) -->
<!-- evidence: sonic-net/sonic-swss-common/common/dbconnector.cpp L45-64 (parseDatabaseConfig JSON キー) -->
<!-- evidence: sonic-net/sonic-buildimage/dockers/docker-database/docker-database-init.sh L20,28,40,49,51 (ポート・パス定数) -->

<!-- /constants -->

<!-- side-effects -->
## 副次 DB 書込 (Phase F)

`database_config.json` は CONFIG_DB テーブルではなくインフラ層ファイルである。`SonicDBConfig` がこのファイルを読み込んだ結果は **プロセス内のインメモリキャッシュ** (`m_inst_info` / `m_db_info` / `m_db_separator`) に格納されるのみで、他のRedis DB への副次書込は発生しない。

| 副次 DB | 書込有無 | 根拠 |
|---------|---------|------|
| CONFIG_DB | なし | `database_config.json` 自体が CONFIG_DB に格納されず、`SonicDBConfig` は CONFIG_DB へ書き込まない (`dbconnector.cpp` 全体でDB書込呼出ゼロ) |
| APPL_DB | なし | `SonicDBConfig` は参照専用クラス。`parseDatabaseConfig()` / `initialize()` 内に Producer・Table・hset・set 呼出なし (`dbconnector.cpp:27-204`) |
| STATE_DB | なし | `SonicDBConfig` は STATE_DB への接続を一切保持しない。起動完了通知を STATE_DB に書き込む仕組みも存在しない |
| ASIC_DB / COUNTERS_DB / FLEX_COUNTER_DB | なし | SAI 非経由。`database_config.json` の変更は orchagent / syncd に伝播しない。SAI ドライバ側の DB ID も `schema.h` マクロで静的に固定 |
| LOGLEVEL_DB | なし | `SonicDBConfig` の動作はログレベル DB を購読・書込しない |

### `reset()` 実行時の副次効果

`SonicDBConfig::reset()` を呼んでインメモリキャッシュをクリアした場合、既存の `DBConnector` インスタンスは **キャッシュ参照を失うが自動切断されない**。以降の `getDbInfo()` 系 API 呼び出しは再初期化をトリガーするか `out_of_range` を発生させる。

| 状況 | 挙動 | evidence |
|------|------|---------|
| `reset()` 後に `initialize()` 再実行 | インメモリキャッシュを新設定で再構築。既存 `DBConnector` の TCP/UNIX 接続は継続されるが、接続先 DB ID が旧設定のまま残る場合は論理不整合が生じる | `dbconnector.cpp:209-218` |
| `reset()` 後に `getDbInfo()` 等を呼ぶ | `m_init == false` のため自動的に `initialize(DEFAULT_SONIC_DB_CONFIG_FILE)` を実行 (デフォルトパスから再読み込み) | `dbconnector.cpp:252-253` |
| `reset()` 後に namespace 指定 API を呼ぶ | `m_global_init == false` のため `SWSS_LOG_THROW` でプロセス即 abort | `dbconnector.cpp:229-231` |

!!! note "実運用での reset() 使用"
    `reset()` はテストコードと一部の設定リロードシナリオ専用と位置付けられる。本番環境での使用は原則 `docker-database` コンテナ再起動で代替する (`docker-database-init.sh` 参照)。

<!-- evidence: sonic-net/sonic-swss-common/common/dbconnector.cpp L209-218 (reset 実装) -->
<!-- evidence: sonic-net/sonic-swss-common/common/dbconnector.cpp L252-253 (自動再初期化) -->
<!-- /side-effects -->

<!-- pubsub -->
## 通信メカニズム (Phase G)

`database_config.json` は CONFIG_DB テーブルではなくインフラ層ファイルであるため、通常の CONFIG_DB テーブルが用いる Redis PUBLISH/SUBSCRIBE メカニズムは **一切使用しない**。`SonicDBConfig` クラスはファイルを起動時に一度読み込んでインメモリキャッシュに格納するのみで、keyspace notification の発行も受信も行わない。

### 変更通知が不要な理由

`database_config.json` が定義するのは **Redis インスタンスと DB ID のマッピング** というインフラ基盤であり、実行時に動的に変化しない前提で設計されている。変更を反映するには Redis インスタンス自体を再起動する必要があるため、pub/sub による差分通知では対応できない。

| 経路 | 採用有無 | 根拠 |
|------|---------|------|
| Redis keyspace notification (PSUBSCRIBE) | **不使用** | CONFIG_DB テーブルでなく、変更を受信するサブスクライバーが存在しない |
| `SubscriberStateTable` / `ConsumerStateTable` | **不使用** | `SonicDBConfig` は DB 接続クライアントを保持しない (`dbconnector.cpp` 全体で Subscribe 呼出ゼロ) |
| `NotificationConsumer` / `NotificationProducer` | **不使用** | 同上 |
| コンテナ再起動による再読み込み | **採用** | `docker-database-init.sh` が生成 → supervisord が Redis 再起動 → 各アプリが `SonicDBConfig::initialize()` で再読み込み |

### 変更反映フロー

```
管理者が /etc/sonic/database_config.json を更新
  ↓
docker restart database  (または config reload 経由)
  ↓
docker-database-init.sh が再実行 → /var/run/redis/sonic-db/database_config.json を再生成
  ↓
supervisord が Redis インスタンスを再起動
  ↓
各アプリが再起動 → SonicDBConfig::initialize() でファイルを再読み込み
（pub/sub チャンネルや keyspace notification は介在しない）
```

<!-- evidence: sonic-net/sonic-swss-common/common/dbconnector.cpp (SonicDBConfig 全体: PUBLISH/SUBSCRIBE 呼出なし) -->
<!-- evidence: sonic-net/sonic-buildimage/dockers/docker-database/docker-database-init.sh (生成・配置ロジック) -->

<!-- /pubsub -->

<!-- platform -->
## プラットフォーム差 (Phase H)

> 調査証跡: `meta/_intermediate/cdb-flow/redis-db-config-platform.md`

`SonicDBConfig` クラス自体はプラットフォーム識別文字列 (`broadcom` / `mellanox` 等) を一切参照しない。プラットフォーム差はすべて `docker-database-init.sh` が生成する `database_config.json` の **内容** の差として現れ、`SonicDBConfig` はそのファイルを単純に読み込む。

### `DATABASE_TYPE` 環境変数による構成分岐

`docker-database-init.sh` は `DATABASE_TYPE` 環境変数に応じて生成するテンプレートと起動経路を分岐させる。

| `DATABASE_TYPE` | 起動文脈 | 生成内容 | 特殊処理 |
|-----------------|---------|---------|---------|
| `""` (未設定) | 通常ノード / multi-ASIC host namespace | `database_config.json.j2` | 標準構成 |
| `dpudb` | SmartSwitch NPU から見た DPU 用 DB | `database_config.json.j2` (DPU エントリ付き) | `host_ip=169.254.200.254`、`redis_port=6381+DPU_ID` |
| `bmcdb` | BMC 搭載ノード | `database_config.json.j2` | BMP DB エントリ除外 |
| `chassisdb` | VoQ Chassis Supervisor 専用 DB コンテナ | supervisord config のみ生成して `exit 0` | `update_chassisdb_config -k` で chassis 専用設定を保持 |

<!-- evidence: sonic-net/sonic-buildimage/dockers/docker-database/docker-database-init.sh L22-46 (DATABASE_TYPE 分岐) -->
<!-- evidence: sonic-net/sonic-buildimage/dockers/docker-database/docker-database-init.sh L84-100 (chassisdb 分岐) -->

### `NAMESPACE_ID` による multi-ASIC 対応

`NAMESPACE_ID` が空の場合は host namespace として `lo` (loopback) を使用し REDIS_DIR は `/var/run/redis/sonic-db/`。非空 (`asic0` 等) の場合は ASIC namespace 専用コンテナとして `eth0` を使用し REDIS_DIR は `/var/run/redisasic0/sonic-db/` 等になる。

`database_global.json` の生成は `NAMESPACE_ID == "" && DATABASE_TYPE == "" && (NAMESPACE_COUNT > 1 || NUM_DPU > 1)` の条件を満たす場合のみ行われる。

<!-- evidence: sonic-net/sonic-buildimage/dockers/docker-database/docker-database-init.sh L5-9 (INTFC 分岐) -->
<!-- evidence: sonic-net/sonic-buildimage/dockers/docker-database/docker-database-init.sh L104-110 (database_global.json 生成条件) -->

### VoQ Chassis: `chassisdb.conf` によるエントリ制御

プラットフォームが VoQ Chassis の場合、`/usr/share/sonic/platform/chassisdb.conf` が `start_chassis_db` / `chassis_db_address` / `chassis_db_port` を定義する。

- `start_chassis_db=1`: `CHASSIS_APP_DB` / `CHASSIS_STATE_DB` エントリを最終 `database_config.json` に含める
- `start_chassis_db=0` (デフォルト / 非 VoQ): `update_chassisdb_config -d` で chassis エントリを削除

VoQ ラインカードでは Redis の **protected mode が無効化** される。ラインカード外部の midplane ネットワーク越しに supervisor の `redis_chassis` への接続を許可するためである。

<!-- evidence: sonic-net/sonic-buildimage/dockers/docker-database/docker-database-init.sh L74-78 (chassisdb.conf 読み込み) -->
<!-- evidence: sonic-net/sonic-buildimage/dockers/docker-database/docker-database-init.sh L117-120 (linecard protected mode 無効化) -->

### 構成別まとめ

| 構成 | `database_config.json` の差異 | `database_global.json` 生成 |
|------|------------------------------|---------------------------|
| single-ASIC (T0/T1) | 標準テンプレート | なし |
| multi-ASIC (複数 NPU) | host namespace: 標準 + global。asicN namespace: 標準のみ | host namespace のみ生成 |
| VoQ Chassis (line card) | chassis エントリ除外 / protected mode 無効 | なし (line card は NAMESPACE_COUNT 非対象) |
| VoQ Chassis (supervisor) | `chassisdb` 専用経路 (`exit 0`) | なし |
| SmartSwitch (DPU) | `dpudb` エントリ付き / ポート `6381+DPU_ID` | `NUM_DPU > 1` 時に host 側で生成 |
| BMC 搭載ノード | BMP DB エントリ除外 | なし |

<!-- /platform -->

## separator の役割

`separator` はキー文字列でテーブル名と行キーを区切る文字:

- `":"` — `TABLE_NAME:ROW_KEY` 形式 (APPL_DB 系、COUNTERS_DB 系)
- `"|"` — `TABLE_NAME|ROW_KEY` 形式 (CONFIG_DB、STATE_DB 系)

`SonicDBConfig::getSeparator()` で DB 名または DB ID から取得できる[^2]。

## unix_socket_path の扱い

`parseDatabaseConfig()` では `unix_socket_path` は任意フィールドとして扱われる[^2]:

```cpp
// dbconnector.cpp:49-53
auto path = it.value().find("unix_socket_path");
if (path != it.value().end()) {
    socket = *path;
}
```

`unix_socket_path` が存在しない場合、socket は空文字列となり TCP 接続のみ有効になる。

## 初期化フロー

```
docker-database-init.sh
  │
  ├─ /etc/sonic/database_config.json が存在?
  │    はい → コピー
  │    いいえ → /etc/sonic/enable_multidb が存在?
  │                はい → multi_database_config.json.j2 でレンダリング
  │                いいえ → database_config.json.j2 でレンダリング
  │
  └─ 出力先: /var/run/redis/sonic-db/database_config.json
```

アプリ側では `SonicDBConfig::initialize()` がこのファイルを読み込む。マルチ ASIC / SmartSwitch 環境では `SonicDBConfig::initializeGlobalConfig()` が `database_global.json` も読み込み、namespace ごとの DB 情報をマッピングする[^2]。

## 関連リファレンス

- C++ API: `swsscommon::SonicDBConfig` (`sonic-swss-common`)
- Python API: `from swsscommon import swsscommon; swsscommon.SonicDBConfig.load_sonic_db_config()`

## 引用元

[^1]: `sonic-net/sonic-swss-common` `common/database_config.json` — 配布デフォルト JSON。<https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/database_config.json>

[^2]: `sonic-net/sonic-swss-common` `common/dbconnector.h` / `dbconnector.cpp` — `SonicDBConfig` クラス、`DEFAULT_SONIC_DB_CONFIG_FILE` 定数、`parseDatabaseConfig()` 実装。<https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/dbconnector.h>

[^3]: `sonic-net/sonic-buildimage` `dockers/docker-database/database_config.json.j2` — 実環境 Jinja2 テンプレート。<https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/dockers/docker-database/database_config.json.j2>

[^4]: `sonic-net/sonic-buildimage` `dockers/docker-database/docker-database-init.sh` — docker-database 起動スクリプト、ファイル生成ロジック。<https://github.com/sonic-net/sonic-buildimage/blob/9ea932ec2e18f35e58268ec2e4456b1d4afd65cd/dockers/docker-database/docker-database-init.sh>
