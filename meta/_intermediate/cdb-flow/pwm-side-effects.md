# pwm (WATERMARK_TABLE) — Phase F 副次 DB 書込 調査証跡

調査日: 2026-05-18  
対象ファイル: `sonic-swss/orchagent/watermarkorch.cpp`

## 副次 DB 書込の概要

`WATERMARK_TABLE|TELEMETRY_INTERVAL` への `interval` 書込みは CONFIG_DB のみへの操作だが、
orchagent (WatermarkOrch) がタイマー機構を通じて COUNTERS_DB へ副次的な書込みを行う。

## telemetry タイマー満了時の COUNTERS_DB 書込み

`doTask(SelectableTimer &timer)` (`watermarkorch.cpp:233`) が満了ごとに `clearSingleWm()` を7回呼ぶ:

```cpp
clearSingleWm(m_periodicWatermarkTable.get(),
              "SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES",
              m_pg_ids);                                          // L259-261
clearSingleWm(m_periodicWatermarkTable.get(),
              "SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES",
              m_pg_ids);                                          // L262-265
clearSingleWm(m_periodicWatermarkTable.get(),
              "SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES",
              m_unicast_queue_ids);                               // L266-269
clearSingleWm(m_periodicWatermarkTable.get(),
              "SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES",
              m_multicast_queue_ids);                             // L270-273
clearSingleWm(m_periodicWatermarkTable.get(),
              "SAI_QUEUE_STAT_SHARED_WATERMARK_BYTES",
              m_all_queue_ids);                                   // L274-277
clearSingleWm(m_periodicWatermarkTable.get(),
              "SAI_BUFFER_POOL_STAT_WATERMARK_BYTES",
              gBufferOrch->getBufferPoolNameOidMap());            // L278-281
clearSingleWm(m_periodicWatermarkTable.get(),
              "SAI_BUFFER_POOL_STAT_XOFF_ROOM_WATERMARK_BYTES",
              gBufferOrch->getBufferPoolNameOidMap());            // L282-285
```

`clearSingleWm()` は各 OID に対して `table->set(oid_str, {{"<stat_name>", "0"}})` を呼ぶだけ。
COUNTERS_DB `PERIODIC_WATERMARKS` テーブルに直接書き込む。SAI 呼び出しはなし。

## 手動クリア (NotificationConsumer 経由)

`doTask(NotificationConsumer &consumer)` (`watermarkorch.cpp:144`) が `WATERMARK_CLEAR_REQUEST` を受信。

- `op == "PERSISTENT"` → `m_persistentWatermarkTable` (`PERSISTENT_WATERMARKS`) を対象
- `op == "USER"` → `m_userWatermarkTable` (`USER_WATERMARKS`) を対象
- `PERIODIC_WATERMARKS` は手動クリアの対象外

## SAI への直接操作

`WATERMARK_TABLE` の書込みは SAI を直接呼び出さない。
タイマーが COUNTERS_DB に書き込み、flexcounter が SAI 統計を読んで上書きする間接構造。
