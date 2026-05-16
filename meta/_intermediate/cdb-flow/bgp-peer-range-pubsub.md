# BGP_PEER_RANGE — Phase G: 通信メカニズム調査証跡

> 調査日: 2026-05-16
> ソース: `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`, `managers_bgp.py`, `main.py`
> ソース: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## bgpcfgd 経路: SubscriberStateTable + Runner

`bgpcfgd` は `swsscommon.SubscriberStateTable` を利用した Redis keyspace 通知モデルを採用する。

### 登録フロー

1. `main.py:90` が `BGPPeerMgrBase(common_objs, "CONFIG_DB", "BGP_PEER_RANGE", "dynamic", False)` を生成し、`Runner.add_manager()` へ渡す。
2. `runner.py:49` の `add_manager()` が `swsscommon.SubscriberStateTable(conn, "BGP_PEER_RANGE")` を生成し `swsscommon.Select()` セレクタに登録する。
3. `Runner.run()` (runner.py:54–73) がメインループを形成: `selector.select(1000ms)` でブロッキング待機 → イベント受信時に `subscriber.pop()` でメッセージ取得 → `manager.handler(key, op, fvs)` を呼び出す。

### データフロー

```
CONFIG_DB: BGP_PEER_RANGE (Redis keyspace イベント)
  └→ swsscommon.SubscriberStateTable ("BGP_PEER_RANGE")
       └→ swsscommon.Select.select() [1000ms タイムアウト]
            └→ Runner.run() ループ
                 └→ BGPPeerMgrBase.handler(key, op, fvs)
                      ├→ set_handler()   [op=SET]
                      └→ del_handler()   [op=DEL]
```

### コードポイント

| ファイル | 行 | 内容 |
|---|---|---|
| `bgpcfgd/main.py` | 90 | `BGPPeerMgrBase(..., "BGP_PEER_RANGE", "dynamic", False)` 生成 |
| `bgpcfgd/main.py` | 134 | `Runner(common_objs['cfg_mgr'])` 生成・実行 |
| `bgpcfgd/runner.py` | 49 | `swsscommon.SubscriberStateTable(conn, table_name)` |
| `bgpcfgd/runner.py` | 27 | `swsscommon.Select()` セレクタ生成 |
| `bgpcfgd/runner.py` | 57 | `selector.select(Runner.SELECT_TIMEOUT)` (1000ms) |
| `bgpcfgd/runner.py` | 65 | `subscriber.pop()` でメッセージ取得 |

## frrcfgd 経路: ExtConfigDBConnector + Redis pubsub スレッド

`frrcfgd` は `BGP_PEER_RANGE` を直接購読しないが、機能的に重複する `BGP_GLOBALS_LISTEN_PREFIX` テーブルを独自の `ExtConfigDBConnector` 機構で購読する。

### ExtConfigDBConnector の仕組み

- `ExtConfigDBConnector` (frrcfgd.py:1506) は `swsscommon.ConfigDBConnector` を継承し、`listen_thread()` メソッドで Redis keyspace パターン `__keyspace@<dbid>__:*` を `psubscribe` する。
- `subscribe_all()` (frrcfgd.py:2359) が `table_handler_list` の全テーブルに `config_db.subscribe(table, hdlr)` を呼び出し、ハンドラを登録する。
- `start()` (frrcfgd.py:3954–3956) が `subscribe_all()` → `config_db.listen()` を順に呼び出し、別スレッドで `listen_thread()` を起動する。

### BGP_GLOBALS_LISTEN_PREFIX との関係

`frrcfgd.py:92` が `'BGP_GLOBALS_LISTEN_PREFIX': ['bgpd']` を管理テーブルとして登録し、`frrcfgd.py:2307` の `table_handler_list` に `('BGP_GLOBALS_LISTEN_PREFIX', self.bgp_table_handler_common)` を含む。

`frrcfgd.py:2783` の `bgp_table_handler_common` が `table == 'BGP_GLOBALS_LISTEN_PREFIX'` を検出し `bgp listen range` コマンドを生成する。これは `bgpcfgd` の `BGP_PEER_RANGE` 経路と同等機能だが、異なるテーブルを購読する二重管理構造。

### コードポイント

| ファイル | 行 | 内容 |
|---|---|---|
| `frrcfgd/frrcfgd.py` | 1506–1556 | `ExtConfigDBConnector` クラス定義 |
| `frrcfgd/frrcfgd.py` | 1539 | `pubsub.psubscribe(sub_key_space)` |
| `frrcfgd/frrcfgd.py` | 1540–1543 | `pubsub.get_message()` ループ |
| `frrcfgd/frrcfgd.py` | 2359–2361 | `subscribe_all()` 全テーブル登録 |
| `frrcfgd/frrcfgd.py` | 3955 | `start()`: subscribe_all + listen() 起動 |
| `frrcfgd/frrcfgd.py` | 92 | `BGP_GLOBALS_LISTEN_PREFIX` 管理テーブル登録 |
| `frrcfgd/frrcfgd.py` | 2783 | `bgp listen range` コマンド生成分岐 |

## まとめ

- `BGP_PEER_RANGE` の主要購読者は **bgpcfgd**: `SubscriberStateTable` + `Select` ループ（同期 IO 多重化）
- `BGP_GLOBALS_LISTEN_PREFIX` の購読者は **frrcfgd**: `ExtConfigDBConnector` + Redis `psubscribe` 別スレッド（非同期）
- 2 つの経路は別テーブルを購読するが、FRR への `bgp listen range` コマンド生成という同等機能を持つ二重管理構造
