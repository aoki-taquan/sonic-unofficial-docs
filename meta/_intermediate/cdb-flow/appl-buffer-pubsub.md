# appl-buffer — 通信メカニズム (Phase G) 中間調査

対象ページ: `docs/reference/config-db/appl-buffer.md`

APPL_DB の `BUFFER_POOL_TABLE` / `BUFFER_PROFILE_TABLE` / `BUFFER_PG_TABLE` / `BUFFER_QUEUE_TABLE` / `BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE` / `BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE` は **書き込み側 = `buffermgrd` (`buffermgrdyn` / `buffermgr`)、消費側 = `orchagent` の `BufferOrch`** という Producer / Consumer 関係。すべて APPL_DB (DB id = 0) 経由で、`ProducerStateTable` ↔ `ConsumerStateTable` で 1:1 接続される。

## 1. 書き込み側 (`buffermgrd`) — Producer

### 1.1 dynamic model (`buffermgrdyn`)

`sonic-swss/cfgmgr/buffermgrdyn.cpp` L42-L47, ヘッダ `buffermgrdyn.h` L208/L214:

```cpp
m_applBufferPoolTable(applDb, APP_BUFFER_POOL_TABLE_NAME),
m_applStateBufferPoolTable(applStateDb, APP_BUFFER_POOL_TABLE_NAME),
m_applBufferProfileTable(applDb, APP_BUFFER_PROFILE_TABLE_NAME),
m_applStateBufferProfileTable(applStateDb, APP_BUFFER_PROFILE_TABLE_NAME),
m_applBufferObjectTables{
    ProducerStateTable(applDb, APP_BUFFER_PG_TABLE_NAME),
    ProducerStateTable(applDb, APP_BUFFER_QUEUE_TABLE_NAME)},
m_applBufferProfileListTables{
    ProducerStateTable(applDb, APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME),
    ProducerStateTable(applDb, APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME)},
```

`m_applBufferPoolTable` / `m_applBufferProfileTable` は `buffermgrdyn.h:208/214` で `ProducerStateTable`。SHP 計算同期用に APPL_STATE_DB 側にも同名テーブル (`m_applStateBufferPoolTable` 等) を持つが、これは ResponsePublisher 経由の応答受信用 (`Table` クラス)。

### 1.2 static model (`buffermgr`)

`sonic-swss/cfgmgr/buffermgr.cpp` L25-L33, ヘッダ `buffermgr.h` L48/L50:

```cpp
m_cfgBufferProfileTable(cfgDb, CFG_BUFFER_PROFILE_TABLE_NAME),
m_cfgLosslessPgPoolTable(cfgDb, CFG_BUFFER_POOL_TABLE_NAME),
m_applBufferPoolTable(applDb, APP_BUFFER_POOL_TABLE_NAME),       // ProducerStateTable
m_applBufferProfileTable(applDb, APP_BUFFER_PROFILE_TABLE_NAME), // ProducerStateTable
m_applBufferPgTable(applDb, APP_BUFFER_PG_TABLE_NAME),
m_applBufferQueueTable(applDb, APP_BUFFER_QUEUE_TABLE_NAME),
m_applBufferIngressProfileListTable(applDb, APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME),
m_applBufferEgressProfileListTable(applDb, APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME)
```

`buffermgr` も 6 種すべて `ProducerStateTable` で書く。

`ProducerStateTable::set/del` の実体は swss-common `table.cpp` で、key を `<TABLE>_KEY_SET` / `_KEY_DEL` 中継ハッシュに書いて `<TABLE>_CHANNEL@<db_id>` に PUBLISH する。

## 2. 消費側 (`orchagent` の `BufferOrch`) — ConsumerStateTable

### 2.1 BufferOrch コンストラクタ

`sonic-swss/orchagent/orchdaemon.cpp` L386-L394:

```cpp
vector<string> buffer_tables = {
    APP_BUFFER_POOL_TABLE_NAME,
    APP_BUFFER_PROFILE_TABLE_NAME,
    APP_BUFFER_QUEUE_TABLE_NAME,
    APP_BUFFER_PG_TABLE_NAME,
    APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME,
    APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME
};
gBufferOrch = new BufferOrch(m_applDb, m_configDb, m_stateDb, buffer_tables);
```

`bufferorch.cpp` L53-L54:

```cpp
BufferOrch::BufferOrch(DBConnector *applDb, DBConnector *confDb, DBConnector *stateDb, vector<string> &tableNames) :
    Orch(applDb, tableNames),
```

`Orch(DBConnector*, const vector<string>&)` (`orch.cpp` L97-L103) は table ごとに `addConsumer(db, tableName, default_orch_pri=0)` を呼ぶ。

### 2.2 addConsumer の DB ID 分岐 — APPL_DB は `ConsumerStateTable`

`orch.cpp` L1186-L1196:

```cpp
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    {
        addExecutor(new Consumer(
            new SubscriberStateTable(db, tableName, TableConsumable::DEFAULT_POP_BATCH_SIZE, pri),
            this, tableName));
    }
    else
    {
        addExecutor(new Consumer(
            new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
    }
}
```

APPL_DB (DB id = 0) は `else` 側に落ちる → **6 テーブルすべて `ConsumerStateTable` で購読**。

- `gBatchSize`: `orch.cpp` L17 で `int gBatchSize = 0;`。コマンドラインフラグ `-b` で上書き可。0 のとき swss-common `consumerstatetable.cpp` 内の `DEFAULT_POP_BATCH_SIZE = 128` が適用される (per `pops()` の Lua SCRIPT)
- `pri = default_orch_pri = 0` (`orch.h` L59) — 全 BUFFER テーブルとも同一優先度

`ConsumerStateTable` は **`SUBSCRIBE <TABLE>_CHANNEL@0`** を発行し、PUBLISH 受信のたびに `pops()` で `<TABLE>_KEY_SET` / `_KEY_DEL` ハッシュからエントリを取り出す (swss-common `consumerstatetable.cpp`)。`SubscriberStateTable` の `PSUBSCRIBE __keyspace@N__:<table>|*` とは別経路。

### 2.3 doTask の drain 順序 — Pool → Profile → 残り

`bufferorch.cpp` L2040-L2073:

```cpp
void BufferOrch::doTask()
{
    auto pool_consumer = getExecutor((APP_BUFFER_POOL_TABLE_NAME));
    pool_consumer->drain();

    auto profile_consumer = getExecutor(APP_BUFFER_PROFILE_TABLE_NAME);
    profile_consumer->drain();

    for(auto &it : m_consumerMap)
    {
        auto consumer = it.second.get();
        if (consumer == profile_consumer) continue;
        if (consumer == pool_consumer)    continue;
        consumer->drain();
    }
    gPortsOrch->flushCounters();
}
```

- `default_orch_pri` は同値だが、`doTask()` がオーバーライドされており、**Select の優先度ではなく drain の明示順** で依存解決 (pool → profile → pg/queue/profile-list) を行う
- 各 `consumer->drain()` は `Consumer::drain()` → `Executor::execute()` → `Orch::doTask(Consumer&)` (= `BufferOrch::doTask(Consumer&)`, L2075) を呼び、`m_toSync` を消化する
- 既定の `Orch::doTask()` が `m_consumerMap` をイテレートする実装と異なり、BufferOrch は **同一 doTask 呼出で 6 テーブルすべてを順序付きで掃く**

### 2.4 orchagent 主ループの select 周期

`orchdaemon.cpp` L23, L959:

```cpp
#define SELECT_TIMEOUT 1000
ret = m_select->select(&s, SELECT_TIMEOUT);
```

APPL_DB の PUBLISH 受信ごとに `Select::select` が return し、対応する Consumer の `execute()` → `BufferOrch::doTask(Consumer&)` が走る。1000 ms タイムアウト時は `Orch::doTask()` (= 上記 drain チェーン) が pipeline flush と合わせて呼ばれる。

### 2.5 ガード — `isConfigDone` / `isInitDone`

`bufferorch.cpp` L2079-L2091:

```cpp
if (gMySwitchType == "voq")
{
    if(!gPortsOrch->isInitDone())  return;   // VOQ chassis
}
else if (!gPortsOrch->isConfigDone())
{
    return;                                   // 非 VOQ
}
```

port 初期化前に PUBLISH を受けても消化せず、`m_toSync` に積み残して次回 select で再試行。

## 3. ResponsePublisher による上り通知 (APPL_STATE_DB)

`orch.h` L382:

```cpp
ResponsePublisher m_publisher{"APPL_STATE_DB"};
```

`ResponsePublisher` (`response_publisher.cpp` L67-L78) は `APPL_STATE_DB` への通常 HSET と Redis Pub/Sub (`<TABLE>_RESPONSE_CHANNEL`) で **buffermgrdyn / config-validator 側に SAI 反映完了 ack を返す**。BufferOrch から呼ばれるのは:

| 行 | テーブル | 内容 | 条件 |
|---|---|---|---|
| `bufferorch.cpp:555` | `APP_BUFFER_POOL_TABLE_NAME` | `xoff=<value>` (force=true) | pool SET 成功 + `xoff` 非空 (SHP 有効時) |
| `bufferorch.cpp:589` | `APP_BUFFER_POOL_TABLE_NAME` | 空 fvs (force=true) | pool DEL 成功 |
| `bufferorch.cpp:832` | `APP_BUFFER_PROFILE_TABLE_NAME` | 全 fvs (force=true) | profile 新規 SET 成功 |
| `bufferorch.cpp:880` | `APP_BUFFER_PROFILE_TABLE_NAME` | 全 fvs (force=true) | profile 更新成功 |

PG / Queue / PROFILE_LIST 系の handler は `m_publisher.publish()` を呼ばない (上り ack なし)。

buffermgrdyn 側は `m_applStateBufferPoolTable` / `m_applStateBufferProfileTable` (型 `Table`、`buffermgrdyn.h:209/215`) を polling/直読みする経路で、Pub/Sub channel 購読ではない。

## 4. PUBSUB チャネルまとめ

| 経路 | DB | チャンネル | 書き込み元 | 消費者 |
|---|---|---|---|---|
| buffermgrd → APPL_DB BUFFER_POOL | 0 | `BUFFER_POOL_TABLE_CHANNEL@0` | ProducerStateTable | BufferOrch ConsumerStateTable |
| buffermgrd → APPL_DB BUFFER_PROFILE | 0 | `BUFFER_PROFILE_TABLE_CHANNEL@0` | ProducerStateTable | BufferOrch ConsumerStateTable |
| buffermgrd → APPL_DB BUFFER_PG | 0 | `BUFFER_PG_TABLE_CHANNEL@0` | ProducerStateTable | BufferOrch ConsumerStateTable |
| buffermgrd → APPL_DB BUFFER_QUEUE | 0 | `BUFFER_QUEUE_TABLE_CHANNEL@0` | ProducerStateTable | BufferOrch ConsumerStateTable |
| buffermgrd → APPL_DB BUFFER_PORT_INGRESS_PROFILE_LIST | 0 | `BUFFER_PORT_INGRESS_PROFILE_LIST_TABLE_CHANNEL@0` | ProducerStateTable | BufferOrch ConsumerStateTable |
| buffermgrd → APPL_DB BUFFER_PORT_EGRESS_PROFILE_LIST | 0 | `BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE_CHANNEL@0` | ProducerStateTable | BufferOrch ConsumerStateTable |
| BufferOrch → APPL_STATE_DB BUFFER_POOL | n/a | `BUFFER_POOL_TABLE_RESPONSE_CHANNEL` | ResponsePublisher | buffermgrdyn / config-validator |
| BufferOrch → APPL_STATE_DB BUFFER_PROFILE | n/a | `BUFFER_PROFILE_TABLE_RESPONSE_CHANNEL` | ResponsePublisher | buffermgrdyn / config-validator |

DB 番号: APPL_DB = 0、APPL_STATE_DB は別 logical DB。

## 5. バッチ / リトライ / 優先度

- **batch size**: `gBatchSize = 0` → swss-common `DEFAULT_POP_BATCH_SIZE = 128` (per `ConsumerStateTable::pops()` Lua SCRIPT 一回あたり最大 128 keys)
- **priority**: `default_orch_pri = 0` (BUFFER テーブル全て同値)。Select は同優先度なので **doTask 内の手動 drain 順** で依存解決
- **retry**: `task_need_retry` で `it++` のみ (`m_toSync` から erase しない) → 次回 select 回でリトライ。明示的な sleep / backoff なし
- **task_failed**: doTask 関数を `return` で抜けるため、その回の残タスクは次回まで保留 (`bufferorch.cpp:2117-2120`)
- **immediate 2-stage retry** (profile のみ): `processBufferProfile()` L778-L797 で SAI set 失敗時に同 attr で 1 回だけ即時再呼び出し (ベンダ transient 吸収)

## 6. リスナー再生 (warm reboot / 起動初期)

`ConsumerStateTable` 自体は KEYS 再生を行わない (`SubscriberStateTable` と違って) ため、buffermgrdyn 側が起動時に CONFIG_DB の現状を読み込んで `ProducerStateTable::set()` で APPL_DB に再書き込みする。BufferOrch はその PUBLISH を通常通り受ける。

warm reboot 時は `BufferOrch::initBufferReadyLists()` (`bufferorch.cpp` L86-L143) が APPL_DB の `BUFFER_PG_TABLE` / `BUFFER_QUEUE_TABLE` の `Table::getKeys()` で初期 ready list を直接読み込む (Pub/Sub ではなく直読)。cold/fast start 時は CONFIG_DB の `BUFFER_PG` / `BUFFER_QUEUE` を直読み。

## 7. 参照

- `sonic-swss/orchagent/bufferorch.cpp` L53-L84, L2040-L2138
- `sonic-swss/orchagent/orchdaemon.cpp` L23, L386-L394, L959
- `sonic-swss/orchagent/orch.cpp` L17, L97-L103, L1186-L1196
- `sonic-swss/orchagent/orch.h` L59 (`default_orch_pri`), L382 (`m_publisher`)
- `sonic-swss/orchagent/response_publisher.cpp` L67-L150
- `sonic-swss/cfgmgr/buffermgr.cpp` L25-L33; `buffermgr.h` L48/L50
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` L42-L51; `buffermgrdyn.h` L208/L214
- `sonic-swss-common/common/consumerstatetable.cpp` (Pub/Sub + `pops()` Lua SCRIPT)
- `sonic-swss-common/common/producerstatetable.cpp` (`<TABLE>_CHANNEL` PUBLISH)
