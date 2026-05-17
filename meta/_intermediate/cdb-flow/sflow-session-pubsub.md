# sflow-session — Phase G: 通信メカニズム (pubsub)

調査日: 2026-05-17
対象ページ: `docs/reference/config-db/sflow-session.md`
ソース:
- `sonic-swss/cfgmgr/sflowmgrd.cpp`
- `sonic-swss/cfgmgr/sflowmgr.cpp` / `sflowmgr.h`
- `sonic-swss/orchagent/sfloworch.cpp` / `sfloworch.h`
- `sonic-swss/orchagent/orchdaemon.cpp`

---

## 購読 API（CONFIG_DB → sflowmgrd）

`sflowmgrd.cpp:31-34` で `TableConnector` を 4 つ生成し、`SflowMgr(Orch)` に渡す。

```cpp
TableConnector conf_port_table(&cfgDb, CFG_PORT_TABLE_NAME);
TableConnector state_port_table(&stateDb, STATE_PORT_TABLE_NAME);
TableConnector conf_sflow_table(&cfgDb, CFG_SFLOW_TABLE_NAME);
TableConnector conf_sflow_session_table(&cfgDb, CFG_SFLOW_SESSION_TABLE_NAME);
```

`Orch` フレームワークが各 `TableConnector` を **`SubscriberStateTable`**（Redis keyspace 通知ベース）に変換し、`swss::Select` ループで多重化する。CONFIG_DB の `SFLOW_SESSION|*` に対する HSET / DEL が Redis keyspace 通知 (`__keyspace@4__:SFLOW_SESSION|*`) を発火し、sflowmgrd の `Executor::execute()` → `SflowMgr::doTask()` が呼ばれる。

## 書き込み API（sflowmgrd → APPL_DB）

`sflowmgr.h:39-40`：

```cpp
ProducerStateTable  m_appSflowTable;
ProducerStateTable  m_appSflowSessionTable;
```

- `m_appSflowSessionTable` は APPL_DB の `SFLOW_SESSION_TABLE` に対する **`ProducerStateTable`**（Redis Stream + 通知チャネルベース）。
- `m_appSflowSessionTable.set(key, fvs)` が `SFLOW_SESSION_TABLE` に SET を書き込み、同時に APPL_DB の通知チャネルへ `PUBLISH` する。

## 購読 API（APPL_DB → SflowOrch）

`orchdaemon.cpp:439-444`：

```cpp
vector<string> sflow_tables = {
    APP_SFLOW_TABLE_NAME,
    APP_SFLOW_SESSION_TABLE_NAME,
    APP_SFLOW_SAMPLE_RATE_TABLE_NAME
};
SflowOrch *sflow_orch = new SflowOrch(m_applDb, sflow_tables);
```

`SflowOrch` は `Orch` 基底クラス経由で 3 テーブルを **`ConsumerStateTable`** として登録する。APPL_DB の通知チャネルを待ち受け、`SFLOW_SESSION_TABLE` への変更を受信して `SflowOrch::doTask()` を呼び出す。

## STATE_DB 購読（oper_speed 変化追跡）

`sflowmgrd.cpp:32`：
```cpp
TableConnector state_port_table(&stateDb, STATE_PORT_TABLE_NAME);
```

sflowmgrd は STATE_DB の `PORT_TABLE` も `SubscriberStateTable` で購読する。ポートの `oper_speed` フィールド変化を検知すると `SflowMgr::sflowProcessOperSpeed()` が呼ばれ、`sample_rate` 未指定のポートの APPL_DB 書き込みが自動更新される。**一方向のみ（sflowmgrd が State を読む）で、sflowmgrd は STATE_DB に書き込まない**。

## show sflow interface の APPL_DB 直接参照

`sonic-utilities/show/sflow.py:51-52`：
```python
intf_key = 'SFLOW_SESSION_TABLE:' + pname
sess_info = sess_db.get_all(sess_db.APPL_DB, intf_key)
```

`show sflow interface` コマンドは CONFIG_DB ではなく APPL_DB の `SFLOW_SESSION_TABLE` を直接 HGETALL して表示する。pub/sub は使用せず、Read-through パターン。

## 通信メカニズム サマリ

| 方向 | 送信側 | API | 受信側 | DB / テーブル |
|------|-------|-----|-------|-------------|
| CONFIG_DB → mgrd | CONFIG_DB (HSET/DEL) | Redis keyspace 通知 → `SubscriberStateTable` | sflowmgrd | `CONFIG_DB SFLOW_SESSION` |
| STATE_DB → mgrd | STATE_DB (oper_speed) | Redis keyspace 通知 → `SubscriberStateTable` | sflowmgrd | `STATE_DB PORT_TABLE` |
| mgrd → APPL_DB | sflowmgrd | `ProducerStateTable.set()` / `.del()` | SflowOrch | `APPL_DB SFLOW_SESSION_TABLE` |
| APPL_DB → orch | APPL_DB (Stream) | `ConsumerStateTable` | SflowOrch | `APPL_DB SFLOW_SESSION_TABLE` |
| show CLI → APPL_DB | show sflow interface | Redis HGETALL (read-through) | — | `APPL_DB SFLOW_SESSION_TABLE` |

## keyspace 通知 非使用（明示的 PUBLISH なし）

- CONFIG_DB への書き込み側（CLI / sonic-cfggen）は `HSET` のみ実行し、明示的な `PUBLISH` は行わない。Redis keyspace notification 機能が変更を通知する。
- APPL_DB の書き込み（`ProducerStateTable`）は内部で Redis Stream (`XADD`) と通知チャネルへの `PUBLISH` を自動実行する。
- `NotificationProducer` / `NotificationConsumer` は SFLOW_SESSION の経路では使用しない。
