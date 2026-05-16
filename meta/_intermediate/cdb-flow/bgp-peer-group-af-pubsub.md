# BGP_PEER_GROUP_AF — Phase G: Redis PUBSUB / keyspace / ExtConfigDBConnector

## 調査対象

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 購読メカニズム全体像

`BGP_PEER_GROUP_AF` テーブルの変更通知は **`ExtConfigDBConnector` + Redis keyspace notification (PSUBSCRIBE)** で実装されている。`bgpcfgd`（bgpcfgd 系）とは異なり、`SubscriberStateTable` は使用しない。frrcfgd 独自の `ExtConfigDBConnector` クラスが Redis の pubsub チャンネルを直接購読する。

### 1. PSUBSCRIBE チャンネルパターン

`ExtConfigDBConnector.listen_thread()` (frrcfgd.py:1536-1545) が `listen()` 呼び出し時に以下を PSUBSCRIBE する:

```
__keyspace@<db_id>__:*
```

- `<db_id>` は CONFIG_DB の Redis DB 番号 (通常 4)
- パターンは `*` 全体をカバーし、CONFIG_DB の全テーブルを捕捉する
- 実装: `self.pubsub.psubscribe(sub_key_space)` (frrcfgd.py:1539)
- `sub_key_space = "__keyspace@{}__:*".format(self.get_dbid(self.db_name))` (frrcfgd.py:1538)

### 2. keyspace イベントの発火

CONFIG_DB に対して `HSET BGP_PEER_GROUP_AF|<key> field value` / `DEL BGP_PEER_GROUP_AF|<key>` が実行されると、Redis サーバーが keyspace notification を発火する。書き込み元は:

- `sonic-mgmt-common` (OpenConfig BGP peer-group REST / gNMI)
- `vtysh` 経由の bgpcfgd 同期書き戻し
- `config` CLI (sonic-utilities)
- SONiC startup config ロード (`sonic-cfggen`)

### 3. listen スレッドと sub_msg_handler

`ExtConfigDBConnector.listen()` (frrcfgd.py:1547-1552) は別スレッドで `listen_thread()` を起動する:

```python
self.pubsub = self.get_redis_client(self.db_name).pubsub()
self.sub_thread = threading.Thread(target=self.listen_thread, args=(10,))
self.sub_thread.start()
```

`listen_thread()` (frrcfgd.py:1536-1545) は 10 秒タイムアウトのポーリングループ:

```python
while self.__listen_thread_running:
    msg = self.pubsub.get_message(timeout, True)
    if msg:
        self.sub_msg_handler(msg)
```

### 4. sub_msg_handler — テーブル振り分け

`ExtConfigDBConnector.sub_msg_handler()` (frrcfgd.py:1521-1532) が pmessage を受信してテーブルを識別する:

```
pmessage チャンネル "__keyspace@4__:BGP_PEER_GROUP_AF|<vrf>|<pg>|<af>"
  → channel.split(':', 1)[1] → "BGP_PEER_GROUP_AF|<vrf>|<pg>|<af>"
  → key.split(TABLE_NAME_SEPARATOR, 1) → (table="BGP_PEER_GROUP_AF", row="<vrf>|<pg>|<af>")
  → table in self.handlers → ハンドラ登録済みを確認
  → client.hgetall(key) で現在のフィールド値を全件取得
  → __fire(table, row, data) でハンドラを呼び出す
```

`data` が空 (`{}`) の場合は `raw_to_typed()` (frrcfgd.py:1512-1520) が `None` を返す。これが DELETE を示すシグナルとなる (`bgp_table_handler_common` の `data is None` 分岐へ)。

### 5. subscribe_all — ハンドラ登録

`BGPConfigDaemon.subscribe_all()` (frrcfgd.py:2359-2361) が `start()` 時に全テーブルのハンドラを登録する:

```python
for table, hdlr in self.table_handler_list:
    self.config_db.subscribe(table, hdlr)
```

`table_handler_list` (frrcfgd.py:2305) に:

```python
('BGP_PEER_GROUP_AF', self.bgp_table_handler_common),
```

が含まれる。条件なし — 常時登録。

### 6. デーモン起動フロー

```
BGPConfigDaemon.start()       (frrcfgd.py:3955-3956)
  → subscribe_all()            ハンドラ登録
  → config_db.listen()         listen スレッド起動
    → psubscribe("__keyspace@4__:*")
    → polling loop (10 秒タイムアウト)
      → sub_msg_handler(msg)
        → __fire(table, row, data)
          → bgp_table_handler_common(table, key, data)
```

### 7. bgp_table_handler_common の SET/DEL 分岐

| data の状態 | 分岐 | 動作 |
|---|---|---|
| `None` (DELETE / 空 hgetall) | `del_table=True` | FRR から該当 AF を削除 (`no neighbor PG ...`) |
| dict (SET) | `del_table=False` | FRR へ peer-group AF 設定コマンドを生成・送出 |

ソース: frrcfgd.py:3918, 3930

### 8. 初期スナップショット取得

frrcfgd は起動時に `config_db.get_table_data(table_list)` (frrcfgd.py:2327-2350) で既存エントリを一括ロードし、`__fire()` を呼び出して再生する。PSUBSCRIBE による継続監視と合わせて再起動耐性を確保している。

### 9. ProducerStateTable / ConsumerStateTable との関係

frrcfgd は `SubscriberStateTable` や `ConsumerStateTable` を使用しない。`ExtConfigDBConnector` が Redis keyspace notification を直接 PSUBSCRIBE することで、書き込み経路 (REST / CLI / cfggen) に依存せず CONFIG_DB の変更を捕捉できる設計になっている。

## まとめ

| フェーズ | 実装 | ファイル |
|---------|------|---------|
| 書き込み → Redis keyspace | `HSET`/`DEL` が `__keyspace@4__:BGP_PEER_GROUP_AF\|*` を発火 | Redis サーバー内部 |
| keyspace → ExtConfigDBConnector | `PSUBSCRIBE "__keyspace@4__:*"` + `get_message(10s)` ポーリング | frrcfgd.py:1536-1545 |
| sub_msg_handler → ハンドラ呼び出し | `hgetall` + `__fire(table, row, data)` | frrcfgd.py:1521-1532 |
| data=None (DELETE) / dict (SET) 分岐 | `bgp_table_handler_common` が `del_table` フラグで制御 | frrcfgd.py:3918, 3930 |
| FRR vtysh コマンド発行 | `nbr_af_key_map` ベースのコマンド生成 → vtysh | frrcfgd.py:2112, 2865-2874 |
