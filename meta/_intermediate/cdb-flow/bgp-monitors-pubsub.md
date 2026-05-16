# BGP_MONITORS テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `BGP_MONITORS` テーブル。

## 1. 購読 API — `swsscommon.SubscriberStateTable` (直接購読)

`bgpcfgd` は `swsscommon.SubscriberStateTable` を **直接** 使用する。`ConfigDBConnector.subscribe()` ラッパではなく、`Runner` クラスが自前で `swsscommon.Select` / `SubscriberStateTable` を管理する。

```python
# sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py:49-51
subscriber = swsscommon.SubscriberStateTable(conn, table_name)
self.subscribers.add(subscriber)
self.selector.addSelectable(subscriber)
```

```python
# sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py:54-70
def run(self):
    while g_run:
        state, _ = self.selector.select(Runner.SELECT_TIMEOUT)
        ...
        for subscriber in self.subscribers:
            while True:
                key, op, fvs = subscriber.pop()
                if not key:
                    break
                for callback in self.callbacks[...][subscriber.getTableName()]:
                    callback(key, op, dict(fvs))
        rc = self.cfg_manager.commit()
```

- `SELECT_TIMEOUT = 1000` (ms) で `swsscommon.Select.select()` をポーリング。
- `SubscriberStateTable` は Redis の **ConsumerStateTable 形式** を使用。CONFIG_DB へのキー変更が内部チャンネル (`__shadow__` / `XADD` ストリーム) 経由で通知される。
- keyspace notification ではなく、swsscommon の **ストリームベース通知** 機構。

## 2. BGP_MONITORS の登録経路

```python
# sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:89
BGPPeerMgrBase(common_objs, "CONFIG_DB", "BGP_MONITORS", "monitors", False)

# main.py:134-136
runner = Runner(common_objs['cfg_mgr'])
for mgr in managers:
    runner.add_manager(mgr)
runner.run()
```

`runner.add_manager(mgr)` が `BGPPeerMgrBase` の `get_database()` と `get_table_name()` を呼んで `"CONFIG_DB"` / `"BGP_MONITORS"` を取得し、`SubscriberStateTable` を生成してコールバック (`manager.handler`) を登録する。

## 3. イベントディスパッチフロー

```
CONFIG_DB: BGP_MONITORS|<addr> HSET/DEL
  ↓ (swsscommon ConsumerStateTable / ストリーム)
Runner.selector.select() が通知を受信
  ↓
subscriber.pop() → (key="<addr>", op="SET"|"DEL", fvs={...})
  ↓
BGPPeerMgrBase.handler(key, op, data)   [Manager.handler()]
  ↓ op=="SET"
  BGPPeerMgrBase.set_handler(key, data)
    → key が未登録なら add_peer(key, data)
    → key が登録済みなら update_peer(key, data)
  ↓ op=="DEL"
  BGPPeerMgrBase.del_handler(key)
  ↓
runner.cfg_manager.commit()
  → vtysh コマンド列を FRR bgpd に送信
```

## 4. frrcfgd との関係

`frrcfgd` (`sonic-frr-mgmt-framework`) の `table_handler_list` (frrcfgd.py:2293-2338) には `BGP_MONITORS` が含まれない。`frrcfgd` は BGP_NEIGHBOR / BGP_PEER_GROUP 等の sonic-mgmt-framework 経由の BGP 設定を担当するが、`BGP_MONITORS` は `bgpcfgd` 専用。両デーモンは同一テーブルを二重購読しない。

## 5. 購読方式の特性比較

| 項目 | BGP_MONITORS (bgpcfgd) | 参考: AAA (hostcfgd) |
|------|------------------------|----------------------|
| 購読 API | `swsscommon.SubscriberStateTable` | `ConfigDBConnector.subscribe()` |
| 通知機構 | swsscommon ConsumerStateTable ストリーム | Redis keyspace notification (PSUBSCRIBE) |
| 初期スナップショット | なし（起動時は empty peers dict、通知待ち） | `init_data_handler=self.load` で一括取得 |
| APPL_DB 中継 | なし（FRR vtysh 直接） | なし（ファイル書き換え） |

## 6. keyspace 通知パターン

| CONFIG_DB 操作 | bgpcfgd 受信 |
|---------------|-------------|
| `BGP_MONITORS\|<addr>` HSET | `handler("<addr>", "SET", {"asn": ..., "admin_status": ..., ...})` |
| `BGP_MONITORS\|<addr>` DEL  | `handler("<addr>", "DEL", {})` |

`BGPPeerMgrBase.wait_for_all_deps=False` のため、依存テーブル (DEVICE_METADATA / Loopback0) が未到着でも SET は即座に処理試行される。Loopback0 / bgp_router_id 未設定なら `add_peer()` が `return False` して `set_queue` に退避し、依存が揃った時点で `on_deps_change()` が再処理する。

## 7. ConsumerStateTable vs SubscriberStateTable

`BGP_MONITORS` は `CONFIG_DB` テーブルであり、`APPL_DB` の `ConsumerStateTable`（orchagent 向け）とは異なる。`swsscommon.SubscriberStateTable` は CONFIG_DB の ハッシュ変更イベントを受信するラッパ（内部的には Redis Streams または keyspace 通知を swsscommon が抽象化）。

## 8. 参考行番号

- `sonic-bgpcfgd/bgpcfgd/runner.py`
  - 27: `self.selector = swsscommon.Select()`
  - 49-51: `SubscriberStateTable` 生成 + `addSelectable`
  - 52: `self.callbacks[db][table_name].append(manager.handler)`
  - 54-70: `run()` メインループ
- `sonic-bgpcfgd/bgpcfgd/main.py`
  - 89: `BGPPeerMgrBase(... "BGP_MONITORS", "monitors", False)`
  - 134-136: `runner.add_manager()` → `runner.run()`
- `sonic-bgpcfgd/bgpcfgd/manager.py`
  - 34-53: `Manager.handler()` — SET/DEL ディスパッチ
  - 55-63: `on_deps_change()` — 再試行キュー処理
- `sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
  - 2293-2338: `table_handler_list` — BGP_MONITORS は含まない
  - 2359-2361: `subscribe_all()` → `config_db.subscribe(table, hdlr)`
