# vxlan-fdb — 通信メカニズム (pubsub) 調査メモ

## 調査対象

`docs/reference/config-db/vxlan-fdb.md` Phase G 追加分。
`fdbsyncd` → `APP_DB VXLAN_FDB_TABLE` → `FdbOrch` の通信経路・購読方式を調査する。

## 調査ファイル

- `sonic-swss/fdbsyncd/fdbsync.cpp` — fdbsyncd の書き込み実装
- `sonic-swss/fdbsyncd/fdbsync.h` — `m_fdbTable: ProducerStateTable` 宣言
- `sonic-swss/orchagent/orchdaemon.cpp` — FdbOrch 生成・テーブル登録
- `sonic-swss/orchagent/fdborch.cpp` — `fdborch_pri = 20` 定義
- `sonic-swss/orchagent/orch.cpp` — APPL_DB に対する ConsumerStateTable 選択ロジック

## 結果

### 書き込み側: fdbsyncd が ProducerStateTable を使用

`FdbSync` コンストラクタ (`fdbsync.cpp:25`):
```cpp
m_fdbTable(pipelineAppDB, APP_VXLAN_FDB_TABLE_NAME)
```
`m_fdbTable` の型は `ProducerStateTable` (`fdbsync.h:88`)。

- SET: `m_fdbTable.set(key, fvVector)` (`fdbsync.cpp:676`) — `VXLAN_FDB_TABLE_KEY_SET` に key を SADD し、`_VXLAN_FDB_TABLE:<key>` に HSET、`VXLAN_FDB_TABLE_CHANNEL@0` に PUBLISH
- DEL: `m_fdbTable.del(key)` (`fdbsync.cpp:645`)

warm-restart 中は `m_AppRestartAssist->insertToMap(APP_VXLAN_FDB_TABLE_NAME, ...)` でキャッシュに蓄積し APPL_DB への直接書き込みを遅延する (`fdbsync.cpp:641,672`)。

### 読み取り側: FdbOrch が ConsumerStateTable を使用

`orchdaemon.cpp:226-235`:
```cpp
vector<table_name_with_pri_t> app_fdb_tables = {
    { APP_FDB_TABLE_NAME,       FdbOrch::fdborch_pri },
    { APP_VXLAN_FDB_TABLE_NAME, FdbOrch::fdborch_pri },
    { APP_MCLAG_FDB_TABLE_NAME, FdbOrch::fdborch_pri }
};
gFdbOrch = new FdbOrch(m_applDb, app_fdb_tables, ...);
```

`Orch::addConsumer()` (`orch.cpp:1186-1196`) は APPL_DB (ID = 0) に対して **`ConsumerStateTable`** を選択する。
`fdborch_pri = 20` (`fdborch.cpp:25`)。バッチサイズは orchagent global の `gBatchSize` (default 128, `-b` 引数で変更可)。

### keyspace 通知は使用しない

`ProducerStateTable` → `ConsumerStateTable` ペアは `VXLAN_FDB_TABLE_CHANNEL@0` チャネルへの直接 PUBLISH/SUBSCRIBE を使用する。
CONFIG_DB の `__keyspace@4__:...` keyspace 通知とは無関係。

## 結論

fdbsyncd は `ProducerStateTable` (`m_fdbTable`) で `APP_DB VXLAN_FDB_TABLE` に書き込む。
FdbOrch は `ConsumerStateTable` で同テーブルを購読する。
この `ProducerStateTable/ConsumerStateTable` ペアが VXLAN_FDB_TABLE の唯一の通信経路であり、
keyspace PSUBSCRIBE は使用しない。

## evidence

- `sonic-swss/fdbsyncd/fdbsync.h:88` — `ProducerStateTable m_fdbTable`
- `sonic-swss/fdbsyncd/fdbsync.cpp:25` — `m_fdbTable(pipelineAppDB, APP_VXLAN_FDB_TABLE_NAME)`
- `sonic-swss/fdbsyncd/fdbsync.cpp:645,676` — `m_fdbTable.del/set()` 書き込み
- `sonic-swss/orchagent/orchdaemon.cpp:226-235` — FdbOrch + APP_VXLAN_FDB_TABLE_NAME 登録
- `sonic-swss/orchagent/fdborch.cpp:25` — `fdborch_pri = 20`
- `sonic-swss/orchagent/orch.cpp:1186-1196` — APPL_DB に対する ConsumerStateTable 選択
