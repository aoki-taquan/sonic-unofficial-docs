# feature-state STATE_DB — Phase G 通信メカニズムスキャンノート

対象ページ: `docs/reference/config-db/feature-state.md`
対象テーブル: `STATE_DB FEATURE|<feature-name>`
Producer: `featured` (`sonic-host-services/scripts/featured`)
スキャン範囲: `FeatureHandler.set_feature_state()` / `FeatureDaemon.subscribe()` / `FeatureDaemon.start()` の全行精読

---

## 書き込み側 — swsscommon.Table による直接 set

`STATE_DB FEATURE` への書き込みは **ProducerStateTable ではなく** `swsscommon.Table.set()` を使用する。
これは `featured` が STATE_DB へ「オペレーション状態の通知」として書き込むデーモン直書き方式であるため。

```python
# featured:620
feature_state_table = Table(self.state_db_conn, FEATURE_TBL)

# FeatureHandler:585-590
def set_feature_state(self, feature, state):
    self._feature_state_table.set(feature.name, [('state', state)])
    # Multi-ASIC: 各名前空間の STATE_DB にも書き込み
    for ns, tbl in self.ns_feature_state_tbl.items():
        tbl.set(feature.name, [('state', state)])
```

`swsscommon.Table.set()` は内部で Redis `HSET` + keyspace notification (`__keyspace@6__:FEATURE|<name>`) を発行する。

### 書き込みメソッド一覧

| 書き込み元 | メソッド | 書き込み内容 |
|-----------|---------|------------|
| `FeatureHandler.set_feature_state()` (featured:585-590) | `Table.set(name, [('state', state)])` | `STATE_DB FEATURE\|<name>` の `state` フィールド |
| Multi-ASIC 名前空間テーブル (featured:589-590) | `tbl.set(name, [('state', state)])` | 各名前空間の `STATE_DB FEATURE\|<name>` |

---

## 読み取り側 — SubscriberStateTable による subscribe ループ

`FeatureDaemon` は **CONFIG_DB** と **APPL_DB** の変更を `SubscriberStateTable` で受信し、STATE_DB へ書き込む。
STATE_DB FEATURE テーブル自体は、`featured` が書き手であり、外部からの subscribe 対象にはならない（`featured` は自分が書いた STATE_DB の変化を再受信しない）。

### 購読テーブル一覧

```python
# FeatureDaemon.register_callbacks() featured:638-648
self.subscribe(self.cfg_db_conn, FEATURE_TBL,           # CONFIG_DB FEATURE
               make_callback(self.feature_handler.handler), HOSTCFGD_MAX_PRI)

self.subscribe(self.appl_db_conn, PORT_TBL,             # APPL_DB PORT_TABLE
               make_callback(self.feature_handler.port_listener), HOSTCFGD_MAX_PRI-1)
```

| DB | DB ID | テーブル | keyspace チャネル | 用途 |
|----|-------|---------|----------------|------|
| CONFIG_DB | 4 | `FEATURE` | `__keyspace@4__:FEATURE\|<name>` | feature の `state` 変更通知を受信 → `set_feature_state()` を呼び出して STATE_DB を更新 |
| APPL_DB | 0 | `PORT_TABLE` | `__keyspace@0__:PORT_TABLE\|*` | delayed feature のポート Ready 検知 → `port_listener()` で delayed feature を有効化 |

### select ループ

```python
# FeatureDaemon.start() featured:655-678
DEFAULT_SELECT_TIMEOUT = 1000  # ms (featured:23)

while True:
    state, selectable_ = self.selector.select(DEFAULT_SELECT_TIMEOUT)
    if state == selector.TIMEOUT:
        if elapsed > PORT_INIT_TIMEOUT_SEC:  # 180秒
            self.feature_handler.handle_port_table_timeout()
        continue
    # OBJECT 受信時: subscriber.pop() でイベント取得 → callback 呼び出し
```

- `TIMEOUT`: 1000 ms ごとに PORT 初期化タイムアウト（180 秒）を確認。タイムアウト超過時は delayed feature を強制 enable
- `OBJECT`: イベント受信時のみ `subscriber.pop()` で `(key, op, fvs)` を取得し、登録済み callback を呼び出す
- `ERROR`: ログ出力のみで継続

---

## 通知連鎖の全体像

```
CONFIG_DB FEATURE|<name> 変更
  → keyspace notification → SubscriberStateTable (featured)
  → FeatureHandler.handler()
  → feature.state 更新
  → set_feature_state() → STATE_DB FEATURE|<name> state=<state>

APPL_DB PORT_TABLE|* 変更 (port ready)
  → keyspace notification → SubscriberStateTable (featured)
  → FeatureHandler.port_listener()
  → delayed feature の enable 判定
  → set_feature_state() → STATE_DB FEATURE|<name> state=enabled
```

---

## STATE_DB FEATURE テーブルの consumer

`featured` が STATE_DB FEATURE に書き込んだ後、以下のプロセスが読み取る:

| consumer | 読み取り方法 | 用途 |
|----------|------------|------|
| `show feature status` (sonic-utilities) | `swsscommon.Table.get()` (on-demand) | feature の現在状態表示 |
| `ctrmgrd.py` | `ConfigDBConnector.subscribe()` (CONFIG_DB の FEATURE を監視、STATE_DB は直接購読せず) | Kubernetes との feature 状態同期 |
| `container_startup.py` | 起動時に `Table.get()` で確認 | コンテナ起動前の状態チェック |

---

## スキャン証跡

`featured` L1-700 全行読了。
検出:
- 書き込み: `Table.set()` via `set_feature_state()` (L585-590) — ProducerStateTable 不使用
- 購読: `SubscriberStateTable` 2 テーブル (CONFIG_DB FEATURE, APPL_DB PORT_TABLE) (L630-648)
- select ループ: `DEFAULT_SELECT_TIMEOUT = 1000 ms` (L23, L656)
- PORT_INIT_TIMEOUT_SEC: 180 秒 (L24)
- Multi-ASIC: 名前空間ごとの STATE_DB FEATURE テーブルに同一内容を書き込み (L589-590)
