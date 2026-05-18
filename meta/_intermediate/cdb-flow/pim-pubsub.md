# PIM_GLOBALS / PIM_INTERFACE — Phase G: CONFIG_DB 購読メカニズム調査結果

調査日: 2026-05-18
対象ファイル:
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

---

## 1. 購読デーモン一覧

`PIM_GLOBALS` および `PIM_INTERFACE` を CONFIG_DB から購読するのは `frrcfgd` のみ。
他の swss / orchagent 系デーモン、bgpcfgd からの購読は確認されていない。

```
grep -rn "PIM_GLOBALS\|PIM_INTERFACE" sonic-buildimage/src/ *.py *.cpp
  → 結果: frrcfgd.py のみ
```

---

## 2. frrcfgd の購読メカニズム

### ExtConfigDBConnector + keyspace イベント

`BGPConfigDaemon` は `ExtConfigDBConnector`（`ConfigDBConnector` サブクラス）を使用する。
`listen()` (L1547-1552) が Redis keyspace イベント全体を `psubscribe` し、
`sub_msg_handler` (L1521-1533) がテーブル名でルーティングする。

```python
# frrcfgd.py L1538-1539
sub_key_space = "__keyspace@{}__:*".format(self.get_dbid(self.db_name))
self.pubsub.psubscribe(sub_key_space)
```

CONFIG_DB の任意のキー変更が Redis keyspace イベントとして届き、
`sub_msg_handler` が `key.split(TABLE_NAME_SEPARATOR, 1)` でテーブル名を抽出、
登録済みハンドラ (`self.handlers[table]`) を呼び出す。

### subscribe_all() による PIM テーブル登録

```python
# frrcfgd.py L2331-2332, L2359-2361
('PIM_GLOBALS', self.bgp_table_handler_common),
('PIM_INTERFACE', self.bgp_table_handler_common),
...
def subscribe_all(self):
    for table, hdlr in self.table_handler_list:
        self.config_db.subscribe(table, hdlr)
```

`subscribe_all()` は `daemon.start()` (L3954-3955) で呼ばれる。
`config_db.listen()` (L3956) がバックグラウンドスレッドを起動し、以降のイベントを非同期で受信する。

---

## 3. 処理フロー詳細

```
Redis HSET/HDEL (CONFIG_DB PIM_GLOBALS / PIM_INTERFACE)
  → keyspace イベント "__keyspace@N__:PIM_GLOBALS|<vrf>|<af>"
  → ExtConfigDBConnector.sub_msg_handler()
      → table = 'PIM_GLOBALS' / 'PIM_INTERFACE'
      → client.hgetall(key) → raw_to_typed() → data
      → ConfigDBConnector.__fire(table, row, data)
          → bgp_table_handler_common(table, key, data)
              → bgp_message.put((key, del_table, table, data))
              → __update_bgp(upd_data_list)
                  → __update_bgp() 内部の PIM_GLOBALS / PIM_INTERFACE 分岐
                  → key_map.run_command() → vtysh → pimd
```

---

## 4. pimd デーモンへの最終到達経路

frrcfgd が `vtysh -c "configure terminal" -c "..."` を実行する際、
FRR の `daemon_table_map` (frrcfgd.py L117-120) に基づき対象デーモンが決定される:

```python
'PIM_GLOBALS':  ['pimd'],
'PIM_INTERFACE': ['pimd'],
```

vtysh はソケット経由で `pimd` に設定コマンドを転送する。
frrcfgd 自身は pimd の内部状態を直接購読しない（単方向: CONFIG_DB → pimd）。

---

## 5. 初期設定 replay

frrcfgd 起動時（L2340-2358）、`config_mode == "unified"` の場合に
全購読テーブルの初期エントリを `config_db.get_table()` で一括取得し、
`bgp_message.put()` でキューに積む。これにより再起動後も CONFIG_DB の状態が
pimd に再注入される（replay）。

```python
# frrcfgd.py L2344-2352
if self.config_mode == "unified":
    for table, _ in self.table_handler_list:
        table_list = self.config_db.get_table(table)
        for key, data in table_list.items():
            upd_data = {...}
            self.bgp_message.put(...)
```

---

## 6. 購読まとめ

| 観点 | 内容 |
|------|------|
| 購読デーモン | `frrcfgd` のみ (swss orchagent / bgpcfgd は購読しない) |
| 購読方式 | Redis keyspace イベント (`psubscribe "__keyspace@N__:*"`) |
| 購読登録 | `subscribe_all()` → `config_db.subscribe(table, handler)` |
| イベント処理 | `bgp_table_handler_common` → `bgp_message` queue → `__update_bgp()` |
| 最終到達 | vtysh → pimd (単方向) |
| 初期 replay | 起動時 `get_table()` → queue 投入 (unified config mode のみ) |
| STATE_DB 連携 | なし（pimd から CONFIG_DB への逆方向書き込みなし） |
