---
title: swss-common データベース設定（database_config.json）
area: internals
tags: [swss-common, database, configuration, redis, internal]
description: database_config.json が必須となった経緯と DEFAULT_UNIXSOCKET 廃止、非標準環境での注意点。
source_issues:
  - https://github.com/sonic-net/sonic-swss-common/issues/322
verification: issue-confirmed
last_verified: 2026-05-20
---

# swss-common データベース設定（database_config.json）

## 概要

`sonic-swss-common` は [Redis](../reference/glossary.md#term-redis) への接続情報を `database_config.json` から読み取る設計に移行しており、かつての `DEFAULT_UNIXSOCKET` による接続方式は廃止予定（または廃止済み）である。

## database_config.json の役割

`database_config.json` は `swss-common` が使用する Redis データベースの接続設定を定義するファイルである。標準的な [SONiC](../reference/glossary.md#term-sonic) イメージでは `/var/run/redis/sonic-db/database_config.json` に配置される。

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
        ...
    }
}
```

## DEFAULT_UNIXSOCKET の廃止経緯

以前の `swss-common` では、`database_config.json` が存在しない場合にデフォルトの Unix ソケットパス（`/var/run/redis/redis.sock`）を使ってフォールバック接続を行っていた。

しかし、開発チームの方針として：

> 「今後は `DEFAULT_UNIXSOCKET` は使用しない。DB 関連の設定はすべてデフォルトでビルドされる `database_config.json` から読み取る。」

この方針変更により、`database_config.json` が存在しない環境では `swss-common` を使用するコンポーネントが起動に失敗するようになった。

## 非標準環境での利用

公式 SONiC コンテナイメージを使用しない場合（カスタムコンテナ、開発環境、単体テスト等）、`database_config.json` を適切に配置するか、環境変数で場所を指定する必要がある。

### 環境変数による指定

```bash
export SONIC_DB_CONFIG_FILE=/path/to/database_config.json
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
        "ERROR_DB": { "id": 7, "separator": ":", "instance": "redis" }
    },
    "VERSION": "1.0"
}
```

## マルチ DB 構成

大規模 SONiC 構成では、複数の Redis インスタンスに DB を分散配置することが可能である。`database_config.json` の `INSTANCES` セクションに複数のインスタンスを定義し、各 DB を異なるインスタンスに割り当てる。

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

<!-- glossary-links-injected: 3605a1b8842c -->
