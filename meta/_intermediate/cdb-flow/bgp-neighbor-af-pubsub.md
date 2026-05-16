# BGP_NEIGHBOR_AF — Phase G: Redis PUBSUB / keyspace / ExtConfigDBConnector

## 調査対象

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 購読メカニズム全体像

`BGP_NEIGHBOR_AF` テーブルの変更通知は **`ExtConfigDBConnector` + Redis keyspace notification (PSUBSCRIBE)** で実装されている。`frrcfgd.py` 内の `BgpCfgd` クラスが `subscribe_all()` を通じて `ExtConfigDBConnector.subscribe(table, hdlr)` を呼び出し、CONFIG_DB 全テーブルの keyspace チャンネルを一括 PSUBSCRIBE する。`BGP_NEIGHBOR_AF` 専用の購読ハンドラは `bgp_table_handler_common` (`frrcfgd.py:3895`)。

### 1. PSUBSCRIBE チャンネルパターン

`ExtConfigDBConnector.listen_thread()` (`frrcfgd.py:1538-1543`) が以下を実行する:

```python
sub_key_space = "__keyspace@{}__:*".format(self.get_dbid(self.db_name))
self.pubsub.psubscribe(sub_key_space)
```

- `<dbid>` は CONFIG_DB の Redis DB 番号（通常 **4**）
- パターン `__keyspace@4__:*` により CONFIG_DB 内の**全キー変化**を一括捕捉
- `BGP_NEIGHBOR_AF|<vrf>|<neighbor>|<afi_safi>` への `HSET` / `DEL` も同チャンネルで捕捉される

### 2. keyspace イベントの処理フロー

`ExtConfigDBConnector.sub_msg_handler()` (`frrcfgd.py:1521-1532`) がメッセージ受信時に呼ばれ:

```python
key = msg_item['channel'].split(':', 1)[1]       # "BGP_NEIGHBOR_AF|<vrf>|<neighbor>|<af>"
(table, row) = key.split(self.TABLE_NAME_SEPARATOR, 1)
if table in self.handlers:
    client = self.get_redis_client(self.db_name)
    data = self.raw_to_typed(client.hgetall(key), table)
    super().__fire(table, row, data)              # 登録済みハンドラを呼び出す
```

- `TABLE_NAME_SEPARATOR` は `|`
- `HGETALL` で最新値を再取得してからハンドラに渡す（通知のみで値は含まない keyspace の限界を補う）
- 登録ハンドラは `subscribe_all()` 時に `self.handlers["BGP_NEIGHBOR_AF"] = bgp_table_handler_common` として設定済み

### 3. listen スレッド (ExtConfigDBConnector.listen_thread)

```python
# frrcfgd.py:1536-1544
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

- `timeout=10`（秒）でポーリング
- `listen()` が別スレッドで `listen_thread` を起動する（`frrcfgd.py:1548-1551`）
- メインスレッドとは非同期で動作し、変更を検知した時点で即座にハンドラを呼び出す

### 4. subscribe_all() による登録

`BgpCfgd.subscribe_all()` (`frrcfgd.py:2359-2361`):

```python
def subscribe_all(self):
    for table, hdlr in self.table_handler_list:
        self.config_db.subscribe(table, hdlr)
```

`table_handler_list` 内の登録 (`frrcfgd.py:2306`):

```python
('BGP_NEIGHBOR_AF', self.bgp_table_handler_common),
```

`bgp_table_handler_common` は AF 別設定を `bgp_message` キューに積み、`__update_bgp()` を同期呼び出しして vtysh コマンドを生成する。

### 5. BGP_NEIGHBOR_AF 固有の分岐 (bgp_table_handler_common)

`frrcfgd.py:2665-2668`:

```python
if table == 'BGP_NEIGHBOR_AF' or table == 'BGP_PEER_GROUP_AF' and key is not None:
    _, af_ip_type = key.split('|')
    tbl_key, _ = af_ip_type.lower().split('_')
    tbl_key = {'admin_status': tbl_key}   # 'ipv4' or 'ipv6'
```

`afi_safi` キー部（例: `ipv4_unicast`）から `ipv4` / `ipv6` を抽出し、`admin_status` フィールドを vtysh AF コマンドのプレフィクス（`address-family ipv4 unicast` 等）に紐付ける。

### 6. 初期スナップショット取得

起動時に `BgpCfgd.__init__()` (`frrcfgd.py:2340-2354`) が `config_mode == "unified"` の場合:

```python
table_list = self.config_db.get_table('BGP_NEIGHBOR_AF')
for key, data in table_list.items():
    self.bgp_message.put((self.config_db.serialize_key(key), False, 'BGP_NEIGHBOR_AF', upd_data))
    self.__update_bgp(upd_data_list)
```

PSUBSCRIBE 開始前に CONFIG_DB の既存エントリを `bgp_message` に積んで全件再生する（再起動耐性）。

### 7. vtysh へのコマンド送出

keyspace notification 受信後の変換パス:

```
CONFIG_DB: HSET "BGP_NEIGHBOR_AF|<vrf>|<neighbor>|<afi_safi>" <fields>
  ↓ Redis keyspace event "__keyspace@4__:BGP_NEIGHBOR_AF|..." "hset"
listen_thread: pubsub.get_message(timeout=10s)
  ↓ sub_msg_handler() → HGETALL で再取得 → __fire(table, row, data)
bgp_table_handler_common(table='BGP_NEIGHBOR_AF', key, data)
  ↓ bgp_message.put((key, del_table, table, data))  (frrcfgd.py:3928)
  ↓ __update_bgp() → BGPKeyMapList で nbr_af_key_map をたどり vtysh コマンド生成
['vtysh', '-c', 'configure terminal', '-c', 'router bgp <asn> vrf <vrf>',
 '-c', 'address-family <afi> <safi>', '-c', 'neighbor <addr> activate', ...]
```

### 8. 購読者サマリ

| 購読者 | 購読 API | 購読パターン | タイムアウト |
|--------|---------|--------------|-------------|
| `frrcfgd` (`BgpCfgd`) | `ExtConfigDBConnector` + `redis.pubsub().psubscribe()` | `__keyspace@4__:*`（CONFIG_DB 全キー） | `get_message(10s)` |

CONFIG_DB 側に `SubscriberStateTable` / `ProducerStateTable` は介在しない。`swss-common` ではなく **hiredis 直結の Python `redis` ライブラリ**を `ExtConfigDBConnector` 経由で使用する点が `orchagent` 系との大きな違いである。

## まとめ

| フェーズ | 実装 | ファイル |
|---------|------|---------|
| 書き込み → Redis keyspace | HSET/DEL が `__keyspace@4__:BGP_NEIGHBOR_AF|*` を発火 | Redis サーバー内部 |
| keyspace → listen_thread | `PSUBSCRIBE "__keyspace@4__:*"` + `get_message(10s)` ポーリング | frrcfgd.py:1538-1543 |
| listen_thread → sub_msg_handler | `pmessage` 型チェック → テーブル分割 → HGETALL 再取得 | frrcfgd.py:1521-1532 |
| sub_msg_handler → __fire | `self.handlers[table]` ルックアップ → 登録 callback 呼び出し | frrcfgd.py:1529 |
| __fire → bgp_table_handler_common | `BGP_NEIGHBOR_AF` → `bgp_message` キュー積み | frrcfgd.py:3928 |
| bgp_table_handler_common → vtysh | `__update_bgp()` → `nbr_af_key_map` → vtysh サブプロセス | frrcfgd.py:2640-2642 |
