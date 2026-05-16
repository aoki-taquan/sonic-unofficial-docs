# BGP_DEVICE_GLOBAL — Phase G: 通信メカニズム (pubsub) 中間ファイル

生成日: 2026-05-16

## 検出した subscribe 方式

### 1. bgpcfgd — Runner の SubscriberStateTable (DeviceGlobalCfgMgr)

```python
# sonic-bgpcfgd/bgpcfgd/runner.py:49
subscriber = swsscommon.SubscriberStateTable(conn, table_name)
self.subscribers.add(subscriber)
self.selector.addSelectable(subscriber)
```

`Runner` は各 Manager の `(db, table)` ペアに対して `SubscriberStateTable` を生成し、`swsscommon.Select` で多重化する。`DeviceGlobalCfgMgr` は `("CONFIG_DB", CFG_BGP_DEVICE_GLOBAL_TABLE_NAME)` を引数に登録されるため（`main.py:104`）、`BGP_DEVICE_GLOBAL` テーブル全体が `SubscriberStateTable` で購読される。

イベント受信後は `subscriber.pop()` → `set_handler` / `del_handler` へ dispatch。

### 2. bgpcfgd — directory.subscribe (DeviceGlobalCfgMgr 内 DEVICE_METADATA 購読)

```python
# managers_device_global.py:33
self.directory.subscribe(
    [("CONFIG_DB", swsscommon.CFG_DEVICE_METADATA_TABLE_NAME, "localhost/type")],
    self.handle_type_update
)
```

`BGP_DEVICE_GLOBAL` テーブル自体ではなく、`DEVICE_METADATA.localhost.type` の変化を `directory.subscribe` で受信して `switch_role` を更新する。`directory` は bgpcfgd 内プロセス内 in-memory ディレクトリであり、Redis Pub/Sub ではなく Python オブジェクト内コールバック。

### 3. bgpcfgd — ChassisAppDbMgr の SubscriberStateTable + directory.subscribe

シャーシ環境のみ:

```python
# main.py:113 (条件付き)
if device_info.is_chassis():
    managers.append(ChassisAppDbMgr(common_objs, "CHASSIS_APP_DB", "BGP_DEVICE_GLOBAL"))
```

`ChassisAppDbMgr` は `("CHASSIS_APP_DB", "BGP_DEVICE_GLOBAL")` を `Runner` に登録するため `SubscriberStateTable` で CHASSIS_APP_DB を購読する。さらに：

```python
# managers_chassis_app_db.py:20
self.directory.subscribe(
    [("CONFIG_DB", swsscommon.CFG_BGP_DEVICE_GLOBAL_TABLE_NAME, "tsa_enabled")],
    self.on_lc_tsa_status_change
)
```

LC ローカルの `CONFIG_DB.BGP_DEVICE_GLOBAL.tsa_enabled` の変化も `directory.subscribe` で受信し、シャーシ全体 TSA 状態との調整を行う。

### 4. orchagent — BgpGlobalStateOrch の SubscriberStateTable

```cpp
// orchagent/orch.cpp:1190
addExecutor(new Consumer(
    new SubscriberStateTable(db, tableName, TableConsumable::DEFAULT_POP_BATCH_SIZE, pri),
    this, tableName));
```

`BgpGlobalStateOrch` は `Orch(db, tableName)` コンストラクタを通じて `SubscriberStateTable(CONFIG_DB, "BGP_DEVICE_GLOBAL")` を生成する（`orchdaemon.cpp:240`）。  
`Orch` 基底クラスが `SubscriberStateTable` をラップした `Consumer` を `Executor` として登録し、epoll-based セレクタが変化イベントを受信すると `BgpGlobalStateOrch::doTask(Consumer&)` を呼び出す（`bfdorch.cpp:793`）。

orchagent 側は `tsa_enabled` フィールドのみを消費し、他フィールドは無視する（`bfdorch.cpp:813`）。

## 購読方式まとめ

| コンシューマ | 購読方式 | 対象 DB | 対象テーブル | 処理フィールド |
|------------|---------|---------|------------|--------------|
| `DeviceGlobalCfgMgr` (bgpcfgd) | `SubscriberStateTable` (Runner 経由) | CONFIG_DB | `BGP_DEVICE_GLOBAL` | `tsa_enabled` / `wcmp_enabled` / `idf_isolation_state` |
| `DeviceGlobalCfgMgr` (bgpcfgd) | `directory.subscribe` (in-process) | CONFIG_DB | `DEVICE_METADATA` | `localhost.type` (switch_role 更新) |
| `ChassisAppDbMgr` (bgpcfgd, chassis のみ) | `SubscriberStateTable` (Runner 経由) | CHASSIS_APP_DB | `BGP_DEVICE_GLOBAL` | `tsa_enabled` |
| `ChassisAppDbMgr` (bgpcfgd, chassis のみ) | `directory.subscribe` (in-process) | CONFIG_DB | `BGP_DEVICE_GLOBAL` | `tsa_enabled` (LC ローカル変化追従) |
| `BgpGlobalStateOrch` (orchagent) | `SubscriberStateTable` (Orch 基底) | CONFIG_DB | `BGP_DEVICE_GLOBAL` | `tsa_enabled` のみ |

## タイミング特性

- `SubscriberStateTable` は Redis keyspace notification ベース（`__keyspace@<db>__:<table>` チャネル）。書き込み後の遅延は通常 <1ms（epoll wake-up）。
- bgpcfgd `Runner` は `SELECT_TIMEOUT=10s` でポーリングと epoll を組み合わせる（`runner.py:57`）。タイムアウト時は単に空回り（積み残し処理なし）。
- orchagent の `Orch` はイベントループ 1 周回あたり全 consumer を走査するため、`BGP_DEVICE_GLOBAL` 変化は `BgpGlobalStateOrch::doTask` で即時消費される。
- 両コンシューマ（bgpcfgd / orchagent）は独立したプロセスで動作するため、同一 SET イベントに対して並列に処理が走る。処理完了の相対順序は保証されない。

## evidence

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py:27-73`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_device_global.py:33`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_chassis_app_db.py:19-30`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:104,113`
- `sonic-swss/orchagent/orch.cpp:1190`
- `sonic-swss/orchagent/bfdorch.cpp:729-839`
- `sonic-swss/orchagent/orchdaemon.cpp:240`
