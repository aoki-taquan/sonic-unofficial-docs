# NAT_GLOBAL / NAT_POOL / NAT_BINDINGS — Phase G: Redis PUBSUB / keyspace / ConsumerStateTable / Notification

## 調査対象

- `sonic-swss/cfgmgr/natmgrd.cpp`
- `sonic-swss/cfgmgr/natmgr.cpp`
- `sonic-swss/orchagent/natorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/orch.cpp`
- `sonic-swss-common/common/subscriberstatetable.cpp`
- `sonic-swss-common/common/consumerstatetable.cpp`
- `sonic-swss-common/common/producerstatetable.cpp`
- `sonic-swss-common/common/table.h`

## 購読メカニズム全体像

NAT_GLOBAL / NAT_POOL / NAT_BINDINGS テーブルの変更通知には **2 層** のメカニズムが存在する。

### 層 1: natmgrd (CONFIG_DB → APPL_DB)

`natmgrd` は `NatMgr` クラスを生成し、CONFIG_DB 上の以下のテーブルを `Orch` 基底クラス経由で購読する (`natmgrd.cpp:109-121`):

```
CFG_STATIC_NAT_TABLE_NAME
CFG_STATIC_NAPT_TABLE_NAME
CFG_NAT_POOL_TABLE_NAME
CFG_NAT_BINDINGS_TABLE_NAME
CFG_NAT_GLOBAL_TABLE_NAME
CFG_INTF_TABLE_NAME
CFG_LAG_INTF_TABLE_NAME
CFG_VLAN_INTF_TABLE_NAME
CFG_LOOPBACK_INTERFACE_TABLE_NAME
CFG_ACL_TABLE_TABLE_NAME
CFG_ACL_RULE_TABLE_NAME
```

`Orch::addConsumer()` (`orch.cpp:1186-1194`) は DB 種別を判定し、CONFIG_DB の場合は **`SubscriberStateTable`** を生成する:

```cpp
if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || ...)
    addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ...), this, tableName));
else
    addExecutor(new Consumer(new ConsumerStateTable(db, tableName, ...), this, tableName));
```

### 層 2: orchagent / NatOrch (APPL_DB → SAI)

`orchdaemon.cpp:457-465` で `NatOrch` を生成し、APPL_DB 上の以下のテーブルを **`ConsumerStateTable`** で購読する:

```cpp
{ APP_NAT_DNAT_POOL_TABLE_NAME,  natorch_base_pri + 5 },
{ APP_NAT_TABLE_NAME,            natorch_base_pri + 4 },
{ APP_NAPT_TABLE_NAME,           natorch_base_pri + 3 },
{ APP_NAT_TWICE_TABLE_NAME,      natorch_base_pri + 2 },
{ APP_NAPT_TWICE_TABLE_NAME,     natorch_base_pri + 1 },
{ APP_NAT_GLOBAL_TABLE_NAME,     natorch_base_pri     }
```

## 購読チャンネルの詳細

### CONFIG_DB 側 — SubscriberStateTable (keyspace PSUBSCRIBE)

`SubscriberStateTable::SubscriberStateTable()` (`subscriberstatetable.cpp:17-43`) は構築時に以下を PSUBSCRIBE する:

```
__keyspace@<db_id>__:<table_name>|*
```

例 (`NAT_GLOBAL_TABLE_NAME` = `"NAT_GLOBAL"`, db_id=4):
```
PSUBSCRIBE __keyspace@4__:NAT_GLOBAL|*
PSUBSCRIBE __keyspace@4__:NAT_POOL|*
PSUBSCRIBE __keyspace@4__:NAT_BINDINGS|*
```

- CONFIG_DB の DB 番号は通常 4
- glob パターンにより `NAT_GLOBAL|Values`、`NAT_POOL|<name>`、`NAT_BINDINGS|<name>` を捕捉

イベント受信フロー (`subscriberstatetable.cpp:45-165`):

```
CONFIG_DB への HSET / HDEL / DEL
  → Redis: __keyspace@4__:<table>|<key> に pmessage 発火
  → SubscriberStateTable::readData()
    → hiredis 経由で reply を受信
    → m_keyspace_event_buffer に push
  → SubscriberStateTable::pops()
    → keyspace_event_buffer から pmessage を取り出す
    → "del" なら DEL_COMMAND を設定
    → それ以外なら HGETALL でフィールド値を取得し SET_COMMAND を設定
    → KeyOpFieldsValuesTuple (key, op, fvs) を返す
  → natmgrd の select ループ (SELECT_TIMEOUT=1000ms)
    → Consumer::execute() → NatMgr::doTask(Consumer&)
      → doNatGlobalTask / doNatPoolTask / doNatBindingTask 等へディスパッチ
```

### APPL_DB 側 — ConsumerStateTable (ProducerStateTable チャンネル SUBSCRIBE)

`ConsumerStateTable::ConsumerStateTable()` (`consumerstatetable.cpp:14-30`) は構築時に以下を SUBSCRIBE する:

```
SUBSCRIBE APP_NAT_GLOBAL_TABLE_NAME_CHANNEL@<db_id>
```

例 (`APP_NAT_GLOBAL_TABLE_NAME` = `"APP_NAT_GLOBAL_TABLE"`, db_id=0):
```
APP_NAT_GLOBAL_TABLE_CHANNEL@0
```

チャンネル名は `table.h:85-96` の `getChannelName(db_id)` で `m_tableName + "_CHANNEL@" + db_id` として生成される。

### 初期スナップショット再生 (起動時)

`SubscriberStateTable` のコンストラクタ (`subscriberstatetable.cpp:25-42`) は PSUBSCRIBE 後に `m_table.getKeys()` で既存 key を全件取得し、`SET` イベントとして `m_buffer` に積む。`natmgrd` 再起動後もすべての既存 NAT エントリが再処理される (再起動耐性)。

`ConsumerStateTable` は `EVALSHA` で key-set から未処理エントリを取得することで初期スナップショットを処理する。

## 非同期通知チャンネル (APPL_DB pub/sub)

NAT データパスには通常の表テーブル以外に **NotificationConsumer / NotificationProducer** を使った非同期チャンネルが存在する:

| チャンネル名 | DB | 方向 | 送信者 | 受信者 | 用途 |
|---|---|---|---|---|---|
| `SETTIMEOUTNAT` | APPL_DB | natorch → natmgrd | `NatOrch::setTimeoutNotifier` (`natorch.cpp:137`) | `natmgrd.cpp:149` の `timeoutNotificationsConsumer` | NatOrch が conntrack timeout 変更を natmgrd に通知 |
| `FLUSHNATENTRIES` | APPL_DB | 外部 (`show nat translate flush`) → natmgrd | 外部プロセス / CLI | `natmgrd.cpp:152` の `flushNotificationsConsumer` | conntrack エントリ全フラッシュ要求 |
| `FLUSHNATSTATISTICS` | APPL_DB | 外部 → NatOrch | 外部プロセス | `natorch.cpp:84-86` の `m_flushNotificationsConsumer` | NAT カウンタのクリア要求 |
| `NAT_DB_CLEANUP_NOTIFICATION` | APPL_DB | natmgrd → NatOrch | `natmgrd.cpp:86-87` の `cleanupNotifier` | `natorch.cpp:89-91` の `m_cleanupNotificationConsumer` | natmgrd 終了時に orchagent へ Redis/ASIC の NAT エントリ削除を依頼 |

これらのチャンネルはすべて `swss::Select` の `Selectable` として登録され、メインループ内で処理される。

## natmgrd メインループ

```cpp
// natmgrd.cpp:155-198
while (!gExit)
{
    ret = s.select(&sel, SELECT_TIMEOUT);  // 1000ms タイムアウト
    if (ret == Select::ERROR) { continue; }

    if (sel == timeoutNotificationsConsumer)
    {
        timeoutNotificationsConsumer->pop(op, data, values);
        natmgr->timeoutNotifications(op, data);
        continue;
    }
    if (sel == flushNotificationsConsumer)
    {
        flushNotificationsConsumer->pop(op, data, values);
        natmgr->flushNotifications(op, data);
        continue;
    }
    if (ret == Select::TIMEOUT)
    {
        natmgr->doTask();
        continue;
    }
    auto *c = (Executor *)sel;
    c->execute();  // Consumer::execute() → NatMgr::doTask(Consumer&)
}
```

- タイムアウト (1000ms) 経過時は `natmgr->doTask()` を呼び出してキューに残ったタスクを処理
- 通知チャンネル受信時は専用ハンドラを直接呼び出す (Consumer の doTask ループをバイパス)

## NatOrch の select ループ (orchagent 側)

`NatOrch` は `orchagent` の共有 `Select` ループに組み込まれる (`orchdaemon.cpp:594`)。orchagent の `doTask()` は orchdaemon の統合メインループから呼び出され、APPL_DB の ConsumerStateTable からイベントを受け取る。

## ProducerStateTable との関係

CONFIG_DB への書き込みが `ProducerStateTable` 経由の場合、書き込み側は `APP_NAT_GLOBAL_TABLE_CHANNEL@<db_id>` を PUBLISH する (`table.h:85-96`)。ただし `natmgrd` は CONFIG_DB を **SubscriberStateTable (keyspace notification)** で購読するため、書き込み元が ProducerStateTable か直接 HSET かを問わずイベントを捕捉できる。CONFIG_DB → APPL_DB 間の変換は natmgrd が担い、APPL_DB への書き込みは ProducerStateTable 経由で行われる。

## まとめ

| フェーズ | 実装 | ファイル |
|---------|------|---------|
| CLI/mgmt → CONFIG_DB 書き込み | HSET が `__keyspace@4__:NAT_GLOBAL|*` 等を発火 | Redis サーバー内部 |
| CONFIG_DB keyspace → natmgrd | `SubscriberStateTable` (PSUBSCRIBE) + `readData()` + `pops()` | subscriberstatetable.cpp |
| natmgrd select ループ | `swss::Select::select(1000ms)` + `Consumer::execute()` | natmgrd.cpp |
| Consumer → NatMgr::doTask | `doNatGlobalTask` / `doNatPoolTask` / `doNatBindingTask` にディスパッチ | natmgr.cpp |
| NatMgr → APPL_DB 書き込み | `ProducerStateTable::set()` + `getChannelName()` で PUBLISH | natmgr.cpp |
| APPL_DB チャンネル → NatOrch | `ConsumerStateTable` (SUBSCRIBE) + orchagent 統合ループ | natorch.cpp |
| NatOrch → SAI | `sai_nat_api->create_nat_entry()` 等 | natorch.cpp |
| 非同期通知 | `NotificationProducer/Consumer` 4 チャンネル | natmgrd.cpp, natorch.cpp |
