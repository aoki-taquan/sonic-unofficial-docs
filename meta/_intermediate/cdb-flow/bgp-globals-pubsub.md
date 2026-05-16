# 通信メカニズム解析: BGP_GLOBALS (Phase G)

## 対象テーブル

`BGP_GLOBALS` (CONFIG_DB)

## ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 購読者サマリ

| デーモン | 購読 | 通信方式 |
|---------|------|---------|
| `frrcfgd` | あり | Redis keyspace 通知 (`ExtConfigDBConnector.psubscribe`) |
| `bgpcfgd` | なし | — |
| `orchagent` / `syncd` | なし | BGP_GLOBALS は FRR ソフト処理のみ |

## bgpcfgd: BGP_GLOBALS を購読しない

`bgpcfgd/main.py` の Manager 登録リスト（L75-L132）に `BGP_GLOBALS` は含まれない。
`bgpcfgd` が担当するテーブルは `BGP_NEIGHBOR`, `BGP_MONITORS`, `BGP_PEER_RANGE`,
`BGP_VOQ_CHASSIS_NEIGHBOR`, `BGP_SENTINELS`, `BGP_ALLOWED_PREFIXES`, `STATIC_ROUTE` 等。

BGP_GLOBALS はルータ全体設定であり、`frrcfgd` のみが担当する。

## frrcfgd: ExtConfigDBConnector によるキーspace 通知

### クラス継承

```
swsscommon.ConfigDBConnector
  └─ ExtConfigDBConnector   (frrcfgd.py:1506)
        subscribe() / listen() / stop_listen()
```

### 購読登録

`BGPConfigDaemon.subscribe_all()` (frrcfgd.py:2359-2361) が `table_handler_list` を順に処理し、
`config_db.subscribe("BGP_GLOBALS", self.bgp_global_handler)` を呼び出す。

`table_handler_list` の BGP_GLOBALS エントリ:
```python
# frrcfgd.py:2296
('BGP_GLOBALS', self.bgp_global_handler),
```

### keyspace 通知ループ

```python
# frrcfgd.py:1536-1545
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

別スレッドで Redis keyspace 通知をポーリング。通知ペイロードは操作名のみ (`hset` / `del`)。
値は `client.hgetall(key)` で再取得 (frrcfgd.py:1527)。

### ハンドラ呼び出し経路

```
Redis keyspace PUBLISH "__keyspace@4__:BGP_GLOBALS|<vrf>" "hset"
  ↓ listen_thread() → sub_msg_handler() (frrcfgd.py:1521)
  ↓ _ConfigDBConnector__fire("BGP_GLOBALS", "<vrf>", data)
  ↓ bgp_global_handler(table="BGP_GLOBALS", key="<vrf>", data={...})
  ↓ bgp_message キュー → __update_bgp() (frrcfgd.py:2685)
  ↓ vtysh コマンド発行
```

DEL 時は `data is None` → `del_table=True` → `no router bgp <asn>` (frrcfgd.py:3918)

### 起動時 config replay

`BGPConfigDaemon.__init__()` で `subscribe_all()` 前に:
```python
# frrcfgd.py:2175
glb_table = self.config_db.get_table('BGP_GLOBALS')
```
スナップショットを一括取得して replay。`config_mode == "unified"` の場合のみ vtysh 適用される。

## bgpcfgd の SubscriberStateTable（BGP_GLOBALS 以外）

bgpcfgd の `Runner` クラス (runner.py:49) は担当テーブル（BGP_NEIGHBOR 等）に対して
`swsscommon.SubscriberStateTable` を使用する。BGP_GLOBALS にはこの経路を使わない。

```python
# runner.py:49-52
subscriber = swsscommon.SubscriberStateTable(conn, table_name)
self.selector.addSelectable(subscriber)
```

## 二重購読の注意点

`frrcfgd.py` の L87 コメントで、`bgpcfgd` と `frrcfgd` を同時稼働しないよう注意が記されている。
実運用では Docker routing config mode で一方のみが選択される:
- `unified` モード: frrcfgd が BGP_GLOBALS を処理
- `separated` モード: 挙動が異なる可能性（frrcfgd.py:2167-2170 参照）
