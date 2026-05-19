# ROUTE_REDISTRIBUTE — Phase G: Pub/Sub・通信メカニズム調査結果

調査日: 2026-05-19
対象ページ: `docs/reference/config-db/route-common.md`
対象ソース: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
(ref: 9ea932ec2e18f35e58268ec2e4456b1d4afd65cd)

---

## 概要

`ROUTE_REDISTRIBUTE` テーブルは `frrcfgd`（`BGPConfigDaemon`）が
Redis keyspace 通知経由で購読する。`swsscommon.SubscriberStateTable` は不使用。

## 購読メカニズム

### ExtConfigDBConnector

`frrcfgd.py:1507-1555` に定義された `ExtConfigDBConnector`（`ConfigDBConnector` サブクラス）が実装。

- `listen()` (L1547): `redis.client.PubSub` を生成し `listen_thread` をバックグラウンドスレッドで起動
- `listen_thread()` (L1536): `psubscribe("__keyspace@<dbid>__:*")` で CONFIG_DB 全体をワイルドカード購読
- `sub_msg_handler()` (L1521): チャンネル名からテーブル名・キーを分解し、登録ハンドラを呼び出す

### subscribe_all

`BGPConfigDaemon.subscribe_all()` (L2359-2361):

```python
def subscribe_all(self):
    for table, hdlr in self.table_handler_list:
        self.config_db.subscribe(table, hdlr)
```

`ROUTE_REDISTRIBUTE` のハンドラ: `bgp_table_handler_common` (L2316)

### 起動シーケンス

```
BGPConfigDaemon.__init__()
  ├─ subscribe_all()    ← 全テーブルのハンドラを ConfigDBConnector.handlers に登録
  └─ config_db.listen() ← ExtConfigDBConnector.listen_thread 起動
       └─ psubscribe("__keyspace@<CONFIG_DB_id>__:*")
            └─ イベント到着 → sub_msg_handler → __fire(table, row, data)
                 └─ bgp_table_handler_common(key, op, data)
```

`frrcfgd.py:3955-3956` (main ループ):
```python
self.subscribe_all()
self.config_db.listen()
```

## vtysh コマンド送出経路

`bgp_table_handler_common` → `bgp_message` キューへ投入 → `bgp_message_handler_thread` が消費 →
`g_run_command(table, command, True, daemons=['bgpd'])` → UNIX ソケット経由で vtysh へ送信

ターゲットデーモン: `['bgpd']` のみ（`frrcfgd.py:97`）。

## swsscommon 不使用の理由

`frrcfgd` は `swsscommon` の `SubscriberStateTable` / `Select` ループを使用せず、
独自の Redis pub/sub スレッドを実装している。これは `frrcfgd` が sonic-swss ではなく
`sonic-frr-mgmt-framework` の独立サービスとして実装されているため。
