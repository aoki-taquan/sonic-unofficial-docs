# CONFIG_DB ACL_RULE — 通信メカニズム (Phase G) 解析メモ

対象: CONFIG_DB の `ACL_RULE` テーブル（スキーマ定数: `CFG_ACL_RULE_TABLE_NAME`、`sonic-swss-common/common/schema.h`）。

ソース確認: `sonic-swss/orchagent/aclorch.cpp` sha `4305596156d70e9797e8a881b3d19b46de0bce0d`、`sonic-swss/orchagent/orchdaemon.cpp`、`sonic-swss/orchagent/orch.cpp`、`sonic-swss/orchagent/main.cpp`、`sonic-swss-common/common/subscriberstatetable.{h,cpp}`、`sonic-swss-common/common/table.h`。

## 1. 購読 API — `SubscriberStateTable` (keyspace 通知ベース)

CONFIG_DB の `ACL_RULE` は `orchdaemon.cpp` で `TableConnector(m_configDb, CFG_ACL_RULE_TABLE_NAME)` として作られ、`AclOrch` コンストラクタの `connectors` 引数に渡される（`orchdaemon.cpp:410-422`）。

```cpp
// orchdaemon.cpp:408-422
TableConnector confDbAclTableType(m_configDb, CFG_ACL_TABLE_TYPE_TABLE_NAME);
TableConnector confDbAclTable(m_configDb, CFG_ACL_TABLE_TABLE_NAME);
TableConnector confDbAclRuleTable(m_configDb, CFG_ACL_RULE_TABLE_NAME);

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
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName, TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
    }
    else
    {
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
    }
}
```

CONFIG_DB はこの分岐の最初の if 節にマッチするため、**`SubscriberStateTable`** が選択される（APPL_DB 側 `ACL_RULE_TABLE` が `ConsumerStateTable` = channel ベース なのと対照的）。

- `SubscriberStateTable` は Redis の **keyspace 通知** (`__keyspace@<dbId>__:<TABLE>|*` への `PSUBSCRIBE`) を購読し、通知 (`set` / `hset` / `del` / `hdel` 等の op 名) を受信したら **`HGETALL` で値を再取得**してから `pops()` で `(key, op, fvs)` タプル列を返す (`subscriberstatetable.cpp:45-165`)。
- バッチサイズは **`TableConsumable::DEFAULT_POP_BATCH_SIZE = 128`** (`table.h:164`)。`Orch::addConsumer()` がハードコードで渡しており、`orchagent -b` オプションの影響を受けない (`-b` は `gBatchSize` のみを変えるため APPL_DB 側 `ConsumerStateTable` だけに作用する)。
- TTL は CONFIG_DB の全エントリで未設定（CONFIG_DB は永続前提）。

## 2. 書き込み側 (publisher)

CONFIG_DB の `ACL_RULE` は CLI / `sonic-cfggen` / 外部 controller (gNMI / REST) が `Table::set()` または `swsssdk` ベースで `HSET <CONFIG_DB>:ACL_RULE|<table>|<rule> <field> <value>` を発行する。明示的な `PUBLISH` は行われず、Redis の `notify-keyspace-events` 設定（CONFIG_DB は `Kxxx` 相当）が `__keyspace@<dbId>__:ACL_RULE|<table>|<rule>` イベントを発行し、購読者 (`AclOrch`) がそれを受信する。

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

CONFIG_DB と APPL_DB の双方が **同じ `doAclRuleTask` ハンドラ**にディスパッチされるため、フィールド意味論・action / match セット・priority 範囲チェックは完全に共有される。

## 4. select タイムアウト

```cpp
// orchdaemon.cpp:22-23
/* select() function timeout retry time */
#define SELECT_TIMEOUT 1000
```

`m_select->select(&s, SELECT_TIMEOUT)` は **1000 ms (1 秒)** で wake up し、retry / heartbeat 処理を回す。keyspace 通知到着時は即座に wake up し、`execute()` → `pops()` (HGETALL) → `doTask()` が走る。

## 5. リトライキャッシュ

`AclOrch::AclOrch()` は ACL ルール 2 系統（CONFIG_DB / APPL_DB）のリトライキャッシュを **両方** 作成する:

```cpp
// aclorch.cpp:4221-4222
createRetryCache(CFG_ACL_RULE_TABLE_NAME);
createRetryCache(APP_ACL_RULE_TABLE_NAME);
```

SAI リソース枯渇等で一時失敗したルールは consumer ごとに park され、リソース解放時に再試行される。`ACL_TABLE_TABLE` / `ACL_TABLE_TYPE_TABLE` 側は retry cache 対象外（テーブル単位失敗は `doTask` 内の通常 retry／erase でハンドル）。

## 6. サマリ

| 観点 | CONFIG_DB 側 `ACL_RULE` |
|---|---|
| 購読方式 | `swss::SubscriberStateTable`（Redis keyspace 通知 `__keyspace@<dbId>__:ACL_RULE|*` の `PSUBSCRIBE`） |
| バッチサイズ | `TableConsumable::DEFAULT_POP_BATCH_SIZE = 128` (`table.h:164`、ハードコード) |
| select タイムアウト | 1000 ms (`SELECT_TIMEOUT`, `orchdaemon.cpp:23`) |
| 書き込み側 API | `swss::Table::set()` / `swsssdk` (`HSET`); CLI / `sonic-cfggen` / gNMI 経由 |
| ハンドラ | `AclOrch::doAclRuleTask()` (APPL_DB 版と同一) |
| リトライキャッシュ | `createRetryCache(CFG_ACL_RULE_TABLE_NAME)` (`aclorch.cpp:4221`) |
| keyspace 通知 (`__keyspace@<dbId>__:...`) | **使う**（`SubscriberStateTable` の基盤プロトコル） |
| channel `<TABLE>_CHANNEL` PUBLISH | 使わない |
| TTL | 未使用 (CONFIG_DB は永続) |
| `orchagent -b` 影響 | なし（CONFIG_DB は `gBatchSize` ではなく `DEFAULT_POP_BATCH_SIZE` 固定） |

## 7. サービス再起動トリガー

なし。`AclOrch` は orchagent プロセス内のハンドラで、`ACL_RULE` の追加・変更・削除は SAI ACL entry のライブ操作 (`sai_acl_api->create_acl_entry` / `set_acl_entry_attribute` / `remove_acl_entry`) のみで反映され、プロセス再起動・サービス restart を伴わない。`MIRROR_SESSION` の activate 待ちや SAI リソース枯渇時は retry cache に park されるのみ。

## 8. Evidence サマリ

- `sonic-swss/orchagent/orchdaemon.cpp` L22-23, L408-422, L533, L959 — TableConnector 構成、SELECT_TIMEOUT、`new AclOrch(acl_table_connectors, ...)`、select ループ
- `sonic-swss/orchagent/orch.cpp` L1186-1196 — `Orch::addConsumer()` の DB ID 分岐（CONFIG_DB → `SubscriberStateTable`）
- `sonic-swss/orchagent/aclorch.cpp` L4221-4222, L4272-4295 — `createRetryCache(CFG_ACL_RULE_TABLE_NAME)`、`doTask` ディスパッチ
- `sonic-swss/orchagent/main.cpp` L59-60, L459, L478 — `gBatchSize` / `-b` (CONFIG_DB 側には適用されない)
- `sonic-swss-common/common/subscriberstatetable.{h,cpp}` L14, L17, L45-165 — `SubscriberStateTable` コンストラクタと `PSUBSCRIBE` + `HGETALL` 動作
- `sonic-swss-common/common/table.h` L164 — `TableConsumable::DEFAULT_POP_BATCH_SIZE = 128`
- `sonic-swss-common/common/schema.h` — `CFG_ACL_RULE_TABLE_NAME` 定数
