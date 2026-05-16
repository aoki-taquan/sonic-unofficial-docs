# BGP_AGGREGATE_ADDRESS — Phase G: Redis PUBSUB / keyspace / SubscriberStateTable / Notification

## 調査対象

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_aggregate_address.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/manager.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/directory.py`
- `sonic-swss-common/common/subscriberstatetable.cpp`
- `sonic-swss-common/common/redisselect.cpp`

## 購読メカニズム全体像

BGP_AGGREGATE_ADDRESS テーブルの変更通知は **SubscriberStateTable + Redis keyspace notification (PSUBSCRIBE)** で実装されている。bgpcfgd 専用の `AggregateAddressMgr` (`managers_aggregate_address.py:23`) が `Manager` 基底クラスを継承し、`Runner.add_manager()` を介して keyspace 通知を購読する。APPL_DB への中継はなく、FRR vtysh へ直接コマンド発行される。STATE_DB 側は `swsscommon.Table` (`address_table`) で `BGP_AGGREGATE_ADDRESS` テーブルを直接 HSET/HDEL する。

### 1. PSUBSCRIBE チャンネルパターン

`Runner.add_manager()` (`runner.py:31-52`) が `AggregateAddressMgr` を登録する時に以下を実行する:

```python
subscriber = swsscommon.SubscriberStateTable(conn, "BGP_AGGREGATE_ADDRESS")
self.subscribers.add(subscriber)
self.selector.addSelectable(subscriber)
self.callbacks[db]["BGP_AGGREGATE_ADDRESS"].append(manager.handler)
```

`SubscriberStateTable` コンストラクタが PSUBSCRIBE するチャンネル:

```
__keyspace@<config_db_id>__:BGP_AGGREGATE_ADDRESS|*
```

- `<config_db_id>` は CONFIG_DB の Redis DB 番号 (通常 4)
- パターンは `psubscribe(m_db, m_keyspace)` → `redisselect.cpp` 経由で hiredis に送出される
- glob によりキー `BGP_AGGREGATE_ADDRESS|<ip-prefix>` の全エントリ変化を捕捉

### 2. keyspace イベントの発火

CONFIG_DB に対する `HSET BGP_AGGREGATE_ADDRESS|<prefix> <field> <value>` / `DEL BGP_AGGREGATE_ADDRESS|<prefix>` が keyspace notification を発火する。書き込み元は:

- `vtysh` 経由の `aggregate-address <prefix>` (FRR → bgpcfgd フィードバック書き戻し)
- `config bgp` CLI (sonic-utilities)
- REST / gNMI (sonic-mgmt-common OpenConfig BGP)
- minigraph パース後の `sonic-cfggen` 一括書き込み

CONFIG_DB の `notify-keyspace-events` 設定は SONiC のデフォルト Redis 設定で有効化されている。

### 3. Select ループ (runner.py)

`Runner.run()` (`runner.py:54-73`) メインループ:

```python
state, _ = self.selector.select(Runner.SELECT_TIMEOUT)  # SELECT_TIMEOUT=1000ms
for subscriber in self.subscribers:
    while True:
        key, op, fvs = subscriber.pop()
        if not key:
            break
        for callback in self.callbacks[db_id][table_name]:
            callback(key, op, dict(fvs))
rc = self.cfg_manager.commit()
```

- `swsscommon.Select` は epoll/poll 多重化
- タイムアウト 1000 ms (1 秒)
- 受信後は全 subscriber を `pop()` ドレイン
- 全 callback 実行完了後に `cfg_manager.commit()` で FRR vtysh へバッチ送信

### 4. イベントを callback まで届ける流れ

```
Redis keyspace notification (pmessage)
  → SubscriberStateTable::readData()
    → m_keyspace_event_buffer に push
  → SubscriberStateTable::pop()
    → (key, op=SET/DEL, fvs) を返す
  → Runner のコールバックループ
    → Manager.handler(key, op, data)        (manager.py:34-53)
      → op==SET → AggregateAddressMgr.set_handler(key, data)   (managers_aggregate_address.py:65)
      → op==DEL → AggregateAddressMgr.del_handler(key)         (managers_aggregate_address.py:138)
```

### 5. Manager.handler() の SET/DEL 分岐 (manager.py:34-53)

| op | 条件 | 動作 |
|----|------|------|
| `SET` | `wait_for_all_deps=True` かつ全依存解決済 | `set_handler(key, data)` 即時実行 |
| `SET` | 依存未解決 (`bgp_asn` 未設定など) | `set_queue` に積み、`on_deps_change()` で後回し再試行 |
| `SET` | `set_handler` が `False` 返却 | `set_queue` に積みリトライ (本マネージャは常に `True` を返すため発生しない) |
| `DEL` | — | `del_handler(key)` を直接呼出 |

`AggregateAddressMgr` の依存関係 (`managers_aggregate_address.py:36`):

- `("CONFIG_DB", "DEVICE_METADATA", "localhost/bgp_asn")`

加えてコンストラクタ内で `directory.subscribe([(CONFIG_DB, BGP_BBR, status)], self.on_bbr_change)` により **BGP_BBR テーブルの status 変化** を独立して購読する (`managers_aggregate_address.py:41`)。BBR が enabled/disabled に切り替わると `on_bbr_change()` が呼ばれ、STATE_DB の `BGP_AGGREGATE_ADDRESS` から `bbr-required=true` の全エントリを読み出して FRR への再投入 / 削除を行う。

### 6. 初期スナップショット取得

`SubscriberStateTable` コンストラクタは PSUBSCRIBE 後に `m_table.getKeys()` で既存 key を全件取得し、`SET` イベントとして `m_buffer` に積む。これにより bgpcfgd 起動時に CONFIG_DB に既存の `BGP_AGGREGATE_ADDRESS|<prefix>` エントリが再生される (再起動耐性)。

加えて `AggregateAddressMgr.__init__` (`managers_aggregate_address.py:44`) は `remove_all_state_of_address()` を呼び、STATE_DB の `BGP_AGGREGATE_ADDRESS` テーブルを起動時に初期化する。

### 7. Directory ベースの cross-table 連携

bgpcfgd は `directory.py` を共有メモリとして使い、テーブル間依存をパス購読で管理する。`AggregateAddressMgr` は以下を購読:

- `DEVICE_METADATA.localhost/bgp_asn` (Manager 基底クラスの `deps` 経由)
- `BGP_BBR.status` (`on_bbr_change` callback、L41)

`directory.subscribe()` は keyspace ではなく Python オブジェクト内 callback dispatch であり、別 Manager の `set_handler` 内 `directory.put()` 呼び出しによってトリガーされる。

### 8. STATE_DB 書き込みパス

`AggregateAddressMgr` は `swsscommon.Table(state_db_conn, "BGP_AGGREGATE_ADDRESS")` を保持し (`managers_aggregate_address.py:43`)、エントリ状態を以下フィールドで書き込む:

- `state=active` — FRR 投入成功
- `state=inactive` — prefix 不正 / BBR 未確定 / FRR push 失敗 / DEL 時の遅延削除

これは ProducerStateTable ではなく **`Table` (HSET 直接)** 経由のため、STATE_DB の keyspace notification (購読側があれば) のみ発火する。

### 9. FRR vtysh への commit

`cfg_manager.commit()` (`runner.py:71-73`) は `ConfigMgr.commit()` を呼ぶ。`AggregateAddressMgr.address_set_handler()` (`managers_aggregate_address.py:92`) / `address_del_handler()` (L148) が組み立てた `aggregate-address <prefix> [summary-only] [as-set]` コマンドは `cfg_mgr.push()` でキューに積まれ、select ループ末尾でまとめて `vtysh -c ...` に流される。CONFIG_DB → FRR 間に APPL_DB・SAI は介在しない。

### 10. ProducerStateTable チャンネルとの関係

CONFIG_DB への書き込みが `ProducerStateTable` 経由 (`BGP_AGGREGATE_ADDRESS_CHANNEL@<db_id>` への PUBLISH) であっても、bgpcfgd は **SubscriberStateTable** を使い Redis keyspace notification (`__keyspace@<db_id>__:BGP_AGGREGATE_ADDRESS|*`) を PSUBSCRIBE しているため、チャンネル種別に依存せず任意の書き込みを捕捉する。

## まとめ

| フェーズ | 実装 | ファイル |
|---------|------|---------|
| 書き込み → Redis keyspace | HSET/DEL が `__keyspace@4__:BGP_AGGREGATE_ADDRESS|*` を発火 | Redis サーバー内部 |
| keyspace → SubscriberStateTable | `PSUBSCRIBE` + `readData()` + `pop()` | subscriberstatetable.cpp |
| SST → Runner select ループ | `Select.select(1000ms)` + `subscriber.pop()` ドレイン | runner.py:54-70 |
| Runner → Manager.handler | callback 登録テーブル経由 | runner.py:52, manager.py:34 |
| Manager.handler → set/del_handler | op==SET/DEL 分岐、`bgp_asn` 依存ガード、`set_queue` リトライ | manager.py:34-53 |
| 横方向の BBR 連携 | `directory.subscribe(BGP_BBR.status)` → `on_bbr_change()` | managers_aggregate_address.py:41,46 |
| set_handler → STATE_DB | `swsscommon.Table` 直接 HSET (`state=active/inactive`) | managers_aggregate_address.py:43 |
| set_handler → FRR vtysh | `cfg_mgr.push()` → `commit()` でバッチ発行 | managers_aggregate_address.py:92, config.py |
