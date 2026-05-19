# MUX_CABLE (per-port) — 通信メカニズム (Phase G) 解析メモ

対象: CONFIG_DB `MUX_CABLE|<ifname>`

ソース確認:
- `sonic-swss/orchagent/muxorch.cpp` / `orchdaemon.cpp`
- `sonic-swss/orchagent/orch.cpp` (Orch::addConsumer)
- `sonic-linkmgrd/src/DbInterface.cpp`
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_table_helper.py`
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable.py`

## 1. orchagent (MuxOrch) — SubscriberStateTable 経由

`MuxOrch` は `Orch2(db, tables, request_)` 基底コンストラクタを経由して購読を登録する
(`muxorch.cpp:2184`)。`tables` には `{CFG_MUX_CABLE_TABLE_NAME, CFG_PEER_SWITCH_TABLE_NAME}` が渡される
(`orchdaemon.cpp:467-471`)。

`Orch::addConsumer()` (`orch.cpp:1186-1195`) は DB の dbId を見て分岐する:

```cpp
// orch.cpp:1186-1195
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
    {
        addExecutor(new Consumer(new SubscriberStateTable(
            db, tableName, TableConsumable::DEFAULT_POP_BATCH_SIZE, pri), this, tableName));
    }
    else
    {
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, pri), this, tableName));
    }
}
```

CONFIG_DB (`dbId=4`) なので `SubscriberStateTable` が採用される。
Redis の keyspace 通知 (`__keyspace@4__:MUX_CABLE:*` の PSUBSCRIBE) でエントリ変化を検知し、
`Consumer::execute()` → `MuxOrch::doTask(Consumer&)` → `handler_map_[CFG_MUX_CABLE_TABLE_NAME]`
= `MuxOrch::handleMuxCfg()` へディスパッチされる。

| 項目 | 値 |
|------|-----|
| 購読クラス | `SubscriberStateTable` (CONFIG_DB 分岐) |
| keyspace パターン | `__keyspace@4__:MUX_CABLE:*` (CONFIG_DB dbId=4) |
| key 区切り | `MUX_CABLE|<ifname>` (TableNameSeparator `|`) |
| POP_BATCH_SIZE | `DEFAULT_POP_BATCH_SIZE` = **128** (`sonic-swss-common/common/table.h:164`) |
| 優先度 (`pri`) | 0 (既定) |
| 起動時スナップショット | `SubscriberStateTable` が既存エントリを SET イベントとして再配信 |
| ディスパッチ先 | `MuxOrch::handleMuxCfg()` (handler_map_ 登録: `muxorch.cpp:2189`) |

## 2. linkmgrd — swss::Select + SubscriberStateTable

linkmgrd の `DbInterface::pollSwssNotification()` (`DbInterface.cpp:1820`) がメインループで
`swss::Select` + 複数の `SubscriberStateTable` を管理する。

CONFIG_DB `MUX_CABLE` テーブルの購読:

```cpp
// DbInterface.cpp:1823
swss::SubscriberStateTable configDbMuxTable(configDbPtr.get(), CFG_MUX_CABLE_TABLE_NAME);
...
swssSelect.addSelectable(&configDbMuxTable);
```

イベントループ内の処理:

```cpp
// DbInterface.cpp:1889-1891
} else if (selectable == static_cast<swss::Selectable *> (&configDbMuxTable)) {
    handleMuxPortConfigNotifiction(configDbMuxTable);
}
```

`handleMuxPortConfigNotifiction()` (`DbInterface.cpp:1107`) が `configMuxTable.pops(entries)` で
バッチ取得し、`processMuxPortConfigNotifiction(entries)` へ渡す。

| 項目 | 値 |
|------|-----|
| 購読クラス | `swss::SubscriberStateTable` |
| DB | CONFIG_DB |
| テーブル | `CFG_MUX_CABLE_TABLE_NAME` |
| タイムアウト | `DEFAULT_TIMEOUT_MSEC` = **1000 ms** (`DbInterface.cpp:48`) |
| バッチ取得 | `configMuxTable.pops(entries)` — 1 回の `select()` wake で全エントリを pop |
| ディスパッチ先 | `DbInterface::processMuxPortConfigNotifiction()` |

## 3. ycabled — swss::Table (ポーリング) + SubscriberStateTable (transceiver)

ycabled は `MUX_CABLE` テーブルを `swss::Table` (`port_tbl`) として直読みする。
`SubscriberStateTable` 経由の subscribe は**使わない**:

```python
# y_cable_table_helper.py:90
self.port_tbl[asic_id] = swsscommon.Table(self.config_db[asic_id], "MUX_CABLE")
```

起動時に `port_tbl[asic_id].getKeys()` で全ポートリストを取得し、
`check_mux_cable_port_type()` でポートごとの `cable_type` / `state` / `soc_ipv4` を読む。

ランタイム更新トリガーは `swsscommon.SubscriberStateTable(state_db, TRANSCEIVER_INFO_TABLE)`
(`y_cable_table_helper.py:87-88`) — トランシーバー情報変化を契機として `MUX_CABLE` の再読みが走る。

つまり ycabled は MUX_CABLE 変化を直接購読せず、トランシーバーイベント駆動で間接的に再読みする設計。

## 4. 通信フロー全体図

```
CONFIG_DB MUX_CABLE|<ifname>  (SET/DEL)
  ├─ [orchagent] MuxOrch
  │    SubscriberStateTable(__keyspace@4__:MUX_CABLE:*)
  │    → Consumer::execute()
  │    → MuxOrch::doTask()
  │    → handler_map_[CFG_MUX_CABLE_TABLE_NAME] = handleMuxCfg()
  │         → SAI nexthop 設定 / STATE_DB MUX_CABLE_TABLE 書込
  │
  ├─ [linkmgrd] DbInterface::pollSwssNotification()
  │    SubscriberStateTable(CONFIG_DB, CFG_MUX_CABLE_TABLE_NAME)
  │    → swss::Select::select() (タイムアウト 1000 ms)
  │    → handleMuxPortConfigNotifiction()
  │    → processMuxPortConfigNotifiction()
  │         → ステートマシン更新 / APPL_DB MUX_CABLE_TABLE 書込
  │
  └─ [ycabled] 直接購読なし
       swsscommon.Table(config_db, "MUX_CABLE") — 起動時 + TRANSCEIVER_INFO イベント駆動で再読み
```
