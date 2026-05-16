# PORT_STORM_CONTROL — Phase G 通信メカニズム中間ファイル

生成日: 2026-05-16 (Phase G)
ソース: `sonic-swss/orchagent/policerorch.cpp`, `sonic-swss/orchagent/orchdaemon.cpp`

## Producer/Consumer ペア

PORT_STORM_CONTROL テーブルは CONFIG_DB → SAI の **直接経路**をとる。APPL_DB への中継は行わない。

| 区間 | 方式 | チャンネル/パターン |
|------|------|--------------------|
| CONFIG_DB → PolicerOrch | `SubscriberStateTable` | `__keyspace@{config_db_id}__:PORT_STORM_CONTROL\|*` |
| PolicerOrch → SAI | SAI API 直接呼び出し | `sai_policer_api` + `sai_port_api` |

## SubscriberStateTable の動作

`orchdaemon.cpp:396-402` で `PolicerOrch` は `POLICER` と `CFG_PORT_STORM_CONTROL_TABLE_NAME` の 2 テーブルを `TableConnector` としてまとめ、`Orch(tableNames)` 基底クラスの `addConsumer()` を通じて `SubscriberStateTable` を生成する。CONFIG_DB の keyspace notification (`PSUBSCRIBE __keyspace@db__:PORT_STORM_CONTROL|*`) でエントリ変化を検出し、`pops()` で現在値を読み出す。初回起動時は `getKeys()` で既存エントリを先読みし、起動前の設定を取りこぼさない。

## select() ループと doTask 実行順序

orchdaemon は `Select::select()` を 1000 ms タイムアウトで実行する。イベント受信時は `Consumer::drain()` → `PolicerOrch::doTask(Consumer&)` が呼ばれる (`policerorch.cpp:374`)。

`PolicerOrch::doTask()` の先頭 (`policerorch.cpp:379-382`) では `gPortsOrch->allPortsReady()` チェックがあり、全ポート初期化完了まで処理を保留する。その後 `consumer.getTableName() == CFG_PORT_STORM_CONTROL_TABLE_NAME` を判定し (`policerorch.cpp:394`)、`handlePortStormControlTable(tuple)` にディスパッチする（POLICER テーブルとは別経路）。

## retry メカニズム

`handlePortStormControlTable()` の戻り値:
- `task_success` または `task_failed` → `m_toSync.erase(it)` (エントリ削除、リトライなし)
- `task_need_retry` → `it++` (エントリ保留、次サイクルで再試行)

SAI policer create/set 失敗は `task_failed` で silent drop。ポート未発見 (`getPort()` が false) は `task_success` で erase (設計上リトライなし)。

## SAI 呼び出し経路

```
handlePortStormControlTable()
  ↓ sai_policer_api->create_policer()   [SAI_POLICER_ATTR_METER_TYPE=BYTES,
  |                                       SAI_POLICER_ATTR_MODE=STORM_CONTROL,
  |                                       SAI_POLICER_ATTR_RED_PACKET_ACTION=DROP,
  |                                       SAI_POLICER_ATTR_CIR=kbps*1000/8]
  ↓ sai_port_api->set_port_attribute()
      SAI_PORT_ATTR_BROADCAST_STORM_CONTROL_POLICER_ID   (storm_type=broadcast)
      SAI_PORT_ATTR_FLOOD_STORM_CONTROL_POLICER_ID       (storm_type=unknown-unicast)
      SAI_PORT_ATTR_MULTICAST_STORM_CONTROL_POLICER_ID   (storm_type=unknown-multicast)
```

## データフロー図

```
CONFIG_DB[PORT_STORM_CONTROL|<ifname>|<storm_type>]
  ↓ SubscriberStateTable (keyspace notification)
  ↓ PSUBSCRIBE __keyspace@config_db_id__:PORT_STORM_CONTROL|*
orchdaemon select() loop (SELECT_TIMEOUT=1000ms)
  ↓ Consumer::drain() → PolicerOrch::doTask()
  ↓   [allPortsReady() チェック — false なら即 return]
  ↓   [table_name == CFG_PORT_STORM_CONTROL_TABLE_NAME でディスパッチ]
  ↓ handlePortStormControlTable()
    ↓ sai_policer_api->create_policer() / set_policer_attribute()
    ↓ sai_port_api->set_port_attribute()
        SAI_PORT_ATTR_{BROADCAST,FLOOD,MULTICAST}_STORM_CONTROL_POLICER_ID
ASIC (sairedis → ASIC_DB 経由)

APPL_DB 書き込み: なし
STATE_DB 書き込み: なし
NotificationConsumer: なし
```

**証跡**: `sonic-swss/orchagent/orchdaemon.cpp:396-402` (TableConnector 登録)、`sonic-swss/orchagent/policerorch.cpp:374-407` (doTask / ディスパッチ / retry 制御)、`sonic-swss/orchagent/policerorch.cpp:120-300` (handlePortStormControlTable / SAI 呼び出し)
