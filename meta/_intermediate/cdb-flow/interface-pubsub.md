# INTERFACE テーブル — 通信メカニズム調査メモ (Phase G)

調査日: 2026-05-14
対象ソース:
- `sonic-swss/cfgmgr/intfmgr.cpp` / `intfmgr.h`
- `sonic-swss/cfgmgr/intfmgrd.cpp`
- `sonic-swss/orchagent/intfsorch.cpp` / `intfsorch.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss-common/common/producerstatetable.cpp`
- `sonic-swss-common/common/subscriberstatetable.cpp`
- `sonic-swss-common/common/consumerstatetable.cpp`
- `sonic-swss-common/common/table.h`

---

## 1. Producer/Consumer ペア

### CONFIG_DB → intfmgrd

| 項目 | 値 |
|------|----|
| 購読方式 | `Orch(cfgDb, tableNames)` 基底クラス経由の `SubscriberStateTable` |
| keyspace パターン | `__keyspace@{db_id}__:INTERFACE|*` (および VLAN_INTERFACE|* / LAG_INTERFACE|* 等) |
| 購読テーブル (intfmgrd が登録する全テーブル) | `CFG_INTF_TABLE_NAME`, `CFG_LAG_INTF_TABLE_NAME`, `CFG_VLAN_INTF_TABLE_NAME`, `CFG_LOOPBACK_INTERFACE_TABLE_NAME`, `CFG_VLAN_SUB_INTF_TABLE_NAME`, `CFG_VOQ_INBAND_INTERFACE_TABLE_NAME` |
| Consumer クラス | `Consumer` (wraps `SubscriberStateTable`) |
| 追加 Consumer | `SubscriberStateTable(stateDb, STATE_PORT_TABLE_NAME)` — PORT状態変化を受け取る (intfmgr.cpp L45-48) |
| 追加 Consumer (LAG) | `SubscriberStateTable(stateDb, STATE_LAG_TABLE_NAME)` — LAG状態変化 (L50-53) |

### intfmgrd → APPL_DB (ProducerStateTable)

| 項目 | 値 |
|------|----|
| Producer クラス | `ProducerStateTable m_appIntfTableProducer(appDb, APP_INTF_TABLE_NAME)` |
| Publish チャンネル | `APP_INTF_TABLE_NAME + "_CHANNEL@" + db_id` (実値: `APPL_DB|APP_INTF_TABLE_CHANNEL@0`) |
| Key SET 名 | `APP_INTF_TABLE_NAME + "_KEY_SET"` |
| Del SET 名 | `APP_INTF_TABLE_NAME + "_DEL_SET"` |
| State hash prefix | `_` (一時 hash: `_APP_INTF_TABLE_NAME:key`) |
| 書き込み操作 | `m_appIntfTableProducer.set(alias, data)` (SET) / `m_appIntfTableProducer.del(alias)` (DEL) |
| Lua スクリプト | `EVALSHA` + SADD to KEY_SET + HSET to `_<table>:<key>` + `PUBLISH <channel> G` |

### APPL_DB → orchagent (ConsumerStateTable)

| 項目 | 値 |
|------|----|
| Consumer クラス | `ConsumerStateTable` (orchdaemon.cpp L296: `new IntfsOrch(m_applDb, APP_INTF_TABLE_NAME, ...)`) |
| Subscribe チャンネル | `APP_INTF_TABLE_NAME + "_CHANNEL@0"` |
| Pop Lua スクリプト | `consumer_state_table_pops.lua` — KEY_SET から SCARD/SPOP → HGETALL の一括取得 |
| select() ループ | orchagent の `Select::select()` がチャンネル通知で wake-up → `IntfsOrch::doTask(Consumer&)` 呼び出し |

---

## 2. keyspace notification (SubscriberStateTable)

`SubscriberStateTable` は CONFIG_DB の keyspace notification を使う。

```
PSUBSCRIBE __keyspace@{db_id}__:<tableName>|*
```

- CONFIG_DB の Redis 設定: `notify-keyspace-events` が `KEA` 等で有効化されている必要がある (notify-keyspace-events は sonic-db-cli / ConfigDB で設定)
- 通知イベントの種類: `hset`, `hdel`, `del` 等の hash 操作イベント
- `readData()` が `redisGetReply()` でイベントを受信し `m_keyspace_event_buffer` に蓄積
- `pops()` がバッファからキーを取り出し `m_table.get(key, ...)` で現在の hash 値を取得

---

## 3. STATE_DB 書き込み (hset)

intfmgr が STATE_DB に書き込む箇所 (TTL なし通常 hset):

| 操作 | コード |
|------|--------|
| L3 IF 設定完了 | `m_stateIntfTable.hset(alias, "vrf", vrf_name)` (L1054) |
| IP アドレス追加完了 | `m_stateIntfTable.hset(keys[0]+"|"+keys[1], "state", "ok")` (L1138) |
| IP アドレス削除 | `m_stateIntfTable.del(...)` (L1162) |
| IF 属性削除 | `m_stateIntfTable.del(alias)` (L1089) |

**hSetWithTTL は使用されない** — INTERFACE テーブルの処理において TTL 付き書き込みは発見されなかった。

---

## 4. cross-namespace 通信 (VOQ / chassis)

`intfsorch.cpp` L102-108:

```cpp
if (isChassisDbInUse()) {
    tableName = CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME;
    Orch::addExecutor(new Consumer(
        new SubscriberStateTable(chassisAppDb, tableName, ..., 0),
        this, tableName));
    m_tableVoqSystemInterfaceTable = unique_ptr<Table>(
        new Table(chassisAppDb, CHASSIS_APP_SYSTEM_INTERFACE_TABLE_NAME));
}
```

- chassis App DB (`CHASSIS_APP_DB`) に接続し `SYSTEM_INTERFACE_TABLE` を購読
- VOQ スイッチでのみ有効。通常の単体スイッチでは使用されない

---

## 5. select() ループと retry

intfmgrd.cpp:
```cpp
ret = s.select(&sel, SELECT_TIMEOUT);  // SELECT_TIMEOUT = 1000 ms
if (ret == Select::TIMEOUT) {
    intfmgr.doTask();  // 全 consumer の未処理タスクを再試行
    continue;
}
auto *c = (Executor *)sel;
c->execute();
```

- 1000 ms タイムアウト: 未処理タスク (interface/VRF が not ready) を定期再試行
- `doIntfGeneralTask` / `doIntfAddrTask` が `false` を返すと `m_toSync` にタスクが残り次ループで再試行

---

## 6. Producer/Consumer 対応まとめ

```
CONFIG_DB[INTERFACE|*]
  ↓ SubscriberStateTable (keyspace notification psubscribe)
intfmgrd::doIntfGeneralTask / doIntfAddrTask
  ↓ ProducerStateTable::set/del
  ↓ EVALSHA → SADD KEY_SET + HSET _APP_INTF_TABLE:key + PUBLISH APP_INTF_TABLE_CHANNEL@0
APPL_DB[APP_INTF_TABLE|*]
  ↓ ConsumerStateTable (subscribe APP_INTF_TABLE_CHANNEL@0)
  ↓ EVALSHA consumer_state_table_pops.lua → SPOP KEY_SET + HGETALL
orchagent::IntfsOrch::doTask
  ↓ sai_router_intf_api (SAI)

STATE_DB[STATE_INTERFACE_TABLE|*]
  ← intfmgrd::hset (vrf, state=ok)  [TTLなし]

STATE_DB[STATE_PORT_TABLE|*]
  → SubscriberStateTable → intfmgrd::doPortTableTask  [admin_status/mtu変化検知]
```
