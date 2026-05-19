# DEVICE_NEIGHBOR（deviceop-state）— Phase G: Redis 通知メカニズム調査

## 調査方法

1. consumer 一覧: `pfcwd/main.py`, `scripts/ecnconfig`, `show/interfaces/__init__.py`, `lldpmgrd`, `managers_bgp.py`
2. 各 consumer の DB アクセス API を確認（SubscriberStateTable / get_table / subscribe 等）
3. bgpcfgd Runner の SELECT_TIMEOUT 確認

対象ファイル:
- `sonic-utilities/pfcwd/main.py:97-108,405-416`
- `sonic-utilities/scripts/ecnconfig:282-293`
- `sonic-utilities/show/interfaces/__init__.py:310-320`
- `sonic-buildimage/dockers/docker-lldp/lldpmgrd:12-14,74-78`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:139-140,219-224`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py:21,49-52`

---

## 調査結果

### DEVICE_NEIGHBOR への購読方式

DEVICE_NEIGHBOR を consumer が参照する方法は全件「スナップショット（`get_table` / `get_entry` の一回限り読み出し）」のみ。
**`SubscriberStateTable` や `ConfigDBConnector.subscribe()` で DEVICE_NEIGHBOR を継続購読するプロセスは存在しない。**

| consumer | 方式 | API | タイミング |
|---------|------|-----|---------|
| `pfcwd start_default` | スナップショット | `config_db.get_table('DEVICE_NEIGHBOR')` | pfcwd 起動時 1 回のみ |
| `pfcwd get_server_facing_ports` | スナップショット | `db.get_table('DEVICE_NEIGHBOR')` + `db.get_entry('DEVICE_NEIGHBOR_METADATA', ...)` | pfcwd 起動時 1 回のみ |
| `ecnconfig` (非 multi-ASIC) | スナップショット | `self.config_db.get_table(DEVICE_NEIGHBOR_TABLE_NAME)` | ecnconfig 実行時 1 回のみ |
| `show interfaces neighbor expected` | スナップショット | `db.cfgdb_clients[namespace].get_table("DEVICE_NEIGHBOR")` | コマンド実行時 1 回のみ |
| `lldpmgrd` | **購読なし（TODO 状態）** | — | DEVICE_NEIGHBOR を subscribe していない |
| `bgpcfgd` | **購読なし（DEVICE_NEIGHBOR 本体は対象外）** | — | DEVICE_NEIGHBOR_METADATA のみ SubscriberStateTable で購読 |

### lldpmgrd の TODO 状態

`lldpmgrd` のソース (lldpmgrd:12-14) に明示:
```python
# TODO: Also listen for changes in DEVICE_NEIGHBOR and PORT tables in
#       Config DB and update LLDP config upon changes.
```
現時点で DEVICE_NEIGHBOR への subscribe は未実装。

### bgpcfgd は DEVICE_NEIGHBOR_METADATA を購読（DEVICE_NEIGHBOR 本体は対象外）

`bgpcfgd` の `BGPDataBaseMgr` は `CFG_DEVICE_NEIGHBOR_METADATA_TABLE_NAME` を `SubscriberStateTable` で購読するが、DEVICE_NEIGHBOR テーブル本体は購読対象ではない。

```python
# runner.py:49-51
subscriber = swsscommon.SubscriberStateTable(conn, table_name)
self.subscribers.add(subscriber)
self.selector.addSelectable(subscriber)
```

DEVICE_NEIGHBOR の内容（`name` フィールド値）は DEVICE_NEIGHBOR_METADATA 購読イベント内で参照されるが、DEVICE_NEIGHBOR 自体の変化は bgpcfgd に通知されない。

### keyspace 通知の不在

DEVICE_NEIGHBOR は CONFIG_DB に保存される永続テーブルであり TTL なし。
DEVICE_NEIGHBOR への書込み（`HSET`）は Redis keyspace 通知を生成するが、それを受信するプロセスは現行実装では存在しない。

---

## Evidence

- `sonic-utilities` `pfcwd/main.py:97-108,405-416`
- `sonic-utilities` `scripts/ecnconfig:282-293`
- `sonic-utilities` `show/interfaces/__init__.py:310-320`
- `sonic-buildimage` `dockers/docker-lldp/lldpmgrd:12-14`
- `sonic-buildimage` `src/sonic-bgpcfgd/bgpcfgd/runner.py:21,49-52`
- `sonic-buildimage` `src/sonic-bgpcfgd/bgpcfgd/managers_bgp.py:139-140,219-224`
