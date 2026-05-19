# NEIGH — Pub/Sub 調査メモ (Phase G)

## 調査対象

- `sonic-swss/cfgmgr/nbrmgrd.cpp`
- `sonic-swss/cfgmgr/nbrmgr.cpp`
- `sonic-swss/cfgmgr/nbrmgr.h`

## CONFIG_DB NEIGH の購読方式

### nbrmgrd — ConsumerStateTable で購読

`nbrmgrd.cpp:32-34`:

```cpp
vector<string> cfg_nbr_tables = {
    CFG_NEIGH_TABLE_NAME,
};
NbrMgr nbrmgr(&cfgDb, &appDb, &stateDb, cfg_nbr_tables);
```

`NbrMgr` は `Orch(cfgDb, tableNames)` で継承元 `Orch` コンストラクタに渡し、
`ConsumerStateTable(cfgDb, CFG_NEIGH_TABLE_NAME)` が swss::Select に登録される。
SET イベントが届くと `doSetNeighTask()` が実行される。

### APP_NEIGH_RESOLVE_TABLE の購読

`nbrmgr.cpp:64-67`:

```cpp
auto consumerStateTable = new swss::ConsumerStateTable(appDb, APP_NEIGH_RESOLVE_TABLE_NAME, ...);
auto consumer = new Consumer(consumerStateTable, this, APP_NEIGH_RESOLVE_TABLE_NAME);
Orch::addExecutor(consumer);
```

nbrmgrd が APPL_DB `NEIGH_RESOLVE_TABLE` も購読する。
外部コントローラ（gNMI / SDN controller）が `NEIGH_RESOLVE_TABLE` に書き込むと nbrmgrd が受け取り Netlink で neighbor 解決をトリガーする。

### VoQ 環境での STATE_SYSTEM_NEIGH_TABLE 購読

`nbrmgr.cpp:78-83`:
VoQ スイッチ (`switch_type == "voq"`) の場合のみ、`STATE_DB:STATE_SYSTEM_NEIGH_TABLE_NAME` を `SubscriberStateTable` で購読する。

## SELECT_TIMEOUT と doTask

`nbrmgrd.cpp:21`: `SELECT_TIMEOUT = 1000` ms。
タイムアウト時は `nbrmgr.doTask()` を呼び出す（pending エントリの再処理）。

## 他コンポーネントの NEIGH 参照

- `orchagent/neighorch.cpp`: APPL_DB `NEIGH_TABLE` を購読。CONFIG_DB `NEIGH` は参照しない
- `minigraph.py`: CONFIG_DB `NEIGH` への書き込み側（購読なし）
