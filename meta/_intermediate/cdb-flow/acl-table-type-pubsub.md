# ACL_TABLE_TYPE — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `ACL_TABLE_TYPE` テーブル、および `APPL_DB` の `ACL_TABLE_TYPE_TABLE`。
購読者は `orchagent` 内 `AclOrch` (`sonic-swss/orchagent/aclorch.cpp`)。

## 1. 購読 API

`AclOrch` は `Orch` 基底クラスを介して 2 つの DB・2 つのテーブルを購読する。
コンストラクタは `vector<TableConnector>` を受け取り、`Orch(connectors)` に転送する:

```cpp
// orchagent/orchdaemon.cpp:408-422
TableConnector confDbAclTableType(m_configDb, CFG_ACL_TABLE_TYPE_TABLE_NAME);  // CONFIG_DB
TableConnector appDbAclTableType(m_applDb, APP_ACL_TABLE_TYPE_TABLE_NAME);     // APPL_DB

vector<TableConnector> acl_table_connectors = {
    confDbAclTableType,    // 先頭: CONFIG_DB|ACL_TABLE_TYPE
    confDbAclTable,
    confDbAclRuleTable,
    appDbAclTable,
    appDbAclRuleTable,
    appDbAclTableType,     // 末尾: APPL_DB|ACL_TABLE_TYPE_TABLE
};
// orchagent/orchdaemon.cpp:533-534
gAclOrch = new AclOrch(acl_table_connectors, m_stateDb, ...);
```

`Orch::addConsumer()` は DB 種別により購読クラスを切り替える:

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

| ソース | DB | テーブル名 | 購読クラス |
|---|---|---|---|
| `confDbAclTableType` | CONFIG_DB (dbId=4) | `CFG_ACL_TABLE_TYPE_TABLE_NAME` = `"ACL_TABLE_TYPE"` | **`SubscriberStateTable`** |
| `appDbAclTableType` | APPL_DB (dbId=0) | `APP_ACL_TABLE_TYPE_TABLE_NAME` = `"ACL_TABLE_TYPE_TABLE"` | **`ConsumerStateTable`** |

## 2. CONFIG_DB 経路（`SubscriberStateTable`）

- Redis keyspace 通知 (`PSUBSCRIBE __keyspace@4__:ACL_TABLE_TYPE|*`) を購読。
- CONFIG_DB の writer (`sonic-cfggen` / `config` CLI / `swssconfig`) は `HSET "ACL_TABLE_TYPE|<name>" MATCHES <val> ...` を発行する。Redis サーバの keyspace 通知機能がこれを `__keyspace@4__:ACL_TABLE_TYPE|<name>` チャンネルに PUBLISH する。
- `SubscriberStateTable` の `pops()` で最大 `DEFAULT_POP_BATCH_SIZE = 128` 件を一括取得。
- 起動時スキャン: `SubscriberStateTable` は購読開始時に既存エントリを `m_buffer` に流し込むため、orchagent 再起動時も CONFIG_DB の既存 `ACL_TABLE_TYPE` エントリは SET イベントとして再配信される。

## 3. APPL_DB 経路（`ConsumerStateTable`）

- `ProducerStateTable` → Redis Lists (`LPUSH <queue>`) → `ConsumerStateTable` の pops() 受信。
- 現在 APPL_DB 経由で `ACL_TABLE_TYPE_TABLE` を書く実装:
  - `VnetOrch` (`orchagent/vnetorch.cpp:3738, 3781`) — VNET トンネル終端用カスタム type を自動登録
  - `DashEniFwdOrch` (`orchagent/dash/dashenifwdorch.cpp:404, 625, 649`) — DASH ENI フォワーディング用 type を自動登録/削除
- バッチサイズ: `gBatchSize`（orchagent 起動時に決定、デフォルト 128）。

## 4. ディスパッチ — `doTask()` 内の分岐

両チャンネルは同一の `AclOrch::doTask(Consumer&)` → `doAclTableTypeTask(consumer)` に合流する:

```cpp
// orchagent/aclorch.cpp:4291-4294
else if (table_name == CFG_ACL_TABLE_TYPE_TABLE_NAME || table_name == APP_ACL_TABLE_TYPE_TABLE_NAME)
{
    doAclTableTypeTask(consumer);
}
```

CONFIG_DB / APPL_DB どちらの通知も `doAclTableTypeTask()` が処理する。

## 5. TTL / 永続性

CONFIG_DB の `ACL_TABLE_TYPE` エントリには TTL は設定されない（CONFIG_DB は永続前提）。
APPL_DB 経路では ProducerStateTable が `EXPIRE` を設定しないため実質永続。

## 6. 関連リファレンス

- `sonic-swss/orchagent/aclorch.cpp:4197-4299` — AclOrch ctor、doTask 分岐
- `sonic-swss/orchagent/orchdaemon.cpp:408-422, 533-534` — TableConnector 構築 / AclOrch 生成
- `sonic-swss/orchagent/orch.cpp:1186-1196` — Orch::addConsumer の DB 種別分岐
- `sonic-swss/orchagent/vnetorch.cpp:3738, 3781` — APPL_DB 経由 producer (VnetOrch)
- `sonic-swss/orchagent/dash/dashenifwdorch.cpp:404, 625, 649` — APPL_DB 経由 producer (DashEniFwdOrch)
- `sonic-swss-common/common/schema.h:95` — `APP_ACL_TABLE_TYPE_TABLE_NAME = "ACL_TABLE_TYPE_TABLE"`
- `sonic-swss-common/common/table.h:164` — `DEFAULT_POP_BATCH_SIZE = 128`
