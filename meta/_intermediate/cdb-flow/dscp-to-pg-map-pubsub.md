# DSCP_TO_PG_MAP — Phase G 通信メカニズムスキャンノート

対象テーブル: `DSCP_TO_PG_MAP`（非実在）— 2 段マッピング代替 (`DSCP_TO_TC_MAP` / `TC_TO_PRIORITY_GROUP_MAP` / `PORT_QOS_MAP`)
Consumer: `QosOrch` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: orchdaemon.cpp L367-384, qosorch.cpp L2231-2299

---

## 登録経路（orchdaemon → QosOrch）

`orchdaemon.cpp:384` で `gQosOrch = new QosOrch(m_configDb, qos_tables)` として生成される。
`qos_tables` には `CFG_DSCP_TO_TC_MAP_TABLE_NAME`（L370）と `CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME`（L376）および `CFG_PORT_QOS_MAP_TABLE_NAME`（L374）が含まれる。

`Orch(db, tableNames)` 基底クラスは各テーブル名に対して `addConsumer()` を呼び、`SubscriberStateTable` を生成する。
keyspace notification パターン: `PSUBSCRIBE __keyspace@{config_db_id}__:<TABLE>|*`

## 実行順序制御（QosOrch::doTask()）

`QosOrch::doTask()` (qosorch.cpp:2231-2252) はカスタム drain 順序を実装する:

1. `PORT_QOS_MAP` と `QUEUE` 以外のすべての Consumer（`DSCP_TO_TC_MAP`、`TC_TO_PRIORITY_GROUP_MAP`、`SCHEDULER`、`WRED_PROFILE` 等）を先に drain
2. `PORT_QOS_MAP` を drain（参照先マップが揃った後）
3. `QUEUE` を drain（最後）

この順序により、`DSCP_TO_TC_MAP` / `TC_TO_PRIORITY_GROUP_MAP` の SAI 反映が常に `PORT_QOS_MAP` の処理より先に行われ、`resolveFieldRefValue()` の `task_need_retry` を最小化する。

## doTask(Consumer&) の allPortsReady ガード

`QosOrch::doTask(Consumer&)` (qosorch.cpp:2258-2261): `gPortsOrch->allPortsReady()` が false の場合は即 return。全ポート初期化完了まで `DSCP_TO_TC_MAP` / `TC_TO_PRIORITY_GROUP_MAP` / `PORT_QOS_MAP` すべての処理がブロックされる。

## APPL_DB / STATE_DB 経由なし

`DSCP_TO_TC_MAP` および `TC_TO_PRIORITY_GROUP_MAP` は CONFIG_DB から QosOrch が直接購読する。cfgmgr ステージや APPL_DB への中継は存在しない。`handleDscpToTcTable()` / `handleTcToPgTable()` は直接 `create_qos_map()` / `set_qos_map_attribute()` を呼ぶ。

## NotificationConsumer なし

QosOrch は NotificationConsumer を使用しない。すべてのイベントは `SubscriberStateTable` の keyspace notification で処理される。

## 参照関係サマリ

| 区間 | 方式 | チャンネル/パターン |
|------|------|--------------------|
| CONFIG_DB → QosOrch (DSCP_TO_TC_MAP) | SubscriberStateTable | `PSUBSCRIBE __keyspace@config_db_id__:DSCP_TO_TC_MAP\|*` |
| CONFIG_DB → QosOrch (TC_TO_PRIORITY_GROUP_MAP) | SubscriberStateTable | `PSUBSCRIBE __keyspace@config_db_id__:TC_TO_PRIORITY_GROUP_MAP\|*` |
| CONFIG_DB → QosOrch (PORT_QOS_MAP) | SubscriberStateTable | `PSUBSCRIBE __keyspace@config_db_id__:PORT_QOS_MAP\|*` |
| QosOrch → SAI | SAI API 直接呼び出し | `sai_qos_map_api->create_qos_map()` / `set_qos_map_attribute()` / `remove_qos_map()` |
| QosOrch → SAI ポート | SAI API | `sai_port_api->set_port_attribute(SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP / TC_TO_PRIORITY_GROUP_MAP)` |

evidence: `orchdaemon.cpp:367-384`, `qosorch.cpp:2231-2261`, `qosorch.cpp:1326-1344`
