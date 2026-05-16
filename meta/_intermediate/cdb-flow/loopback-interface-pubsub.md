# LOOPBACK_INTERFACE — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `LOOPBACK_INTERFACE` テーブル。  
購読者: `intfmgrd` (`sonic-swss/cfgmgr/intfmgr.cpp`) / `orchagent` `IntfsOrch` (`sonic-swss/orchagent/intfsorch.cpp`)

## 1. 購読 API — intfmgrd 側（SubscriberStateTable + Orch 基底）

`intfmgrd` の `main()` は `CFG_LOOPBACK_INTERFACE_TABLE_NAME` を `tableNames` ベクタに含めて `IntfMgr` を構築する:

```cpp
// sonic-swss/cfgmgr/intfmgrd.cpp:28-44
vector<string> cfg_intf_tables = {
    CFG_INTF_TABLE_NAME,
    CFG_LAG_INTF_TABLE_NAME,
    CFG_VLAN_INTF_TABLE_NAME,
    CFG_LOOPBACK_INTERFACE_TABLE_NAME,   // ← LOOPBACK_INTERFACE
    CFG_VLAN_SUB_INTF_TABLE_NAME,
    CFG_VOQ_INBAND_INTERFACE_TABLE_NAME,
};
DBConnector cfgDb("CONFIG_DB", 0);
IntfMgr intfmgr(&cfgDb, &appDb, &stateDb, cfg_intf_tables);
```

`IntfMgr` は `Orch(cfgDb, tableNames)` を継承するため、`Orch::addConsumer()` 内の DB 種別分岐によって CONFIG_DB に対しては **`SubscriberStateTable`** が選ばれる:

```cpp
// sonic-swss/orchagent/orch.cpp (参照)
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName,
            TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
    else
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

- CONFIG_DB(`dbId=4`) のため `SubscriberStateTable` が使用される（`ConsumerStateTable` / `ProducerStateTable` の channel-publish パスではない）。
- `SubscriberStateTable` は内部で `psubscribe __keyspace@4__:LOOPBACK_INTERFACE|*` を発行し、Redis サーバの **keyspace 通知** を受信する。
- CONFIG_DB の書き手（`config loopback` CLI / `sonic-cfggen` / `swssconfig`）は `HSET LOOPBACK_INTERFACE|<key> ...` を直接実行するだけで、`PUBLISH` は行わない。Redis サーバの `notify-keyspace-events` 機能がキー変更時に通知を自動配信する。

さらに `IntfMgr::IntfMgr()` は STATE_DB に対して 2 本の `SubscriberStateTable` を追加登録する:

```cpp
// sonic-swss/cfgmgr/intfmgr.cpp:45-53
auto subscriberStateTable = new swss::SubscriberStateTable(stateDb,
        STATE_PORT_TABLE_NAME, TableConsumable::DEFAULT_POP_BATCH_SIZE, 100);
auto stateConsumer = new Consumer(subscriberStateTable, this, STATE_PORT_TABLE_NAME);
Orch::addExecutor(stateConsumer);

auto subscriberStateLagTable = new swss::SubscriberStateTable(stateDb,
        STATE_LAG_TABLE_NAME, TableConsumable::DEFAULT_POP_BATCH_SIZE, 200);
auto stateLagConsumer = new Consumer(subscriberStateLagTable, this, STATE_LAG_TABLE_NAME);
Orch::addExecutor(stateLagConsumer);
```

これらは `STATE_PORT_TABLE` / `STATE_LAG_TABLE` の ready 通知を受信するためのもので、Loopback 固有の STATE_DB 待ちには**使用されない**（`isIntfStateOk("Loopback*")` は常 `true` を返すため）。

## 2. POP_BATCH_SIZE

`SubscriberStateTable` のコンストラクタ第3引数 `TableConsumable::DEFAULT_POP_BATCH_SIZE`:

```cpp
// sonic-swss-common/common/table.h:164
static constexpr int DEFAULT_POP_BATCH_SIZE = 128;
```

- 1 回の `pops()` 呼び出しで最大 **128 件** の keyspace イベントをまとめて取り出す。
- `SELECT_TIMEOUT = 1000` ミリ秒のポーリングで `intfmgr.doTask()` がフォールバック呼び出しされる（`intfmgrd.cpp:17, 65-68`）。

## 3. Keyspace パターン

- テーブル名: `LOOPBACK_INTERFACE`
- キー区切り: `|`（`swsscommon` デフォルト `TableNameSeparator`）
- 購読パターン: `__keyspace@4__:LOOPBACK_INTERFACE|*`（CONFIG_DB の dbId は通常 4）

```cpp
// sonic-swss-common/common/subscriberstatetable.cpp:20-24
m_keyspace = "__keyspace@";
m_keyspace += to_string(db->getDbId()) + "__:" + tableName + m_table.getTableNameSeparator() + "*";
psubscribe(m_db, m_keyspace);
```

## 4. ディスパッチ — doTask への合流

keyspace 通知到達後の制御フロー:

```
Redis: PUBLISH "__keyspace@4__:LOOPBACK_INTERFACE|Loopback0"  "hset"
  ↓ SubscriberStateTable::readData() でイベントバッファに積む
  ↓ Consumer::execute() → IntfMgr::doTask(Consumer&)
  ↓ consumer.getTableName() == CFG_LOOPBACK_INTERFACE_TABLE_NAME
  ↓ doIntfGeneralTask()  (属性ロウ: key に "|" なし)
  ↓ or doIntfAddrTask()  (IP プレフィクスロウ: key に "|<ip/prefix>")
```

`doTask()` 内でキー形式（区切り文字 `|` の有無）によって `doIntfGeneralTask` / `doIntfAddrTask` を振り分ける（`intfmgr.cpp`）。

## 5. 起動時スナップショット

`SubscriberStateTable` コンストラクタは購読開始前に既存エントリを `HGETALL` 相当でスキャンして `m_buffer` に流し込む:

```cpp
// sonic-swss-common/common/subscriberstatetable.cpp:26-42
vector<string> keys;
m_table.getKeys(keys);
for (const auto &key: keys)
{
    // 既存キーを SET として m_buffer に追加
    m_buffer.push_back(kco);
}
```

これにより `intfmgrd` 起動時に CONFIG_DB に既存する `LOOPBACK_INTERFACE|*` エントリがすべて `SET` として再適用される。Cold restart 時は `flushLoopbackIntfs()` でカーネルから全 Loopback を削除した後に再作成する（`intfmgr.cpp:57`）。Warm start 時は `buildIntfReplayList()` が同様に CONFIG_DB から収集してリプレイする。

## 6. APPL_DB 書込み — ProducerStateTable (channel PUBLISH)

`intfmgrd` が CONFIG_DB の変更を処理した後、`m_appIntfTableProducer`（`ProducerStateTable(appDb, APP_INTF_TABLE_NAME)`）を使って APPL_DB へ書き込む:

```cpp
// sonic-swss/cfgmgr/intfmgr.cpp:42
m_appIntfTableProducer(appDb, APP_INTF_TABLE_NAME)

// intfmgr.cpp:1053
m_appIntfTableProducer.set(alias, data);
```

`ProducerStateTable::set()` は Lua スクリプトで `SADD <TABLE>_KEY_SET <key>` + `HSET _<TABLE>|<key> <fields>` を実行し、変更があれば `PUBLISH INTF_TABLE_CHANNEL@<dbId> G` を発行する:

```lua
// ProducerStateTable luaSet の Publish 部分
if added > 0 then
    redis.call('PUBLISH', KEYS[1], ARGV[1])
end
```

- チャンネル名: `INTF_TABLE_CHANNEL@<appDb.dbId>`（`Table::getChannelName(dbId)`）
- `IntfsOrch` は APPL_DB に対して `ConsumerStateTable` を使い `INTF_TABLE_CHANNEL` を購読する（APPL_DB は `dbId != CONFIG_DB` のため `addConsumer` の `else` 分岐）。

## 7. IntfsOrch 側の購読（APPL_DB ConsumerStateTable）

`orchdaemon.cpp:296`:
```cpp
gIntfsOrch = new IntfsOrch(m_applDb, APP_INTF_TABLE_NAME, vrf_orch, m_chassisAppDb);
```

`IntfsOrch(db, tableName, ...)` → `Orch(db, tableName, intfsorch_pri)` → `Orch::addConsumer(applDb, "INTF_TABLE", 35)` の `else` 分岐で `ConsumerStateTable` が選ばれる（APPL_DB の dbId は通常 0 で CONFIG_DB ではないため）。

VOQ 環境では追加の `SubscriberStateTable` を `CHASSIS_APP_DB` に対して登録する（`intfsorch.cpp:102-107`）。

## 8. エンドツーエンドの通信メカニズム全体像

```
┌──────────────────────────────────────────────────────────────────────────┐
│ CONFIG_DB (dbId=4)                                                       │
│   HSET "LOOPBACK_INTERFACE|Loopback0" vrf_name "" ...                   │
│   → Redis keyspace PUBLISH "__keyspace@4__:LOOPBACK_INTERFACE|Loopback0" │
└─────────────────────┬────────────────────────────────────────────────────┘
                      │ psubscribe パターンマッチ
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ intfmgrd (swss コンテナ)                                                │
│   SubscriberStateTable("LOOPBACK_INTERFACE")                            │
│   → Consumer::execute() → doIntfGeneralTask() / doIntfAddrTask()        │
│   → ip link add Loopback0 mtu 65536 type dummy  (kernel)                │
│   → m_appIntfTableProducer.set("Loopback0", data)                       │
│     SADD INTF_TABLE_KEY_SET Loopback0                                   │
│     HSET _INTF_TABLE|Loopback0 vrf_name "" mac_addr "00:..."            │
│     PUBLISH INTF_TABLE_CHANNEL@0 G                                      │
│   → m_stateIntfTable.hset("Loopback0", "vrf", "")  (STATE_DB)          │
└─────────────────────┬────────────────────────────────────────────────────┘
                      │ INTF_TABLE_CHANNEL SUBSCRIBE
                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ orchagent IntfsOrch (swss コンテナ)                                     │
│   ConsumerStateTable("INTF_TABLE")                                      │
│   → doTask() → doIntfTask()                                             │
│   → sai_router_intf_api->create_router_interface(...)                   │
│   → COUNTERS_RIF_NAME_MAP / COUNTERS_RIF_TYPE_MAP 更新 (≤1秒後)        │
└─────────────────────────────────────────────────────────────────────────┘
```

## 9. TTL / 永続性

- CONFIG_DB の `LOOPBACK_INTERFACE` エントリに TTL は設定されない（CONFIG_DB は永続前提）。
- `notify-keyspace-events` は SONiC の `database_config.json` で有効化されている前提（`K` フラグを含む）。

## 10. 関連リファレンス

- `sonic-swss/cfgmgr/intfmgrd.cpp:19-80` (main、tableNames 構築、Select ループ)
- `sonic-swss/cfgmgr/intfmgr.cpp:31-76` (IntfMgr ctor、SubscriberStateTable 登録)
- `sonic-swss/cfgmgr/intfmgr.cpp:1053,1088,1137,1161` (ProducerStateTable.set/del 呼び出し)
- `sonic-swss/orchagent/orchdaemon.cpp:296` (IntfsOrch 生成、APP_INTF_TABLE_NAME)
- `sonic-swss/orchagent/intfsorch.cpp:61-108` (IntfsOrch ctor、ConsumerStateTable / VOQ SubscriberStateTable)
- `sonic-swss-common/common/subscriberstatetable.cpp:17-43` (SubscriberStateTable ctor、psubscribe、起動スナップショット)
- `sonic-swss-common/common/producerstatetable.cpp:72-120` (luaSet / PUBLISH ロジック)
- `sonic-swss-common/common/table.h:85-96` (getChannelName)
- `sonic-swss-common/common/table.h:164` (DEFAULT_POP_BATCH_SIZE = 128)
