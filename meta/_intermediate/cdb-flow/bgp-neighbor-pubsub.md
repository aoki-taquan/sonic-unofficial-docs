# BGP_NEIGHBOR — Phase G: Redis PUBSUB / keyspace / ConsumerStateTable / Notification

## 調査対象

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/manager.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-swss-common/common/subscriberstatetable.cpp`
- `sonic-swss-common/common/producerstatetable.cpp`
- `sonic-swss-common/common/redisselect.cpp`
- `sonic-swss-common/common/table.h`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 購読メカニズム全体像

BGP_NEIGHBOR テーブルの変更通知は **SubscriberStateTable + Redis keyspace notification (PSUBSCRIBE)** の組み合わせで実装されている。ProducerStateTable/CONFIG_DB への書き込みは行われず、CONFIG_DB への直接 HSET/HDEL が keyspace を発火させる。

### 1. PSUBSCRIBE チャンネルパターン (bgpcfgd 経路)

`SubscriberStateTable::SubscriberStateTable()` (subscriberstatetable.cpp:20-24) が構築時に以下を PSUBSCRIBE する:

```
__keyspace@<db_id>__:BGP_NEIGHBOR|*
```

- `<db_id>` は CONFIG_DB の Redis DB 番号 (通常 4)
- パターンは `PSUBSCRIBE` (glob) で登録されるため、`BGP_NEIGHBOR|<vrf>|<neighbor>` 形式・`BGP_NEIGHBOR|<neighbor>` 形式の両方を捕捉する
- 実装: `psubscribe(m_db, m_keyspace)` → `redisselect.cpp:85-92` で `m_subscribe->psubscribe(channelName)` を hiredis 経由で送出

### 2. frrcfgd 経路 (frr_mgmt_framework_config=true 時)

`frrcfgd.py` の `BGPConfigDaemon.subscribe_all()` (L2359-2361) は `ConfigDBConnector.subscribe()` で `BGP_NEIGHBOR` テーブルを登録する。ハンドラは `bgp_neighbor_handler()` (L3942-3943) → `bgp_table_handler_common()` (L3910)。最終的に `vtysh -c 'configure terminal' ...` コマンド列を直接実行する。Jinja2 テンプレートは使用しない。

### 3. keyspace イベントの発火

CONFIG_DB に対して誰かが `HSET BGP_NEIGHBOR|<key> field value` / `HDEL BGP_NEIGHBOR|<key> field` / `DEL BGP_NEIGHBOR|<key>` を実行すると、Redis サーバーが keyspace notification を発火する。書き込み元は:

- `sonic-cfggen -m <minigraph.xml>` (minigraph パース後の一括書き込み)
- `config bgp` CLI (sonic-utilities/config/main.py)
- REST / gNMI (sonic-mgmt-common OpenConfig BGP)
- `bgpcfgd` 自身 (FRR running-config との同期フィードバック)

### 4. Select ループ (runner.py)

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
- イベント受信後は全 subscriber をラウンドロビンでドレイン
- ドレイン完了後 `cfg_manager.commit()` で FRR vtysh へのバッチ送信を実行

### 5. Jinja2 テンプレート経路

`BGPPeerMgrBase.__init__()` (managers_bgp.py:103-116) が `peer_type` に対応するテンプレートを読み込む:

| テンプレートファイル | 用途 |
|---------------------|------|
| `bgpd/templates/<peer_type>/instance.conf.j2` | ADD (新規ピア) |
| `bgpd/templates/<peer_type>/update.conf.j2` | UPDATE (存在する場合のみ) |
| `bgpd/templates/<peer_type>/delete.conf.j2` | DEL (存在する場合のみ) |
| `bgpd/templates/<peer_type>/peer-group.conf.j2` | peer-group 生成 |
| `bgpd/templates/<peer_type>/policies.conf.j2` | route-map / policy |

`add_peer()` (managers_bgp.py:230) が `self.templates["add"].render(**kwargs)` で Jinja2 展開を行い、得られた FRR 設定コマンド文字列を `cfg_manager.push()` でバッファリングする。レンダリング失敗 (`jinja2.TemplateError`) は `log_err` して `return True` (再試行なし)。

### 6. Manager.handler() の SET/DEL 分岐

`manager.py:34-53`:

| op | 条件 | 動作 |
|----|------|------|
| `SET` | 全依存関係が揃っている | `set_handler(key, data)` を即時実行 |
| `SET` | 依存関係が未揃い | `set_queue` に積んで後回し |
| `SET` | `set_handler` が `False` 返却 | `set_queue` に積む (ループバック待機) |
| `DEL` | — | `del_handler(key)` を直接呼出 |

BGP_NEIGHBOR の依存関係:
- `DEVICE_METADATA.localhost/bgp_asn`
- `DEVICE_METADATA.localhost/type`
- `LOOPBACK_INTERFACE.Loopback0`
- `BGP_DEVICE_GLOBAL.tsa_enabled` / `idf_isolation_state`
- (check_neig_meta=True のとき) `DEVICE_NEIGHBOR_METADATA`

### 7. 初期スナップショット取得

`SubscriberStateTable` のコンストラクタ (subscriberstatetable.cpp:25-39) は PSUBSCRIBE 後に `m_table.getKeys()` で既存 key を全件取得し、`SET` イベントとして `m_buffer` に積む。bgpcfgd 起動時に CONFIG_DB に既存の BGP_NEIGHBOR エントリが再生される (再起動耐性)。

### 8. ProducerStateTable チャンネルとの関係

CONFIG_DB への書き込みが `ProducerStateTable` 経由の場合、書き込み側は `BGP_NEIGHBOR_CHANNEL@<db_id>` (table.h:85-96 `getChannelName()`) に PUBLISH する。bgpcfgd 側は **SubscriberStateTable** を使っており、Redis keyspace notification を PSUBSCRIBE することで、チャンネルに依存せず任意の書き込みを捕捉できる。APPL_DB・STATE_DB は BGP_NEIGHBOR のパスには介在しない。

## まとめ

| フェーズ | 実装 | ファイル |
|---------|------|---------|
| 書き込み → Redis keyspace | HSET/DEL が `__keyspace@4__:BGP_NEIGHBOR|*` を発火 | Redis サーバー内部 |
| keyspace → SubscriberStateTable | `PSUBSCRIBE` + `readData()` + `pop()` | subscriberstatetable.cpp |
| SST → Runner select ループ | `Select.select(1000ms)` + `subscriber.pop()` ドレイン | runner.py |
| Runner → Manager.handler | callback 登録テーブル経由 | runner.py, manager.py |
| Manager.handler → set/del_handler | op==SET/DEL 分岐、依存関係ガード、set_queue リトライ | manager.py |
| set_handler → Jinja2 テンプレート展開 | `templates["add"].render(**kwargs)` | managers_bgp.py |
| テンプレート → FRR vtysh | `cfg_manager.push()` + `commit()` でバッチ発行 | managers_bgp.py, config.py |
| frrcfgd 経路 | `subscribe()` → `bgp_neighbor_handler()` → `vtysh` 直接実行 | frrcfgd.py |
