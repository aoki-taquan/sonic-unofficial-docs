# VLAN_MEMBER — Phase G 通信メカニズム (Redis PUBSUB / keyspace notification)

対象ページ: `docs/reference/config-db/vlan-member.md`
調査日: 2026-05-16
Evidence:
- `sonic-swss/cfgmgr/vlanmgr.cpp`
- `sonic-swss/cfgmgr/vlanmgrd.cpp`
- `sonic-swss/cfgmgr/vlanmgr.h`
- `sonic-swss-common/common/consumerstatetable.cpp`
- `sonic-swss-common/common/producerstatetable.cpp`
- `sonic-swss-common/common/consumer_state_table_pops.lua`
- `sonic-swss/orchagent/orch.cpp`

---

## 概要

`VLAN_MEMBER` テーブルは `vlanmgrd` と `orchagent` (VlanOrch) の 2 系統から購読される。

| 購読者 | 方式 | Redis primitive |
|--------|------|-----------------|
| `vlanmgrd` | **ConsumerStateTable** | PUBLISH/SUBSCRIBE (channel ベース) |
| `orchagent` (VlanOrch) | **ConsumerStateTable** | PUBLISH/SUBSCRIBE (channel ベース) |

`SubscriberStateTable` (keyspace PSUBSCRIBE) は**使用しない**。
`NotificationConsumer` も TTL/keyevent expire 通知も使用しない。

---

## 通信シーケンス (vlanmgrd — CFG_VLAN_MEMBER → APP_VLAN_MEMBER_TABLE)

### 1. 初期化 — `vlanmgrd` 起動 (vlanmgrd.cpp:26-102)

```
vlanmgrd 起動 (main)
  └─ DBConnector cfgDb("CONFIG_DB", 0)
  └─ DBConnector appDb("APPL_DB", 0)
  └─ DBConnector stateDb("STATE_DB", 0)
  └─ VlanMgr vlanmgr(&cfgDb, &appDb, &stateDb,
       cfg_vlan_tables = ["VLAN", "VLAN_MEMBER"],     ← VLAN_MEMBER を含む
       state_vlan_tables = ["OPER_PORT_TABLE", "OPER_FDB_TABLE", "OPER_VLAN_MEMBER_TABLE"])
  └─ swss::Select s
  └─ s.addSelectables(vlanmgr.getSelectables())   ← ConsumerStateTable x5 を登録
```

### 2. Consumer 登録 — Orch 基底クラス (orch.cpp:1186-1194)

`VlanMgr` は `Orch` を継承し、`Orch::addConsumer()` が各テーブルに対して `ConsumerStateTable` を生成する。

```
Orch::addConsumer(cfgDb, "VLAN_MEMBER", pri)
  └─ new ConsumerStateTable(cfgDb, "VLAN_MEMBER", gBatchSize, pri)
       └─ [ctor] WATCH VLAN_MEMBER_KEY_SET
       └─ [ctor] SCARD VLAN_MEMBER_KEY_SET
       └─ [ctor] SUBSCRIBE "VLAN_MEMBER_CHANNEL@<dbId>"  ← Redis SUBSCRIBE
```

- チャンネル名: `VLAN_MEMBER_CHANNEL@<dbId>` (table.h `getChannelName()`)
- KeySet 名: `VLAN_MEMBER_KEY_SET`
- DelKeySet 名: `VLAN_MEMBER_DEL_SET`
- StateHash プレフィクス: `_` (例: `_VLAN_MEMBER|Vlan100|Ethernet0`)

### 3. 書き込み側 — CONFIG_DB への書き込みと PUBLISH

CLI (`config vlan member add/del`) は Python `ConfigDBConnector.set_entry()` → `HSET VLAN_MEMBER|Vlan<id>|<port> tagging_mode <val>` で直接 CONFIG_DB に書く。
`ProducerStateTable` (SWSS 経由) が `SADD VLAN_MEMBER_KEY_SET` + `HSET _VLAN_MEMBER|...` + `PUBLISH VLAN_MEMBER_CHANNEL@<dbId> "G"` をアトミック (EVALSHA) に実行する。

```
ConfigDBConnector.set_entry("VLAN_MEMBER", ("Vlan100", "Ethernet0"), {"tagging_mode": "tagged"})
  └─ ProducerStateTable.set("Vlan100|Ethernet0", fvVector)
       └─ EVALSHA <luaSet> 3
             VLAN_MEMBER_CHANNEL@<cfgDbId>
             VLAN_MEMBER_KEY_SET
             _VLAN_MEMBER|Vlan100|Ethernet0
          Lua 内:
            SADD VLAN_MEMBER_KEY_SET "Vlan100|Ethernet0"
            HSET _VLAN_MEMBER|Vlan100|Ethernet0 tagging_mode tagged
            (added > 0) PUBLISH VLAN_MEMBER_CHANNEL@<cfgDbId> "G"
```

### 4. Select ループ (vlanmgrd.cpp:69-95)

```
while (true)
  ret = s.select(&sel, SELECT_TIMEOUT=1000ms)
  ├─ ERROR   → SWSS_LOG_NOTICE("Error: %s!") ; continue
  ├─ TIMEOUT → vlanmgr.doTask()              ← 遅延タスク再実行 (ポート未準備 retry)
  └─ データあり
       → (Executor*)sel → c->execute()
            └─ Consumer::execute()
                 └─ pops(vkco)               ← ConsumerStateTable::pops (Lua EVALSHA)
                 └─ addToSync(vkco)
                 └─ vlanmgr.doTask(consumer)
                      └─ doVlanMemberTask(consumer)  ← table_name == "VLAN_MEMBER"
```

### 5. ConsumerStateTable::pops (consumer_state_table_pops.lua)

```lua
-- KEYS[1]=VLAN_MEMBER_KEY_SET, KEYS[2]=VLAN_MEMBER|, KEYS[3]=VLAN_MEMBER_DEL_SET
keys = SPOP(VLAN_MEMBER_KEY_SET, batch_size)
for key in keys:
  num = SREM(VLAN_MEMBER_DEL_SET, key)
  if num == 1: DEL("VLAN_MEMBER|" + key)      ← 削除フラグがあれば本体も削除
  fieldvalues = HGETALL("_VLAN_MEMBER|" + key) ← 一時ステートハッシュから取得
  HSET("VLAN_MEMBER|" + key, fieldvalues)      ← 本体ハッシュへコピー
  DEL("_VLAN_MEMBER|" + key)                   ← 一時ハッシュを削除
  ret.insert({key, fieldvalues})
return ret
```

フィールドが空 → `DEL_COMMAND`、フィールドあり → `SET_COMMAND`。

### 6. doVlanMemberTask — Linux bridge 操作と APP_VLAN_MEMBER への書き込み (vlanmgr.cpp:593-724)

```
doVlanMemberTask(consumer)
  SET 操作:
    isVlanMemberStateOk(key)  → 既存なら m_vlanMemberReplay.erase, skip
    isMemberStateOk(port_alias) && isVlanStateOk(vlan_alias) → false なら it++ (retry)
    tagging_mode = "untagged" (デフォルト) or kfvFieldsValues から取得
    addHostVlanMember(vlan_id, port_alias, tagging_mode)
      └─ ip link set <port> master Bridge
      └─ bridge vlan del vid 1 dev <port>
      └─ bridge vlan add vid <vlan_id> dev <port> [pvid untagged]  ← kernel bridge
    m_appVlanMemberTableProducer.set(key, kfvFieldsValues(t))
      └─ ProducerStateTable → PUBLISH APP_VLAN_MEMBER_TABLE_CHANNEL@<appDbId> "G"
    m_stateVlanMemberTable.set(kfvKey(t), [("state","ok")])
  DEL 操作:
    removeHostVlanMember(vlan_id, port_alias)
      └─ bridge vlan del vid <vlan_id> dev <port>
      └─ (VLAN ゼロなら) ip link set <port> nomaster
    m_appVlanMemberTableProducer.del(key)
    m_stateVlanMemberTable.del(kfvKey(t))
```

---

## 通信シーケンス (orchagent / VlanOrch — APP_VLAN_MEMBER_TABLE → SAI)

`orchagent` は APP_DB `APP_VLAN_MEMBER_TABLE` を `ConsumerStateTable` で購読する。

```
orchagent 起動
  └─ ConsumerStateTable(appDb, "APP_VLAN_MEMBER_TABLE", gBatchSize)
       └─ SUBSCRIBE APP_VLAN_MEMBER_TABLE_CHANNEL@<appDbId>
  ← vlanmgrd が m_appVlanMemberTableProducer.set() → PUBLISH APP_VLAN_MEMBER_TABLE_CHANNEL "G"
  └─ orchagent VlanOrch::doTask(consumer)
       ├─ sai_vlan_api->create_vlan_member(
       │     SAI_VLAN_MEMBER_ATTR_VLAN_ID,
       │     SAI_VLAN_MEMBER_ATTR_BRIDGE_PORT_ID,
       │     SAI_VLAN_MEMBER_ATTR_VLAN_TAGGING_MODE  ← tagged/untagged/priority_tagged → SAI enum
       │   )
       └─ STATE_DB VLAN_MEMBER_TABLE に state=ok を書き込み (orchagent 側)
```

---

## PAC 経由の VLAN_MEMBER (doVlanPacVlanMemberTask)

`STATE_OPER_VLAN_MEMBER_TABLE` (STATE_DB) を購読する別ハンドラ経路。

```
STATE_DB STATE_OPER_VLAN_MEMBER_TABLE 変更
  └─ doVlanPacVlanMemberTask(consumer)
       SET: tagging_mode = "untagged" (固定)
         既存 VLAN メンバを全削除 → addHostVlanMember(vlan_id, port, "untagged")
         → m_appVlanMemberTableProducer.set(key, fvVector + [("dynamic","yes")])
       DEL: removeHostVlanMember → m_appVlanMemberTableProducer.del
         既存 m_PortVlanMember を再追加 (アクセス VLAN 復元)
```

---

## 重要な特性

| 特性 | 内容 |
|------|------|
| 通知種別 | Redis PUBLISH/SUBSCRIBE (channel ベース) |
| CFG→VLANMGRD チャンネル | `VLAN_MEMBER_CHANNEL@<cfgDbId>` |
| VLANMGRD→ORCHAGENT チャンネル | `APP_VLAN_MEMBER_TABLE_CHANNEL@<appDbId>` |
| PUBLISH ペイロード | 固定文字列 `"G"` |
| SWSS abstraction | `swss::ConsumerStateTable` + `swss::Select` (1000ms タイムアウト) |
| keyspace notification | **不使用** (`SubscriberStateTable` は使用しない) |
| NotificationConsumer | **不使用** |
| TTL / keyevent expire | **不使用** |
| batch サイズ | `gBatchSize` (デフォルト 128) |
| タイムアウト | 1000ms (SELECT_TIMEOUT、vlanmgrd.cpp:22) |
| TIMEOUT 時の動作 | `vlanmgr.doTask()` で保留タスク再実行 (ポート/VLAN 未準備 retry) |
| warm-restart 対応 | `m_vlanMemberReplay` セットで STATE_DB 既存エントリをスキップ |
| Linux bridge 操作 | `bridge vlan add/del` + `ip link set master/nomaster` をカーネルに発行 |
| SAI API | `sai_vlan_api->create_vlan_member()` / `remove_vlan_member()` |

---

## 参照コード

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-swss/cfgmgr/vlanmgrd.cpp` | 22 | `SELECT_TIMEOUT = 1000` (ms) |
| `sonic-swss/cfgmgr/vlanmgrd.cpp` | 35-43 | `cfg_vlan_tables` に `"VLAN_MEMBER"` を含む |
| `sonic-swss/cfgmgr/vlanmgrd.cpp` | 65-95 | `swss::Select` ループ本体 |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 24-37 | VlanMgr ctor — `m_appVlanMemberTableProducer` 初期化 |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 233-273 | `addHostVlanMember()` — bridge vlan add コマンド生成 |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 593-724 | `doVlanMemberTask()` — SET/DEL 分岐 + APP_DB 書き込み |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 672 | `m_appVlanMemberTableProducer.set(key, kfvFieldsValues(t))` |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 677 | `m_stateVlanMemberTable.set(kfvKey(t), ...)` — STATE_DB 更新 |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 842-923 | `doVlanPacVlanMemberTask()` — PAC 経路 |
| `sonic-swss/cfgmgr/vlanmgr.cpp` | 887 | PAC 経路の `dynamic: yes` 注入 |
| `sonic-swss/orchagent/orch.cpp` | 1186-1194 | `Orch::addConsumer()` — ConsumerStateTable 生成 |
| `sonic-swss-common/common/consumerstatetable.cpp` | 14-34 | ctor — WATCH/SCARD/SUBSCRIBE |
| `sonic-swss-common/common/consumerstatetable.cpp` | 36-94 | `pops()` — EVALSHA + deque |
| `sonic-swss-common/common/producerstatetable.cpp` | 129-168 | `set()` — EVALSHA (SADD + HSET + PUBLISH) |
| `sonic-swss-common/common/table.h` | 85-96 | `getChannelName()` — チャンネル名生成 |
