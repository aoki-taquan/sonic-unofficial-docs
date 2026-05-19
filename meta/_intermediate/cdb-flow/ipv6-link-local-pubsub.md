# ipv6-link-local — Phase G: 通信メカニズム (pubsub)

## 調査対象

- `sonic-swss/cfgmgr/intfmgrd.cpp` (main loop, table registration)
- `sonic-swss/cfgmgr/intfmgr.cpp` (IntfMgr constructor, table declarations)
- `sonic-swss/cfgmgr/intfmgr.h` (ProducerStateTable declaration)
- `sonic-swss/neighsyncd/neighsync.cpp` (isLinkLocalEnabled, m_cfgInterfaceTable direct read)

## 調査結果

### CONFIG_DB → IntfMgr (Orch ベース ConsumerStateTable)

`intfmgrd.cpp:28-35` で購読テーブルリストを構築し `IntfMgr` コンストラクタに渡す:

```
CFG_INTF_TABLE_NAME           → "INTERFACE"
CFG_LAG_INTF_TABLE_NAME       → "PORTCHANNEL_INTERFACE"
CFG_VLAN_INTF_TABLE_NAME      → "VLAN_INTERFACE"
CFG_LOOPBACK_INTERFACE_TABLE_NAME
CFG_VLAN_SUB_INTF_TABLE_NAME
CFG_VOQ_INBAND_INTERFACE_TABLE_NAME
```

`IntfMgr` は `Orch(cfgDb, tableNames)` を継承するため、Orch 基底クラスが各テーブルを
`ConsumerStateTable` (Redis keyspace notification) でラップして `Executor` に登録する。
`ipv6_use_link_local_only` フィールドへの `HSET`/`DEL` が INTERFACE / PORTCHANNEL_INTERFACE /
VLAN_INTERFACE テーブルで発生すると `doIntfGeneralTask()` が呼ばれる。

### IntfMgr → APPL_DB (ProducerStateTable)

`intfmgr.cpp:42`:
```cpp
m_appIntfTableProducer(appDb, APP_INTF_TABLE_NAME)
```

`ProducerStateTable` を使用。`doIntfGeneralTask()` の SET 処理内 (`intfmgr.cpp:1053`) で
`m_appIntfTableProducer.set(alias, data)` により `INTF_TABLE|<ifname>` に `ipv6_use_link_local_only`
フィールドを書き込む。DEL 時は `m_appIntfTableProducer.del(alias)` (`intfmgr.cpp:1088`)。

IntfsOrch (orchagent) は `APP_INTF_TABLE_NAME` を `ConsumerStateTable` で購読しているが、
`ipv6_use_link_local_only` フィールドを SAI に転送しない (dead consumer)。

### neighsyncd の CONFIG_DB 直接参照 (Table::get, NOT SubscriberStateTable)

`neighsync.cpp:25-27`:
```cpp
m_cfgInterfaceTable(cfgDb, CFG_INTF_TABLE_NAME),
m_cfgLagInterfaceTable(cfgDb, CFG_LAG_INTF_TABLE_NAME),
m_cfgVlanInterfaceTable(cfgDb, CFG_VLAN_INTF_TABLE_NAME),
```

これらは `Table` オブジェクト (SubscriberStateTable ではない) による直接読み取り。
`isLinkLocalEnabled()` は netlink `RTM_NEWNEIGH` / `RTM_DELNEIGH` イベント受信時に呼ばれ、
CONFIG_DB を同期的に `get()` する。購読チャンネルではなくポイントインタイム参照。

### 通知チャンネルまとめ

| Publisher | チャンネル種別 | テーブル / キー | Subscriber | 備考 |
|-----------|-------------|--------------|------------|------|
| CLI / minigraph (CONFIG_DB HSET) | ConsumerStateTable (Orch継承) | `INTERFACE\|<name>` ほか | IntfMgrd | keyspace notification |
| IntfMgrd | ProducerStateTable | `APPL_DB INTF_TABLE\|<name>` | IntfsOrch (orchagent) | dead consumer (SAI 転送なし) |
| kernel netlink | rtnetlink `RTM_NEWNEIGH` | — | neighsyncd | netlink socket, DB pubsub 外 |
| neighsyncd | ProducerStateTable | `APPL_DB NEIGH_TABLE\|<intf>:<ip>` | NeighOrch (orchagent) | link-local enabled 時のみ ADD |

### 明示 PUBLISH / Notifier

`ipv6_use_link_local_only` の処理経路に Redis `PUBLISH` コマンドや `Notifier` 機構は使用されていない。
すべてのトリガは ConsumerStateTable (keyspace notification) または netlink イベントによる。
