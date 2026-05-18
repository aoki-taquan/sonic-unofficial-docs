# vlan-state-pubsub — Phase G 調査メモ

対象: `STATE_DB VLAN_TABLE` の Redis PUBSUB / 通知メカニズム
調査日: 2026-05-18
精読ファイル:
- `sonic-swss/cfgmgr/vlanmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/cfgmgr/vlanmgr.h`
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/cfgmgr/stpmgr.cpp`
- `sonic-swss/cfgmgr/natmgr.cpp`
- `sonic-swss/cfgmgr/vxlanmgr.cpp`

---

## 書き込みメカニズム: swss::Table（直接書き込み）

`m_stateVlanTable` は `swss::Table` として定義されている (vlanmgr.h:26)。
`ProducerStateTable` ではなく `Table` を使用するため、書き込み時に Redis チャンネルへの
`PUBLISH` は行われない。

```cpp
// vlanmgr.h:26
Table m_stateVlanTable, m_stateVlanMemberTable;
```

書き込み操作:
- `m_stateVlanTable.set(key, fvVector)` → `HSET STATE_DB VLAN_TABLE|VlanN state ok` の直接実行
- `m_stateVlanTable.del(key)` → `DEL STATE_DB VLAN_TABLE|VlanN` の直接実行

これは Redis の通常の keyspace notification (`__keyspace@6__:VLAN_TABLE|*`) を生成するが、
swss::ConsumerStateTable が使うチャンネル (`VLAN_TABLE_CHANNEL@6`) は存在しない。

---

## 読み取りメカニズム: Table::get() によるポーリング

各 consumer は `swss::Table m_stateVlanTable` (stateDb, STATE_VLAN_TABLE_NAME) を
コンストラクタで保持し、`isVlanStateOk()` / `isIntfStateOk()` などのヘルパーメソッドで
`Table::get()` を呼ぶ。

- `intfmgr.cpp:655`: `m_stateVlanTable.get(alias, temp)` → keyspace event なし、直接 HGETALL
- `vlanmgr.cpp:523`: `m_stateVlanTable.get(alias, temp)` → 同上
- `stpmgr.cpp:1282` (isVlanStateOk): 同パターン
- `natmgr.cpp:102`: 同パターン
- `vxlanmgr.cpp:774`: 同パターン

poll タイミングは各 consumer が自身のタスク処理ループ (`doTask()`) 内でのみ実行する。

---

## intfmgrd の SubscriberStateTable は PORT/LAG のみ

intfmgr.cpp:45-55 で SubscriberStateTable を登録しているのは `STATE_PORT_TABLE_NAME`
および `STATE_LAG_TABLE_NAME` のみ。`STATE_VLAN_TABLE_NAME` は SubscriberStateTable
を持たず、インタフェース設定タスク内で直接 `Table::get()` で確認している。

---

## VLAN_TABLE が State_DB keyspace notification を生成するか

`swss::Table::set()` は EVALSHA を使わず、直接 HSET を Redis に送る。
Redis の keyspace notification が有効な場合 (`notify-keyspace-events KEA` など)、
`__keyspace@6__:VLAN_TABLE|Vlan100` チャンネルに `set` イベントが PUBLISH される。
しかし swss の標準デーモンは `VLAN_TABLE` の keyspace notification を購読していない。

---

## まとめ

| 項目 | 内容 |
|------|------|
| 書き込み方式 | `swss::Table::set()`（直接 HSET、PUBLISH なし） |
| 読み取り方式 | `swss::Table::get()`（直接 HGETALL、SUBSCRIBE なし） |
| consumer 通知トリガー | なし — consumer 自身が自タスク処理時にポーリング |
| keyspace notification | Redis が生成するが swss デーモンは購読していない |
| 使用していない方式 | ProducerStateTable / ConsumerStateTable / NotificationConsumer / TTL |
