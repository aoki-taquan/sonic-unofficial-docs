# SUPPRESS_ASIC_SDK_HEALTH_EVENT — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `SUPPRESS_ASIC_SDK_HEALTH_EVENT` テーブル。購読者は `orchagent` 内 `SwitchOrch` (`sonic-swss/orchagent/switchorch.cpp`)。

## 1. 購読 API — `SubscriberStateTable`

`SwitchOrch` は `Orch` 基底クラス経由で CONFIG_DB テーブルを購読。`Orch::addConsumer()` は DB が CONFIG_DB (dbId=4) の場合に `SubscriberStateTable` を選択する。

証跡: `switchorch.cpp:1410-1491` (doCfgSuppressAsicSdkHealthEventTableTask), `orch.cpp` (addConsumer 分岐)

## 2. 購読チャンネル

`__keyspace@4__:SUPPRESS_ASIC_SDK_HEALTH_EVENT:*` (CONFIG_DB dbId=4)

## 3. ディスパッチ

`SwitchOrch::doTask()` → `doCfgSuppressAsicSdkHealthEventTableTask()`:
- SET_COMMAND: categories フィールドあり → `registerAsicSdkHealthEventCategories(attr, key, categories)` / なし → 全購読
- DEL_COMMAND: `registerAsicSdkHealthEventCategories(attr, key)` で全購読（抑制解除）
- 処理後 `erase(it)` でエントリ消費

## 4. APPL_DB 中継なし

CONFIG_DB → SAI 直結。`ProducerStateTable` / `ConsumerStateTable` 方式は使わない。

## 5. 起動時スナップショット二重経路

- `SubscriberStateTable` の通常再配信: 購読開始時に既存エントリを m_buffer に流し込み
- `initAsicSdkHealthEventNotification()` が直接 `hget` で CONFIG_DB を読む独立経路も存在 (`switchorch.cpp:240-274`)

## 6. STATE_DB 書込

起動時 1 回、`initAsicSdkHealthEventNotification()` が `SWITCH_CAPABILITY|switch` へ直接書き込む。SET/DEL Consumer 処理では STATE_DB への書き込みは発生しない（Phase F 参照）。
