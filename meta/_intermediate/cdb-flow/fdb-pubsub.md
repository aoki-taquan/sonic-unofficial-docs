# FDB テーブル — Phase G 通信メカニズム抽出メモ

ソース: `sonic-swss/orchagent/fdborch.cpp` (master)

## CONFIG_DB Subscribe 経路

`FdbOrch` は CONFIG_DB の `FDB` テーブルを直接購読しない。
`swssconfig` が CONFIG_DB:FDB を読み出し APPL_DB:FDB_TABLE へ転記する。

```
CONFIG_DB:FDB  ──swssconfig──▶  APPL_DB:FDB_TABLE
```

コード根拠: `fdborch.cpp:27–33` — `Orch(applDbConnector, appFdbTables)` で APPL_DB Consumer として登録。

## APPL_DB Consumer

`FdbOrch::doTask(Consumer& consumer)` (`fdborch.cpp:707`) が APPL_DB:FDB_TABLE の SET/DEL イベントを受け取る。

- SET → `addFdbEntry()` → `sai_fdb_api->create_fdb_entry()`
- DEL → `removeFdbEntry()` → `sai_fdb_api->remove_fdb_entry()`

## ASIC_DB:NOTIFICATIONS — sai_fdb_event_notification

ハードウェア MAC 学習・エージングイベントは syncd が `ASIC_DB:NOTIFICATIONS` チャンネルに `fdb_event` として publish する。

登録コード (`fdborch.cpp:45–48`):
```cpp
m_notificationsDb = make_shared<DBConnector>("ASIC_DB", 0);
m_fdbNotificationConsumer = new swss::NotificationConsumer(m_notificationsDb.get(), "NOTIFICATIONS");
auto fdbNotifier = new Notifier(m_fdbNotificationConsumer, this, "FDB_NOTIFICATIONS");
Orch::addExecutor(fdbNotifier);
```

受信ハンドラ (`fdborch.cpp:923,1048–1074`):
```cpp
else if (&consumer == m_fdbNotificationConsumer && op == "fdb_event")
{
    sai_fdb_event_notification_data_t *fdbevent = nullptr;
    sai_deserialize_fdb_event_ntf(data, count, &fdbevent);
    for (uint32_t i = 0; i < count; ++i)
        this->update(fdbevent[i].event_type, &fdbevent[i].fdb_entry, oid, sai_fdb_type);
    sai_deserialize_free_fdb_event_ntf(count, fdbevent);
}
```

`FdbOrch::update()` (`fdborch.cpp:278`) がイベント種別 (LEARN / AGE / MOVE / FLUSHED) を分岐処理し、STATE_DB:FDB_TABLE への書き戻しや APPL_DB 更新を行う。

## FLUSHFDBREQUEST 経路

`APPL_DB:FLUSHFDBREQUEST` を `NotificationConsumer` で購読 (`fdborch.cpp:40–42`)。
`op == "ALL"` で `sai_fdb_api->flush_fdb_entries()` を発行 (`fdborch.cpp:940–955`)。

## 通信経路サマリ

| 経路 | チャンネル / テーブル | 種別 | ハンドラ |
|------|----------------------|------|---------|
| CONFIG_DB → APPL_DB | `FDB_TABLE` | swssconfig 転記 | — |
| APPL_DB → FdbOrch | `APP_FDB_TABLE_NAME` | SubscribeTable (Consumer) | `doTask(Consumer&)` L707 |
| FdbOrch → SAI | `sai_fdb_api` | 同期 API | `addFdbEntry()` / `removeFdbEntry()` |
| syncd → FdbOrch | `ASIC_DB:NOTIFICATIONS` `fdb_event` | NotificationConsumer | `doTask(NotificationConsumer&)` L923 → `update()` L278 |
| FdbOrch → STATE_DB | `FDB_TABLE` | 書き戻し | `storeFdbEntryState()` |
| CLI → FdbOrch | `APPL_DB:FLUSHFDBREQUEST` | NotificationConsumer | `doTask(NotificationConsumer&)` `op=ALL` L940 |
