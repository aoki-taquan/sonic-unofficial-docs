# PBH_TABLE / PBH_RULE / PBH_HASH / PBH_HASH_FIELD — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `PBH_TABLE`, `PBH_RULE`, `PBH_HASH`, `PBH_HASH_FIELD` テーブル群。購読者は `orchagent` 内 `PbhOrch` (`sonic-swss/orchagent/pbhorch.cpp`)。

## 1. 購読 API — `SubscriberStateTable` (Redis keyspace 通知)

`PbhOrch` は `Orch` 基底クラスを介して PBH 4 テーブルを購読する。コンストラクタは `vector<TableConnector>` を受け取り、`Orch(connectorList)` に転送する形:

```cpp
// sonic-swss/orchagent/pbhorch.cpp:88-97
PbhOrch::PbhOrch(
    std::vector<TableConnector> &connectorList,
    AclOrch *aclOrch,
    PortsOrch *portsOrch
) : Orch(connectorList)
{
    this->aclOrch = aclOrch;
    this->portsOrch = portsOrch;
}
```

`Orch::addConsumer()` は DB 種別で購読クラスを切り替える (CONFIG_DB → `SubscriberStateTable`):

```cpp
// sonic-swss/orchagent/orch.cpp
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

- CONFIG_DB 起源の PBH テーブルはすべて **`SubscriberStateTable`** が選ばれる。
- `SubscriberStateTable` は Redis の **keyspace 通知** (`__keyspace@<dbId>__:<TABLE>:*` の PSUBSCRIBE) を購読する。channel ベースの publisher (`PUBLISH`) は使わない。

## 2. TableConnector 構築 (orchdaemon.cpp)

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:553-565
TableConnector cfgDbPbhTable(m_configDb, CFG_PBH_TABLE_TABLE_NAME);
TableConnector cfgDbPbhRuleTable(m_configDb, CFG_PBH_RULE_TABLE_NAME);
TableConnector cfgDbPbhHashTable(m_configDb, CFG_PBH_HASH_TABLE_NAME);
TableConnector cfgDbPbhHashFieldTable(m_configDb, CFG_PBH_HASH_FIELD_TABLE_NAME);

vector<TableConnector> pbhTableConnectorList = {
    cfgDbPbhTable,
    cfgDbPbhRuleTable,
    cfgDbPbhHashTable,
    cfgDbPbhHashFieldTable
};

gPbhOrch = new PbhOrch(pbhTableConnectorList, gAclOrch, gPortsOrch);
```

4 テーブルすべてが単一の `PbhOrch` インスタンスに束ねられる。

## 3. POP_BATCH_SIZE

```cpp
// sonic-swss-common/common/table.h:164
static constexpr int DEFAULT_POP_BATCH_SIZE = 128;
```

1 回の `pops()` 呼び出しで最大 128 件の keyspace イベントをまとめて取り出す。

## 4. Keyspace パターン

- `__keyspace@4__:PBH_TABLE:*` (CONFIG_DB dbId=4)
- `__keyspace@4__:PBH_RULE:*`
- `__keyspace@4__:PBH_HASH:*`
- `__keyspace@4__:PBH_HASH_FIELD:*`
- key 区切り: `|` (TableNameSeparator 既定値)

## 5. ディスパッチ — `PbhOrch::doTask(Consumer &)`

```cpp
// sonic-swss/orchagent/pbhorch.cpp:1804-1838
void PbhOrch::doTask(Consumer &consumer)
{
    if (!this->portsOrch->allPortsReady()) { return; }

    auto tableName = consumer.getTableName();

    if (tableName == CFG_PBH_TABLE_TABLE_NAME)
        this->doPbhTableTask(consumer);
    else if (tableName == CFG_PBH_RULE_TABLE_NAME)
        this->doPbhRuleTask(consumer);
    else if (tableName == CFG_PBH_HASH_TABLE_NAME)
        this->doPbhHashTask(consumer);
    else if (tableName == CFG_PBH_HASH_FIELD_TABLE_NAME)
        this->doPbhHashFieldTask(consumer);
    else
        SWSS_LOG_ERROR("Unknown table(%s)", tableName.c_str());

    this->deployPbhTasks();
}
```

- `allPortsReady()` が false の間は処理スキップ。
- 処理後に `deployPbhTasks()` で依存関係 (HASH_FIELD → HASH → TABLE → RULE) を解消。

## 6. CONFIG_DB → SAI 完全経路

```
config pbh rule add ... → sonic-utilities/config/plugins/pbh.py → set_entry()
  → HSET CONFIG_DB PBH_RULE|<table>|<rule> <fields>
  → Redis keyspace 通知 (__keyspace@4__:PBH_RULE:*)
  → SubscriberStateTable.pops() (batch=128)
  → Consumer::execute() → PbhOrch::doTask()
  → doPbhRuleTask() → validatePbhRule() → AclRulePbh::validate()
  → sai_acl_api->create_acl_entry() (SAI へ直接反映)
```

APP_DB への書き込みなし。

## 7. 起動時スナップショット

`SubscriberStateTable` は購読開始時に既存エントリを `m_buffer` に流し込んで SET イベントとして再配信するため、`orchagent` 起動時に CONFIG_DB に既に存在する PBH エントリも同じハンドラ経路で処理される。

## 8. 関連リファレンス

- `sonic-swss/orchagent/pbhorch.cpp:88-97` (PbhOrch::PbhOrch)
- `sonic-swss/orchagent/pbhorch.cpp:1804-1838` (PbhOrch::doTask)
- `sonic-swss/orchagent/orchdaemon.cpp:553-565` (TableConnector 構築 + gPbhOrch 生成)
- `sonic-swss/orchagent/orch.cpp` (Orch::addConsumer DB 種別分岐)
- `sonic-swss-common/common/table.h:164` (DEFAULT_POP_BATCH_SIZE = 128)
