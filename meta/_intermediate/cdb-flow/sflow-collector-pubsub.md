# SFLOW_COLLECTOR テーブル — 通信メカニズム (Phase G) 解析メモ

対象: CONFIG_DB の `SFLOW_COLLECTOR` テーブル。

ソース確認: `sonic-swss/cfgmgr/sflowmgrd.cpp`、`sonic-swss/cfgmgr/sflowmgr.cpp`、`sonic-swss/cfgmgr/sflowmgr.h`、`sonic-swss-common/common/schema.h`、`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-sflow.yang`。

## 1. 核心事実: SFLOW_COLLECTOR は sflowmgrd に購読されない

`sflowmgrd.cpp:31-41` に TableConnector リストが確認できる:

```cpp
// sflowmgrd.cpp:31-41
TableConnector conf_port_table(&cfgDb, CFG_PORT_TABLE_NAME);        // CONFIG_DB: PORT
TableConnector state_port_table(&stateDb, STATE_PORT_TABLE_NAME);   // STATE_DB: PORT_TABLE
TableConnector conf_sflow_table(&cfgDb, CFG_SFLOW_TABLE_NAME);      // CONFIG_DB: SFLOW
TableConnector conf_sflow_session_table(&cfgDb, CFG_SFLOW_SESSION_TABLE_NAME); // CONFIG_DB: SFLOW_SESSION

vector<TableConnector> sflow_tables = {
    conf_port_table,
    state_port_table,
    conf_sflow_table,
    conf_sflow_session_table
};

SflowMgr sflowmgr(&appDb, sflow_tables);
```

`SFLOW_COLLECTOR` は `sflow_tables` ベクターに含まれない。`SflowMgr` はこのテーブルを一切購読しない。

## 2. 購読されているテーブルの通信メカニズム

`SflowMgr` は `Orch` を継承する。`Orch::addConsumer()` は DB ID で分岐し、CONFIG_DB / STATE_DB には `SubscriberStateTable`（keyspace 通知ベース）を、APPL_DB には `ConsumerStateTable`（channel ベース PUBLISH/SUBSCRIBE）を割り当てる:

```cpp
// swss-common/orch.cpp (共通実装)
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || ...)
        addExecutor(new Consumer(new SubscriberStateTable(...), this, tableName));
    else
        addExecutor(new Consumer(new ConsumerStateTable(...), this, tableName));
}
```

| TableConnector | DB | 購読 API | 通知方式 |
|---------------|----|---------|---------|
| `CFG_PORT_TABLE_NAME` | CONFIG_DB | `SubscriberStateTable` | keyspace 通知 `__keyspace@4__:PORT|*` |
| `STATE_PORT_TABLE_NAME` | STATE_DB | `SubscriberStateTable` | keyspace 通知 `__keyspace@6__:PORT_TABLE|*` |
| `CFG_SFLOW_TABLE_NAME` | CONFIG_DB | `SubscriberStateTable` | keyspace 通知 `__keyspace@4__:SFLOW|*` |
| `CFG_SFLOW_SESSION_TABLE_NAME` | CONFIG_DB | `SubscriberStateTable` | keyspace 通知 `__keyspace@4__:SFLOW_SESSION|*` |
| **`SFLOW_COLLECTOR`** | (**未登録**) | **なし** | **購読なし** |

`SubscriberStateTable` は通知受信後に `HGETALL` で値を再取得し `(key, op, fvs)` タプルを返す。CONFIG_DB は HSET のみ（明示的 PUBLISH なし）で Redis の keyspace 通知機能が変更を通知する。

## 3. sflowmgrd メインループ

```cpp
// sflowmgrd.cpp:56-71
#define SELECT_TIMEOUT 1000  // ms

while (true)
{
    Selectable *sel;
    int ret;

    ret = s.select(&sel, SELECT_TIMEOUT);
    if (ret == Select::TIMEOUT)
    {
        sflowmgr.doTask();   // タイムアウト時は全テーブルを drain
        continue;
    }

    auto *c = (Executor *)sel;
    c->execute();
}
```

- タイムアウト 1000 ms ごとに `doTask()` を呼ぶ。keyspace 通知到着で即座に wake up。
- `doTask(Consumer&)` はテーブル名で分岐:
  - `CFG_PORT_TABLE_NAME` → `sflowUpdatePortInfo(consumer)`
  - `STATE_PORT_TABLE_NAME` → `sflowProcessOperSpeed(consumer)`
  - `CFG_SFLOW_TABLE_NAME` → admin_state / sample_direction 処理 + `m_appSflowTable.set()`
  - `CFG_SFLOW_SESSION_TABLE_NAME` → セッション設定処理 + `m_appSflowSessionTable.set()`
  - **`SFLOW_COLLECTOR`** → **該当する case なし（購読外）**

## 4. SFLOW_COLLECTOR 変更後の hsflowd 反映経路

SFLOW_COLLECTOR の変更は直接トリガーを持たない。コレクタ設定が hsflowd に届くまでの唯一の経路は:

```
SFLOW_COLLECTOR|<name> SET/DEL  (sflowmgrd は notified されない)
  ↓ 後続操作が必要
SFLOW|global admin_state 変化 (down→up)
  ↓ keyspace 通知 → sflowmgrd 受信 → doTask(CFG_SFLOW_TABLE_NAME)
sflowHandleService(enable=true)  (sflowmgr.cpp:51-78)
  ↓
"service hsflowd restart"
  ↓
hsflowd 起動: /etc/hsflowd.conf 再読込み → 新コレクタ設定が有効化
```

`sflowHandleService()` は `service hsflowd restart` または `service hsflowd stop` コマンドを `swss::exec()` で実行する (sflowmgr.cpp:60,63)。失敗時は `SWSS_LOG_ERROR("Command '%s' failed with rc %d", ...)` のみで例外なし (sflowmgr.cpp:69-70)。

## 5. gNMI / REST 経由の購読なし確認

`sonic-mgmt-common/translib/transformer/xfmr_sflow.go` は REST / gNMI 経由の SFLOW_COLLECTOR 書き込みトランスフォーマーを提供するが、`xfmr_sflow.go` 内に CONFIG_DB 購読の仕組みはない（translib は書き込みパスを提供するだけで、変更通知を sflowmgrd へ転送しない）。

## 6. 結論

- `SFLOW_COLLECTOR` テーブルを購読するプロセスは SONiC 実装上 **存在しない**
- 変更通知 (keyspace 通知 / ConsumerStateTable channel) の受信者ゼロ
- CONFIG_DB への書き込みは即時 Redis に反映されるが、hsflowd プロセスはその変更を検知しない
- コレクタ設定の実効化には `SFLOW|global` の admin_state トグルによる hsflowd 再起動が必要
