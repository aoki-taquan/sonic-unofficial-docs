---
title: swss-common データベース設定（database_config.json）
area: internals
tags: [swss-common, database, configuration, redis, internal]
description: database_config.json が必須となった経緯と DEFAULT_UNIXSOCKET 廃止、非標準環境での読み込みパス指定方法。
source_issues:
  - https://github.com/sonic-net/sonic-swss-common/issues/322
sources:
- repo: sonic-net/sonic-swss-common
  path: common/dbconnector.h
  ref: master
- repo: sonic-net/sonic-swss-common
  path: common/dbconnector.cpp
  ref: master
- repo: sonic-net/sonic-swss-common
  path: common/database_config.json
  ref: master
verification: code-verified
last_verified: 2026-06-04
---

# swss-common データベース設定（database_config.json）

## 概要

`sonic-swss-common` は [Redis](../reference/glossary.md#term-redis) への接続情報を `database_config.json` から読み取る設計に統一されており、かつての `DEFAULT_UNIXSOCKET` ベースの暗黙フォールバック接続は廃止されている。デフォルトの読み込みパスはコード上の定数 `DEFAULT_SONIC_DB_CONFIG_FILE` で固定されている[^default-const]。

[^default-const]: `common/dbconnector.h` の `SonicDBConfig` クラスは `static constexpr const char *DEFAULT_SONIC_DB_CONFIG_FILE = "/var/run/redis/sonic-db/database_config.json";` を宣言し、`initialize()` の引数デフォルトとしてこの定数を使う ([sonic-swss-common common/dbconnector.h L90-L92](https://github.com/sonic-net/sonic-swss-common/blob/master/common/dbconnector.h#L90-L92))。

## database_config.json の役割

`database_config.json` は `swss-common` が使用する Redis データベースの接続設定を定義するファイルである。標準的な [SONiC](../reference/glossary.md#term-sonic) イメージでは `/var/run/redis/sonic-db/database_config.json` に配置される[^default-const]。リポジトリにもリファレンス用の最小構成 (`common/database_config.json`) が同梱されている[^repo-sample]。

[^repo-sample]: swss-common リポジトリ内のサンプル: [sonic-swss-common common/database_config.json](https://github.com/sonic-net/sonic-swss-common/blob/master/common/database_config.json)。

```json
{
    "INSTANCES": {
        "redis": {
            "hostname" : "127.0.0.1",
            "port" : 6379,
            "unix_socket_path" : "/var/run/redis/redis.sock"
        }
    },
    "DATABASES": {
        "APPL_DB": {
            "id" : 0,
            "separator": ":",
            "instance" : "redis"
        },
        "CONFIG_DB": {
            "id" : 4,
            "separator": "|",
            "instance" : "redis"
        }
    },
    "VERSION": "1.0"
}
```

## DEFAULT_UNIXSOCKET の廃止経緯

以前の `swss-common` では `database_config.json` が無い場合に `DEFAULT_UNIXSOCKET` (`/var/run/redis/redis.sock`) で暗黙フォールバック接続を行うコードパスが存在した。しかし issue [#322](https://github.com/sonic-net/sonic-swss-common/issues/322) で「DB 接続設定はすべて `database_config.json` から読み取る方針に統一する」ことが合意され、現在は `SonicDBConfig::initialize()` を経由して JSON を読まないと `DBConnector` 系コンストラクタが利用できない設計になっている[^init-required]。`RedisContext::DEFAULT_UNIXSOCKET` という定数自体は `RedisContext` 内部のデフォルト値として残るが、ユーザーが意識する暗黙フォールバックとしての役割は持たない[^default-unixsocket-const]。

[^init-required]: `common/dbconnector.cpp` の `DBConnector` 各コンストラクタは `SonicDBConfig::isInit()` が false の場合に `initialize(DEFAULT_SONIC_DB_CONFIG_FILE)` を呼ぶ ([sonic-swss-common common/dbconnector.cpp L250-L290](https://github.com/sonic-net/sonic-swss-common/blob/master/common/dbconnector.cpp#L250-L290))。ファイルが無ければここで例外が投げられる。

[^default-unixsocket-const]: `RedisContext` クラスは `static constexpr const char *DEFAULT_UNIXSOCKET = "/var/run/redis/redis.sock";` を保持するが、`SonicDBConfig` 初期化失敗時のフォールバック接続には使われない ([sonic-swss-common common/dbconnector.h L169](https://github.com/sonic-net/sonic-swss-common/blob/master/common/dbconnector.h#L169))。

## 非標準環境での利用

公式 SONiC コンテナイメージを使用しない場合（カスタムコンテナ、開発環境、単体テスト等）、`database_config.json` を以下のいずれかの方法で読み込ませる必要がある。`swss-common` 自体には設定ファイル位置を切り替える環境変数は無い[^no-env-var]ため、ファイル配置 または 明示的初期化呼び出し のいずれかが必要となる。

[^no-env-var]: `common/dbconnector.{h,cpp}` 内に `getenv("SONIC_DB_CONFIG_FILE")` のような環境変数読み取りは存在せず、`DEFAULT_SONIC_DB_CONFIG_FILE` 定数のみがデフォルトパスとして使われる ([sonic-swss-common common/dbconnector.h L90](https://github.com/sonic-net/sonic-swss-common/blob/master/common/dbconnector.h#L90), [common/dbconnector.cpp L240-L475](https://github.com/sonic-net/sonic-swss-common/blob/master/common/dbconnector.cpp#L240-L475))。

### デフォルトパスに配置する

最も単純な方法は、デフォルトの読み込みパス `/var/run/redis/sonic-db/database_config.json` にファイルを配置することである。これにより `DBConnector` 初回利用時に自動的に読み込まれる[^init-required]。

### 明示的に初期化する（推奨）

任意の場所に置いた JSON を読ませる場合は、`DBConnector` を生成する前に `SonicDBConfig` の初期化 API をアプリケーション側から呼ぶ[^init-api]。

[^init-api]: C++ 側は `SonicDBConfig::initialize(file)` ([common/dbconnector.h L92](https://github.com/sonic-net/sonic-swss-common/blob/master/common/dbconnector.h#L92))。Python 側は SWIG バインディングが提供する `SonicDBConfig.load_sonic_db_config(path)` ([common/dbconnector.h L96-L99](https://github.com/sonic-net/sonic-swss-common/blob/master/common/dbconnector.h#L96-L99))。

```cpp
// C++ 例
swss::SonicDBConfig::initialize("/path/to/database_config.json");
swss::DBConnector db("APPL_DB", 0);
```

```python
# Python 例
from swsscommon import swsscommon
swsscommon.SonicDBConfig.load_sonic_db_config("/path/to/database_config.json")
db = swsscommon.DBConnector("APPL_DB", 0)
```

### 単体テスト用の最小設定例

```json
{
    "INSTANCES": {
        "redis": {
            "hostname" : "127.0.0.1",
            "port" : 6379,
            "unix_socket_path" : "/tmp/redis.sock"
        }
    },
    "DATABASES": {
        "APPL_DB": { "id": 0, "separator": ":", "instance": "redis" },
        "ASIC_DB": { "id": 1, "separator": ":", "instance": "redis" },
        "COUNTERS_DB": { "id": 2, "separator": ":", "instance": "redis" },
        "LOGLEVEL_DB": { "id": 3, "separator": ":", "instance": "redis" },
        "CONFIG_DB": { "id": 4, "separator": "|", "instance": "redis" },
        "PFC_WD_DB": { "id": 5, "separator": ":", "instance": "redis" },
        "STATE_DB": { "id": 6, "separator": "|", "instance": "redis" },
        "SNMP_OVERLAY_DB": { "id": 7, "separator": "|", "instance": "redis" }
    },
    "VERSION": "1.0"
}
```

## マルチ DB / マルチネームスペース構成

大規模 SONiC 構成（chassis / multi-[ASIC](../reference/glossary.md#term-asic)）では、複数の Redis インスタンスに DB を分散配置できる。`database_config.json` の `INSTANCES` セクションに複数のインスタンスを定義し、各 DB を異なるインスタンスに割り当てる。さらにネームスペース横断の構成は `database_global.json`（デフォルト `/var/run/redis/sonic-db/database_global.json`）から読み込まれる[^global-config]。

[^global-config]: `SonicDBConfig::initializeGlobalConfig()` は `DEFAULT_SONIC_DB_GLOBAL_CONFIG_FILE = "/var/run/redis/sonic-db/database_global.json"` をデフォルトとして使う ([sonic-swss-common common/dbconnector.h L91, L102](https://github.com/sonic-net/sonic-swss-common/blob/master/common/dbconnector.h#L91-L102))。

```json
{
    "INSTANCES": {
        "redis": { "hostname": "127.0.0.1", "port": 6379, "unix_socket_path": "/var/run/redis/redis.sock" },
        "redis_chassis_db": { "hostname": "127.100.1.1", "port": 6380, "unix_socket_path": "" }
    }
}
```

## 関連

- [swss-common DB リンク順序制約](swss-common-db-link-ordering.md)
- GitHub Issue: [sonic-net/sonic-swss-common#322](https://github.com/sonic-net/sonic-swss-common/issues/322)

<!-- glossary-links-injected: c006405759d8 -->
