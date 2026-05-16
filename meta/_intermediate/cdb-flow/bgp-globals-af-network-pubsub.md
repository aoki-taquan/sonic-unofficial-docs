# BGP_GLOBALS_AF_NETWORK — 通信メカニズム (Phase G) 解析メモ

生成日: 2026-05-16

## 1. 購読 API — `ExtConfigDBConnector.subscribe()` + Redis keyspace 通知

`frrcfgd` (sonic-frr-mgmt-framework) は `swsscommon.ConsumerStateTable` を直接使わず、独自の `ExtConfigDBConnector`（`ConfigDBConnector` サブクラス）の `subscribe(table, handler)` で `BGP_GLOBALS_AF_NETWORK` ハンドラを登録する。

```python
# frrcfgd.py:2318-2319
('BGP_GLOBALS_AF_NETWORK', self.bgp_table_handler_common),
...
def subscribe_all(self):
    for table, hdlr in self.table_handler_list:
        self.config_db.subscribe(table, hdlr)  # frrcfgd.py:2360-2361
```

起動フロー:

```python
# frrcfgd.py:3954-3955
def start(self):
    self.subscribe_all()
    self.config_db.listen()
```

## 2. Redis keyspace 通知の仕組み

`ExtConfigDBConnector.listen()` が内部スレッドを起動し、Redis の keyspace 通知パターン `__keyspace@<dbId>__:*` を **PSUBSCRIBE** する。

```python
# frrcfgd.py:1538-1545
sub_key_space = "__keyspace@{}__:*".format(self.get_dbid(self.db_name))
self.pubsub.psubscribe(sub_key_space)
while self.__listen_thread_running:
    msg = self.pubsub.get_message(timeout, True)
    if msg:
        self.sub_msg_handler(msg)
```

`sub_msg_handler` がメッセージを受信し、channel から `TABLE|row` を解析してハンドラに振り分ける:

```python
# frrcfgd.py:1520-1530
def sub_msg_handler(self, msg_item):
    if msg_item['type'] == 'pmessage':
        key = msg_item['channel'].split(':', 1)[1]
        try:
            (table, row) = key.split(self.TABLE_NAME_SEPARATOR, 1)
            if table in self.handlers:
                client = self.get_redis_client(self.db_name)
                data = self.raw_to_typed(client.hgetall(key), table)
                super(ExtConfigDBConnector, self)._ConfigDBConnector__fire(table, row, data)
        ...
```

- keyspace 通知本体には値は含まれず操作名 (`hset`/`del`) のみ。
- ハンドラは通知後に **HGETALL で再取得した** dict を受け取る（`data is None` → DEL 操作）。

## 3. BGP_GLOBALS_AF_NETWORK の通知パターン

| Redis keyspace 通知 | frrcfgd 受信 |
|---------------------|-------------|
| `__keyspace@4__:BGP_GLOBALS_AF_NETWORK|default|ipv4_unicast|10.0.0.0/8` `hset` | `bgp_table_handler_common("BGP_GLOBALS_AF_NETWORK", "default|ipv4_unicast|10.0.0.0/8", {data})` |
| `__keyspace@4__:BGP_GLOBALS_AF_NETWORK|default|ipv4_unicast|10.0.0.0/8` `del` | `bgp_table_handler_common("BGP_GLOBALS_AF_NETWORK", "default|ipv4_unicast|10.0.0.0/8", None)` |

dbId は CONFIG_DB の通常 4（`database_config.json` 既定）。

## 4. ハンドラ — `bgp_table_handler_common`

```python
# frrcfgd.py:2318
('BGP_GLOBALS_AF_NETWORK', self.bgp_table_handler_common),
```

`bgp_table_handler_common` は `af_network_key_map` を使って FRR `network` コマンドへ変換する。`BGP_GLOBALS_AF_NETWORK` は `vrf_tables` に含まれるため、キーの VRF コンテキストで `bgpd` デーモンにコマンドを発行する。

```python
# frrcfgd.py:99
'BGP_GLOBALS_AF_NETWORK': ['bgpd'],  # TABLE_DAEMON マッピング
```

## 5. ConsumerStateTable / NotificationProducer 非使用の確認

- `BGP_GLOBALS_AF_NETWORK` テーブルへの `swsscommon.ConsumerStateTable` 購読者なし。
- `NotificationProducer` で BGP_GLOBALS_AF_NETWORK 関連の通知を出す箇所は SONiC ソース内にない。
- 結論: **CONFIG_DB → frrcfgd (ExtConfigDBConnector keyspace 通知) → FRR bgpd vtysh コマンド** の一方向パス。APPL_DB/STATE_DB の中継なし。

## 6. 起動時スナップショット

`frrcfgd` は `config_mode == "unified"` の場合、`start()` の前に全テーブルの既存エントリを `get_table()` で取得してリプレイする（差分ではなく初期フル適用）:

```python
# frrcfgd.py:2344-2357 (unified モード)
for table, _ in self.table_handler_list:
    table_list = self.config_db.get_table(table)
    for key, data in table_list.items():
        self.bgp_message.put((self.config_db.serialize_key(key), False, table, upd_data))
```

## 7. 参考行番号

- `sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
  - 1506-1560: `ExtConfigDBConnector` クラス定義（`subscribe`/`listen`/`sub_msg_handler`/`listen_thread`）
  - 1538-1545: `listen_thread` — PSUBSCRIBE + メッセージポーリング
  - 1520-1530: `sub_msg_handler` — channel 解析 + HGETALL + ハンドラ呼び出し
  - 99: `TABLE_DAEMON` マッピング（`BGP_GLOBALS_AF_NETWORK` → `['bgpd']`）
  - 2119: `tbl_to_key_map`（`BGP_GLOBALS_AF_NETWORK` → `af_network_key_map`）
  - 2139: `vrf_tables`（VRF スコープテーブルセット）
  - 2318: `table_handler_list` — `BGP_GLOBALS_AF_NETWORK` の登録
  - 2359-2361: `subscribe_all()`
  - 3954-3955: `start()` — `subscribe_all()` + `listen()`
