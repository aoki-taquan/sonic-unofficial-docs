# BGP_GLOBALS_AF_AGGREGATE_ADDR テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `BGP_GLOBALS_AF_AGGREGATE_ADDR` テーブル。`frr-mgmt-framework` の `frrcfgd` が `DEVICE_METADATA.frr_mgmt_framework_config = true` 経路で購読する。

## 1. 購読者は単一 — `frrcfgd` のみ (Redis keyspace 通知)

| 購読者 | 対象テーブル | 購読 API | 通信方式 | ハンドラ |
|--------|------------|---------|---------|---------|
| `frrcfgd` (sonic-frr-mgmt-framework) | `BGP_GLOBALS_AF_AGGREGATE_ADDR` | `ExtConfigDBConnector.subscribe(table, hdlr)` + `listen()` | Redis **keyspace 通知** (`PSUBSCRIBE __keyspace@<dbId>__:*`) | `bgp_table_handler_common` |

- bgpcfgd テンプレ経路 (`bgpd.conf.db.addr_family.j2`) は別テーブル `BGP_AGGREGATE_ADDRESS` を使用し、本テーブルは購読しない (Phase F `side-effects` で確認済み)。
- `orchagent` / `syncd` 等の APPL_DB / ASIC_DB レイヤは本テーブルを読まない (FRR `bgpd` のソフト処理で完結)。
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
# frrcfgd.py:2293-2317 抜粋
self.table_handler_list = [
    ('VRF', self.vrf_handler),
    ('DEVICE_METADATA', self.metadata_handler),
    ('BGP_GLOBALS', self.bgp_global_handler),
    ('BGP_GLOBALS_AF', self.bgp_af_handler),
    ...
    ('BGP_GLOBALS_AF_AGGREGATE_ADDR', self.bgp_table_handler_common),
    ('BGP_GLOBALS_AF_NETWORK',        self.bgp_table_handler_common),
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

- `BGP_GLOBALS_AF_AGGREGATE_ADDR` を購読するハンドラは `bgp_table_handler_common` (`frrcfgd.py:2317`)。
- 起動時スナップショット: `subscribe_all()` 開始前に `config_db.get_table_data([...])` で `table_handler_list` 全テーブルを一括取得 (`frrcfgd.py:2340`)、`config_mode == "unified"` であれば各エントリを `bgp_message` キューへ流して `__update_bgp()` で config replay (`frrcfgd.py:2344-2357`)。
- daemon バインド: `BGP_GLOBALS_AF_AGGREGATE_ADDR` は `['bgpd']` のみへ送信 (`frrcfgd.py:98`)。

## 4. キー単位ディスパッチ

`bgp_table_handler_common(table, key, data)` 3 引数を受ける (`ConfigDBConnector` 標準動作)。

- `key`: `BGP_GLOBALS_AF_AGGREGATE_ADDR|<vrf>|<afi_safi>|<ip_prefix>` の右辺 (vrf 抽出後、残り `<afi_safi>|<ip_prefix>` がハンドラ内で `split('|')` される。`frrcfgd.py:3170`)。
- `op`: `data is None` で DEL、それ以外で SET と判別。Redis 操作種別 (`HSET` / `HDEL`) 自体は区別しない。
- `data`: `{as_set, summary_only, policy}` を含む dict (keyspace 通知後に HGETALL で再取得した結果)。

FRR コマンド生成は `af_aggregate_key_map = [(..., '{no:no-prefix}aggregate-address {2} {3:aggr-as-set} {4:aggr-summary-only} {5:aggr-policy}', hdl_af_aggregate)]` (`frrcfgd.py:1982-1983`) と `hdl_af_aggregate` (`frrcfgd.py:1313-`) が担当。

## 5. keyspace 通知 → ハンドラ呼び出しの流れ

```
sonic-db-cli CONFIG_DB hset 'BGP_GLOBALS_AF_AGGREGATE_ADDR|default|ipv4_unicast|10.0.0.0/8' summary_only true
  ↓ Redis 側で keyspace 通知発火
Redis keyspace PUBLISH "__keyspace@4__:BGP_GLOBALS_AF_AGGREGATE_ADDR|default|ipv4_unicast|10.0.0.0/8" "hset"
  ↓ ExtConfigDBConnector.listen_thread() (frrcfgd.py:1536-1545) が PSUBSCRIBE パターンで受信
sub_msg_handler() (frrcfgd.py:1521-1534)
  ↓ key を table / row に分割: table="BGP_GLOBALS_AF_AGGREGATE_ADDR", row="default|ipv4_unicast|10.0.0.0/8"
  ↓ client.hgetall(key) で値再取得 → {as_set: "false", summary_only: "true", policy: ""}
  ↓ raw_to_typed() で型変換 (list 型 leaf は sort 後 set/list 化)
_ConfigDBConnector__fire("BGP_GLOBALS_AF_AGGREGATE_ADDR", "default|ipv4_unicast|10.0.0.0/8", data)
  ↓ bgp_table_handler_common → bgp_message キューへ enqueue
__update_bgp(upd_data_list) で順次処理 (frrcfgd.py:3169-3196)
  ↓ key を vrf / af_type / ip_prefix に分解、normalize_ip_prefix() で正規化
  ↓ cmd_prefix = ['configure terminal', 'router bgp <asn> vrf <vrf>', 'address-family <af> <ip_type>']
  ↓ vtysh -c "aggregate-address 10.0.0.0/8 summary-only"  (frrcfgd.py:1982-1983 + run_command)
  ↓ AggregateAddr() を self.af_aggr_list[vrf][prefix] にキャッシュ (frrcfgd.py:3189-3193)
```

DEL (`data is None`) では `self.af_aggr_list[vrf].pop(norm_ip_prefix, None)` でキャッシュから除去 (`frrcfgd.py:3194-3196`)。

## 6. サービス再起動トリガー

| 契機 | 操作 | コード |
|------|------|--------|
| `BGP_GLOBALS_AF_AGGREGATE_ADDR` 変更 | FRR `bgpd` へ vtysh `(no )aggregate-address <prefix> [as-set] [summary-only] [route-map <name>]` を送出のみ。プロセス restart なし | `frrcfgd.py:3169-3196`, `1982-1983` |
| `BGP_GLOBALS` (bgp_asn) 未設定 | 上位 `__update_bgp` で local_asn 未解決 → 当該 update は依存待ちで保留 (キューに残置) | `frrcfgd.py:__update_bgp` 上層 |
| IP prefix 形式不正 | `MatchPrefix.normalize_ip_prefix()` → `None` で syslog ERR、continue | `frrcfgd.py:3172-3175` |

vtysh コマンド送出のみで `bgpd` プロセス自体は再起動されない。既存 BGP セッションへの集約反映は **FRR の RIB 計算ループ** の次サイクルで反映される (RIB に contributing route が 1 本以上ある場合のみ aggregate が広告される; BGP 仕様)。

## 7. 並列性・ロック

- `ExtConfigDBConnector.listen_thread()` は専用スレッド (`frrcfgd.py:1551`)。`table_handler_list` 全ハンドラは同一スレッドで逐次実行され、内部キュー `self.bgp_message` 経由で `__update_bgp` に直列化される。
- ロックは持たず、Redis 側のシリアル化 (単一 client 接続) と Python シングルスレッド実行に依存。
- bgpcfgd 側に並走経路はない (本テーブルは `BGP_AGGREGATE_ADDRESS` とは別経路)。

## 8. 他プロセスからの購読有無

`BGP_GLOBALS_AF_AGGREGATE_ADDR` を購読する SONiC プロセスは **`frrcfgd` のみ**。Phase F `side-effects` で確認済 (`bgpcfgd/` / `dockers/docker-fpm-frr/` を grep して 0 ヒット)。orchagent/syncd は本テーブルを読まず、FRR `bgpd` のソフト処理経路で完結する。

## 9. Evidence サマリ

- `frrcfgd.py:98` `'BGP_GLOBALS_AF_AGGREGATE_ADDR': ['bgpd']`
- `frrcfgd.py:1313-` `hdl_af_aggregate`
- `frrcfgd.py:1506-1555` `ExtConfigDBConnector` (keyspace listen 実装)
- `frrcfgd.py:1982-1983` `af_aggregate_key_map` (FRR コマンドテンプレ + `hdl_af_aggregate` 連結)
- `frrcfgd.py:2118` `'BGP_GLOBALS_AF_AGGREGATE_ADDR': af_aggregate_key_map`
- `frrcfgd.py:2257-` 起動時 `get_table('BGP_GLOBALS_AF_AGGREGATE_ADDR')` スナップショット
- `frrcfgd.py:2317` `table_handler_list` 登録 (`bgp_table_handler_common`)
- `frrcfgd.py:2340-2357` config replay (`config_mode=="unified"`)
- `frrcfgd.py:2359-2361` `subscribe_all`
- `frrcfgd.py:3169-3196` `BGP_GLOBALS_AF_AGGREGATE_ADDR` 分岐 (vtysh コマンド送出 + `af_aggr_list` キャッシュ更新)
- `frrcfgd.py:3955-3956` `subscribe_all()` → `listen()` 起動順
