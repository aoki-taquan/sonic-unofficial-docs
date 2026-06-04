---
title: swss-common Logger の linkToDb / linkToDbNative 呼び出し順序
area: internals
tags: [swss-common, logger, api, internal]
description: Logger::linkToDb と Logger::linkToDbNative の呼び出し順序に関する API 設計上の制約と、その意図を logger.h / logger.cpp の実コードから整理する。
source_issues:
  - https://github.com/sonic-net/sonic-swss-common/issues/507
sources:
- repo: sonic-net/sonic-swss-common
  path: common/logger.h
  ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
- repo: sonic-net/sonic-swss-common
  path: common/logger.cpp
  ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
verification: code-verified
last_verified: 2026-06-04
related:
  cli: []
  config_db:
    - LOGGER
  yang: []
  _no_related_yang: true
  _no_related_cli: true
---

# swss-common Logger の linkToDb / linkToDbNative 呼び出し順序

## 概要

`linkToDb()` と `linkToDbNative()` は `sonic-swss-common` の `Logger` クラス（`common/logger.h`）が公開する **静的メソッド**で、daemon の最小ログ優先度 (`LOGLEVEL`) や出力先 (`LOGOUTPUT`) を [CONFIG_DB](../reference/glossary.md#term-config_db) の `LOGGER` テーブルから動的に取得・反映するための初期化 API である。

このページでは [sonic-swss-common#507](https://github.com/sonic-net/sonic-swss-common/issues/507) で論点となった「なぜ呼び出し順序に依存するのか」を、master の実装に即して整理する。

## API の所在

`linkToDb` / `linkToDbNative` は **`Logger` クラスの static メソッド**であって、`ProducerStateTable` / `SubscriberStateTable` / `ConsumerStateTable` 等の table クラスには存在しない。

```cpp
// common/logger.h (抜粋)
static void linkToDb(const std::string& dbName,
                     const PriorityChangeNotify& notify,
                     const std::string& defPrio);
// Must be called after all linkToDb to start select from DB
static void linkToDbNative(const std::string& dbName,
                           const char * defPrio="NOTICE");
```

<!-- evidence:
source: sonic-net/sonic-swss-common/common/logger.h#L85-L95 (sha: 158de8d3463ff4b841653f6d57190bb142b80d9c)
excerpt: |
  static void linkToDb(const std::string& dbName, const PriorityChangeNotify& notify, const std::string& defPrio);
  // Must be called after all linkToDb to start select from DB
  static void linkToDbNative(const std::string& dbName, const char * defPrio="NOTICE");
reasoning: linkToDb / linkToDbNative は Logger の static メソッドであり、ヘッダコメントが順序制約 (linkToDbNative は linkToDb の後で呼ぶ) を明示している。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-swss-common/common/logger.h#L85-L95 (sha: 158de8d3463ff4b841653f6d57190bb142b80d9c)"

    **出典**:

    `sonic-net/sonic-swss-common/common/logger.h#L85-L95 (sha: 158de8d3463ff4b841653f6d57190bb142b80d9c)`

    **抜粋**:

    ```text
    static void linkToDb(const std::string& dbName, const PriorityChangeNotify& notify, const std::string& defPrio);
    // Must be called after all linkToDb to start select from DB
    static void linkToDbNative(const std::string& dbName, const char * defPrio="NOTICE");
    ```

    **判断根拠**: linkToDb / linkToDbNative は Logger の static メソッドであり、ヘッダコメントが順序制約 (linkToDbNative は linkToDb の後で呼ぶ) を明示している。

<!-- evidence-rendered:end -->

## 現行 master が要求する順序

ヘッダの `// Must be called after all linkToDb to start select from DB` というコメントどおり、現行 master では:

1. まず各 component について `Logger::linkToDb(dbName, prioNotify, defPrio)` を呼んで `PriorityChangeNotify` コールバックを登録する
2. すべての component の登録を終えた後で `Logger::linkToDbNative(dbName)` を呼ぶ

順序になっている。`linkToDbNative()` 自身は `linkToDb()` を内部で呼んだうえで設定取得スレッド (`settingThread`) を起動するため、`linkToDb` 系の登録より先に呼ぶと「未登録 component のコールバックが呼ばれない」「コールバック登録レースが起こる」可能性がある設計になっている。

```cpp
// common/logger.cpp (抜粋)
void Logger::linkToDb(const std::string& dbName, const PriorityChangeNotify& prioNotify, const std::string& defPrio)
{
    linkToDbWithOutput(dbName, prioNotify, defPrio, swssOutputNotify, "SYSLOG");
}

void Logger::linkToDbNative(const std::string& dbName, const char * defPrio)
{
    linkToDb(dbName, swssPrioNotify, defPrio);
    getInstance().restartSettingThread();
}
```

<!-- evidence:
source: sonic-net/sonic-swss-common/common/logger.cpp#L159-L169 (sha: 158de8d3463ff4b841653f6d57190bb142b80d9c)
excerpt: |
  void Logger::linkToDbNative(const std::string& dbName, const char * defPrio)
  {
      linkToDb(dbName, swssPrioNotify, defPrio);
      getInstance().restartSettingThread();
  }
reasoning: linkToDbNative は内部で linkToDb を呼んだ後に restartSettingThread() で CONFIG_DB を購読する settingThread を再起動する。これが「最後に呼ぶべき」理由である。
-->

<!-- evidence-rendered:start -->
??? note "📋 検証エビデンス: sonic-net/sonic-swss-common/common/logger.cpp#L159-L169 (sha: 158de8d3463ff4b841653f6d57190bb142b80d9c)"

    **出典**:

    `sonic-net/sonic-swss-common/common/logger.cpp#L159-L169 (sha: 158de8d3463ff4b841653f6d57190bb142b80d9c)`

    **抜粋**:

    ```text
    void Logger::linkToDbNative(const std::string& dbName, const char * defPrio)
    {
        linkToDb(dbName, swssPrioNotify, defPrio);
        getInstance().restartSettingThread();
    }
    ```

    **判断根拠**: linkToDbNative は内部で linkToDb を呼んだ後に restartSettingThread() で CONFIG_DB を購読する settingThread を再起動する。これが「最後に呼ぶべき」理由である。

<!-- evidence-rendered:end -->

`restartSettingThread()` が起動する `settingThread` は CONFIG_DB の `LOGGER` テーブルを `SubscriberStateTable` で購読し続け、優先度・出力先の変更通知を受け取ったら `linkToDb` で登録された `PriorityChangeNotify` / `OutputChangeNotify` を呼び出す。したがって `linkToDb` よりも先にスレッドを走らせる意味は無い。

## Issue #507 の論点

[sonic-net/sonic-swss-common#507](https://github.com/sonic-net/sonic-swss-common/issues/507) は、公開 API なのに呼び出し順序に依存しているのは設計として疑問であり、

- 順序依存を取り払う（API 内部で順序を強制する）か、
- `linkToDbNative` を private にして公開 API としては露出させない

のどちらかで「呼び出し元が順序を意識せずに済む形」にすべきではないか、という提起である。本 issue は現時点 (master `158de8d3`) でも open であり、API は順序依存のまま運用されている。

## 利用者への注意

`swss-common` の `Logger` 経由で CONFIG_DB 連動のログレベル動的変更を使う daemon / カスタムエージェントを書くとき:

- `Logger::linkToDb()` で必要な component を全部登録してから、最後に `Logger::linkToDbNative()` を 1 回呼ぶ
- `linkToDbNative()` は内部で `restartSettingThread()` を呼ぶため、複数回呼ぶ動機は通常無い
- これらは `Logger` の static メソッドであり、`ProducerStateTable` / `SubscriberStateTable` / `ConsumerStateTable` には同名 API は無い

## 関連

- [swss-common データベース設定](swss-common-database-config.md)
- GitHub Issue: [sonic-net/sonic-swss-common#507](https://github.com/sonic-net/sonic-swss-common/issues/507)

## 引用元

- [sonic-swss-common `common/logger.h` (master `158de8d3`)](https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/logger.h#L85-L95)
- [sonic-swss-common `common/logger.cpp` (master `158de8d3`)](https://github.com/sonic-net/sonic-swss-common/blob/158de8d3463ff4b841653f6d57190bb142b80d9c/common/logger.cpp#L159-L169)

<!-- glossary-links-injected: 896d391185a9 -->
