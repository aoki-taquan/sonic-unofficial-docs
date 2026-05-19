# NAT_POOL — Phase G: 通信メカニズム (PUBSUB / ConsumerStateTable / Notification)

## 調査対象

- `sonic-swss/cfgmgr/natmgrd.cpp` L100-198
- `sonic-swss/cfgmgr/natmgr.cpp` L8163-8165
- `sonic-swss/orchagent/orchdaemon.cpp` L456-465
- `sonic-swss/orchagent/natorch.cpp` L84-91, L137
- `sonic-swss-common/common/subscriberstatetable.cpp`
- `sonic-swss-common/common/consumerstatetable.cpp`

## NAT_POOL の購読経路 (2 層構造)

### 層 1: natmgrd — CONFIG_DB NAT_POOL → APPL_DB NAT_DNAT_POOL_TABLE

`natmgrd.cpp:109-121` で以下のテーブルを `SubscriberStateTable` (Redis keyspace PSUBSCRIBE) で購読する:

```
CONFIG_DB#4:NAT_POOL|*  ← PSUBSCRIBE __keyspace@4__:NAT_POOL|*
```

ディスパッチ (`natmgr.cpp:8163-8165`):

```cpp
else if (table_name == CFG_NAT_POOL_TABLE_NAME)
{
    SWSS_LOG_INFO("Received update from CFG_NAT_POOL_TABLE_NAME");
    doNatPoolTask(consumer);
}
```

イベント受信フロー:
```
CONFIG_DB HSET/DEL NAT_POOL|<name>
  → Redis: PMESSAGE __keyspace@4__:NAT_POOL|<name>
  → SubscriberStateTable::readData() → pops()
    → "del" なら DEL、それ以外は HGETALL して SET_COMMAND
  → natmgrd select ループ (SELECT_TIMEOUT=1000ms)
  → Consumer::execute() → NatMgr::doNatPoolTask()
```

### 層 2: NatOrch — APPL_DB NAT_DNAT_POOL_TABLE → SAI

`orchdaemon.cpp:457` で NatOrch を `ConsumerStateTable` で登録:

```cpp
{ APP_NAT_DNAT_POOL_TABLE_NAME,  natorch_base_pri + 5 },  // 最高優先度
```

イベント受信フロー:
```
natmgrd: ProducerStateTable::set("NAT_DNAT_POOL_TABLE", destIp, ...)
  → APPL_DB HSET + PUBLISH APP_NAT_DNAT_POOL_TABLE_CHANNEL@0
  → NatOrch ConsumerStateTable SUBSCRIBE
  → orchagent 統合 doTask ループ
  → NatOrch::doTask() → doDnatPoolTableTask()
  → sai_nat_api->create_nat_entry(SAI_NAT_TYPE_DESTINATION_NAT_POOL)
```

## 初期スナップショット再生

`natmgrd` 起動時 (`SubscriberStateTable::SubscriberStateTable()`): PSUBSCRIBE 後に `m_table.getKeys()` で既存 key を全件取得し SET イベントとして積む。`natmgrd` 再起動後も既存 `NAT_POOL` エントリを全再処理する (再起動耐性)。

`NatOrch` 起動時 (`ConsumerStateTable`): EVALSHA スクリプトで APPL_DB の未処理エントリを取得し初期スナップショットを処理する。

## 非同期通知チャンネル (NAT_POOL 関連)

| チャンネル名 | DB | 方向 | 送信者 | 受信者 | 用途 |
|---|---|---|---|---|---|
| `NAT_DB_CLEANUP_NOTIFICATION` | APPL_DB | natmgrd → NatOrch | `natmgrd.cpp:86-87` の `cleanupNotifier` | `natorch.cpp:89-91` の `m_cleanupNotificationConsumer` | natmgrd 終了時に NAT_DNAT_POOL_TABLE を含む全 NAT エントリの Redis/ASIC クリーンアップを依頼 |
| `FLUSHNATENTRIES` | APPL_DB | CLI → natmgrd | 外部プロセス (`sonic-utilities`) | `natmgrd.cpp:152` | `show nat translate flush` による conntrack 全エントリフラッシュ。pool に紐づく dynamic session も削除される |

## まとめ

| フェーズ | 実装 | ファイル |
|---------|------|---------|
| CLI → CONFIG_DB 書き込み | `config nat add pool` が `sonic-db-cli CONFIG_DB HSET 'NAT_POOL|<name>'` を発行 | sonic-utilities/config/nat.py |
| CONFIG_DB keyspace → natmgrd | `SubscriberStateTable` (PSUBSCRIBE `__keyspace@4__:NAT_POOL|*`) | subscriberstatetable.cpp |
| natmgrd ディスパッチ | `doNatPoolTask(consumer)` | natmgr.cpp:8163 |
| natmgrd → APPL_DB 書き込み | `ProducerStateTable::set("NAT_DNAT_POOL_TABLE", destIp, ...)` | natmgr.cpp:1520 |
| APPL_DB チャンネル → NatOrch | `ConsumerStateTable("NAT_DNAT_POOL_TABLE")` + orchagent 統合ループ | orchdaemon.cpp:457 |
| NatOrch → SAI | `sai_nat_api->create_nat_entry(SAI_NAT_TYPE_DESTINATION_NAT_POOL)` | natorch.cpp:1805 |
| 終了通知 | `NotificationProducer "NAT_DB_CLEANUP_NOTIFICATION"` | natmgrd.cpp:86 |
