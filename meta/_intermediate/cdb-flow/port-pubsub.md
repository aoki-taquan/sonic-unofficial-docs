# PORT テーブル — 通信メカニズム調査メモ (Phase G)

調査日: 2026-05-15
対象ソース:
- `sonic-swss/cfgmgr/portmgr.cpp` / `portmgr.h`
- `sonic-swss/cfgmgr/portmgrd.cpp`
- `sonic-swss/orchagent/portsorch.cpp` / `portsorch.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/portsyncd/portsyncd.cpp`
- `sonic-swss-common/common/producerstatetable.cpp`
- `sonic-swss-common/common/subscriberstatetable.cpp`
- `sonic-swss-common/common/notificationconsumer.cpp`
- `sonic-swss-common/common/table.h` / `table.cpp`

---

## 1. Producer/Consumer ペア

### CONFIG_DB → portmgrd (SubscriberStateTable)

| 項目 | 値 |
|------|----|
| 購読方式 | `Orch(cfgDb, tableNames)` 基底クラス経由の `SubscriberStateTable` |
| keyspace パターン | `__keyspace@{db_id}__:PORT|*` (および `SEND_TO_INGRESS_PORT_TABLE|*`) |
| 購読テーブル | `CFG_PORT_TABLE_NAME` (`PORT`), `CFG_SEND_TO_INGRESS_PORT_TABLE_NAME` |
| Consumer クラス | `Consumer` (wraps `SubscriberStateTable`) |
| 初期化 (`portmgr.cpp:14`) | `Orch(cfgDb, tableNames)` — コンストラクタ時に全テーブルの既存キーを `m_buffer` に読み込む |

### portmgrd → APPL_DB (ProducerStateTable)

| 項目 | 値 |
|------|----|
| Producer クラス | `ProducerStateTable m_appPortTable(appDb, APP_PORT_TABLE_NAME)` (`portmgr.h:47`) |
| Publish チャンネル | `APP_PORT_TABLE_NAME + "_CHANNEL@" + db_id` (実値: `APPL_DB|PORT_TABLE_CHANNEL@0`) |
| Key SET 名 | `APP_PORT_TABLE_NAME + "_KEY_SET"` |
| Del SET 名 | `APP_PORT_TABLE_NAME + "_DEL_SET"` |
| State hash prefix | `_` (一時 hash: `_PORT_TABLE:<key>`) |
| 書き込み操作 | `m_appPortTable.set(alias, data)` (SET) — `portmgr.cpp:writeConfigToAppDb()` |
| Lua スクリプト | `EVALSHA` + `SADD KEY_SET` + `HSET _PORT_TABLE:<key>` + `PUBLISH PORT_TABLE_CHANNEL@0 G` |

### APPL_DB → orchagent PortsOrch (ConsumerStateTable)

| 項目 | 値 |
|------|----|
| Consumer クラス | `ConsumerStateTable` |
| Subscribe チャンネル | `APP_PORT_TABLE_NAME + "_CHANNEL@0"` |
| Pop Lua スクリプト | `consumer_state_table_pops.lua` — KEY_SET から SPOP → HGETALL の一括取得 |
| select() ループ | orchagent の `Select::select()` がチャンネル通知で wake-up → `PortsOrch::doTask(Consumer&)` 呼び出し |

---

## 2. keyspace notification (SubscriberStateTable)

`SubscriberStateTable` は CONFIG_DB の keyspace notification を使う。

```
PSUBSCRIBE __keyspace@{db_id}__:PORT|*
```

- CONFIG_DB の Redis 設定: `notify-keyspace-events AKE`（sonic-swss/.azure-pipelines/build-template.yml:117 でテスト環境は `AKE` 設定）
- 通知イベントの種類: `hset`, `hdel`, `del` 等の hash 操作イベント
- `readData()` が `redisGetReply()` でイベントを受信し `m_keyspace_event_buffer` に蓄積
- `pops()` がバッファからキーを取り出し `m_table.get(key, ...)` で現在の hash 値を取得
- 初回起動時: `SubscriberStateTable` コンストラクタが `m_table.getKeys()` で既存キーを `m_buffer` に先読みするため、起動時の missed event を回避する

---

## 3. NotificationConsumer (syncd → PortsOrch 非同期通知)

PortsOrch は keyspace notification 以外に、syncd からの非同期イベントを `NotificationConsumer` で受信する:

```cpp
// portsorch.cpp:1070
m_portStatusNotificationConsumer = new swss::NotificationConsumer(
    m_notificationsDb.get(), "NOTIFICATIONS");
auto portStatusNotificatier = new Notifier(
    m_portStatusNotificationConsumer, this, "PORT_STATUS_NOTIFICATIONS");
Orch::addExecutor(portStatusNotificatier);
```

| 項目 | 値 |
|------|----|
| Consumer クラス | `swss::NotificationConsumer` |
| 受信チャンネル | Redis SUBSCRIBE `NOTIFICATIONS` (ASIC_DB 上) |
| イベント種別 | `port_state_change` (syncd → PortsOrch: ポートの oper_status 変化) |
| イベント種別 | `port_host_tx_ready` (syncd → PortsOrch: ホスト Tx ready 状態変化) |
| Transport | Redis PUBLISH/SUBSCRIBE (keyspace notification ではなく通常の pub/sub) |
| Payload | JSON シリアライズ: `[{op: "port_state_change", data: "<serialized_ntf>"}]` |
| Handler | `PortsOrch::doTask(NotificationConsumer&)` → `handleNotification()` |

### NotificationConsumer の動作

```cpp
// notificationconsumer.cpp
void NotificationConsumer::subscribe() {
    // 専用 DBConnector を新規作成
    m_subscribe = new DBConnector(...);
    // Redis SUBSCRIBE コマンド送信
    RedisReply r(m_subscribe, "SUBSCRIBE NOTIFICATIONS", REDIS_REPLY_ARRAY);
}
```

- `NotificationConsumer` は keyspace notification ではなく通常の Redis **SUBSCRIBE** (exact channel)
- `readData()` → `processReply()` が受信 message を JSON パースして `m_queue` に積む
- `pops()` が `m_queue` からバッチ取り出し、`POP_BATCH_SIZE` を超えた場合は次ループへ分割
- `allPortsReady()` が false のうちは `doTask` は即時リターン (初期化完了待ち)

---

## 4. portsyncd → APPL_DB 書き込み (起動時)

```
portsyncd.cpp:205-211:
```
- warm reboot 中は `APP_PORT_TABLE` への書き込みおよび `PortConfigDone` 通知をスキップ
- 通常起動: portsyncd が CONFIG_DB|PORT の全件を APPL_DB|PORT_TABLE に `ProducerStateTable::set()` で転送後、`PortConfigDone` フラグを APP_DB に書き込む

---

## 5. STATE_DB 書き込み (TTL なし)

| 操作 | コード | TTL |
|------|--------|-----|
| oper_status 更新 | `m_portStateTable.set(port.m_alias, tuples)` (portsorch.cpp) | なし (DEFAULT_DB_TTL=-1) |
| PortConfigDone | `m_portTable.set("PortConfigDone", ...)` (portsyncd) | なし |
| PortInitDone | `m_portTable.set("PortInitDone", ...)` (portsyncd) | なし |

**hSetWithTTL / EXPIRE は使用されない** — PORT テーブル処理において TTL 付き書き込みは発見されなかった。`table.cpp:146-149` の `EXPIRE` パスは `ttl != DEFAULT_DB_TTL` の場合のみ実行され、PORT の処理では常に `DEFAULT_DB_TTL (-1)` が使われる。

---

## 6. cross-namespace 通信 (VOQ chassis)

`portsorch.cpp:1086-1091`:

```cpp
if (isChassisDbInUse()) {
    Orch::addExecutor(new Consumer(
        new SubscriberStateTable(chassisAppDb, CHASSIS_APP_LAG_TABLE_NAME, ..., 0),
        this, CHASSIS_APP_LAG_TABLE_NAME));
    Orch::addExecutor(new Consumer(
        new SubscriberStateTable(chassisAppDb, CHASSIS_APP_LAG_MEMBER_TABLE_NAME, ..., 0),
        this, CHASSIS_APP_LAG_MEMBER_TABLE_NAME));
}
```

- CHASSIS_APP_DB の LAG テーブルも `SubscriberStateTable` で購読 (VOQ chassis のみ)
- PORT テーブル自体は CHASSIS_APP_DB へは購読しない

---

## 7. select() ループと retry (portmgrd)

`portmgrd.cpp`:
```cpp
ret = s.select(&sel, SELECT_TIMEOUT);  // SELECT_TIMEOUT = 1000 ms
if (ret == Select::TIMEOUT) {
    portmgr.doTask();  // 全 consumer の未処理タスクを再試行
    continue;
}
auto *c = (Executor *)sel;
c->execute();
```

- 1000 ms タイムアウト: netdev 設定失敗タスクの定期再試行に使われる
- `setPortMtu` / `setPortAdminStatus` が `false` を返すと `m_toSync` にタスクが残り次ループで再試行

---

## 8. Producer/Consumer 対応まとめ

```
CONFIG_DB[PORT|*]
  ↓ SubscriberStateTable (keyspace notification psubscribe __keyspace@db__:PORT|*)
portmgrd::doTask(Consumer&) → writeConfigToAppDb()
  ↓ ProducerStateTable::set/del
  ↓ EVALSHA → SADD KEY_SET + HSET _PORT_TABLE:<key> + PUBLISH PORT_TABLE_CHANNEL@0 G
APPL_DB[PORT_TABLE|*]
  ↓ ConsumerStateTable (subscribe PORT_TABLE_CHANNEL@0)
  ↓ EVALSHA consumer_state_table_pops.lua → SPOP KEY_SET + HGETALL
orchagent::PortsOrch::doTask(Consumer&)
  ↓ sai_port_api (SAI)

ASIC_DB[NOTIFICATIONS]
  ↑ syncd PUBLISH (port_state_change / port_host_tx_ready)
  ↓ NotificationConsumer::subscribe (SUBSCRIBE NOTIFICATIONS)
orchagent::PortsOrch::doTask(NotificationConsumer&) → handleNotification()
  ↓ updatePortOperStatus() → STATE_DB[PORT_TABLE|Ethernet*].oper_status

STATE_DB[PORT_TABLE|*]
  ← portsorch hset (oper_status, oper_speed, oper_fec) [TTL なし]
  ← portsyncd hset (PortConfigDone, PortInitDone) [TTL なし]
  → SubscriberStateTable → PortsOrch::doTask (STATE_TRANSCEIVER_INFO_TABLE 購読) [xcvrd 向け]
```
