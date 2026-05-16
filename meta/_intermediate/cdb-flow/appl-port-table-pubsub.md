# APPL_DB PORT_TABLE — 通信メカニズム (Phase G) 解析メモ

対象: APPL_DB `PORT_TABLE`（producer: `portsyncd` / `portmgrd` / `orchagent` 自書き戻し、consumer: `orchagent` PortsOrch）。

source ref: `sonic-net/sonic-swss` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`、`sonic-net/sonic-swss-common` @ `158de8d3463ff4b841653f6d57190bb142b80d9c`

## 1. 購読 API — `ConsumerStateTable`（channel ベース、batch pop）

PortsOrch は APPL_DB を購読するため `Orch::addConsumer()` 経由で **`ConsumerStateTable`** をテーブルごとに登録する。CONFIG_DB / STATE_DB / CHASSIS_APP_DB のような keyspace 通知ベースの `SubscriberStateTable` ではない点に注意。

```cpp
// orchagent/orch.cpp:1185-1196
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    {
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName,
            TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
    }
    else
    {
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName,
            gBatchSize, pri), this, tableName));
    }
}
```

APPL_DB は上記 if 分岐の **else 側**（DB_ID は CONFIG/STATE/CHASSIS_APP のいずれでもない）に入るため、`ConsumerStateTable` が使われる。

- producer 側は `ProducerStateTable` で `_<TABLE>_KEY_SET` セットに key を push し、Lua スクリプト経由で `PUBLISH <channel> G` を打つ（`sonic-swss-common/common/producerstatetable.cpp:104-108` の Lua）。
- consumer 側は `consumer_state_table_pops.lua` で `SPOP <KEY_SET>` してから `HGETALL <TABLE>:<key>` を一括取得する（`sonic-swss-common/common/consumerstatetable.cpp:35-50`）。
- channel 名は `getChannelName(db_id)` 形式（DB ID ごとに 1 channel、テーブル単位ではない）。Lua の `redis.call('PUBLISH', KEYS[1], ARGV[1])` がそれを叩く。

## 2. batch サイズ — `gBatchSize`（default 128、`-b` で可変）

```cpp
// orchagent/main.cpp:95-105
"-b batch_size: set consumer table pop operation batch size (default 128)"
// orchagent/main.cpp:459, 478
gBatchSize = DEFAULT_BATCH_SIZE;
case 'b': gBatchSize = atoi(optarg); break;
```

- `orchagent` 起動オプション `-b <N>` で APPL_DB consumer の pop batch サイズを変更可能。
- `gBatchSize = 0` のとき `Consumer::execute()` 系は `gBatchSize == 0 ? 30000 : gBatchSize` で 30000 を上限値として扱う（`orch.cpp:913`）。
- 大量ポート同時 SET 時はこの batch サイズで `pops()` が分割される（PortsOrch::doPortTask 内で `consumer.pops(entries)` — `portsorch.cpp:9629` ほか）。

## 3. テーブル登録 — `ports_tables` ベクトルで 6 テーブルまとめて投入

```cpp
// orchagent/orchdaemon.cpp:215-232
const int portsorch_base_pri = 40;
vector<table_name_with_pri_t> ports_tables = {
    { APP_PORT_TABLE_NAME,             portsorch_base_pri + 5 },  // PORT_TABLE
    { APP_SEND_TO_INGRESS_PORT_TABLE_NAME, portsorch_base_pri + 5 },
    { APP_VLAN_TABLE_NAME,             portsorch_base_pri + 2 },
    { APP_VLAN_MEMBER_TABLE_NAME,      portsorch_base_pri     },
    { APP_LAG_TABLE_NAME,              portsorch_base_pri + 4 },
    { APP_LAG_MEMBER_TABLE_NAME,       portsorch_base_pri     },
};
gPortsOrch = new PortsOrch(m_applDb, m_stateDb, ports_tables, m_chassisAppDb);
```

- `PORT_TABLE` の優先度は **45**（`portsorch_base_pri (=40) + 5`）。LAG_MEMBER (40) や VLAN_MEMBER (40) より高く、これにより同 cycle 内で PORT 系の SET が先に処理される。
- `PortsOrch::PortsOrch(...)` (`portsorch.cpp:723-724`) → `Orch(db, tableNames)` 基底コンストラクタが `addConsumer()` を呼び、`PORT_TABLE` に対して `ConsumerStateTable(m_applDb, "PORT_TABLE", gBatchSize, 45)` を登録する。

## 4. 追加 consumer — STATE_DB transceiver / CHASSIS_APP_DB system port

PortsOrch は APPL_DB 以外にも以下を購読する（こちらは `SubscriberStateTable`）:

```cpp
// orchagent/portsorch.cpp:984
Orch::addExecutor(new Consumer(new SubscriberStateTable(stateDb,
    STATE_TRANSCEIVER_INFO_TABLE_NAME, TableConsumable::DEFAULT_POP_BATCH_SIZE, 0),
    this, STATE_TRANSCEIVER_INFO_TABLE_NAME));

// orchagent/portsorch.cpp:1086, 1091 (VOQ chassis のみ)
Orch::addExecutor(new Consumer(new SubscriberStateTable(chassisAppDb, tableName,
    TableConsumable::DEFAULT_POP_BATCH_SIZE, 0), this, tableName));
```

これらは `gMySwitchType` や Gearbox 有無で条件付き登録。`PORT_TABLE` 本体の consumer 種別とは別物だが、`PortsOrch::doTask(Consumer&)` (`portsorch.cpp:6498-`) で table_name 別に分岐ディスパッチされる。

## 5. PortConfigDone / PortInitDone — テーブル内 sentinel key（特殊 channel ではない）

`PortConfigDone` / `PortInitDone` は **`PORT_TABLE` 内の特殊 key**であって、専用 channel や NotificationProducer ではない。portsyncd は通常の `ProducerStateTable::set()` でこれらの key を書き、orchagent は通常の `pops()` で `KeyOpFieldsValuesTuple` の `key` フィールドを文字列比較して検出する。

producer 側 (portsyncd):

```cpp
// portsyncd/portsyncd.cpp:71
ProducerStateTable p(&appl_db, APP_PORT_TABLE_NAME);
// portsyncd/portsyncd.cpp:171-176
static void notifyPortConfigDone(ProducerStateTable &p)
{
    FieldValueTuple finish_notice("count", to_string(g_portSet.size()));
    vector<FieldValueTuple> attrs = { finish_notice };
    p.set("PortConfigDone", attrs);
}
// portsyncd/portsyncd.cpp:134
p.set("PortInitDone", attrs);
```

consumer 側 (orchagent PortsOrch::doPortTask):

```cpp
// orchagent/portsorch.cpp:4585-4626
if (key == "PortConfigDone") {
    // ... setPortConfigState(PORT_CONFIG_RECEIVED) ...
    it = taskMap.begin();   // ← 保留中タスクを最初から再評価
    continue;
}
if (key == "PortInitDone") {
    if (!m_initDone) { addSystemPorts(); m_initDone = true; }
    it = taskMap.erase(it);
    continue;
}
```

- 通常の `PORT_TABLE:<alias>` SET が `PortConfigDone` 受信前に届いた場合、`portsorch.cpp:4772-4777` の保留分岐で `taskMap` に残され、`PortConfigDone` 受信時に `it = taskMap.begin()` で先頭から再評価される。
- `addExistingData(m_portTable.get())` (`portsorch.cpp:4386`) は warm-restart の `bake()` 後に呼ばれ、APPL_DB に残っている既存キーを `m_toSync` に投入してから上記 doTask ループに入る。

## 6. orchagent → APPL_DB の自書き戻し（producer 側）

PortsOrch は `m_portTable` を `Table`（`ProducerStateTable` ではない素の `Table`）として保持し、SAI 通知由来の `oper_status` / `flap_count` / `last_*_time` / Gearbox 状態を**直接 HSET** で書き戻す:

```cpp
// orchagent/portsorch.cpp:770
m_portTable = unique_ptr<Table>(new Table(db, APP_PORT_TABLE_NAME));
// portsorch.cpp:3890, 3930, 6643, 6656, 11244, 11259
m_portTable->set(port.m_alias, tuples);
m_portTable->hset(port.m_alias, "oper_status", "down");
m_portTable->hset(port.m_alias, "flap_count", flapCount);
```

- これは `ProducerStateTable` 経由ではないため `_PORT_TABLE_KEY_SET` を経由せず、Redis の `PUBLISH` も発火しない（通常の `HSET <key> <field> <value>`）。
- 結果: orchagent 自身の `ConsumerStateTable` consumer はこれら自書き戻しを検出しない（KEY_SET に投入されないため）。これは「自分の通知を自分が拾うループ」を回避する設計。
- 一方 `portsyncd` / `portmgrd` の書き込みは `ProducerStateTable::set()` 経由で KEY_SET + PUBLISH を伴うため、orchagent の consumer が即時拾う。

## 7. channel / TTL / 通知量

| 項目 | 値 | evidence |
|------|----|----------|
| Redis channel | `getChannelName(<APPL_DB id>)` (DB 0 用、テーブル単位ではなく DB 単位 1 ch) | `producerstatetable.cpp:104-108` の Lua `PUBLISH KEYS[1] ARGV[1]` |
| 通知 payload | 固定文字列 `"G"`（実際の差分は KEY_SET + HGETALL で取得） | 同上 Lua |
| pop batch | `gBatchSize` (default 128, `orchagent -b` で可変、0 で 30000 cap) | `orch.cpp:913, 1194` / `main.cpp:459, 478` |
| TTL | なし（APPL_DB の通常エントリは永続） | — |
| 自書き戻しの通知 | なし（`Table::hset` は KEY_SET を更新しない） | `portsorch.cpp:770, 6643` |

## 8. 例外: `FabricPortsOrch` の `APP_FABRIC_MONITOR_PORT_TABLE_NAME`

VOQ chassis の Fabric 監視用 `FABRIC_PORT_TABLE` は本ページのスコープ外だが、同じ `Orch::addConsumer` 経路で `ConsumerStateTable` として登録される（`orchdaemon.cpp:603-610`、優先度 `fabric_portsorch_base_pri = 30`）。`PORT_TABLE` とは独立した consumer。

## 9. 参考行番号

- `sonic-swss/orchagent/portsorch.cpp`
  - 723-724: `PortsOrch::PortsOrch(...)` で `Orch(db, tableNames)` 経由 consumer 登録
  - 770: `m_portTable = new Table(db, APP_PORT_TABLE_NAME)` — 書き戻し用 Table
  - 984: STATE_TRANSCEIVER_INFO 追加 consumer
  - 1086, 1091: VOQ chassis CHASSIS_APP_DB 追加 consumer
  - 3890, 3930, 6643, 6656, 11244, 11259: `m_portTable->set/hset` 自書き戻し
  - 4345, 4350: `bake()` で `PortConfigDone:count` と `PortInitDone` を検出
  - 4386: `addExistingData(m_portTable.get())` で APPL_DB の既存キーを `m_toSync` に投入
  - 4585-4626: `PortConfigDone` / `PortInitDone` 受信ハンドラ
  - 4772-4777: PortConfigDone 前の SET を保留
  - 6498-6502: `doTask(Consumer&)` で APP_PORT_TABLE_NAME 分岐
  - 9629: `consumer.pops(entries)` で batch pop
- `sonic-swss/orchagent/orch.cpp`
  - 17: `int gBatchSize = 0;`
  - 913: `auto threshold = gBatchSize == 0 ? 30000 : gBatchSize;`
  - 1185-1196: `Orch::addConsumer()` の `ConsumerStateTable` vs `SubscriberStateTable` 分岐
- `sonic-swss/orchagent/orchdaemon.cpp`
  - 215-232: `ports_tables` (priority 40+5 etc.) と `PortsOrch` 生成
- `sonic-swss/orchagent/main.cpp`
  - 95-105, 459, 478: `gBatchSize` 起動オプション
- `sonic-swss/portsyncd/portsyncd.cpp`
  - 71: `ProducerStateTable p(&appl_db, APP_PORT_TABLE_NAME)`
  - 134: `p.set("PortInitDone", attrs)`
  - 171-176: `notifyPortConfigDone()`
- `sonic-swss-common/common/producerstatetable.cpp`
  - 104-108: Lua の `redis.call('PUBLISH', KEYS[1], ARGV[1])`
- `sonic-swss-common/common/consumerstatetable.cpp`
  - 35-50: `pops()` の SPOP + HGETALL Lua
