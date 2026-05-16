# VLAN — Phase G 通信メカニズム (Redis PUBSUB / keyspace notification)

対象ページ: `docs/reference/config-db/vlan.md`
調査日: 2026-05-15
Evidence:
- `sonic-swss/cfgmgr/vlanmgr.cpp`
- `sonic-swss/cfgmgr/vlanmgrd.cpp`
- `sonic-swss-common/common/consumerstatetable.cpp`
- `sonic-swss-common/common/subscriberstatetable.cpp`
- `sonic-swss-common/common/producerstatetable.cpp`
- `sonic-swss-common/common/consumer_state_table_pops.lua`
- `sonic-swss-common/common/dbinterface.h`
- `sonic-swss/orchagent/orch.cpp`

---

## 概要

`VLAN` テーブルは 2 系統の購読経路を持つ。

| 購読者 | 方式 | Redis primitive |
|--------|------|-----------------|
| `vlanmgrd` | **ConsumerStateTable** | PUBLISH/SUBSCRIBE (channel ベース) |
| `orchagent` (VlanOrch) | **ConsumerStateTable** | PUBLISH/SUBSCRIBE (channel ベース) |

`SubscriberStateTable` (keyspace PSUBSCRIBE) は VLAN テーブルでは**使用しない**。
`NotificationConsumer` も使用しない。TTL/keyevent expire 通知も使用しない。

---

## 通信シーケンス (vlanmgrd)

### 1. 初期化 — `vlanmgrd` 起動 (vlanmgrd.cpp:26-102)

```
vlanmgrd 起動 (main)
  └─ DBConnector cfgDb("CONFIG_DB", 0)
  └─ DBConnector appDb("APPL_DB", 0)
  └─ DBConnector stateDb("STATE_DB", 0)
  └─ VlanMgr vlanmgr(&cfgDb, &appDb, &stateDb,
       cfg_vlan_tables = ["VLAN", "VLAN_MEMBER"],
       state_vlan_tables = ["OPER_PORT_TABLE", "OPER_FDB_TABLE", "OPER_VLAN_MEMBER_TABLE"])
  └─ swss::Select s
  └─ s.addSelectables(vlanmgr.getSelectables())   ← Consumer (ConsumerStateTable x5) を登録
```

### 2. Consumer 登録 — Orch 基底クラス (orch.cpp:1186-1194)

`VlanMgr` は `Orch` を継承。`Orch::addConsumer()` が各テーブルに対して `ConsumerStateTable` を生成する。

```
Orch::addConsumer(cfgDb, "VLAN", pri)
  └─ new ConsumerStateTable(cfgDb, "VLAN", gBatchSize, pri)
       └─ [ctor] WATCH VLAN_KEY_SET
       └─ [ctor] SCARD VLAN_KEY_SET
       └─ [ctor] SUBSCRIBE "VLAN_CHANNEL@<dbId>"  ← Redis SUBSCRIBE
```

- チャンネル名: `VLAN_CHANNEL@<dbId>`  (table.h `getChannelName(int tag)`)
- KeySet 名: `VLAN_KEY_SET`
- DelKeySet 名: `VLAN_DEL_SET`
- StateHash プレフィクス: `_` (例: `_VLAN|Vlan100`)

### 3. 書き込み側 — ProducerStateTable (producerstatetable.cpp:129-168)

CONFIG_DB への書き込み (CLI / minigraph 等) は直接 HSET を使う。
`vlanmgrd` 自身は APP_DB への書き込みに `ProducerStateTable` を使用する:

```
vlanmgr.m_appVlanTableProducer.set("Vlan100", fvVector)
  ├─ EVALSHA <luaSet> 3 VLAN_CHANNEL@<dbId> VLAN_KEY_SET _VLAN|Vlan100
  │     Lua 内:
  │       SADD VLAN_KEY_SET "Vlan100"         ← 変更済みキーをキーセットに追加
  │       HSET _VLAN|Vlan100 field1 val1 ...  ← 一時ステートハッシュへ書き込み
  │       (added > 0) PUBLISH VLAN_CHANNEL@<dbId> "G"  ← 通知発行
  └─ pipeline flush
```

Lua スクリプト (`producer_state_table.lua` 埋め込み) は SADD + HSET + PUBLISH をアトミックに実行する。
PUBLISH のペイロードは固定文字列 `"G"` (ガード値)。

### 4. CONFIG_DB 購読の PUBLISH 経路

CONFIG_DB への書き込みは `sonic-db-cli`/Python `ConfigDBConnector` が `HSET` で直接書く。
`ConsumerStateTable` の ctor 内で行う `SUBSCRIBE` は **APP_DB の VLAN_CHANNEL** への通知を受け取る経路であり、CONFIG_DB の変更通知は `cfgOrch` / `cfgmgrd` フレームワーク側が別途 `swss::Select` を介して受信する。

実際には `vlanmgrd` の `cfgDb` 側も `ConsumerStateTable` を経由して CONFIG_DB `VLAN_CHANNEL@<dbId>` を購読する（Orch::addConsumer が cfgDb を引数として受け取る）。

### 5. Select ループ (vlanmgrd.cpp:69-95)

```
while (true)
  ret = s.select(&sel, SELECT_TIMEOUT=1000ms)
  ├─ ERROR   → SWSS_LOG_NOTICE("Error: %s!") ; continue
  ├─ TIMEOUT → vlanmgr.doTask()              ← 遅延タスク再実行
  └─ データあり
       → (Executor*)sel → c->execute()
            └─ Consumer::execute()
                 └─ pops(vkco)               ← ConsumerStateTable::pops (Lua EVALSHA)
                 └─ addToSync(vkco)
                 └─ vlanmgr.doTask(consumer)
                      └─ doVlanTask(consumer)  ← "VLAN"
                      └─ doVlanMemberTask(consumer) ← "VLAN_MEMBER"
                      └─ doVlanPacPortTask / PacFdbTask / PacVlanMemberTask
```

### 6. ConsumerStateTable::pops (consumer_state_table_pops.lua)

```lua
-- KEYS[1]=VLAN_KEY_SET, KEYS[2]=VLAN|, KEYS[3]=VLAN_DEL_SET
-- ARGV[1]=batch_size, ARGV[2]=stateprefix="_"
keys = SPOP(VLAN_KEY_SET, batch_size)   ← キーセットから一括取得 (非ブロッキング)
for key in keys:
  num = SREM(VLAN_DEL_SET, key)
  if num == 1: DEL("VLAN|" + key)      ← 削除フラグがあれば本体も削除
  fieldvalues = HGETALL("_VLAN|" + key)← 一時ステートハッシュから取得
  HSET("VLAN|" + key, fieldvalues)     ← 本体ハッシュへコピー
  DEL("_VLAN|" + key)                  ← 一時ハッシュを削除
  ret.insert({key, fieldvalues})
return ret
```

`pops()` は EVALSHA でこの Lua をアトミック実行し、`std::deque<KeyOpFieldsValuesTuple>` として返す。
フィールドが空 → `DEL_COMMAND`、フィールドあり → `SET_COMMAND` と判定 (consumerstatetable.cpp:84-92)。

---

## 通信シーケンス (orchagent / VlanOrch)

VlanOrch も同一 `ConsumerStateTable` 機構を使用。ただし APP_DB `APP_VLAN_TABLE` を購読する。

```
orchagent 起動
  └─ ConsumerStateTable(appDb, "APP_VLAN_TABLE", gBatchSize)
       └─ SUBSCRIBE APP_VLAN_TABLE_CHANNEL@<dbId>
  ← vlanmgrd が ProducerStateTable.set() → PUBLISH APP_VLAN_TABLE_CHANNEL@<dbId> "G"
  └─ orchagent VlanOrch::doTask()
       └─ sai_vlan_api->create_vlan(SAI_VLAN_ATTR_VLAN_ID, vlan_id)
```

---

## 重要な特性

| 特性 | 内容 |
|------|------|
| 通知種別 | Redis PUBLISH/SUBSCRIBE (channel ベース) |
| チャンネル名 | `VLAN_CHANNEL@<dbId>` (CONFIG_DB 側) / `APP_VLAN_TABLE_CHANNEL@<dbId>` (APP_DB 側) |
| PUBLISH ペイロード | 固定文字列 `"G"` |
| SWSS abstraction | `swss::ConsumerStateTable` + `swss::Select` (1000ms タイムアウトポーリング) |
| keyspace notification | **不使用** (`SubscriberStateTable` は使用しない) |
| ConsumerStateTable 内部 | `SPOP` + Lua アトミックスクリプト (`consumer_state_table_pops.lua`) |
| NotificationConsumer | **不使用** |
| TTL / keyevent expire | **不使用** |
| 起動時スナップショット | `ConsumerStateTable` ctor が `SCARD VLAN_KEY_SET` でキュー長を初期化。起動時に既存エントリを即時処理 |
| batch サイズ | `gBatchSize` (デフォルト 128) |
| タイムアウト | 1000ms (SELECT_TIMEOUT、vlanmgrd.cpp:22) |
| TIMEOUT 時の動作 | `vlanmgr.doTask()` で保留タスクを再実行 (ポート未準備時の retry) |
| warm-restart 対応 | `WarmStart::isWarmStart()` 判定で既存 STATE_DB エントリをスキップ |

---

## TTL / expire の非使用

`VLAN` テーブルエントリに TTL は設定されない。`notify-keyspace-events = "KEA"` (dbinterface.h:102) は SONiC 全体のデフォルトだが、`ConsumerStateTable` は keyspace 通知ではなく channel SUBSCRIBE を使用するため、expire イベントは受信しない。

---

## 参照コード

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-swss/cfgmgr/vlanmgrd.cpp` | 22 | `SELECT_TIMEOUT = 1000` (ms) |
| `sonic-swss/cfgmgr/vlanmgrd.cpp` | 35-43 | `cfg_vlan_tables` / `state_vlan_tables` |
| `sonic-swss/cfgmgr/vlanmgrd.cpp` | 65-95 | `swss::Select` ループ本体 |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 24-37 | VlanMgr ctor — ProducerStateTable 初期化 |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 316-489 | `doVlanTask()` — SET/DEL 分岐 |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 437 | `m_appVlanTableProducer.set(key, fvVector)` |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 441-443 | `m_stateVlanTable.set(key, ...)` — STATE_DB 更新 |
| `sonic-swss/orchagent/orch.cpp` | 1186-1194 | `Orch::addConsumer()` — ConsumerStateTable 生成 |
| `sonic-swss-common/common/consumerstatetable.cpp` | 14-34 | ctor — WATCH/SCARD/SUBSCRIBE |
| `sonic-swss-common/common/consumerstatetable.cpp` | 36-94 | `pops()` — EVALSHA + deque 組み立て |
| `sonic-swss-common/common/consumer_state_table_pops.lua` | 1-24 | SPOP + HGETALL + HSET アトミックスクリプト |
| `sonic-swss-common/common/producerstatetable.cpp` | 129-168 | `set()` — EVALSHA (SADD + HSET + PUBLISH) |
| `sonic-swss-common/common/table.h` | 85-96 | `getChannelName()` — チャンネル名生成 |
| `sonic-swss-common/common/table.h` | 278-308 | `TableName_KeySet` — VLAN_KEY_SET / VLAN_DEL_SET |
| `sonic-swss-common/common/dbinterface.h` | 83 | `KEYSPACE_PATTERN = "__key*__:*"` |
| `sonic-swss-common/common/dbinterface.h` | 102 | `KEYSPACE_EVENTS = "KEA"` |
