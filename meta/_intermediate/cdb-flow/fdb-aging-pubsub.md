# fdb-aging — Phase G pubsub 調査メモ

調査対象:
- `sonic-swss/orchagent/switchorch.cpp` L595-748 (doAppSwitchTableTask)
- `sonic-swss/orchagent/orchdaemon.cpp` L197-212 (SwitchOrch 登録)
- `sonic-swss/orchagent/orch.cpp` L1186-1196 (addConsumer dispatch)

## 購読チャンネル

`fdb_aging_time` は `APPL_DB SWITCH_TABLE:switch` の 1 フィールドとして書き込まれる。
`SwitchOrch` は `APPL_DB` の `APP_SWITCH_TABLE_NAME` を `Consumer` として保持し、
`Orch::addConsumer()` の DB ID 分岐により **`ConsumerStateTable`** （Redis Lists 方式）が割り当てられる。

```cpp
// orchdaemon.cpp:197-212
TableConnector app_switch_table(m_applDb, APP_SWITCH_TABLE_NAME);
// ...
vector<TableConnector> switch_tables = {
    conf_switch_hash, conf_switch_trim, conf_switch_fast_linkup,
    conf_asic_sensors, conf_suppress_asic_sdk_health_categories,
    app_switch_table   // ← APPL_DB = ConsumerStateTable
};
gSwitchOrch = new SwitchOrch(m_applDb, switch_tables, stateDbSwitchTable);
```

```cpp
// orch.cpp:1186-1196
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
        addExecutor(new Consumer(new SubscriberStateTable(...), this, tableName));
    else
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
}
```

APPL_DB (`dbId=0`) は `else` ブランチに入るため `ConsumerStateTable` が使われる。
書き込み側は `swssconfig switch.json.j2` 展開後の `swssconfig` コマンドが
`ProducerStateTable`（Redis LPUSH/RPOP Lists）でエントリを書き込む。

## 購読者まとめ

| 購読者 | 購読 API | 購読テーブル | 優先度 |
|--------|---------|--------------|--------|
| `orchagent` (`SwitchOrch`) | `swss::ConsumerStateTable` | `SWITCH_TABLE` (APPL_DB) | デフォルト |

## 発行元まとめ

| 発行元 | 発行 API | 書込テーブル | トリガー |
|--------|---------|--------------|---------|
| `swssconfig` (switch.json) | `ProducerStateTable` / `swssconfig` | `SWITCH_TABLE:switch` (APPL_DB) | orchagent コンテナ起動時 |
| `sonic-db-cli`（手動） | `HSET` | `SWITCH_TABLE:switch` (APPL_DB) | 管理者手動操作 |

## 補足: RESTARTCHECK 通知チャンネル

`SwitchOrch` は `RESTARTCHECKREPLY` という `NotificationProducer` も持つが、これは
warm-reboot 再起動可否通知のチャンネルであり `fdb_aging_time` の pub/sub とは無関係。
