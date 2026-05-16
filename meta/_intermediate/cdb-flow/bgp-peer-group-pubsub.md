# BGP_PEER_GROUP — 通信メカニズム調査 (Phase G)

対象ページ: `docs/reference/config-db/bgp-peer-group.md`

## 調査対象ソース

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`

## 購読者サマリー

`BGP_PEER_GROUP` テーブルを処理するデーモンは 2 系統存在し、購読 API が異なる。

| 購読者 | 購読 API | 通信方式 |
|--------|---------|---------|
| `frrcfgd` | `ExtConfigDBConnector.subscribe()` + `listen()` | Redis keyspace PSUBSCRIBE |
| `bgpcfgd` `BGPPeerMgrBase` | `swsscommon.SubscriberStateTable` + `Select` | PUBLISH/SUBSCRIBE チャネルベース |

## frrcfgd 経路の詳細

### ExtConfigDBConnector の仕組み

`frrcfgd.py` L1506-1555: `ExtConfigDBConnector` は `ConfigDBConnector` を継承し、`listen()` でバックグラウンドスレッドを起動する。

```python
# frrcfgd.py L1536-1543
def listen_thread(self, timeout):
    self.__listen_thread_running = True
    sub_key_space = "__keyspace@{}__:*".format(self.get_dbid(self.db_name))
    self.pubsub.psubscribe(sub_key_space)
    while self.__listen_thread_running:
        msg = self.pubsub.get_message(timeout, True)
        if msg:
            self.sub_msg_handler(msg)
    self.pubsub.punsubscribe(sub_key_space)
```

`sub_msg_handler` (L1521-1533) はチャネル名からテーブル名・行を抽出し、`client.hgetall(key)` で最新値を取得してから `__fire` でハンドラを呼び出す。

### BGP_PEER_GROUP の登録

```python
# frrcfgd.py L2303
('BGP_PEER_GROUP', self.bgp_neighbor_handler),
```

`subscribe_all()` (L2359-2361) で `config_db.subscribe('BGP_PEER_GROUP', bgp_neighbor_handler)` が実行される。

### bgp_neighbor_handler

```python
# frrcfgd.py L3942-3943
def bgp_neighbor_handler(self, table, key, data):
    self.bgp_table_handler_common(table, key, data, [{'keepalive', 'holdtime'}])
```

`BGP_NEIGHBOR` と `BGP_PEER_GROUP` は同一ハンドラ `bgp_neighbor_handler` を共有する。
`comb_attr_list=[{'keepalive', 'holdtime'}]` により、両フィールドが揃わない場合は FRR タイマーコマンドが生成されない。

### __update_bgp の BGP_PEER_GROUP ブランチ

`frrcfgd.py` L2790-2863:
1. `is_peer_group = True` (BGP_PEER_GROUP の場合)
2. FRR に peer-group 未存在 → `neighbor <pg_name> peer-group` を先行実行 (L2793-2802)
   - 失敗時: `LOG_ERR: failed to create peer-group %s for VRF %s` → `continue`
3. `key_map.run_command()` で属性コマンド群を vtysh 送出
4. `asn` が OP_ADD → `__apply_dep_vrf_table('BGP_GLOBALS_LISTEN_PREFIX')` + `__apply_dep_vrf_table('BGP_NEIGHBOR')` を再適用 (L2847-2849)
5. peer-group 削除 → `__delete_pg_neighbors(vrf, key)` でメンバーキャッシュを削除 (L2840-2842, L2856-2858)

### 起動時スナップショット + config replay

`frrcfgd.py` L2340: `table_data_cache = self.config_db.get_table_data([...])` で全テーブル一括スナップショット。
`frrcfgd.py` L2187-2191: `pg_table = self.config_db.get_table('BGP_PEER_GROUP')` で既存 peer-group を `self.bgp_peer_group` キャッシュに読み込み。
`frrcfgd.py` L2344-2357: `config_mode == "unified"` 時に config replay を実行。

## bgpcfgd 経路の詳細

### Runner + SubscriberStateTable

`runner.py` L16-73: `Runner.add_manager()` が manager を登録すると `swsscommon.SubscriberStateTable(conn, table_name)` を生成し `swsscommon.Select` に追加する (L49-51)。

```python
# runner.py L49-51
subscriber = swsscommon.SubscriberStateTable(conn, table_name)
self.subscribers.add(subscriber)
self.selector.addSelectable(subscriber)
```

`run()` ループ (L54-73): `selector.select()` → タイムアウト or イベント → `subscriber.pop()` → `callback(key, op, dict(fvs))`。

### BGP_PEER_GROUP を直接購読しない理由

`main.py` L87-92: `BGPPeerMgrBase` のインスタンスは `CFG_BGP_NEIGHBOR_TABLE_NAME`, `CFG_BGP_INTERNAL_NEIGHBOR_TABLE_NAME`, `BGP_MONITORS`, `BGP_PEER_RANGE`, `BGP_VOQ_CHASSIS_NEIGHBOR`, `BGP_SENTINELS` を購読する。`BGP_PEER_GROUP` テーブルは登録されていない。

`BGPPeerGroupMgr` (`managers_bgp.py` L15-84) は `BGPPeerMgrBase.add_peer()` (L227) から呼ばれる内部ヘルパー。peer 追加時に peer-group の Jinja2 テンプレート (`policies.conf.j2` + `peer-group.conf.j2`) をレンダリングして `cfg_mgr.push()` 経由で FRR に送出する。

### BGPPeerGroupMgr の動作

```python
# managers_bgp.py L30-38
def update(self, name, **kwargs):
    rc_policy = self.update_policy(name, **kwargs)
    rc_pg = self.update_pg(name, **kwargs)
    return rc_policy and rc_pg
```

`update_pg()` は TSA (`tsa_enabled`) と IDF isolation (`idf_isolation_state`) のルートマップを自動付与する (L62-63)。VRF が `default` か否かで `router bgp <asn>` / `router bgp <asn> vrf <vrf>` を切り替える (L68-71)。

## 通信方式の差異まとめ

| 比較項目 | frrcfgd (keyspace) | bgpcfgd (SubscriberStateTable) |
|---------|-------------------|-------------------------------|
| 購読単位 | DB 全体のキースペース (`__keyspace@N__:*`) | テーブル単位のチャネル |
| イベント発生源 | Redis HSET/HDEL 操作後の自動通知 | swsscommon の ProducerStateTable 書込 |
| フィールド値取得 | 通知後に `hgetall` で再取得 | `pop()` で key/op/fvs を一括取得 |
| スレッドモデル | バックグラウンドスレッド (listen_thread) | メインループ (selector.select) |
| BGP_PEER_GROUP 直接購読 | あり (bgp_neighbor_handler) | なし (BGPPeerGroupMgr は内部ヘルパー) |

## Evidence リスト

- `frrcfgd.py` L1506-1555: `ExtConfigDBConnector` クラス定義 (subscribe/listen/listen_thread/sub_msg_handler)
- `frrcfgd.py` L2187-2191: 起動時 BGP_PEER_GROUP スナップショット読み込み
- `frrcfgd.py` L2303: `('BGP_PEER_GROUP', self.bgp_neighbor_handler)` 登録
- `frrcfgd.py` L2340, L2344-2357: 起動時スナップショット + config replay
- `frrcfgd.py` L2359-2361: `subscribe_all()` 実装
- `frrcfgd.py` L2790-2863: `__update_bgp` の BGP_PEER_GROUP / BGP_NEIGHBOR ブランチ
- `frrcfgd.py` L3942-3943: `bgp_neighbor_handler` 定義
- `runner.py` L31-73: `Runner.add_manager()` + `run()` ループ
- `managers_bgp.py` L15-84: `BGPPeerGroupMgr` クラス定義
- `managers_bgp.py` L156-157: `BGPPeerMgrBase.__init__` で `BGPPeerGroupMgr` 生成
- `managers_bgp.py` L227: `add_peer()` 内で `peer_group_mgr.update()` 呼出
- `main.py` L87-92: `BGPPeerMgrBase` の登録テーブル一覧
