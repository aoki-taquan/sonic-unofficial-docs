# VOQ_INBAND_INTERFACE — Phase G pubsub 調査ノート

## 調査対象

- `sonic-swss/cfgmgr/intfmgrd.cpp`
- `sonic-swss/cfgmgr/intfmgr.cpp`

## 調査日

2026-05-18

## 購読方式

`intfmgrd` は `Orch(cfgDb, tableNames)` コンストラクタ経由で以下のテーブルを購読:

```
cfg_intf_tables = {
    CFG_INTF_TABLE_NAME,
    CFG_LAG_INTF_TABLE_NAME,
    CFG_VLAN_INTF_TABLE_NAME,
    CFG_LOOPBACK_INTERFACE_TABLE_NAME,
    CFG_VLAN_SUB_INTF_TABLE_NAME,
    CFG_VOQ_INBAND_INTERFACE_TABLE_NAME,  ← 対象
}
```

Orch コンストラクタは各テーブルに対して `ConsumerStateTable` を生成し、Redis の keyspace channel を PSUBSCRIBE する。

## ProducerStateTable → ConsumerStateTable

CONFIG_DB への HSET は `ProducerStateTable` → `ConsumerStateTable` の Lua スクリプトを経由。
ペイロードは常に `"G"` (固定)。

## APPL_DB への書き込み

単一キー SET の場合 (`intfmgr.cpp:1195-1204`):
```cpp
m_appIntfTableProducer.set(keys[0], data);
```
`m_appIntfTableProducer` は `ProducerStateTable(appDb, APP_INTF_TABLE_NAME)` なので、
APPL_DB `APP_INTF_TABLE` に ProducerStateTable 経由で書き込む。

## STATE_DB への書き込み (逆方向通知)

`intfmgrd` は `SubscriberStateTable(stateDb, STATE_PORT_TABLE_NAME)` を登録
(`intfmgr.cpp:45-48`)。STATE_DB に `PORT_TABLE|Ethernet-IB<n>` の `state=ok` が書かれると
keyspace 通知で `intfmgrd.doPortTableTask()` が呼ばれ、pending タスクが再処理される。

## SELECT_TIMEOUT

`intfmgrd.cpp:17` に `#define SELECT_TIMEOUT 1000` (ms)。
TIMEOUT 時は `intfmgr.doTask()` で保留タスクを再実行。
