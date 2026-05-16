# BMP テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `BMP` テーブル。
ソース: `sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py`、`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`。

## 1. 購読 API — `ConfigDBConnector.subscribe()` + `listen()`

`bmpcfgd` は `swsscommon` の Python ラッパ `ConfigDBConnector` の `subscribe(table, callback)` でハンドラを登録し、`listen(init_data_handler=...)` でループを開始する。

```python
# sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py:86-89
def register_callbacks(self):
    self.config_db.subscribe(BMP_TABLE,           # "BMP"
                             lambda table, key, data:
                                 self.bmp_handler(key, data))
    self.config_db.listen(init_data_handler=self.bmpcfg.load)
```

- `BMP_TABLE = "BMP"` のみを購読する（単一テーブル）。
- `ConfigDBConnector.listen()` が内部で Redis の **keyspace 通知** (`__keyspace@<dbId>__:BMP|*` の PSUBSCRIBE) を購読し、テーブル名にマッチしたコールバックへディスパッチする。
- channel ベースの `PUBLISH/SUBSCRIBE`（`ConsumerStateTable` 形式）は使用していない。
  CONFIG_DB は writer（`config bmp` CLI / sonic-cfggen）が `HSET` するのみで明示的な `PUBLISH` を行わず、Redis 側の keyspace notification が変更を通知する。

## 2. 起動時スナップショット (`init_data_handler`)

`listen(init_data_handler=self.bmpcfg.load)` を渡すことで、Subscribe ループ開始前に **CONFIG_DB の現在値を一括取得**して `BMPCfg.load(data)` に渡す。

```python
# bmpcfgd.py:39-49
def load(self, data={}):
    common_config = data.get('table', {})
    self.bgp_neighbor_table = is_true(common_config.get('bgp_neighbor_table', 'false'))
    self.bgp_rib_in_table   = is_true(common_config.get('bgp_rib_in_table',   'false'))
    self.bgp_rib_out_table  = is_true(common_config.get('bgp_rib_out_table',  'false'))
    self.stop_bmp()
    self.reset_bmp_table()
    self.start_bmp()
```

これにより bmpcfgd 再起動時にも既存設定が openbmpd へ即座に反映される。

## 3. キー変化時のディスパッチ

keyspace 通知を受けると `bmp_handler()` が呼ばれる。

```python
# bmpcfgd.py:81-83
def bmp_handler(self, key, data):
    data = self.config_db.get_table(BMP_TABLE)   # 再 HGETALL
    self.bmpcfg.cfg_handler(data)
```

- keyspace 通知本体には値は含まれない（Redis 仕様）。`bmp_handler` は通知を受けたら即座に `get_table("BMP")` で **再 HGETALL** して最新値を取得する。
- `cfg_handler` は `load()` を呼び直すだけのラッパ。フィールドの差分判定はせず、**常に stop → reset → start** を実行する。

## 4. `reset_bmp_table` の起動経路まとめ

`reset_bmp_table()` は以下の 2 経路で呼ばれる（いずれも `load()` 内）。

| 起動経路 | トリガー | コード |
|---------|---------|--------|
| 起動時スナップショット | bmpcfgd プロセス起動 → `listen(init_data_handler=self.bmpcfg.load)` | `bmpcfgd.py:89` |
| 差分通知 | `BMP` テーブル内任意フィールドの `HSET` / `DEL` → `bmp_handler` → `cfg_handler` → `load` | `bmpcfgd.py:81-83, 52-53` |

どちらの場合も `stop_bmp()` → `reset_bmp_table()` → `start_bmp()` の順序は変わらない。

## 5. keyspace 通知パターン

| Redis 通知 | bmpcfgd 受信 |
|-----------|-------------|
| `__keyspace@4__:BMP\|table` `hset` | `bmp_handler("table", {…})` → `load()` 実行 |
| `__keyspace@4__:BMP\|table` `del`  | `bmp_handler("table", {})` → `load({})` → 全フィールド `false` で openbmpd 再起動 |

dbId は CONFIG_DB の通常 4（`database_config.json` 既定）。

## 6. frrcfgd の keyspace 実装（参考）

`frrcfgd` は独自の `ExtConfigDBConnector` に keyspace 購読ロジックを実装している。BMP テーブルを直接購読はしないが、keyspace 通知の実装参照として記録する。

```python
# frrcfgd.py:1536-1545  ExtConfigDBConnector.listen_thread()
sub_key_space = "__keyspace@{}__:*".format(self.get_dbid(self.db_name))
self.pubsub.psubscribe(sub_key_space)
while self.__listen_thread_running:
    msg = self.pubsub.get_message(timeout, True)
    if msg:
        self.sub_msg_handler(msg)
self.pubsub.punsubscribe(sub_key_space)
```

- `sub_msg_handler` が `channel` から `TABLE|row` を分解し、登録済みハンドラへディスパッチ（`bmpcfgd` の `swsscommon.ConfigDBConnector` と同様のパターン）。

## 7. ConsumerStateTable / NotificationProducer 非使用の確認

- `BMP` テーブルは `swsscommon.ConsumerStateTable`（channel ベース）の購読者なし。
- `NotificationProducer` で BMP 関連の通知を出す箇所は SONiC ソース内になし。
- 結論: BMP は **CONFIG_DB → bmpcfgd（keyspace 通知） → supervisorctl stop/start openbmpd + BMP_STATE_DB クリア** の一方向で完結し、APPL_DB/STATE_DB の中継・通知パスを持たない。

## 8. 参考行番号

- `sonic-buildimage/src/sonic-bmpcfgd/bmpcfgd/bmpcfgd.py`
  - 16: `from swsscommon.swsscommon import ConfigDBConnector, DBConnector, Table`
  - 27-28: `is_true(val)` — `str(val).lower() == 'true'`
  - 39-49: `BMPCfg.load()` — フィールド読み込み + stop/reset/start
  - 52-53: `BMPCfg.cfg_handler()` — `load()` ラッパ
  - 61-65: `BMPCfg.reset_bmp_table()` — BMP_STATE_DB のパターン削除
  - 75-78: `BMPCfgDaemon.__init__()` — `ConfigDBConnector.connect(retry_on=True)`
  - 81-83: `BMPCfgDaemon.bmp_handler()` — 再 HGETALL + cfg_handler 呼び出し
  - 85-89: `BMPCfgDaemon.register_callbacks()` — subscribe + listen
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
  - 1506-1555: `ExtConfigDBConnector` — keyspace 購読の独自実装
  - 1536-1545: `listen_thread()` — `psubscribe("__keyspace@N__:*")` + `sub_msg_handler`
