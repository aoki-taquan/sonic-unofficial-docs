# pfcwd-state Phase G 調査メモ (pubsub)

## 調査対象
- `sonic-swss/orchagent/pfcwdorch.cpp`
- `sonic-swss/orchagent/pfc_detect_broadcom.lua`
- `sonic-swss/orchagent/pfc_detect_cisco-8000.lua`
- `sonic-swss/orchagent/pfc_restore.lua`

## 通知方式の概要

`pfcwdorch` は 3 系統の通知方式を使用する:

1. **NotificationConsumer (Redis SUBSCRIBE)**: `PFC_WD_ACTION` チャンネル (COUNTERS_DB) を購読し Lua プラグインからの storm/restore イベントを受信
2. **SubscriberStateTable**: `APPL_DB:PFC_WD` テーブルを購読（外部コントローラ / warm-reboot 用）
3. **ConsumerStateTable**: `CONFIG_DB:PFC_WD` を購読して pfcwd start/stop 操作を受信

## 証拠行番号

### pfcwdorch.cpp
- L724-728: `NotificationConsumer` 作成 (`"PFC_WD_ACTION"`, COUNTERS_DB) → `Notifier` 登録
- L736-739: `SubscriberStateTable` 作成 (`APPL_DB`, `APP_PFC_WD_TABLE_NAME`) → `Consumer` 登録
- L890-916: `doTask(swss::NotificationConsumer&)` — `pop()` → `startWdActionOnQueue(event, queueId)`
- L965: `event_publish(g_events_handle, "pfc-storm", &params)` — SONiC events framework 発行
- L1108: warm-reboot 時 `refillToSync()` が `APPL_DB:PFC_WD_INSTORM` スキャン

### pfc_detect_broadcom.lua
- L75: `HGET COUNTERS:<queueOid> PFC_WD_STATUS`
- L76: `HGET COUNTERS:<queueOid> PFC_WD_ACTION`
- L77: `HGET COUNTERS:<queueOid> BIG_RED_SWITCH_MODE`
- L79: `HGET COUNTERS:<queueOid> PFC_WD_DETECTION_TIME`
- L82: `HGET COUNTERS:<queueOid> PFC_WD_DETECTION_TIME_LEFT`
- L100: `HGET COUNTERS:<queueOid> PFC_STAT_HISTORY`
- L130: `redis.call('PUBLISH', 'PFC_WD_ACTION', '["' .. KEYS[i] .. '","storm"]')`
- L138: `redis.call('PUBLISH', 'PFC_WD_ACTION', '["' .. KEYS[i] .. '","restore"]')`

### pfc_detect_cisco-8000.lua
- L55: `redis.call('PUBLISH', 'PFC_WD_ACTION', '["' .. KEYS[i] .. '","storm"]')`
- L62: `redis.call('PUBLISH', 'PFC_WD_ACTION', '["' .. KEYS[i] .. '","restore"]')`

## 結論

- Lua プラグインは COUNTERS_DB `PFC_WD_ACTION` チャンネルに `PUBLISH` する
- `pfcwdorch` が `NotificationConsumer::pop()` で受信 → `doTask(NotificationConsumer&)` 呼び出し
- `event="storm"` / `"restore"` で分岐して COUNTERS_DB フィールドを更新
- swsscommon の `SubscriberStateTable` / `ConsumerStateTable` は CONFIG_DB / APPL_DB の通常 SET/DEL 処理に使用
