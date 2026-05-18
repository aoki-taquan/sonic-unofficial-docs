# VLAN_SUB_INTERFACE — pubsub 調査メモ (Phase G)

調査対象:
- `sonic-swss/cfgmgr/intfmgrd.cpp`
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`
- `sonic-swss/orchagent/orch.cpp`

## CONFIG_DB → intfmgrd

`intfmgrd.cpp:28-35` の `cfg_intf_tables` ベクタに `CFG_VLAN_SUB_INTF_TABLE_NAME` ("VLAN_SUB_INTERFACE") が含まれる。
`Orch(cfgDb, tableNames)` コンストラクタ内で `addConsumer()` が `SubscriberStateTable` を生成し、CONFIG_DB (db_id=4) に対して PSUBSCRIBE を発行する。

```
PSUBSCRIBE __keyspace@4__:VLAN_SUB_INTERFACE|*
```

`notify-keyspace-events = "KEA"` が有効なため、`HSET VLAN_SUB_INTERFACE|Ethernet0.100 …` 書き込みで Redis が
`PUBLISH __keyspace@4__:VLAN_SUB_INTERFACE|Ethernet0.100 hset` を自動発行する。

親ポートの状態変化検知のため、STATE_DB の `STATE_PORT_TABLE` と `STATE_LAG_TABLE` も別途 SubscriberStateTable で購読
(`intfmgr.cpp:45-53`)。親の admin_status/MTU 変化を sub-interface へ伝播するために必要。

## intfmgrd → APPL_DB

`m_appIntfTableProducer` (`ProducerStateTable(appDb, APP_INTF_TABLE_NAME)`) が書き込みを担当。
Lua スクリプトでアトミック実行:

```
SADD APP_INTF_TABLE_KEY_SET "Ethernet0.100"
HSET _APP_INTF_TABLE|Ethernet0.100 field1 val1 …
PUBLISH APP_INTF_TABLE_CHANNEL@0 "G"
```

ペイロードは固定文字列 `"G"`。IP prefix 行 (`doIntfAddrTask`) も同じ Producer を使い
`APP_INTF_TABLE|<alias>|<prefix>` キーで書き込む (`intfmgr.cpp:1137`)。

## APPL_DB → orchagent/IntfsOrch

`IntfsOrch` が `ConsumerStateTable` で `APP_INTF_TABLE_CHANNEL@0` を購読する。
`consumer_state_table_pops.lua` が `SPOP KEY_SET` + `HGETALL _APP_INTF_TABLE:<alias>` をアトミック実行し
`IntfsOrch::doTask()` へ渡す。`doTask()` 内でサブインタフェース判定 (`alias.find('.')`) を行い、
`gPortsOrch->addSubPort()` → `setIntf()` → `sai_router_intf_api->create_router_interface()` の経路で SAI に反映。

## STATE_DB への書き戻し

`intfmgrd` は処理完了後に STATE_DB `STATE_INTERFACE_TABLE` へ TTL なしで書き込む:
- sub-IF 属性設定完了: `hset(alias, "vrf", vrf_name)`
- IP アドレス追加完了: `hset("<alias>|<prefix>", "state", "ok")`
- sub-IF 削除: `del(alias)`

`setSubIntfStateOk(alias)` / `removeSubIntfState(alias)` (`intfmgr.cpp:542-567`) が担当。
`isIntfCreated(alias)` は `m_stateIntfTable.get(alias, ...)` で STATE_DB エントリの有無を確認し、
IP アドレス設定の前提条件チェックに使用する。

## select() ループと retry

`intfmgrd` の main ループはタイムアウト 1000 ms で `Select::select()` を呼ぶ (`intfmgrd.cpp:17,59`)。
`doIntfGeneralTask` / `doIntfAddrTask` が `false` を返した場合、エントリは `m_toSync` に残留し次のループで再試行される。

## 特性まとめ

| 特性 | 内容 |
|------|------|
| CONFIG_DB → intfmgrd | Redis PSUBSCRIBE (keyspace notification) |
| keyspace pattern | `__keyspace@4__:VLAN_SUB_INTERFACE\|*` |
| 追加購読 | `STATE_PORT_TABLE`、`STATE_LAG_TABLE` (親ポート状態変化検知) |
| intfmgrd → APPL_DB | ProducerStateTable / channel PUBLISH |
| Publish チャンネル | `APP_INTF_TABLE_CHANNEL@0`、ペイロード固定 `"G"` |
| APPL_DB → orchagent | ConsumerStateTable + SUBSCRIBE |
| NotificationConsumer | 不使用 |
| TTL / keyevent expire | 不使用 |
| Select タイムアウト | 1000 ms → `intfmgr.doTask()` で未処理タスクを再試行 |
