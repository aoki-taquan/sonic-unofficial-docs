# DEFAULT_LOSSLESS_BUFFER_PARAMETER — 通信メカニズム (Phase G) 中間調査

対象ページ: `docs/reference/config-db/default-lossless-buffer-parameter.md`
対象テーブル: `CONFIG_DB` `DEFAULT_LOSSLESS_BUFFER_PARAMETER`
Consumer: `buffermgrdyn` (`sonic-swss/cfgmgr/buffermgrd.cpp`, `buffermgrdyn.cpp`)

---

## 1. 購読方式 — SubscriberStateTable (keyspace PSUBSCRIBE)

`buffermgrd.cpp` L174-186 でコンストラクタに渡す `vector<TableConnector>` に
`TableConnector(&cfgDb, CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER)` (L183) が含まれる。

```cpp
// buffermgrd.cpp L174-186
vector<TableConnector> buffer_table_connectors = {
    TableConnector(&cfgDb, CFG_PORT_TABLE_NAME),
    TableConnector(&cfgDb, CFG_PORT_CABLE_LEN_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_POOL_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PROFILE_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PG_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_QUEUE_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME),
    TableConnector(&cfgDb, CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER),   // ← 対象
    TableConnector(&stateDb, STATE_BUFFER_MAXIMUM_VALUE_TABLE),
    TableConnector(&stateDb, STATE_PORT_TABLE_NAME)
};
```

`Orch::addConsumer()` (`orch.cpp:1186-1195`) は `db->getDbId() == CONFIG_DB` の場合に
`SubscriberStateTable` を生成する。

```cpp
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || ...)
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ...), this, tableName));
    else
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, ...), this, tableName));
}
```

`SubscriberStateTable` は内部で Redis keyspace notification を PSUBSCRIBE する。

| テーブル | DB | DB ID | PSUBSCRIBE パターン |
|---------|-----|-------|-------------------|
| `DEFAULT_LOSSLESS_BUFFER_PARAMETER` | CONFIG_DB | 4 | `__keyspace@4__:DEFAULT_LOSSLESS_BUFFER_PARAMETER\|*` |

---

## 2. 主ループ — SELECT_TIMEOUT 1000 ms

`buffermgrd.cpp` L22 で `#define SELECT_TIMEOUT 1000` (ミリ秒)。
主ループ (L220-238):

```cpp
while (true) {
    Selectable *sel;
    int ret = s.select(&sel, SELECT_TIMEOUT);   // 1000 ms タイムアウト
    if (ret == Select::ERROR)   { continue; }
    if (ret == Select::TIMEOUT) { buffmgr->doTask(); continue; }
    auto *c = (Executor *)sel;
    c->execute();
}
```

- イベント到着時: `c->execute()` → `Consumer::execute()` → `BufferMgrDynamic::doTask(Consumer&)` が呼ばれ、`handleDefaultLossLessBufferParam()` に委譲される。
- タイムアウト時: `buffmgr->doTask()` (引数なし) が呼ばれ、`task_need_retry` でキューに残った全エントリを再処理する。

タイムアウト 1000 ms は CONFIG_DB 変更から `buffermgrdyn` への通知遅延の**最大上限**。通常は keyspace notification が即時到達するため実レイテンシははるかに短い。

---

## 3. 起動時の直接 hget (SubscriberStateTable 外)

`buffermgrdyn.cpp` L148-154 でコンストラクタ内に直接 `m_cfgDefaultLosslessBufferParam.hget()` が呼ばれる。
これは `SubscriberStateTable` 経由ではなく `Table` クラスの直接読み取りであり、起動時に既存エントリの `default_dynamic_th` を先行取得する。

```cpp
// buffermgrdyn.cpp L148-154
m_cfgDefaultLosslessBufferParam.getKeys(keys);
if (!keys.empty())
    m_cfgDefaultLosslessBufferParam.hget(keys[0], "default_dynamic_th", m_defaultThreshold);
```

起動後の変更はすべて `SubscriberStateTable` の keyspace notification 経路で通知される。

---

## 4. 書き込み側 (ProducerStateTable 経由)

`DEFAULT_LOSSLESS_BUFFER_PARAMETER` は `buffermgrdyn` にとって**消費専用**テーブルであり、書き込みは行わない。
CONFIG_DB への書き込みは外部ツール (`sonic-cfggen`, `db_migrator.py`, 手動 `sonic-db-cli`) が `Table::set()` で直接 hset し、keyspace notification をトリガーする。

`ProducerStateTable` は使用しない（`APPL_DB` 専用の通知チャネルであるため）。

---

## 5. 証跡サマリ

| 機構 | 実装 | 証拠 |
|------|------|------|
| CONFIG_DB 購読 | `SubscriberStateTable(cfgDb, CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER)` | `buffermgrd.cpp:183`, `orch.cpp:1188-1190` |
| PSUBSCRIBE パターン | `__keyspace@4__:DEFAULT_LOSSLESS_BUFFER_PARAMETER\|*` | swss-common `SubscriberStateTable` 実装 |
| select タイムアウト | 1000 ms | `buffermgrd.cpp:22,225` |
| タイムアウト時再処理 | `buffmgr->doTask()` 全エントリ再試行 | `buffermgrd.cpp:232-233` |
| 起動時直接 hget | `m_cfgDefaultLosslessBufferParam.hget()` | `buffermgrdyn.cpp:150-153` |
