# BREAKOUT_CFG — Redis 通知メカニズム調査 (Phase G)

## 調査対象

- `sonic-swss/cfgmgr/portmgrd.cpp`
- `sonic-swss/cfgmgr/portmgr.cpp`
- `sonic-utilities/config/main.py`
- `sonic-utilities/config/config_mgmt.py`

## BREAKOUT_CFG テーブル自体の購読状況

`BREAKOUT_CFG` テーブルを `SubscriberStateTable` / keyspace notification で購読するデーモンは **存在しない**。

grep 結果 (`grep -rn "BREAKOUT_CFG" sonic-swss sonic-buildimage sonic-utilities`) で、
`config/main.py` および `show/interfaces/__init__.py` の `get_table('BREAKOUT_CFG')` のみヒット。
これらはいずれも CLI の **点時間ポーリング**（`ConfigDBConnector.get_table()`）であり、
Redis pub/sub ではない。

## CONFIG_DB → portmgrd の通知フロー

`portmgrd` は以下のテーブルを `ConsumerStateTable`（＝ Redis keyspace notification）で購読する:

| テーブル | DB | 購読メカニズム |
|---------|-----|--------------|
| `PORT`（CFG_PORT_TABLE_NAME） | CONFIG_DB (DB 4) | `Orch` フレームワークの `Consumer`（`SubscriberStateTable`） |
| `SEND_TO_INGRESS_PORT_TABLE` | CONFIG_DB | 同上 |

実装: `portmgrd.cpp:27-29`, `portmgr.cpp:14-22`。

`Orch` フレームワークは内部で `__keyspace@4__:PORT|*` パターンの PSUBSCRIBE を行う。

## portmgrd の select タイムアウト

`portmgrd.cpp:16, 50`:
```cpp
#define SELECT_TIMEOUT 1000   // 1000 ms
ret = s.select(&sel, SELECT_TIMEOUT);
```

タイムアウト時は `portmgr.doTask()` を呼び出してキュー内の保留タスクを再試行する。

## CONFIG_DB 書込み → APPL_DB 伝播

DPB シーケンスで `PORT` テーブルが変更されると、`portmgrd` がそれを受け取り `APPL_DB PORT_TABLE` に伝播する:

| CONFIG_DB 操作 | portmgrd の動作 | APPL_DB 結果 |
|--------------|----------------|-------------|
| `PORT|<port>` SET | `writeConfigToAppDb()` → `m_appPortTable.set()` | `PORT_TABLE|<port>` 更新 |
| `PORT|<port>` DEL | `m_appPortTable.del(alias)` | `PORT_TABLE|<port>` 削除 |

実装: `portmgr.cpp:213,244`。

## BREAKOUT_CFG の更新通知

`main.py:5554`:
```python
config_db.set_entry("BREAKOUT_CFG", interface_name, {'brkout_mode': target_brkout_mode})
```

`ConfigDBConnector.set_entry()` は Redis `HSET` + keyspace notification を生成するが、
これを購読するデーモンは存在しない。`BREAKOUT_CFG` の変更は他サービスに通知されない。

## 結論

- `BREAKOUT_CFG` テーブル自体は pub/sub の対象外（購読ゼロ）
- DPB フローの通知の核心は `PORT` テーブルの変更であり、`portmgrd` が `ConsumerStateTable`
  経由で受け取り `APPL_DB PORT_TABLE` へ伝播する
- `portmgrd` の select タイムアウトは 1000 ms（定数 `SELECT_TIMEOUT`）
- `BREAKOUT_CFG` への書込み後に他デーモンへの即時通知手段はなく、CLI が次回読み直す際に最新値を取得する
