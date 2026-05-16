# BGP_GLOBALS_AF テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `BGP_GLOBALS_AF` テーブル。`frr-mgmt-framework` の `frrcfgd` が `ExtConfigDBConnector.subscribe()` + Redis keyspace 通知方式で購読する。

## 1. 購読者は単一 — `frrcfgd` のみ (Redis keyspace 通知)

| 購読者 | 対象テーブル | 購読 API | 通信方式 | ハンドラ |
|--------|------------|---------|---------|---------|
| `frrcfgd` (sonic-frr-mgmt-framework) | `BGP_GLOBALS_AF` | `ExtConfigDBConnector.subscribe(table, hdlr)` + `listen()` | Redis **keyspace 通知** (`PSUBSCRIBE __keyspace@<dbId>__:*`) | `bgp_af_handler` |

- `bgpcfgd` は `BGP_GLOBALS_AF` を購読しない (`bgpcfgd/` 配下に参照なし)。
- `orchagent` / `syncd` 等の APPL_DB / ASIC_DB レイヤは本テーブルを読まない (FRR `bgpd` のソフト処理経路で完結)。
- CONFIG_DB は永続前提で TTL は設定されない。

## 2. `ExtConfigDBConnector` の実装 (keyspace 通知)

`frrcfgd` は `swsscommon.ConfigDBConnector` を継承した独自クラス `ExtConfigDBConnector` を使う (`frrcfgd.py:1506-1555`)。

```python
# frrcfgd.py:1536-1552 (抜粋)
def listen_thread(self, timeout):
    self.__listen_thread_running = True
    sub_key_space = "__keyspace@{}__:*".format(self.get_dbid(self.db_name))
    self.pubsub.psubscribe(sub_key_space)
    while self.__listen_thread_running:
        msg = self.pubsub.get_message(timeout, True)
        if msg:
            self.sub_msg_handler(msg)
    self.pubsub.punsubscribe(sub_key_space)

def listen(self):
    self.pubsub = self.get_redis_client(self.db_name).pubsub()
    self.sub_thread = threading.Thread(target=self.listen_thread, args=(10,))
    self.sub_thread.start()
```

- 通知ペイロード本体は操作名 (`hset` / `del` 等) のみ。値は `client.hgetall(key)` で再取得する (`frrcfgd.py:1527-1528`)。
- `sub_msg_handler` でテーブル名と key を分離し、`raw_to_typed()` で list 型 leaf-list を Python list 化したあと、`_ConfigDBConnector__fire(table, row, data)` でテーブル毎ハンドラへディスパッチ (`frrcfgd.py:1521-1534`)。
- `SubscriberStateTable` (channel ベース PUBLISH/SUBSCRIBE) は使用しない。

## 3. テーブル登録と起動シーケンス

```python
# frrcfgd.py:2293-2297 抜粋
self.table_handler_list = [
    ('VRF', self.vrf_handler),
    ('DEVICE_METADATA', self.metadata_handler),
    ('BGP_GLOBALS', self.bgp_global_handler),
    ('BGP_GLOBALS_AF', self.bgp_af_handler),   # ← 4 番目に登録
    ...
]

# frrcfgd.py:2359-2361
def subscribe_all(self):
    for table, hdlr in self.table_handler_list:
        self.config_db.subscribe(table, hdlr)

# frrcfgd.py:3955-3956
self.subscribe_all()
self.config_db.listen()
```

- `BGP_GLOBALS_AF` を購読するハンドラは `bgp_af_handler` (`frrcfgd.py:2297`)。
- 起動時スナップショット: `subscribe_all()` 開始前に `config_db.get_table_data([...])` で `table_handler_list` 全テーブルを一括取得 (`frrcfgd.py:2340`)、`config_mode == "unified"` であれば各エントリを `bgp_message` キューへ流して `__update_bgp()` で config replay (`frrcfgd.py:2344-2357`)。
- daemon バインド: `BGP_GLOBALS_AF` は `['bgpd']` のみへ送信 (`frrcfgd.py:82`)。

## 4. キー単位ディスパッチ

`bgp_af_handler(table, key, data)` 3 引数を受ける (`ConfigDBConnector` 標準動作)。

- `key`: `BGP_GLOBALS_AF|<vrf>|<afi_safi>` の右辺 (`<vrf>|<afi_safi>`)。
- `op`: `data is None` で DEL (`del_table=True`)、それ以外で SET と判別。
- `data`: `{max_ebgp_paths, max_ibgp_paths, import_vrf, ...}` を含む dict。

FRR コマンド生成は `global_af_key_map` (`frrcfgd.py:2107`) と `bgp_af_handler()` 内の `comb_attr_list` (`frrcfgd.py:3938-3941`) が担当。

## 5. keyspace 通知 → ハンドラ呼び出しの流れ

```
sonic-db-cli CONFIG_DB hset 'BGP_GLOBALS_AF|default|ipv4_unicast' max_ebgp_paths 8
  ↓ Redis 側で keyspace 通知発火
Redis keyspace PUBLISH "__keyspace@4__:BGP_GLOBALS_AF|default|ipv4_unicast" "hset"
  ↓ ExtConfigDBConnector.listen_thread() (frrcfgd.py:1536-1545) が PSUBSCRIBE パターンで受信
sub_msg_handler() (frrcfgd.py:1521-1534)
  ↓ key を table / row に分割: table="BGP_GLOBALS_AF", row="default|ipv4_unicast"
  ↓ client.hgetall(key) で値再取得 → {max_ebgp_paths: "8", ...}
  ↓ raw_to_typed() で型変換
_ConfigDBConnector__fire("BGP_GLOBALS_AF", "default|ipv4_unicast", data)
  ↓ bgp_af_handler → bgp_message キューへ enqueue
__update_bgp(upd_data_list) で順次処理 (frrcfgd.py:2771-2780)
  ↓ tmp_cache_key = 'BGP_GLOBALS_AF&&default|ipv4_unicast'
  ↓ cmd_prefix = ['configure terminal', 'router bgp <asn>', 'address-family ipv4 unicast']
  ↓ vtysh -c "maximum-paths 8"  など (global_af_key_map テンプレ)
```

DEL (`data is None`) では `del_table=True` が設定され AF 設定全体を FRR から削除 (`frrcfgd.py:3918`)。

## 6. サービス再起動トリガー

| 契機 | 操作 | コード |
|------|------|--------|
| `BGP_GLOBALS_AF` 変更 | FRR `bgpd` へ vtysh コマンドを送出のみ。プロセス restart なし | `frrcfgd.py:2771-2780` |
| `BGP_GLOBALS.local_asn` 未設定 VRF | 当該 update を LOG_DEBUG して skip (`continue`) | `frrcfgd.py:2660` |
| vtysh コマンド失敗 | `failed running BGP global AF config command` を LOG_ERR → continue (drop) | `frrcfgd.py:2780` |

vtysh コマンド送出のみで `bgpd` プロセス自体は再起動されない。

## 7. 並列性・ロック

- `ExtConfigDBConnector.listen_thread()` は専用スレッド (`frrcfgd.py:1551`)。`table_handler_list` 全ハンドラは同一スレッドで逐次実行され、内部キュー `self.bgp_message` 経由で `__update_bgp` に直列化される。
- ロックは持たず、Redis 側のシリアル化 (単一 client 接続) と Python シングルスレッド実行に依存。

## 8. 他プロセスからの購読有無

`BGP_GLOBALS_AF` を購読する SONiC プロセスは **`frrcfgd` のみ**。`bgpcfgd/` 配下および `orchagent` / `syncd` には本テーブルの参照なし。FRR `bgpd` のソフト処理経路で完結する。

## 9. Evidence サマリ

- `frrcfgd.py:82` `'BGP_GLOBALS_AF': ['bgpd']`
- `frrcfgd.py:1506-1555` `ExtConfigDBConnector` (keyspace listen 実装)
- `frrcfgd.py:2107` `'BGP_GLOBALS_AF': global_af_key_map`
- `frrcfgd.py:2297` `table_handler_list` 登録 (`bgp_af_handler`)
- `frrcfgd.py:2340-2357` config replay (`config_mode=="unified"`)
- `frrcfgd.py:2359-2361` `subscribe_all`
- `frrcfgd.py:2771-2780` `BGP_GLOBALS_AF` 分岐 (vtysh コマンド送出)
- `frrcfgd.py:3918` `del_table=True` (DEL パス)
- `frrcfgd.py:3938-3941` `comb_attr_list` (distance / dampening 組み合わせ制約)
- `frrcfgd.py:3955-3956` `subscribe_all()` → `listen()` 起動順
