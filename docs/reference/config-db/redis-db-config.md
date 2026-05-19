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
