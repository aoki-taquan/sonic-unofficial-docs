# srv6-applb Phase G: Redis 通信メカニズム調査

## 調査対象
- `sonic-swss/orchagent/srv6orch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/orch.cpp` L1186-1196

## 調査日
2026-05-18

## 調査結果

### Srv6Orch のコンシューマ構成 (orchdaemon.cpp:312-324)

Srv6Orch は以下の 4 テーブルを消費する:
1. `APPL_DB SRV6_SID_LIST_TABLE` (db_id=0) → ConsumerStateTable
2. `APPL_DB SRV6_MY_SID_TABLE` (db_id=0) → ConsumerStateTable
3. `APPL_DB PIC_CONTEXT_TABLE` (db_id=0) → ConsumerStateTable
4. `CONFIG_DB SRV6_MY_SID_TABLE` (db_id=4) → SubscriberStateTable

### db_id によるコンシューマ切り替え (orch.cpp:1186-1196)

```cpp
void Orch::addConsumer(DBConnector *db, string tableName, int pri) {
    if (db->getDbId() == CONFIG_DB)
        addExecutor(new Consumer(new SubscriberStateTable(...), this, tableName));
    else
        addExecutor(new Consumer(new ConsumerStateTable(...), this, tableName));
}
```

- APPL_DB (db_id=0): `ConsumerStateTable` — `ProducerStateTable` と組み合わせて使用。
  fpmsyncd が `ProducerStateTable::set()` で書き込み、Srv6Orch が LPOP で取得する。
- CONFIG_DB (db_id=4): `SubscriberStateTable` — Redis keyspace notification で変更を検出し、HGETALL でフィールドを取得する。

### 書き込み元ごとの通信方式

| テーブル | 書き込み元 | 通信方式 | 備考 |
|---------|----------|---------|------|
| APPL_DB SRV6_SID_LIST_TABLE | fpmsyncd | ProducerStateTable → ConsumerStateTable (LPOP) | routesync.cpp:1396-1410 |
| APPL_DB SRV6_MY_SID_TABLE | fpmsyncd | ProducerStateTable → ConsumerStateTable (LPOP) | routesync.cpp:1169-1182 |
| CONFIG_DB SRV6_MY_SID_TABLE | sonic-cfggen / SONiC CLI | SubscriberStateTable (keyspace notification + HGETALL) | |

### Neighbor 通知: Observer パターン

`Srv6Orch` は `m_neighOrch->attach(this)` で NeighOrch の Observer に登録する (srv6orch.cpp:110)。
Neighbor ADD/DEL イベントは `Srv6Orch::updateNeighbor()` コールバックで受信する (srv6orch.cpp:1212)。
これは pub/sub ではなく C++ Observer パターンによる直接コールバックであり、Redis チャンネルを使用しない。

### APPL_DB への書き戻しなし

`doTaskMySidTable()` は APPL_DB への書き戻しを一切行わない。SET/DEL イベント処理後は SAI のみに作用し、
APPL_DB 側のテーブルへフィールドを書き戻す実装は存在しない。
