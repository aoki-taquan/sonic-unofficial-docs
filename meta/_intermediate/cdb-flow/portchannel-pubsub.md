# PORTCHANNEL — Phase G: PUBSUB / Keyspace / Subscribers 調査メモ

調査日: 2026-05-15  
対象: `docs/reference/config-db/portchannel.md`

## 調査対象ソース

| ファイル | 役割 |
|---|---|
| `sonic-swss/cfgmgr/teammgrd.cpp` | teammgrd エントリポイント — Select ループ / Selectable 登録 |
| `sonic-swss/cfgmgr/teammgr.cpp` | TeamMgr — CONFIG_DB PORTCHANNEL 購読処理 |
| `sonic-swss/cfgmgr/teammgr.h` | TeamMgr クラス定義 |
| `sonic-swss/orchagent/orchdaemon.cpp` | PortsOrch — APP_DB LAG_TABLE 登録 |
| `sonic-swss/orchagent/portsorch.cpp` | PortsOrch::doTask() — APP_DB LAG_TABLE 消費 |
| `sonic-swss-common/common/subscriberstatetable.cpp` | SubscriberStateTable — Redis keyspace PSUBSCRIBE 実装 |
| `sonic-swss-common/common/producerstatetable.cpp` | ProducerStateTable — Redis PUBLISH 実装 |
| `sonic-swss-common/common/consumerstatetable.cpp` | ConsumerStateTable — SUBSCRIBE + Lua EVALSHA 実装 |
| `sonic-swss-common/common/schema.h` | テーブル名定数定義 |
| `sonic-swss-common/common/table.h` | getChannelName() 定義 |

---

## 1. CONFIG_DB → teammgrd: SubscriberStateTable (keyspace PSUBSCRIBE)

### 仕組み

`SubscriberStateTable` (`subscriberstatetable.cpp:17-43`) が CONFIG_DB (db_id=4) の PORTCHANNEL テーブルを購読する。

```
m_keyspace = "__keyspace@4__:PORTCHANNEL|*"
psubscribe(m_db, m_keyspace)    // Redis PSUBSCRIBE
```

- Redis の keyspace notification 機能により、`PORTCHANNEL|<name>` キーへの HSET / DEL 操作が発生すると、Redis が `__keyspace@4__:PORTCHANNEL|<name>` チャネルに `set` / `del` メッセージを PUBLISH する
- `SubscriberStateTable::readData()` が `redisGetReply()` で非ブロッキングに受信し `m_keyspace_event_buffer` に蓄積
- `pops()` がバッファを消費し `KeyOpFieldsValuesTuple` (key, op, fvs) に変換。op=`del` はそのまま DEL コマンド、それ以外は `m_table.get()` で実データを Redis から取得して SET コマンドに変換
- 初期化時に既存キーを全件バッファに積む (`m_buffer`) → 起動時の全量同期

### teammgrd での登録 (`teammgrd.cpp:55-73`)

```cpp
TableConnector conf_lag_table(&conf_db, CFG_LAG_TABLE_NAME);      // "PORTCHANNEL"
TableConnector conf_lag_member_table(&conf_db, CFG_LAG_MEMBER_TABLE_NAME);
TableConnector state_port_table(&state_db, STATE_PORT_TABLE_NAME);

vector<TableConnector> tables = {conf_lag_table, conf_lag_member_table, state_port_table};
TeamMgr teammgr(&conf_db, &app_db, &state_db, tables);

Select s;
s.addSelectables(o->getSelectables());   // fd-based epoll 登録

while (!received_sigterm) {
    ret = s.select(&sel, SELECT_TIMEOUT);  // SELECT_TIMEOUT=1000ms
    ...
    auto *c = (Executor *)sel;
    c->execute();
}
```

`Orch(tables)` の内部でテーブルごとに `SubscriberStateTable` が生成され `Select` に登録される。  
Redis の keyspace 通知が fd に届いた時点で `select()` が返り `execute()` → `doTask()` が呼ばれる。

### Subscriber: TeamMgr (`teammgr.cpp:149-165`)

```cpp
void TeamMgr::doTask(Consumer &consumer) {
    if (table == CFG_LAG_TABLE_NAME)        doLagTask(consumer);
    else if (table == CFG_LAG_MEMBER_TABLE_NAME) doLagMemberTask(consumer);
    else if (table == STATE_PORT_TABLE_NAME)     doPortUpdateTask(consumer);
}
```

---

## 2. TeamMgr → APP_DB: ProducerStateTable (PUBLISH)

### 仕組み

`ProducerStateTable` (`producerstatetable.cpp`) が APP_DB (APPL_DB, db_id=0) の `LAG_TABLE` ("APP_LAG_TABLE_NAME") を操作する。

- `set()` / `del()` 呼び出し時、Lua スクリプト (EVALSHA) が Redis に対して以下を実行:
  1. Key を key-set (`LAG_TABLE_KEY_SET`) に SADD
  2. フィールドを Hash に HSET (`LAG_TABLE|<name>`)
  3. `redis.call('PUBLISH', KEYS[1], ARGV[1])` でチャネル `LAG_TABLE_CHANNEL@<db_id>` にメッセージを PUBLISH

チャネル名: `LAG_TABLE_CHANNEL@0`  
(`table.h:90`: `getChannelName(tag) = m_tableName + "_CHANNEL@" + tag`)

### TeamMgr での APP_DB 書込み (`teammgr.cpp:515,545,559`)

| 関数 | APP_DB への書込み内容 |
|---|---|
| `setLagMtu()` | `m_appLagTable.set(alias, {{"mtu", mtu}})` → `LAG_TABLE|<name>` に mtu フィールド HSET + PUBLISH |
| `setLagTpid()` | `m_appLagTable.set(alias, {{"tpid", tpid}})` → TPID フィールド HSET + PUBLISH |
| `setLagLearnMode()` | `m_appLagTable.set(alias, {{"learn_mode", ...}})` → learn_mode HSET + PUBLISH |
| `addLag()` (内部) | admin_status / min_links / flags を `m_appLagTable.set()` で書込み |

---

## 3. APP_DB → PortsOrch (LagOrch): ConsumerStateTable (SUBSCRIBE + EVALSHA)

### 仕組み

`orchdaemon.cpp:222` で `APP_LAG_TABLE_NAME` (= `"LAG_TABLE"`) を priority 44 (`portsorch_base_pri + 4`) で登録。  
`ConsumerStateTable` が APP_DB の `LAG_TABLE_CHANNEL@0` を `SUBSCRIBE` で購読する。  
`PUBLISH` が来ると `execute()` → `pops()` (Lua EVALSHA) → `KeyOpFieldsValuesTuple` → `doTask(Consumer)` が呼ばれる。

### PortsOrch::doTask() 経路 (`portsorch.cpp:6492-6535`)

```cpp
if (table_name == APP_LAG_TABLE_NAME || table_name == CHASSIS_APP_LAG_TABLE_NAME)
    doLagTask(consumer);
```

`PortsOrch::doLagTask()` が `sai_lag_api->create_lag()` / `remove_lag()` を呼ぶ。

### 優先度処理順 (`portsorch.cpp:6466-6478`)

```cpp
auto tableOrder = { APP_PORT_TABLE_NAME, APP_LAG_TABLE_NAME, ... };
```

PORT → LAG → LAG_MEMBER → VLAN → VLAN_MEMBER の順でドレインする。

---

## 4. STATE_DB への書戻し

- `orchagent / LagOrch` が SAI LAG 作成後に `STATE_DB.LAG_TABLE|<name>` に `state=ok` を書込む
- `TeamMgr::isLagStateOk()` (`teammgr.cpp`) が `m_stateLagTable.get()` でポーリング → LAG STATE_DB 準備完了待ち
- `TeamMgr::doPortUpdateTask()` が `STATE_DB.PORT_TABLE` 変化通知 (SubscriberStateTable) を受け、LAG メンバの再追加を自動実行

---

## 5. チャネル / キー 一覧

| DB | Redis チャネル / パターン | 用途 |
|---|---|---|
| CONFIG_DB (db=4) | `__keyspace@4__:PORTCHANNEL\|*` | TeamMgr が PSUBSCRIBE — SET/DEL 検知 |
| APPL_DB (db=0) | `LAG_TABLE_CHANNEL@0` | PortsOrch の ConsumerStateTable が SUBSCRIBE — SET/DEL 受信 |
| STATE_DB (db=6) | `__keyspace@6__:LAG_TABLE\|*` | TeamMgr が STATE_DB SubscriberStateTable で LAG 状態を監視 |
| STATE_DB (db=6) | `__keyspace@6__:PORT_TABLE\|*` | TeamMgr が doPortUpdateTask() で PORT 再作成を検知 |

---

## 6. 通信シーケンス図 (概略)

```
CONFIG_DB PORTCHANNEL SET
  → Redis keyspace notify → PSUBSCRIBE "__keyspace@4__:PORTCHANNEL|*"
    → TeamMgr::doLagTask() → teamd spawn + ProducerStateTable::set()
      → APPL_DB LAG_TABLE HSET + PUBLISH "LAG_TABLE_CHANNEL@0"
        → ConsumerStateTable SUBSCRIBE → PortsOrch::doLagTask()
          → SAI create_lag() → STATE_DB LAG_TABLE state=ok
            → TeamMgr isLagStateOk() = true
```

---

## 7. ソース証跡

| コード箇所 | 内容 |
|---|---|
| `subscriberstatetable.cpp:20-22` | `m_keyspace = "__keyspace@<id>__:<table>|*"` + `psubscribe()` |
| `subscriberstatetable.cpp:45-83` | `readData()` — `redisGetReply()` でバッファ蓄積 |
| `subscriberstatetable.cpp:95-165` | `pops()` — keyspace event → SET/DEL 変換 |
| `producerstatetable.cpp:106-113` | Lua `PUBLISH KEYS[1] ARGV[1]` |
| `table.h:88-96` | `getChannelName(tag)` = `<tableName>_CHANNEL@<tag>` |
| `consumerstatetable.cpp:27` | `subscribe(m_db, getChannelName(...))` |
| `teammgrd.cpp:55-73` | TableConnector 3 本 + Select ループ |
| `teammgr.cpp:149-165` | `doTask()` — テーブル別ディスパッチ |
| `orchdaemon.cpp:222` | `APP_LAG_TABLE_NAME` priority 44 登録 |
| `portsorch.cpp:6527-6529` | `doLagTask(consumer)` 分岐 |
