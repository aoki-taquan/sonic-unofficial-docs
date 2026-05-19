# SUPPRESS_ASIC_SDK_HEALTH_EVENT テーブル — Phase G pubsub 調査ノート

対象ページ: `docs/reference/config-db/suppress-asic-sdk-health-event.md`
対象テーブル: `CONFIG_DB.SUPPRESS_ASIC_SDK_HEALTH_EVENT`
調査ソース: `sonic-swss/orchagent/switchorch.cpp`, `orchagent/orchdaemon.cpp`
調査日: 2026-05-19

---

## 結論

`SUPPRESS_ASIC_SDK_HEALTH_EVENT` は CONFIG_DB → SwitchOrch (SubscriberStateTable) → SAI の直接経路。APPL_DB 中継なし。

## 購読構成

- `orchdaemon.cpp:212` で `SwitchOrch` が初期化される際、`SubscriberStateTable` が `SUPPRESS_ASIC_SDK_HEALTH_EVENT` テーブルに対して登録される
- テーブル定数: `CFG_SUPPRESS_ASIC_SDK_HEALTH_EVENT_NAME = "SUPPRESS_ASIC_SDK_HEALTH_EVENT"` (`schema.h:394`)
- PSUBSCRIBE パターン: `__keyspace@4__:SUPPRESS_ASIC_SDK_HEALTH_EVENT|*`
- SELECT_TIMEOUT: 1000 ms (`orchdaemon.cpp:23`)

## 起動時スナップショット

- `switchorch.cpp:208-280` の `initAsicSdkHealthEventNotification()` がコンストラクタ内で同期的に CONFIG_DB を直接 `hget` する
- これは Consumer キュー非経由のため、orchagent 起動前の CONFIG_DB 値がそのまま取り込まれる
- 起動後に Consumer 経由で届く SET/DEL とは独立した経路

## SAI 書き込み

- `registerAsicSdkHealthEventCategories()` が `sai_switch_api->set_switch_attribute()` を呼ぶ
- 属性: `SAI_SWITCH_ATTR_REG_FATAL/WARNING/NOTICE_SWITCH_ASIC_SDK_HEALTH_CATEGORY`
