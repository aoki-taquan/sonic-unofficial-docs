# BGP_NEIGHBOR — Phase G: Redis PUBSUB / keyspace / ConsumerStateTable / Notification

## 調査対象

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/manager.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-swss-common/common/subscriberstatetable.cpp`
- `sonic-swss-common/common/producerstatetable.cpp`
- `sonic-swss-common/common/redisselect.cpp`
- `sonic-swss-common/common/table.h`

## 購読メカニズム全体像

BGP_NEIGHBOR テーブルの変更通知は **SubscriberStateTable + Redis keyspace notification (PSUBSCRIBE)** の組み合わせで実装されている。ProducerStateTable/CONFIG_DB への書き込みは行われず、CONFIG_DB への直接 HSET/HDEL が keyspace を発火させる。

### 1. PSUBSCRIBE チャンネルパターン

`SubscriberStateTable::SubscriberStateTable()` (subscriberstatetable.cpp:20-24) が構築時に以下を PSUBSCRIBE する:

```
__keyspace@<db_id>__:BGP_NEIGHBOR|*
```

- `<db_id>` は CONFIG_DB の Redis DB 番号 (通常 4)
- パターンは `PSUBSCRIBE` (glob) で登録されるため、`BGP_NEIGHBOR|<vrf>|<neighbor>` 形式・`BGP_NEIGHBOR|<neighbor>` 形式の両方を捕捉する
- 実装: `psubscribe(m_db, m_keyspace)` → `redisselect.cpp:85-92` で `m_subscribe->psubscribe(channelName)` を hiredis 経由で送出

### 2. keyspace イベントの発火

CONFIG_DB に対して誰かが `HSET BGP_NEIGHBOR|<key> field value` / `HDEL BGP_NEIGHBOR|<key> field` / `DEL BGP_NEIGHBOR|<key>` を実行すると、Redis サーバーが keyspace notification を発火する。書き込み元は:

- `sonic-cfggen -m <minigraph.xml>` (minigraph パース後の一括書き込み)
- `config bgp` CLI (sonic-utilities/config/main.py)
- REST / gNMI (sonic-mgmt-common OpenConfig BGP)
- `bgpcfgd` 自身 (FRR running-config との同期フィードバック)

keyspace notification は Redis の `notify-keyspace-events Kx` (または `KEA`) 設定が必要。SONiC のデフォルト設定では CONFIG_DB に対して keyspace events が有効化されている。

### 3. Select ループ (runner.py)

`Runner.add_manager()` (runner.py:31-52) が各 Manager を登録する:

```python
subscriber = swsscommon.SubscriberStateTable(conn, table_name)
self.subscribers.add(subscriber)
self.selector.addSelectable(subscriber)
```

`Runner.run()` (runner.py:54-73) のメインループ:

```python
state, _ = self.selector.select(Runner.SELECT_TIMEOUT)  # SELECT_TIMEOUT=1000ms
for subscriber in self.subscribers:
    while True:
        key, op, fvs = subscriber.pop()
        if not key:
            break
        for callback in self.callbacks[...][...]:
            callback(key, op, dict(fvs))
rc = self.cfg_manager.commit()
```

- `swsscommon.Select` は epoll/poll ベースの多重化機構
- タイムアウトは 1000 ms (1 秒)
- イベント受信後は全 subscriber をラウンドロビンでドレイン (`subscriber.pop()` を key=None まで繰り返す)
- ドレイン完了後 `cfg_manager.commit()` で FRR vtysh へのバッチ送信を実行

### 4. イベントを callback まで届ける流れ

```
Redis keyspace notification (pmessage)
  → SubscriberStateTable::readData()   (subscriberstatetable.cpp:47-73)
    → m_keyspace_event_buffer に push
  → SubscriberStateTable::pop()        (subscriberstatetable.cpp:106-162)
    → key, op(SET/DEL), fvs を返す
  → Runner のコールバックループ
    → Manager.handler(key, op, data)   (manager.py:34-53)
      → op==SET → BGPPeerMgrBase.set_handler(key, data)
      → op==DEL → BGPPeerMgrBase.del_handler(key)
```

`SubscriberStateTable::pop()` は keyspace_event_buffer から pmessage を取り出し、HGETALL でフィールド値を取得してから KeyOpFieldsValuesTuple を返す。

### 5. Manager.handler() の SET/DEL 分岐

`manager.py:34-53`:

| op | 条件 | 動作 |
|----|------|------|
| `SET` | 全依存関係が揃っている | `set_handler(key, data)` を即時実行 |
| `SET` | 依存関係が未揃い | `set_queue` に積んで後回し (依存解決時に `on_deps_change()` が再試行) |
| `SET` | `set_handler` が `False` 返却 | `set_queue` に積む (ループバック待機) |
| `DEL` | — | `del_handler(key)` を直接呼出 |

BGP_NEIGHBOR の依存関係 (manager.py が wait_for_all_deps=True で管理):
- `DEVICE_METADATA.localhost/bgp_asn`
- `DEVICE_METADATA.localhost/type`
- `LOOPBACK_INTERFACE.Loopback0`
- `BGP_DEVICE_GLOBAL.tsa_enabled` / `idf_isolation_state`
- `local_addresses` / `interfaces` (LOCAL スロット)
- (check_neig_meta=True のとき) `DEVICE_NEIGHBOR_METADATA`

### 6. 初期スナップショット取得

`SubscriberStateTable` のコンストラクタ (subscriberstatetable.cpp:25-39) は PSUBSCRIBE 後に `m_table.getKeys()` で既存 key を全件取得し、`SET` イベントとして `m_buffer` に積む。これにより bgpcfgd 起動時に CONFIG_DB に既存の BGP_NEIGHBOR エントリが再生される (再起動耐性)。

### 7. ProducerStateTable チャンネルとの関係

CONFIG_DB への書き込みが `ProducerStateTable` 経由の場合、書き込み側は `BGP_NEIGHBOR_CHANNEL@<db_id>` (table.h:85-96 `getChannelName()`) に PUBLISH する。ConsumerStateTable はこのチャンネルを SUBSCRIBE して受信する。一方 bgpcfgd 側は **SubscriberStateTable** を使っており、Redis keyspace notification (`__keyspace@<db_id>__:BGP_NEIGHBOR|*`) を PSUBSCRIBE することで、チャンネルに依存せず任意の書き込みを捕捉できる設計になっている。

### 8. FRR vtysh への commit

`cfg_manager.commit()` (runner.py:71-73) は `ConfigMgr.commit()` を呼ぶ。ConfigMgr は `bgpcfgd/config.py` に実装されており、set_handler / add_peer がキューに積んだ vtysh コマンド群をまとめて `vtysh -c ...` で発行する。bgpcfgd の CONFIG_DB → FRR 間に APPL_DB・STATE_DB は介在しない (直接 vtysh 経由)。

## まとめ

| フェーズ | 実装 | ファイル |
|---------|------|---------|
| 書き込み → Redis keyspace | HSET/DEL が `__keyspace@4__:BGP_NEIGHBOR|*` を発火 | Redis サーバー内部 |
| keyspace → SubscriberStateTable | `PSUBSCRIBE` + `readData()` + `pop()` | subscriberstatetable.cpp |
| SST → Runner select ループ | `Select.select(1000ms)` + `subscriber.pop()` ドレイン | runner.py |
| Runner → Manager.handler | callback 登録テーブル経由 | runner.py, manager.py |
| Manager.handler → set/del_handler | op==SET/DEL 分岐、依存関係ガード、set_queue リトライ | manager.py |
| set_handler → FRR vtysh | `cfg_manager.push()` + `commit()` でバッチ発行 | managers_bgp.py, config.py |
