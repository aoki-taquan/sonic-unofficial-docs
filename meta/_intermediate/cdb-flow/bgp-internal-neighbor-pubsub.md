# BGP_INTERNAL_NEIGHBOR — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `BGP_INTERNAL_NEIGHBOR` テーブル。購読者は `bgpcfgd` (`docker-fpm-frr` 内) の `Runner` クラス。`frrcfgd` はこのテーブルを購読しない（Phase H で確認済み）。

## 1. 購読 API — `SubscriberStateTable` + `bgpcfgd Runner`

`bgpcfgd` は `swsscommon.SubscriberStateTable` を使って CONFIG_DB を購読する。`Runner.add_manager()` がマネージャ登録時にサブスクリプションを作成する:

```python
# bgpcfgd/runner.py:47-51
if table_name not in self.callbacks[db]:
    conn = self.db_connectors[db]
    subscriber = swsscommon.SubscriberStateTable(conn, table_name)
    self.subscribers.add(subscriber)
    self.selector.addSelectable(subscriber)
self.callbacks[db][table_name].append(manager.handler)
```

`BGP_INTERNAL_NEIGHBOR` は `main.py` L88 で `BGPPeerMgrBase` として登録される:

```python
# bgpcfgd/main.py:88
BGPPeerMgrBase(common_objs, "CONFIG_DB", swsscommon.CFG_BGP_INTERNAL_NEIGHBOR_TABLE_NAME, "internal", False),
```

`Runner.add_manager()` が呼ばれることで `SubscriberStateTable(conn, "BGP_INTERNAL_NEIGHBOR")` が生成され、Redis keyspace 通知への購読が確立する。

## 2. メインループ — `Runner.run()`

```python
# bgpcfgd/runner.py:54-73
def run(self):
    while g_run:
        state, _ = self.selector.select(Runner.SELECT_TIMEOUT)  # SELECT_TIMEOUT = 1000 ms
        if state == self.selector.TIMEOUT:
            continue
        elif state == self.selector.ERROR:
            raise Exception("Received error from select")

        for subscriber in self.subscribers:
            while True:
                key, op, fvs = subscriber.pop()
                if not key:
                    break
                for callback in self.callbacks[...][subscriber.getTableName()]:
                    callback(key, op, dict(fvs))
        rc = self.cfg_manager.commit()
```

- `selector.select(1000)` は最大 1,000 ms のタイムアウトで `epoll` 相当の待機を行う。
- `subscriber.pop()` はバッファ済みイベントを 1 件ずつ取り出す（`SubscriberStateTable` 内部でバッファリング）。
- 全サブスクライバのイベント処理完了後に `cfg_manager.commit()` で FRR への設定投入をまとめてコミットする。
- `SIGTERM` で `g_run = False` になりループ終了（`runner.py:10-13`）。

## 3. keyspace 通知の流れ

```
CONFIG_DB へ書込 (HSET "BGP_INTERNAL_NEIGHBOR|10.0.0.1" ...)
  ↓ Redis keyspace: PUBLISH "__keyspace@4__:BGP_INTERNAL_NEIGHBOR|10.0.0.1"  "hset"
SubscriberStateTable 内部バッファにイベント蓄積
  ↓ Runner.run() → selector.select() がシグナルを検出
subscriber.pop() → (key="10.0.0.1", op="SET", fvs={...})
  ↓ callback: BGPPeerMgrBase.handler(key, op, fvs)
managers_bgp.py: add_peer() / del_peer() / update_peer() 呼び出し
  ↓ Jinja2 テンプレート (bgpd/templates/internal/*.conf.j2) 展開
FRR bgpd へ設定コマンド投入 (vtysh or UNIX socket 経由)
  ↓ cfg_manager.commit()
```

- イベントペイロードはキー名 + 操作名 + フィールドマップ (`dict(fvs)`)。CONFIG_DB の全フィールドが `fvs` に含まれる。
- `op == "SET"` → `add_peer()` / `update_peer()`、`op == "DEL"` → `del_peer()` に分岐（`BGPPeerMgrBase.set_handler` / `del_handler`）。

## 4. frrcfgd との差異

`frrcfgd` (`src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`) は `ExtConfigDBConnector` を使って `ConfigDBConnector.subscribe()` + `pubsub.psubscribe()` の Redis keyspace 通知を購読する方式を採るが、`BGP_INTERNAL_NEIGHBOR` は `table_handler_list` に含まれない（L2293-2338 全体を確認）。

```python
# frrcfgd/frrcfgd.py:1538-1543  (ExtConfigDBConnector.listen_thread)
sub_key_space = "__keyspace@{}__:*".format(self.get_dbid(self.db_name))
self.pubsub.psubscribe(sub_key_space)
while self.__listen_thread_running:
    msg = self.pubsub.get_message(timeout, True)
    if msg:
        self.sub_msg_handler(msg)
```

`frrcfgd` は全 CONFIG_DB keyspace を購読するが、`sub_msg_handler` 内の `table in self.handlers` チェックで `BGP_INTERNAL_NEIGHBOR` は無視される（`subscribe_all()` が登録するテーブル一覧に含まれないため）。内部 iBGP は `bgpcfgd` 専用パス。

## 5. 起動時スナップショット

`BGPPeerMgrBase` は `Manager` 基底クラスの deps 充足メカニズムを通じて初期化される。起動時はまず `DEVICE_METADATA`・`Loopback0`・`Loopback4096` 等の deps が充足されるまでイベントが保留され、充足後に `post_dependencies_init()` が実行される（`managers_bgp.py:181-182`）。以降に `SubscriberStateTable` から流れてくる既存エントリのスナップショット（`SET` イベント）が `add_peer()` に渡る。

## 6. TTL / 永続性

- CONFIG_DB の `BGP_INTERNAL_NEIGHBOR` エントリには TTL は設定されない（CONFIG_DB は永続前提）。
- `notify-keyspace-events` は SONiC の `database_config.json` で有効化されている前提（`K` フラグ含む設定）。

## 7. 関連リファレンス

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py:16-73` (Runner クラス全体)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py:88, 134-136` (BGP_INTERNAL_NEIGHBOR 登録 + runner.add_manager)
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:87-182` (BGPPeerMgrBase 初期化・deps)
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py:1506-1553, 2293-2338, 2359-2361` (ExtConfigDBConnector, table_handler_list, subscribe_all — BGP_INTERNAL_NEIGHBOR 不在を確認)
