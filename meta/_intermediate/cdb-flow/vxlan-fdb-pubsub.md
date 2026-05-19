# VXLAN_FDB_TABLE — 通信メカニズム (Phase G) 解析メモ

対象: APP_DB の `VXLAN_FDB_TABLE`（`APP_VXLAN_FDB_TABLE_NAME`）。

## 1. テーブルの位置づけ

`VXLAN_FDB_TABLE` は CONFIG_DB ではなく **APP_DB** のテーブルである。書き込み側は `fdbsyncd`（Linux netlink イベント駆動）、読み取り側は `orchagent` の `FdbOrch`（ConsumerStateTable）。

## 2. 書き込み側 — fdbsyncd の ProducerStateTable 書き込み

`fdbsyncd` はコンストラクタで `RedisPipeline` ベースの `ProducerStateTable` (`m_fdbTable`) を生成する:

```cpp
// fdbsync.cpp:25-26
m_fdbTable(pipelineAppDB, APP_VXLAN_FDB_TABLE_NAME),
```

MAC 学習時:
```cpp
// fdbsync.cpp:676
m_fdbTable.set(key, fvVector);
```

MAC 削除時:
```cpp
// fdbsync.cpp:645
m_fdbTable.del(key);
```

`ProducerStateTable` は APP_DB の channel `APP_VXLAN_FDB_TABLE_CHANNEL@0` に PUBLISH する。orchagent 側の `ConsumerStateTable` がこの channel を SUBSCRIBE する。

## 3. warm-restart 中のバッファリング

`fdbsyncd` は `AppRestartAssist` を使って warm-restart 中の書き込みをバッファリングする:

```cpp
// fdbsync.cpp:33-36
m_AppRestartAssist->registerAppTable(APP_VXLAN_FDB_TABLE_NAME, &m_fdbTable);
// warm-restart 中は insertToMap でバッファ、完了後に reconciliation
```

warm-restart タイムアウトは `DEFAULT_FDBSYNC_WARMSTART_TIMER = 120 秒`（`fdbsync.h`）。

## 4. 読み取り側 — FdbOrch の ConsumerStateTable

orchdaemon が `FdbOrch` を `ConsumerStateTable`（APPL_DB）で登録する:

```cpp
// orchdaemon.cpp:226-235
vector<table_name_with_pri_t> app_fdb_tables = {
    { APP_FDB_TABLE_NAME,        FdbOrch::fdborch_pri},
    { APP_VXLAN_FDB_TABLE_NAME,  FdbOrch::fdborch_pri},
    { APP_MCLAG_FDB_TABLE_NAME,  FdbOrch::fdborch_pri}
};
gFdbOrch = new FdbOrch(m_applDb, app_fdb_tables, ...);
```

`FdbOrch::doTask(Consumer&)` は `table_name == APP_VXLAN_FDB_TABLE_NAME` を判定してVXLAN FDB 処理パスに入る（`fdborch.cpp:719`）。

## 5. 通信フロー

```
Linux カーネル netlink RTM_NEWNEIGH / RTM_DELNEIGH
  ↓ fdbsyncd の netlink ハンドラ
  ↓ m_fdbTable.set() / del()   (ProducerStateTable)
  ↓ PUBLISH APP_VXLAN_FDB_TABLE_CHANNEL@0  + HSET APPL_DB:VXLAN_FDB_TABLE|<key>
orchagent ConsumerStateTable: APP_VXLAN_FDB_TABLE_CHANNEL を SUBSCRIBE
  ↓ select() → Consumer::execute() → FdbOrch::doTask()
  ↓ table_name == APP_VXLAN_FDB_TABLE_NAME
  ↓ FdbOrch::doVxlanFdbTask() (fdborch.cpp:778-900)
  ↓ SAI FDB エントリ作成 / VxlanTunnelOrch トンネルポート取得
```

## 6. 購読者一覧

| 購読者 | 購読方式 | 購読テーブル | ハンドラ |
|--------|---------|------------|--------|
| `orchagent` (`FdbOrch`) | `ConsumerStateTable` (channel ベース SUBSCRIBE) | `VXLAN_FDB_TABLE` (APP_DB) | `doVxlanFdbTask()` |

FdbOrch 以外で `VXLAN_FDB_TABLE` を購読するプロセスはなし。

## 7. CONFIG_DB との対比

- CONFIG_DB テーブルは `SubscriberStateTable`（keyspace 通知 PSUBSCRIBE）で購読される。
- APP_DB テーブルは `ConsumerStateTable`（channel ベース SUBSCRIBE + pipeline PUBLISH）で購読される。
- `VXLAN_FDB_TABLE` は APP_DB のため後者の方式。

## 8. 参考行番号

- `sonic-swss/fdbsyncd/fdbsync.cpp`
  - L25-26: `m_fdbTable` (ProducerStateTable) 初期化
  - L645: `m_fdbTable.del(key)` — MAC 削除
  - L676: `m_fdbTable.set(key, fvVector)` — MAC 書き込み
- `sonic-swss/orchagent/orchdaemon.cpp`
  - L226-235: `app_fdb_tables` + `FdbOrch` 生成
- `sonic-swss/orchagent/fdborch.cpp`
  - L719: `APP_VXLAN_FDB_TABLE_NAME` によるルーティング
  - L778-900: `doVxlanFdbTask()`
