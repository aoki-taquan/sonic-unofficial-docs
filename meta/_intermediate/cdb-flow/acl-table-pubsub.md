# ACL_TABLE — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `ACL_TABLE` テーブル。購読者は `orchagent` 内 `AclOrch` (`sonic-swss/orchagent/aclorch.cpp`)。

## 1. 購読 API — `SubscriberStateTable` (Redis keyspace 通知)

`AclOrch` は `Orch` 基底クラスを介して `ACL_TABLE` を購読する。コンストラクタは `vector<TableConnector>` を受け取り、`Orch(connectors)` に転送する形:

```cpp
// orchagent/aclorch.cpp:4197-4214
AclOrch::AclOrch(vector<TableConnector>& connectors, DBConnector* stateDb, SwitchOrch *switchOrch,
        PortsOrch *portOrch, MirrorOrch *mirrorOrch, NeighOrch *neighOrch, RouteOrch *routeOrch, DTelOrch *dtelOrch) :
        Orch(connectors),
        ...
```

`Orch::addConsumer()` は DB 種別で購読クラスを切り替える:

```cpp
// orchagent/orch.cpp:1186-1196
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    {
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName,
            TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
    }
    else
    {
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
    }
}
```

- `CONFIG_DB` 起源の `ACL_TABLE` は **`SubscriberStateTable`** が選ばれる（`ConsumerStateTable` ではない）。
- `SubscriberStateTable` は Redis の **keyspace 通知** (`__keyspace@<dbId>__:<TABLE>:*` の PSUBSCRIBE) を購読する。channel ベースの publisher (`PUBLISH <channel>`) は使わない。
- CONFIG_DB の writer (`sonic-cfggen` / `config` CLI / `swssconfig`) は `HSET ACL_TABLE|<name> <field> <value>` を行うのみで、Redis サーバの `notify-keyspace-events` 機能が変更を通知する。

## 2. POP_BATCH_SIZE

`SubscriberStateTable` のコンストラクタ第3引数は `TableConsumable::DEFAULT_POP_BATCH_SIZE`:

```cpp
// sonic-swss-common/common/table.h:164
static constexpr int DEFAULT_POP_BATCH_SIZE = 128;
```

- 1 回の `pops()` 呼び出しで **最大 128 件** の keyspace イベントをまとめて取り出す。
- `APP_ACL_TABLE` (APPL_DB 経由) はこの分岐の `else` 側（`ConsumerStateTable` + `gBatchSize`）を通る — CONFIG_DB 側とはバッチサイズの取り扱いが異なる。

## 3. Keyspace パターン

- Redis Key パターン: `ACL_TABLE|<table-name>` (区切り文字は `|` — `swsscommon` の `TableNameSeparator` 既定値)。
- keyspace event 名前空間: `__keyspace@4__:ACL_TABLE:*` (CONFIG_DB の dbId は通常 4)。
- `SubscriberStateTable` は内部で `psubscribe __keyspace@<id>__:<table><sep>*` を発行する。

## 4. ディスパッチ — `doTask(Consumer &)` への合流

`AclOrch` は複数テーブル（CONFIG_DB と APPL_DB の `ACL_TABLE` / `ACL_RULE` / `ACL_TABLE_TYPE`）を 1 つの `AclOrch` インスタンスで束ねており、`doTask(Consumer&)` 内で `consumer.getTableName()` により分岐する:

```cpp
// orchagent/aclorch.cpp:4272-4296
void AclOrch::doTask(Consumer &consumer)
{
    ...
    string table_name = consumer.getTableName();
    if (table_name == CFG_ACL_TABLE_TABLE_NAME || table_name == APP_ACL_TABLE_TABLE_NAME)
    {
        doAclTableTask(consumer);
    }
    else if (table_name == CFG_ACL_RULE_TABLE_NAME || table_name == APP_ACL_RULE_TABLE_NAME)
    {
        doAclRuleTask(consumer);
    }
    else if (table_name == CFG_ACL_TABLE_TYPE_TABLE_NAME || table_name == APP_ACL_TABLE_TYPE_TABLE_NAME)
    {
        doAclTableTypeTask(consumer);
    }
    ...
}
```

- すなわち CONFIG_DB の `ACL_TABLE` 変更は `SubscriberStateTable` → `Consumer::execute()` → `AclOrch::doTask(Consumer&)` → `doAclTableTask(consumer)` の経路で処理される。

## 5. 起動時スナップショット

`SubscriberStateTable` は購読開始時に `HGETALL` 相当のスキャンで既存エントリを `m_buffer` に流し込み、その後に keyspace 通知へ切り替える設計のため、`orchagent` 起動時に CONFIG_DB に既に存在する `ACL_TABLE|*` エントリも一度 `SET` イベントとして配信される。これにより冷起動と動的変更が同じハンドラ経路に乗る。

## 6. TTL / 永続性

- CONFIG_DB の `ACL_TABLE` エントリには TTL は設定されない（CONFIG_DB は永続前提）。
- `notify-keyspace-events` は `redis.conf` 側で有効化されている前提（SONiC では `database_config.json` の CONFIG_DB エントリで `K` を含む）。

## 7. 関連リファレンス

- `sonic-swss/orchagent/aclorch.cpp:4197-4296` (AclOrch::AclOrch, AclOrch::doTask)
- `sonic-swss/orchagent/orchdaemon.cpp:408-422, 533` (TableConnector 構築 / AclOrch 生成)
- `sonic-swss/orchagent/orch.cpp:1186-1196` (Orch::addConsumer の DB 種別分岐)
- `sonic-swss-common/common/subscriberstatetable.h:14` (SubscriberStateTable ctor)
- `sonic-swss-common/common/table.h:164` (DEFAULT_POP_BATCH_SIZE = 128)
