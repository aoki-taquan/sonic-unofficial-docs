# APPL_DB FDB_TABLE — 通信メカニズム (Phase G) 解析メモ

対象: `APPL_DB` の `FDB_TABLE` (および `VXLAN_FDB_TABLE` / `MCLAG_FDB_TABLE`)。書込主体は `sonic-swss/orchagent/fdborch.cpp` の `FdbOrch`。

## 1. 購読 API — `swss::ConsumerStateTable` (channel ベース PUBLISH/SUBSCRIBE)

`FdbOrch` のコンストラクタ (`fdborch.cpp:27-49`) は `Orch(applDbConnector, appFdbTables)` を呼び出し、`appFdbTables` に列挙された 3 つの APPL_DB テーブルを **`Orch::addConsumer()`** 経由で executor 化する。`Orch::addConsumer()` は DB ID で分岐し、CONFIG_DB / STATE_DB / CHASSIS_APP_DB 以外（= APPL_DB）には `ConsumerStateTable` を割り当てる (`orch.cpp:1186-1196`)。

```cpp
// sonic-swss/orchagent/orch.cpp:1186-1196
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ..., pri), this, tableName));
    else
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

```cpp
// sonic-swss/orchagent/orchdaemon.cpp:226-235
vector<table_name_with_pri_t> app_fdb_tables = {
    { APP_FDB_TABLE_NAME,        FdbOrch::fdborch_pri },
    { APP_VXLAN_FDB_TABLE_NAME,  FdbOrch::fdborch_pri },
    { APP_MCLAG_FDB_TABLE_NAME,  FdbOrch::fdborch_pri }
};
TableConnector stateDbFdb(m_stateDb, STATE_FDB_TABLE_NAME);
TableConnector stateMclagDbFdb(m_stateDb, STATE_MCLAG_REMOTE_FDB_TABLE_NAME);
gFdbOrch = new FdbOrch(m_applDb, app_fdb_tables, stateDbFdb, stateMclagDbFdb, gPortsOrch);
```

- **keyspace 通知 (`__keyspace@<dbId>__:...`) は使わない**。APPL_DB 側 producer は `ProducerStateTable::set()` 経由で `<TABLE>_KEY_SET` への要素追加と `<TABLE>_CHANNEL@<dbId>` への `PUBLISH "G"` を行う。
- 優先度は **`FdbOrch::fdborch_pri = 20`** (`fdborch.cpp:25`) 固定。Orch スケジューラの相対優先度として使われ、CONFIG_DB から変更不可。
- バッチサイズは `gBatchSize` (`main.cpp:459` で `DEFAULT_BATCH_SIZE = 128`、`orchagent -b <n>` (`main.cpp:478`) で上書き可能)。

| 購読者 | 購読 API | 購読テーブル | 優先度 | バッチ |
|--------|---------|--------------|--------|--------|
| `orchagent` (`FdbOrch`) | `swss::ConsumerStateTable` | `FDB_TABLE` | `fdborch_pri = 20` | `gBatchSize` (default 128) |
| `orchagent` (`FdbOrch`) | 同上 | `VXLAN_FDB_TABLE` | 同上 | 同上 |
| `orchagent` (`FdbOrch`) | 同上 | `MCLAG_FDB_TABLE` | 同上 | 同上 |

## 2. channel PUBLISH → ハンドラ呼び出しの流れ

```
fdbsyncd / swssconfig / vlanmgr (PAC) / vxlanmgr (EVPN)
  ↓ ProducerStateTable::set(<vlan>:<mac>, fvs)
APPL_DB: HSET "_FDB_TABLE:<vlan>:<mac>" port=<...> type=<...>
  ↓ Redis PUBLISH "FDB_TABLE_CHANNEL@0" "G"
OrchDaemon main loop: m_select->select(&s, SELECT_TIMEOUT)
  ↓ Consumer::execute() → ConsumerStateTable::pops()
FdbOrch::doTask(Consumer&)  (fdborch.cpp:707-)
  ↓ consumer.getTableName() で origin を分岐 (FDB / VXLAN_FDB / MCLAG_FDB)
addFdbEntry() / removeFdbEntry()
  ↓
SAI: sai_fdb_api->create_fdb_entry / remove_fdb_entry
```

- `doTask(Consumer&)` 冒頭で `m_portsOrch->allPortsReady()` が false の間は **全 FDB イベント処理を停止** (`fdborch.cpp:711-714`)。
- 3 つの APPL_DB テーブルは別々の `Consumer` executor を持つが、`doTask` は共通実装で `consumer.getTableName()` (`fdborch.cpp:718-727`) により `FDB_ORIGIN_PROVISIONED` / `FDB_ORIGIN_VXLAN_ADVERTIZED` / `FDB_ORIGIN_MCLAG_ADVERTIZED` に分岐する。
- TTL は APPL_DB の FDB エントリで設定されない（再起動非永続だが期限なし）。

## 3. PortsOrch observer (内部通知パス)

channel PUBLISH 以外に、FdbOrch は `PortsOrch` の **C++ レベル observer** として登録される (`fdborch.cpp:39` `m_portsOrch->attach(this)`)。

| `SubjectType` | ディスパッチ先 | 経由メソッド |
|---|---|---|
| `SUBJECT_TYPE_VLAN_MEMBER_CHANGE` | `updateVlanMember()` | `FdbOrch::update()` `fdborch.cpp:655-660` |
| `SUBJECT_TYPE_PORT_OPER_STATE_CHANGE` | `updatePortOperState()` | `FdbOrch::update()` `fdborch.cpp:661-666` |

- これは Redis 経由ではない**プロセス内コールバック**で、Orch スケジューラの doTask とは別パスで即時実行される。
- 主用途は `saved_fdb_entries[port_name]` に保留された SET の **自動 replay** と、port oper-down 時の動的 FDB 一括 flush。
- FdbOrch 自身も `notify(SUBJECT_TYPE_FDB_CHANGE, ...)` / `notify(SUBJECT_TYPE_FDB_FLUSH_CHANGE, ...)` (`fdborch.cpp:199, 391, 415, 544, 619, 1199, 1626, 1736`) で `NeighOrch` 等の下流に通知する。

## 4. NotificationConsumer 経路 (Redis NOTIFICATIONS / FLUSHFDBREQUEST)

`FdbOrch` コンストラクタ (`fdborch.cpp:40-48`) は 2 つの `NotificationConsumer` も追加で executor 化する。

| Notification チャンネル | DB | 用途 |
|---|---|---|
| `FLUSHFDBREQUEST` (APPL_DB) | APPL_DB | `sonic-clear fdb all` 等の flush 要求受信 |
| `NOTIFICATIONS` (ASIC_DB) | ASIC_DB | SAI からの FDB event (LEARN / AGED / MOVE / FLUSHED) 受信 |

- いずれも `NotificationConsumer` (= Redis `SUBSCRIBE` channel ベース) で、`ConsumerStateTable` とは別の Executor / Selectable として OrchDaemon の `Select` ループに参加する。
- channel 名は `swsscommon` の `NotificationProducer` 既定 (`<channel>` をそのまま `SUBSCRIBE`) で、keyspace 通知ではない。

## 5. warm-restart 時の追加経路 — `bake()`

`FdbOrch::bake()` (`fdborch.cpp:51-65`) は warm-restart 時に **STATE_DB `FDB_TABLE` から `m_toSync` を再充填** する経路を持つ。

```cpp
// sonic-swss/orchagent/fdborch.cpp:51-65
bool FdbOrch::bake()
{
    Orch::bake();
    auto consumer = dynamic_cast<Consumer *>(getExecutor(APP_FDB_TABLE_NAME));
    size_t refilled = consumer->refillToSync(&m_fdbStateTable);
    SWSS_LOG_NOTICE("Add warm input FDB State: %s, %zd", APP_FDB_TABLE_NAME, refilled);
    return true;
}
```

- warm-restart 復帰時は通常の channel PUBLISH を待たず、STATE_DB に残っていたローカル MAC を APP_FDB_TABLE consumer の `m_toSync` に**直接 push** して replay する。`VXLAN_FDB_TABLE` / `MCLAG_FDB_TABLE` 側には bake パスなし。

## 6. サービス再起動トリガー

なし。`FdbOrch` は同一 orchagent プロセス内のハンドラであり、APPL_DB エントリの追加/削除は SAI FDB オブジェクトのライブ操作 (`sai_fdb_api->create_fdb_entry` / `remove_fdb_entry`) のみで反映され、プロセス再起動・サービス restart を伴わない。port oper-state / VLAN_MEMBER 変化は PortsOrch observer 経由でハンドラに到達する。

## 7. 参考行番号

- `sonic-swss/orchagent/fdborch.cpp`
  - 25: `const int FdbOrch::fdborch_pri = 20;`
  - 27-49: コンストラクタ (`Orch(applDbConnector, appFdbTables)` + `m_portsOrch->attach(this)` + `NotificationConsumer`)
  - 51-65: `bake()` (warm restart 再充填)
  - 199 / 391 / 415 / 544 / 619 / 1199 / 1626 / 1736: `notify(SUBJECT_TYPE_FDB_*_CHANGE, ...)`
  - 648-672: `FdbOrch::update()` (PortsOrch observer ディスパッチ)
  - 707-727: `doTask(Consumer&)` (`allPortsReady()` ガード + `getTableName()` による origin 分岐)
- `sonic-swss/orchagent/orch.cpp:1186-1196`: `Orch::addConsumer()` (`ConsumerStateTable` vs `SubscriberStateTable` 分岐)
- `sonic-swss/orchagent/orchdaemon.cpp:226-235`: `app_fdb_tables` の bind と `FdbOrch` 生成
- `sonic-swss/orchagent/main.cpp:459, 478`: `gBatchSize = 128` / `-b` オプション
- `sonic-swss-common/common/schema.h`: `APP_FDB_TABLE_NAME` / `APP_VXLAN_FDB_TABLE_NAME` / `APP_MCLAG_FDB_TABLE_NAME`
