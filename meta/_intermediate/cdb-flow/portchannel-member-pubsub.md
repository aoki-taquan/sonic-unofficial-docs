# PORTCHANNEL_MEMBER — Phase G: PUBSUB / Keyspace / Subscribers 調査メモ

調査日: 2026-05-16
対象: `docs/reference/config-db/portchannel-member.md`

## 調査対象ソース

| ファイル | 役割 |
|---|---|
| `sonic-swss/cfgmgr/teammgrd.cpp` | teammgrd エントリポイント — Select ループ / Selectable 登録 |
| `sonic-swss/cfgmgr/teammgr.cpp` | TeamMgr — CONFIG_DB PORTCHANNEL_MEMBER 購読処理 |
| `sonic-swss/orchagent/portsorch.cpp` | PortsOrch — APP_DB LAG_MEMBER_TABLE 消費 + SAI lag_member 操作 |
| `sonic-swss-common/common/subscriberstatetable.cpp` | SubscriberStateTable — Redis keyspace PSUBSCRIBE 実装 |
| `sonic-swss-common/common/producerstatetable.cpp` | ProducerStateTable — Redis PUBLISH 実装 |
| `sonic-swss-common/common/consumerstatetable.cpp` | ConsumerStateTable — SUBSCRIBE + Lua EVALSHA 実装 |

---

## 1. CONFIG_DB → teammgrd: SubscriberStateTable (keyspace PSUBSCRIBE)

### 仕組み

`SubscriberStateTable` (`subscriberstatetable.cpp:17-43`) が CONFIG_DB (db_id=4) の
`PORTCHANNEL_MEMBER` テーブル (= `CFG_LAG_MEMBER_TABLE_NAME`) を購読する。

```
m_keyspace = "__keyspace@4__:PORTCHANNEL_MEMBER|*"
psubscribe(m_db, m_keyspace)    // Redis PSUBSCRIBE
```

- `PORTCHANNEL_MEMBER|<lag>|<member>` キーへの HSET / DEL 操作が発生すると、
  Redis が `__keyspace@4__:PORTCHANNEL_MEMBER|<lag>|<member>` チャネルに
  `set` / `del` メッセージを PUBLISH する
- `SubscriberStateTable::readData()` が非ブロッキングに受信し `m_keyspace_event_buffer` に蓄積
- `pops()` がバッファを消費し `KeyOpFieldsValuesTuple` (key, op, fvs) に変換

### teammgrd での登録 (`teammgrd.cpp:55-65`)

```cpp
TableConnector conf_lag_table(&conf_db, CFG_LAG_TABLE_NAME);
TableConnector conf_lag_member_table(&conf_db, CFG_LAG_MEMBER_TABLE_NAME);  // "PORTCHANNEL_MEMBER"
TableConnector state_port_table(&state_db, STATE_PORT_TABLE_NAME);

vector<TableConnector> tables = {conf_lag_table, conf_lag_member_table, state_port_table};
TeamMgr teammgr(&conf_db, &app_db, &state_db, tables);
```

`Orch(tables)` の内部でテーブルごとに `SubscriberStateTable` が生成され `Select` に登録される。
Redis の keyspace 通知が fd に届いた時点で `select()` が返り `execute()` → `doTask()` が呼ばれる。

### Subscriber: TeamMgr (`teammgr.cpp:149-165`)

```cpp
void TeamMgr::doTask(Consumer &consumer) {
    if (table == CFG_LAG_TABLE_NAME)
        doLagTask(consumer);
    else if (table == CFG_LAG_MEMBER_TABLE_NAME)   // "PORTCHANNEL_MEMBER"
        doLagMemberTask(consumer);
    else if (table == STATE_PORT_TABLE_NAME)
        doPortUpdateTask(consumer);
}
```

---

## 2. TeamMgr → teamd: UNIX ソケット (teamdctl)

`doLagMemberTask()` は APP_DB を経由せず、`teamdctl` コマンド (UNIX ソケット) で teamd プロセスに
直接ポートの追加/削除を指示する。

- **SET**: `teamdctl <lag> port add <member>` — LACP ネゴシエーション開始
- **DEL**: `teamdctl <lag> port remove <member>` — LACP 切断

この経路は Redis PUBLISH を使用しない点で LAG_TABLE の経路と異なる。

---

## 3. TeamMgr → APP_DB: ProducerStateTable (PUBLISH)

teamd がポートの追加/削除を完了すると、TeamMgr が APP_DB `LAG_MEMBER_TABLE`
(= `APP_LAG_MEMBER_TABLE_NAME`) に `ProducerStateTable::set()` / `del()` で書き込む。

- Lua スクリプト (EVALSHA) が以下を実行:
  1. Key を key-set に SADD
  2. フィールドを Hash に HSET
  3. `redis.call('PUBLISH', KEYS[1], ARGV[1])` でチャネルに PUBLISH

チャネル名: `LAG_MEMBER_TABLE_CHANNEL@0`

---

## 4. APP_DB → PortsOrch (LagOrch): ConsumerStateTable (SUBSCRIBE + EVALSHA)

`orchdaemon.cpp` で `APP_LAG_MEMBER_TABLE_NAME` を登録。  
`ConsumerStateTable` が `LAG_MEMBER_TABLE_CHANNEL@0` を SUBSCRIBE で購読する。

### PortsOrch::doTask() 経路 (`portsorch.cpp:6531`)

```cpp
else if (table_name == APP_LAG_MEMBER_TABLE_NAME || table_name == CHASSIS_APP_LAG_MEMBER_TABLE_NAME)
    doLagMemberTask(consumer);
```

`PortsOrch::doLagMemberTask()` が `sai_lag_api->create_lag_member()` / `remove_lag_member()` を呼ぶ。

起動時スナップショット: `addExistingData(APP_LAG_MEMBER_TABLE_NAME)` (`portsorch.cpp:4388`) で
既存エントリを SET イベントとして再配信し SAI 状態を復元する。

---

## 5. チャネル / キー 一覧

| DB | Redis チャネル / パターン | 用途 |
|---|---|---|
| CONFIG_DB (db=4) | `__keyspace@4__:PORTCHANNEL_MEMBER\|*` | TeamMgr が PSUBSCRIBE — SET/DEL 検知 |
| teamd (UNIX ソケット) | `/var/run/teamd/<lag>.ctl` | `teamdctl port add/remove` — LACP 操作 |
| APPL_DB (db=0) | `LAG_MEMBER_TABLE_CHANNEL@0` | PortsOrch の ConsumerStateTable が SUBSCRIBE — SET/DEL 受信 |
| STATE_DB (db=6) | `__keyspace@6__:LAG_TABLE\|*` | TeamMgr が STATE_DB SubscriberStateTable で LAG 状態を監視 |
| STATE_DB (db=6) | `__keyspace@6__:PORT_TABLE\|*` | TeamMgr が doPortUpdateTask() で PORT 再作成を検知 |

---

## 6. 通信シーケンス図 (概略)

```
CONFIG_DB PORTCHANNEL_MEMBER SET
  → Redis keyspace notify → PSUBSCRIBE "__keyspace@4__:PORTCHANNEL_MEMBER|*"
    → TeamMgr::doLagMemberTask()
      → teamdctl <lag> port add <member>  (UNIX ソケット)
        → ProducerStateTable::set() → APPL_DB LAG_MEMBER_TABLE HSET
          + PUBLISH "LAG_MEMBER_TABLE_CHANNEL@0"
            → ConsumerStateTable SUBSCRIBE → PortsOrch::doLagMemberTask()
              → sai_lag_api->create_lag_member()
```

---

## 7. ソース証跡

| コード箇所 | 内容 |
|---|---|
| `subscriberstatetable.cpp:17-43` | keyspace PSUBSCRIBE 実装 |
| `teammgrd.cpp:55-65` | TableConnector 3 本 + Select ループ |
| `teammgr.cpp:149-165` | `doTask()` — テーブル別ディスパッチ |
| `teammgr.cpp:340` | `doLagMemberTask()` 定義開始 |
| `portsorch.cpp:4388` | `addExistingData(APP_LAG_MEMBER_TABLE_NAME)` — 起動時スナップショット |
| `portsorch.cpp:6531` | `doLagMemberTask(consumer)` 分岐 |
| `portsorch.cpp:8172` | `sai_lag_api->create_lag_member()` |
| `portsorch.cpp:8221` | `sai_lag_api->remove_lag_member()` |
| `producerstatetable.cpp:106-113` | Lua `PUBLISH KEYS[1] ARGV[1]` |
| `table.h:88-96` | `getChannelName(tag)` = `<tableName>_CHANNEL@<tag>` |
| `consumerstatetable.cpp:27` | `subscribe(m_db, getChannelName(...))` |
