# APPL_DB ACL テーブル群 — 通信メカニズム (Phase G) 解析メモ

対象: APPL_DB の `ACL_TABLE_TABLE` / `ACL_TABLE_TYPE_TABLE` / `ACL_RULE_TABLE`（スキーマ定数: `APP_ACL_TABLE_TABLE_NAME` / `APP_ACL_TABLE_TYPE_TABLE_NAME` / `APP_ACL_RULE_TABLE_NAME`、`sonic-swss-common/common/schema.h:94-96`）。

ソース確認: `sonic-swss/orchagent/aclorch.cpp` sha `4305596156d70e9797e8a881b3d19b46de0bce0d`、`sonic-swss/orchagent/orchdaemon.cpp`、`sonic-swss/orchagent/orch.cpp`、`sonic-swss/orchagent/main.cpp`。

## 1. 購読 API — `ConsumerStateTable` (channel ベース PUBLISH/SUBSCRIBE)

APPL_DB の ACL 3 テーブルは `orchdaemon.cpp` で `TableConnector(m_applDb, ...)` として作られ、`AclOrch` コンストラクタの `connectors` 引数に渡される（`orchdaemon.cpp:411-422`）。

```cpp
// orchdaemon.cpp:411-422
TableConnector appDbAclTable(m_applDb, APP_ACL_TABLE_TABLE_NAME);
TableConnector appDbAclTableType(m_applDb, APP_ACL_TABLE_TYPE_TABLE_NAME);
TableConnector appDbAclRuleTable(m_applDb, APP_ACL_RULE_TABLE_NAME);

vector<TableConnector> acl_table_connectors = {
    confDbAclTableType,
    confDbAclTable,
    confDbAclRuleTable,
    appDbAclTable,
    appDbAclRuleTable,
    appDbAclTableType,
};
```

`AclOrch::AclOrch(connectors, ...)` は基底 `Orch(connectors)` を呼び出し、その内部で各 TableConnector ごとに `Orch::addConsumer()` が呼ばれる。`addConsumer()` は DB ID で分岐する（`orch.cpp:1186-1196`）:

```cpp
// orch.cpp:1186-1196
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    {
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ..., pri), this, tableName));
    }
    else
    {
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
    }
}
```

APPL_DB は `CONFIG_DB / STATE_DB / CHASSIS_APP_DB` のいずれでもないため **`ConsumerStateTable`** が選択される（CONFIG_DB 側 ACL テーブルが `SubscriberStateTable` = keyspace 通知ベースなのと対照的）。

- `ConsumerStateTable` は producer 側が `ProducerStateTable::set()` で `_<TABLE>` ハッシュ + `<TABLE>_CHANNEL@<dbId>` への `PUBLISH` を行う、channel ベースの PUBLISH/SUBSCRIBE プロトコル。
- バッチサイズは `gBatchSize`。`orchagent/main.cpp:459` で `DEFAULT_BATCH_SIZE = 128` に初期化、`-b <n>` オプションで上書き可。
- TTL は APPL_DB エントリで設定されない（producer 側 `set()` は HSET のみ）。

## 2. 書き込み側 (publisher)

`appl-acl.md` 本文に既出のとおり、APPL_DB 側 ACL テーブルを書き込むプロセスは 3 つ:

| 書き込み元 | 対象テーブル | API |
|---|---|---|
| `vnetorch` | `ACL_TABLE_TYPE_TABLE` / `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` | `ProducerStateTable::set()` (vnetorch.cpp:3775-3832) |
| `mclagsyncd` | `ACL_TABLE_TABLE` / `ACL_RULE_TABLE` | `ProducerStateTable::set()` (mclaglink.cpp:327-372) |
| `dashenifwdorch` | `ACL_TABLE_TYPE_TABLE` / `ACL_TABLE_TABLE` | `ProducerStateTable::set()` (dashenifwdorch.cpp:619-643) |

これらはいずれも同一 orchagent プロセス内のオブジェクト（`vnetorch` / `dashenifwdorch`）か、別プロセス（`mclagsyncd`）から `ProducerStateTable` 経由で書き込み、内部的に `<TABLE>_CHANNEL` への PUBLISH を発行する。

## 3. 購読側 ディスパッチ

`AclOrch` は 6 つの consumer（CONFIG_DB 3 + APPL_DB 3）を内包する。`OrchDaemon` のメインループ（`orchdaemon.cpp:959`）が `m_select->select(&s, SELECT_TIMEOUT)` で待ち、各 `Consumer::execute()` がポップ → `doTask(Consumer&)` を呼ぶ。

```cpp
// aclorch.cpp:4272-4295
void AclOrch::doTask(Consumer &consumer)
{
    auto table_name = consumer.getTableName();

    if (table_name == CFG_ACL_TABLE_TABLE_NAME || table_name == APP_ACL_TABLE_TABLE_NAME)
        doAclTableTask(consumer);
    else if (table_name == CFG_ACL_RULE_TABLE_NAME || table_name == APP_ACL_RULE_TABLE_NAME)
        doAclRuleTask(consumer);
    else if (table_name == CFG_ACL_TABLE_TYPE_TABLE_NAME || table_name == APP_ACL_TABLE_TYPE_TABLE_NAME)
        doAclTableTypeTask(consumer);
}
```

CONFIG_DB と APPL_DB の双方が **同じ `doAclTableTask` / `doAclRuleTask` / `doAclTableTypeTask` ハンドラ**にディスパッチされるため、フィールド意味論・action / match セット・priority 範囲チェックは完全に共有される。

## 4. select タイムアウト

```cpp
// orchdaemon.cpp:22-23
/* select() function timeout retry time */
#define SELECT_TIMEOUT 1000
```

`m_select->select(&s, SELECT_TIMEOUT)` は **1000 ms (1 秒)** で wake up し、retry / heartbeat 処理（`flush`、各種ヘルスチェック）を回す。channel に PUBLISH があれば即座に wake up し、`execute()` → `pop()` → `doTask()` が走る。

## 5. リトライキャッシュ

`AclOrch::AclOrch()` は ACL ルール 2 系統（CONFIG_DB / APPL_DB）のリトライキャッシュを **両方** 作成する:

```cpp
// aclorch.cpp:4221-4222
createRetryCache(CFG_ACL_RULE_TABLE_NAME);
createRetryCache(APP_ACL_RULE_TABLE_NAME);
```

SAI リソース枯渇等で一時失敗したルールは consumer ごとに park され、リソース解放時に再試行される。`ACL_TABLE_TABLE` / `ACL_TABLE_TYPE_TABLE` 側は retry cache 対象外（テーブル単位失敗は `doTask` 内の通常 retry／erase でハンドル）。

## 6. リトライキャッシュ・サマリ

| 観点 | APPL_DB 側 ACL 3 テーブル |
|---|---|
| 購読方式 | `ConsumerStateTable`（channel ベース PUBLISH/SUBSCRIBE） |
| バッチサイズ | `gBatchSize` (default 128, `orchagent -b` で上書き可) |
| select タイムアウト | 1000 ms (`SELECT_TIMEOUT`, orchdaemon.cpp:23) |
| 書き込み側 API | `ProducerStateTable::set()` |
| ハンドラ | CONFIG_DB 版と同一 (`doAclTableTask` / `doAclRuleTask` / `doAclTableTypeTask`) |
| リトライキャッシュ | `ACL_RULE_TABLE` のみ (`createRetryCache(APP_ACL_RULE_TABLE_NAME)`, aclorch.cpp:4222) |
| keyspace 通知 (`__keyspace@<dbId>__:...`) | **使わない**（channel ベースのため） |
| TTL | 未使用 |

## 7. Evidence サマリ

- `sonic-swss/orchagent/orchdaemon.cpp` L22-23, L411-422, L959 — TableConnector 構成、SELECT_TIMEOUT、select ループ
- `sonic-swss/orchagent/orch.cpp` L1186-1196 — `Orch::addConsumer()` の DB ID 分岐
- `sonic-swss/orchagent/aclorch.cpp` L4197-4222, L4272-4295 — AclOrch コンストラクタ、retry cache 作成、`doTask` ディスパッチ
- `sonic-swss/orchagent/main.cpp` L59-60, L459, L478 — `DEFAULT_BATCH_SIZE = 128`、`gBatchSize` 初期化と `-b` オプション
- `sonic-swss-common/common/schema.h` L94-96 — `APP_ACL_TABLE_TABLE_NAME` 等テーブル名定数
