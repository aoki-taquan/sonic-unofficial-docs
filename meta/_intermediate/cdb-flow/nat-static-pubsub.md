# nat-static Phase G — 通信メカニズム調査メモ

## 調査対象

- `sonic-swss/cfgmgr/natmgrd.cpp` (main、購読設定)
- `sonic-swss/cfgmgr/natmgr.cpp` (NatMgr::doTask / doStaticNatTask)
- `sonic-swss/cfgmgr/natmgr.h` (ProducerStateTable 宣言)
- `sonic-swss-common/common/schema.h` (テーブル名定数)

## CONFIG_DB 側の購読

`natmgrd.cpp:109-121` で以下の cfg_tables を渡して `NatMgr` を生成:

```
CFG_STATIC_NAT_TABLE_NAME   → "STATIC_NAT"
CFG_STATIC_NAPT_TABLE_NAME
CFG_NAT_POOL_TABLE_NAME
CFG_NAT_BINDINGS_TABLE_NAME
CFG_NAT_GLOBAL_TABLE_NAME
CFG_INTF_TABLE_NAME (+ LAG / VLAN / LOOPBACK バリアント)
CFG_ACL_TABLE_TABLE_NAME
CFG_ACL_RULE_TABLE_NAME
```

`NatMgr` は `Orch` を継承しており、`cfg_tables` の各テーブルを `SubscriberStateTable` (swss::Orch の内部実装) として CONFIG_DB (DB 4) から購読する。Redis keyspace notification パターンは `__keyspace@4__:STATIC_NAT|*`。

## メインループ

`natmgrd.cpp:156-200` の無限ループで `s.select(&sel, SELECT_TIMEOUT)` を呼び出す。
SELECT_TIMEOUT は通常 1000ms。変更がなければタイムアウトごとに `doTask(SelectableTimer)` が実行される。

## STATIC_NAT イベント到着時の処理パス

```
Redis keyspace notification: __keyspace@4__:STATIC_NAT|<global_ip>
  └─ NatMgr (Orch::doTask) → NatMgr::doTask(Consumer&)  [natmgr.cpp:8147]
        └─ table_name == CFG_STATIC_NAT_TABLE_NAME → doStaticNatTask(consumer)
              └─ SET → addStaticNatEntry() → addStaticSingleNatEntry() or addStaticTwiceNatEntry()
              └─ DEL → removeStaticNatEntry()
```

## APPL_DB への書き込み

`natmgr.h:257` で宣言された `ProducerStateTable m_appNatTableProducer` を使用:

```cpp
m_appNatTableProducer(appDb, APP_NAT_TABLE_NAME)  // "NAT_TABLE"
```

`ProducerStateTable` は書き込み時に Redis `NAT_TABLE_CHANNEL@1` チャネルへ PUBLISH する (APPL_DB = DB 1)。

## 追加通知チャネル

- `SETTIMEOUTNAT` チャンネル (APPL_DB NotificationConsumer): NAT global タイムアウト変更時に `timeoutNotifications()` へ
- `FLUSHNATENTRIES` チャンネル (APPL_DB NotificationConsumer): `flush nat translations` CLI 時に `flushNotifications()` へ
- `NAT_DB_CLEANUP_NOTIFICATION` (APPL_DB NotificationProducer): SIGTERM 受信時に NatOrch へ cleanup を通知

## STATE_DB 依存 (参照のみ)

`m_stateInterfaceTable` (STATE_DB:STATE_INTERFACE_TABLE) を `isIntfStateOk()` で参照するが購読はしない。インタフェース状態変化は CFG_INTF_TABLE_NAME 経由で間接的に受け取る。
