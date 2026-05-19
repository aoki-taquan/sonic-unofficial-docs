# default-lossless-buffer-parameter — 通信メカニズム (Phase G) 中間調査

対象ページ: `docs/reference/config-db/default-lossless-buffer-parameter.md`

`DEFAULT_LOSSLESS_BUFFER_PARAMETER` (CONFIG_DB) → `buffermgrdyn` (BufferMgrDynamic) の通知経路と主ループ構造を調査する。

## 1. 購読方式 — CONFIG_DB → SubscriberStateTable

`buffermgrd.cpp L174-187` で `BufferMgrDynamic` は複数テーブルを `vector<TableConnector>` でまとめて受け取る:

```cpp
vector<TableConnector> buffer_table_connectors = {
    TableConnector(&cfgDb, CFG_PORT_TABLE_NAME),
    TableConnector(&cfgDb, CFG_PORT_CABLE_LEN_TABLE_NAME),
    ...
    TableConnector(&cfgDb, CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER),  // L183
    TableConnector(&stateDb, STATE_BUFFER_MAXIMUM_VALUE_TABLE),
    TableConnector(&stateDb, STATE_PORT_TABLE_NAME)
};
cfgOrchList.emplace_back(new BufferMgrDynamic(..., buffer_table_connectors, ...));
```

`Orch(const vector<TableConnector>& tables)` コンストラクタ (`orch.cpp L127-133`) は全エントリに対して `addConsumer(db, tableName)` を呼ぶ。

`orch.cpp L1186-1196` の `addConsumer` は DB ID で分岐:

```cpp
if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    addExecutor(new Consumer(new SubscriberStateTable(...), this, tableName));
else
    addExecutor(new Consumer(new ConsumerStateTable(...), this, tableName));
```

`DEFAULT_LOSSLESS_BUFFER_PARAMETER` は CONFIG_DB (DB id = 4) のため **`SubscriberStateTable` 経路** に落ちる。`SubscriberStateTable` は内部で `PSUBSCRIBE __keyspace@4__:DEFAULT_LOSSLESS_BUFFER_PARAMETER|*` を発行し、キースペース通知を受け取る。

## 2. 通知受信 → ハンドラ呼び出し

`buffermgrd.cpp L225` の主ループ:

```cpp
ret = s.select(&sel, SELECT_TIMEOUT);  // SELECT_TIMEOUT = 1000 ms
```

`SubscriberStateTable` がキースペース通知を受信すると `Select::select` が return し、対応する `Consumer::execute()` → `BufferMgrDynamic::doTask(Consumer&)` (`buffermgrdyn.cpp L3574`) が呼ばれる。

`doTask` は `m_bufferTableHandlerMap` でテーブル名をディスパッチ:

```cpp
// buffermgrdyn.cpp L442
m_bufferTableHandlerMap.insert(buffer_handler_pair(
    CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER,
    &BufferMgrDynamic::handleDefaultLossLessBufferParam));
```

→ `handleDefaultLossLessBufferParam` (`buffermgrdyn.cpp L1978-2033`) が呼ばれ `over_subscribe_ratio` を処理する。

## 3. キースペース通知の経路まとめ

| 経路 | DB | パターン | 書き込み元 | 消費者 |
|---|---|---|---|---|
| CONFIG_DB → buffermgrdyn | 4 | `__keyspace@4__:DEFAULT_LOSSLESS_BUFFER_PARAMETER\|*` | `config set` / `sonic-cfggen` 等 | `BufferMgrDynamic` SubscriberStateTable |

CONFIG_DB は永続ストア（TTL なし）。`SubscriberStateTable` はキースペース通知のペイロード（操作名 `hset`/`del`）を受け取ったあと `HGETALL` でフィールド値を取得する。`over_subscribe_ratio` の実値は通知ではなく HGETALL で得られる。

## 4. 周期タイマー (SELECT_TIMEOUT 経過時)

SELECT_TIMEOUT = 1000 ms (`buffermgrd.cpp L22`) のタイムアウト時は `OrchDaemon::doTask()` 相当処理が走る。加えて `buffermgrdyn` は内部に `BUFFERMGR_TIMER_PERIOD = 10 秒` の `SelectableTimer` (`buffermgrdyn.h L17`, `buffermgrdyn.cpp L127-131`) を持ち、`doTask(SelectableTimer&)` (`buffermgrdyn.cpp L3791`) を呼び出してポート初期化完了 / 保留タスクを定期消化する。`DEFAULT_LOSSLESS_BUFFER_PARAMETER` のリトライもこのタイマーで回収される。

## 5. 購読者一覧

CONFIG_DB `DEFAULT_LOSSLESS_BUFFER_PARAMETER` を購読するプロセス:

| プロセス | 購読方式 | 目的 |
|---|---|---|
| `buffermgrdyn` (buffermgrd dynamic モード) | `SubscriberStateTable` (keyspace PSUBSCRIBE) | `over_subscribe_ratio` / `default_dynamic_th` 変更を受けて SHP 再計算 |

`buffermgr` (static モード) はこのテーブルを subscribe しない（`buffermgrd.cpp L165` の `if (dynamic_buffer)` 分岐で `BufferMgrDynamic` のみが生成される）。

## 6. 参照

- `sonic-swss/cfgmgr/buffermgrd.cpp` L22, L165-187, L225
- `sonic-swss/cfgmgr/buffermgrdyn.h` L17 (`BUFFERMGR_TIMER_PERIOD`)
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` L127-131, L442, L1978-2033, L3574-3610, L3791
- `sonic-swss/orchagent/orch.cpp` L127-133, L1186-1196
