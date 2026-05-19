# WATERMARK_TABLE — pubsub 調査証跡 (Phase G)

調査日: 2026-05-19  
調査対象: `sonic-swss/orchagent/watermarkorch.cpp`, `orchdaemon.cpp`, `sonic-utilities/scripts/watermarkstat`

## 主要発見

### SubscriberStateTable 登録

`orchdaemon.cpp:432-437` で `WatermarkOrch` は `CFG_WATERMARK_TABLE_NAME` と `CFG_FLEX_COUNTER_TABLE_NAME` の 2 テーブルを購読する。

```cpp
vector<string> wm_tables = {
    CFG_WATERMARK_TABLE_NAME,
    CFG_FLEX_COUNTER_TABLE_NAME
};
WatermarkOrch *wm_orch = new WatermarkOrch(m_configDb, wm_tables);
```

### NotificationConsumer — WATERMARK_CLEAR_REQUEST

`watermarkorch.cpp:35-39`:
```cpp
m_clearNotificationConsumer = new swss::NotificationConsumer(
    m_appDb.get(), "WATERMARK_CLEAR_REQUEST");
auto clearNotifier = new Notifier(m_clearNotificationConsumer, this, "WM_CLEAR_NOTIFIER");
Orch::addExecutor(clearNotifier);
```

`watermarkstat` CLI (`sonic-utilities/scripts/watermarkstat:323-325`):
```python
def send_clear_notification(self, data):
    msg = json.dumps(data, separators=(',', ':'))
    self.db.publish('APPL_DB', 'WATERMARK_CLEAR_REQUEST', msg)
```

### SelectableTimer

`watermarkorch.cpp:41-44`:
```cpp
auto intervT = timespec { .tv_sec = DEFAULT_TELEMETRY_INTERVAL , .tv_nsec = 0 };
m_telemetryTimer = new SelectableTimer(intervT);
auto executorT = new ExecutableTimer(m_telemetryTimer, this, "WM_TELEMETRY_TIMER");
Orch::addExecutor(executorT);
```

タイマー満了ごとに `doTask(SelectableTimer&)` が呼ばれ PERIODIC_WATERMARKS をゼロクリア。

### CONFIG_DB 書き込み経路

`watermarkcfg` スクリプト (`watermarkcfg:23`):
```python
configdb.mod_entry('WATERMARK_TABLE', 'TELEMETRY_INTERVAL', {'interval': interval})
```

APPL_DB 中継なし。直接 CONFIG_DB に HSET。
