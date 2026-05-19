# stp — pubsub 調査メモ (Phase G)

## 調査対象

CONFIG_DB テーブル: `STP`, `STP_VLAN`, `STP_PORT`, `STP_VLAN_PORT`

## アーキテクチャ概要

```
config stp CLI (sonic-utilities)
  ↓ CONFIG_DB への直接書き込み
stpmgrd (sonic-swss/cfgmgr/stpmgrd.cpp)
  ↓ SubscriberStateTable で CONFIG_DB を購読
  ↓ Unix Domain Socket (/var/run/stpipc.sock) で stpd に IPC
stpd (外部 STP デーモン, sonic-stp リポジトリ)
  ↓ ProducerStateTable 経由で APPL_DB に書き込み
StpOrch (orchagent/stporch.cpp)
  ↓ ConsumerStateTable で APPL_DB を購読
  ↓ SAI API でハードウェアに設定
```

## CONFIG_DB → stpmgrd の購読方式

`stpmgrd` は `Orch(tables)` コンストラクタを呼ぶことで各 `TableConnector` に対して `addConsumer()` が呼ばれる (orch.cpp:127-133)。

CONFIG_DB (dbId=4) は `addConsumer()` の `STATE_DB` / `CONFIG_DB` / `CHASSIS_APP_DB` 分岐にマッチするため **SubscriberStateTable** が選択される (orch.cpp:1188-1190):

```cpp
// orch.cpp:1188-1190
if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ..., pri), this, tableName));
```

購読テーブル (stpmgrd.cpp:43-65):
- `CFG_STP_GLOBAL_TABLE_NAME` = "STP"
- `CFG_STP_VLAN_TABLE_NAME` = "STP_VLAN"
- `CFG_STP_VLAN_PORT_TABLE_NAME` = "STP_VLAN_PORT"
- `CFG_STP_PORT_TABLE_NAME` = "STP_PORT"
- `CFG_LAG_MEMBER_TABLE_NAME` (CONFIG_DB)
- `STATE_VLAN_MEMBER_TABLE_NAME` (STATE_DB)
- `"STP_MST"`, `"STP_MST_INST"`, `"STP_MST_PORT"` (MSTP 拡張)

## stpmgrd 主ループ

```cpp
// stpmgrd.cpp:98-116
while (true) {
    ret = s.select(&sel, SELECT_TIMEOUT);  // SELECT_TIMEOUT = 1000 ms
    if (ret == Select::ERROR) { continue; }
    if (ret == Select::TIMEOUT) { stpmgr.doTask(); continue; }  // 定期タスク
    auto *c = (Executor *)sel;
    c->execute();  // Consumer::execute() → StpMgr::doTask(Consumer&)
}
```

タイムアウト時は `stpmgr.doTask()` (引数なし) で内部保留タスクをフラッシュする。

## stpmgrd → stpd IPC (Unix Domain Socket)

CONFIG_DB の変化を受けた `StpMgr::doTask()` は IPC メッセージを組み立てて `sendMsgStpd()` で stpd に送信する。

```cpp
// stpmgr.h:28,49
#define STPMGRD_SOCK_NAME "/var/run/stpmgrd.sock"
#define STPD_SOCK_NAME    "/var/run/stpipc.sock"
```

`sendMsgStpd()` は `AF_UNIX / SOCK_DGRAM` の `sendto()` で `/var/run/stpipc.sock` に送信する (stpmgr.cpp:1241-1243)。戻り値 -1 でエラーログを出力するが再キューは行わない。

## APPL_DB → StpOrch (orchagent) の購読方式

`StpOrch` は `Orch(db, tableNames)` (APPL_DB) として初期化される (stporch.cpp:17-18)。APPL_DB (dbId=0) は `addConsumer()` の else 分岐 → **ConsumerStateTable** が使用される (channel ベース PUBLISH/SUBSCRIBE):

購読テーブル (orchdaemon.cpp:256-261):
- `APP_STP_VLAN_INSTANCE_TABLE_NAME` = "STP_VLAN_INSTANCE_TABLE"
- `APP_STP_PORT_STATE_TABLE_NAME` = "STP_PORT_STATE_TABLE"
- `APP_STP_FASTAGEING_FLUSH_TABLE_NAME` = "STP_FASTAGEING_FLUSH_TABLE"
- `APP_STP_INST_PORT_FLUSH_TABLE_NAME` = "STP_INST_PORT_FLUSH_TABLE"

orchdaemon の select timeout: `SELECT_TIMEOUT = 1000` ms (orchdaemon.cpp:23)。

## retry セマンティクス

- `StpMgr::doTask(Consumer&)` で `addVlanToStpInstance()` が失敗 (`!getPort()` = ポート未準備) の場合は `it++; continue` でエントリを `m_toSync` に残置し次サイクルで再試行。
- `sendMsgStpd()` の IPC 失敗はエラーログのみで再送なし。
- stpd 側から orchagent への APPL_DB 書き込み失敗のフォールバックは stpd 内部で管理される (sonic-stp リポジトリ、本キャッシュ外)。

## keyspace vs channel

| 区間 | API | 通知方式 |
|------|-----|---------|
| CONFIG_DB → stpmgrd | SubscriberStateTable | Redis keyspace `__keyspace@4__:<TABLE>\|<key>` PSUBSCRIBE |
| STATE_DB VLAN_MEMBER → stpmgrd | SubscriberStateTable | Redis keyspace `__keyspace@6__:VLAN_MEMBER_TABLE\|<key>` |
| APPL_DB STP_* → StpOrch | ConsumerStateTable | Redis PUBLISH `<TABLE>_CHANNEL@0` |
