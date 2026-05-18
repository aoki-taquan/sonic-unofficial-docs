# DSCP_TO_FC_MAP — Phase G 通信メカニズム (pubsub)

対象テーブル: `DSCP_TO_FC_MAP`
Consumer: `QosOrch::handleDscpToFcTable()` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: `qosorch.cpp` 全行; `orchdaemon.cpp`; `Orch` 基底クラス

## Producer/Consumer ペア

DSCP_TO_FC_MAP は CONFIG_DB → SAI の **直接経路**をとる。APPL_DB / STATE_DB への書き込みは一切行わない。

| 区間 | 方式 | チャンネル/パターン |
|------|------|--------------------|
| CONFIG_DB → QosOrch | `SubscriberStateTable` | `__keyspace@{config_db_id}__:DSCP_TO_FC_MAP\|*` |
| QosOrch → SAI | SAI API 直接呼び出し | `sai_qos_map_api->create_qos_map` / `set_qos_map_attribute` / `remove_qos_map` |

## SubscriberStateTable の動作

`QosOrch` は `Orch(db, tableNames)` 基底クラスの `addConsumer()` を通じて
`CFG_DSCP_TO_FC_MAP_TABLE_NAME` に対する `SubscriberStateTable` を生成する。
CONFIG_DB の keyspace notification (`PSUBSCRIBE __keyspace@db__:DSCP_TO_FC_MAP|*`) でエントリ変化を検出し、
`pops()` で現在値を読み出す。orchagent 起動直後は `getKeys()` で既存エントリを先読みする。

ソース: `qosorch.cpp:1313-1337` (initTableHandlers で CFG_DSCP_TO_FC_MAP_TABLE_NAME を登録)

## doTask 実行順序

`QosOrch::doTask()` (qosorch.cpp:2231) はカスタム実行順序を実装する:

1. `PORT_QOS_MAP` と `QUEUE` 以外の全テーブル (DSCP_TO_FC_MAP 含む) を先に drain
2. `PORT_QOS_MAP` を drain
3. 最後に `QUEUE` を drain

これにより `DSCP_TO_FC_MAP` の SAI object が `PORT_QOS_MAP` の参照解決前に確実に作成される。

## retry メカニズム

- `task_need_retry` → エントリは `m_toSync` に残留、次の doTask サイクルで再試行
- `task_failed` → silent drop (エントリ消去、エラーログのみ)
- `task_invalid_entry` → silent drop (バリデーション失敗)

## 通知なし

- APPL_DB への書き込み: なし
- STATE_DB への書き込み: なし  
- NotificationConsumer / NotificationProducer: なし
- `gPortsOrch` への通知: なし

ソース: `qosorch.cpp:1039-1130` (DscpToFcMapHandler); `qosorch.cpp:2231-2252` (doTask ordering)
