# COUNTERS_DB NAT カウンタテーブル群 — Phase G: 通信メカニズム

## 調査対象

- `sonic-swss/orchagent/natorch.cpp`
- `sonic-swss/cfgmgr/natmgr.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss-common/common/subscriberstatetable.cpp`
- `sonic-swss-common/common/consumerstatetable.cpp`

## 概要

`COUNTERS_DB` NAT カウンタテーブル群 (`COUNTERS_NAT` / `COUNTERS_NAPT` / `COUNTERS_TWICE_NAT` / `COUNTERS_TWICE_NAPT` / `COUNTERS_GLOBAL_NAT`) は NatOrch のみが書き手となる。通常の CONFIG_DB → APPL_DB pubsub パスとは異なり、SAI タイマーポーリングと APPL_DB 非同期通知チャンネルの 2 経路で更新される。

## 書き込み経路

### 経路 1: APPL_DB ConsumerStateTable → NatOrch → COUNTERS_DB ゼロ初期化

CONFIG_DB への NAT 設定変更 → natmgrd (SubscriberStateTable) → APPL_DB ProducerStateTable → NatOrch ConsumerStateTable → SAI create_nat_entry → updateNatCounters(0,0)

orchdaemon.cpp:457-462 で NatOrch 生成時に ConsumerStateTable を以下の優先度で登録:
- APP_NAT_DNAT_POOL_TABLE: pri=55
- APP_NAT_TABLE: pri=54
- APP_NAPT_TABLE: pri=53
- APP_NAT_TWICE_TABLE: pri=52
- APP_NAPT_TWICE_TABLE: pri=51
- APP_NAT_GLOBAL_TABLE: pri=50

### 経路 2: SelectableTimer (5 秒) → SAI ポーリング → COUNTERS_DB 実測値更新

NatOrch コンストラクタで `m_natQueryTimer = new SelectableTimer({5, 0})` を生成。
`enableNatFeature()` 内で `m_natQueryTimer->start()` → orchagent の Select ループが fd ready を検知 → `doTask(SelectableTimer&)` → `queryCounters()` → `getNatCounters()` → SAI `get_nat_entry_attribute` → `updateNatCounters(ip, pkts, bytes)` → `m_countersNatTable.set(key, values)`

### 非同期通知チャンネル (NotificationConsumer / NotificationProducer)

| チャンネル | 方向 | 影響 |
|---|---|---|
| `FLUSHNATSTATISTICS` (APPL_DB) | CLI → NatOrch | COUNTERS_NAT* を 0 にリセット |
| `FLUSHNATENTRIES` (APPL_DB) | CLI → natmgrd → NatOrch | APPL_DB エントリ削除 → deleteNatCounters → COUNTERS_DB キー消滅 |
| `SETTIMEOUTNAT` (APPL_DB) | NatOrch → natmgrd | conntrack timeout のみ (COUNTERS_DB 無影響) |
| `NAT_DB_CLEANUP_NOTIFICATION` (APPL_DB) | natmgrd → NatOrch | 全エントリ削除 → 全 COUNTERS_NAT* キー消滅 |

## Evidence

- `natorch.cpp:84-91`: NotificationConsumer 2 本登録
- `natorch.cpp:93-100`: SelectableTimer 5 秒周期
- `natorch.cpp:137`: setTimeoutNotifier (NotificationProducer)
- `natorch.cpp:3095-3117`: doTask(SelectableTimer) → queryHitBits/queryCounters
- `natorch.cpp:4049-4135`: updateNatCounters / updateNaptCounters / updateTwiceNatCounters
- `natorch.cpp:4450-4490`: doTask(NotificationConsumer) → FLUSHNATSTATISTICS / NAT_DB_CLEANUP
- `orchdaemon.cpp:457-462`: ConsumerStateTable 優先度設定
- `natmgr.cpp:43-49`: ProducerStateTable 群
