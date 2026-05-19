# MCLAG_INTERFACE — 通信メカニズム調査 (Phase G)

## 調査対象

- `sonic-swss/mclagsyncd/mclagsyncd.cpp`
- `sonic-swss/mclagsyncd/mclaglink.cpp`
- `sonic-swss/mclagsyncd/mclaglink.h`
- `sonic-swss/orchagent/mlagorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## mclagsyncd による MCLAG_INTERFACE 購読

### SubscriberStateTable の遅延生成

mclagsyncd は起動時に `MCLAG_DOMAIN`（`CFG_MCLAG_TABLE_NAME`）のみを
`SubscriberStateTable` として生成・選択に追加する（`mclagsyncd.cpp:41`）。

`MCLAG_INTERFACE`（`CFG_MCLAG_INTF_TABLE_NAME`）の `SubscriberStateTable` は
**MCLAG_DOMAIN の初回 SET が成功した後**に `addDomainCfgDependentSelectables()` で
動的に生成される（`mclaglink.cpp:910-941`）。

```cpp
// mclaglink.cpp:910-921
void MclagLink::addDomainCfgDependentSelectables() {
    p_state_fdb_tbl = new SubscriberStateTable(p_state_db.get(), STATE_FDB_TABLE_NAME);
    p_state_vlan_mbr_subscriber_table = new SubscriberStateTable(p_state_db.get(), STATE_VLAN_MEMBER_TABLE_NAME);
    p_mclag_intf_cfg_tbl = new SubscriberStateTable(p_config_db.get(), CFG_MCLAG_INTF_TABLE_NAME);
    p_mclag_unique_ip_cfg_tbl = new SubscriberStateTable(p_config_db.get(), CFG_MCLAG_UNIQUE_IP_TABLE_NAME);
    ...
    m_select->addSelectable(p_mclag_intf_cfg_tbl);
    SWSS_LOG_NOTICE("MCLagSYNCD Adding mclag_intf_cfg_tbl to selectable");
}
```

トリガー条件: `processMclagDomainCfg()` において op == "SET" で
`entryExists == false`（初回 ADD）のときのみ `add_cfg_dependent_selectables = 1` が立ち、
関数終了後に `addDomainCfgDependentSelectables()` が呼ばれる（`mclaglink.cpp:813-818,903-906`）。

### イベントループでのディスパッチ

`mclagsyncd.cpp:66-110` の Select ループ:

```cpp
// mclagsyncd.cpp:86-92
else if ( temps == (Selectable *)mclag.getMclagIntfCfgTable() ) {
    SWSS_LOG_DEBUG("MCLAGSYNCD processing mclag_intf_cfg_tbl notifications");
    std::deque<KeyOpFieldsValuesTuple> entries;
    mclag.getMclagIntfCfgTable()->pops(entries);
    mclag.mclagsyncdSendMclagIfaceCfg(entries);
}
```

`pops()` で取り出したエントリを `mclagsyncdSendMclagIfaceCfg()` に渡して
`MCLAG_SYNCD_MSG_TYPE_CFG_MCLAG_IFACE` メッセージとして TCP ソケット経由で iccpd に送信する。

### 起動時の初回全量 fetch

`mclagsyncd.cpp:58`:
```cpp
mclag.mclagsyncdFetchMclagInterfaceConfigFromConfigdb();
```
接続確立直後に CONFIG_DB の全 MCLAG_INTERFACE エントリを
`Table::dump()` で取得し `mclagsyncdSendMclagIfaceCfg()` で一括送信する。
これにより iccpd 再起動・接続断後の再接続時も MCLAG_INTERFACE の全設定が iccpd に復元される。

## MlagOrch による MCLAG_INTERFACE 購読

`orchdaemon.cpp:536-540` で `Orch` コンストラクタに `CFG_MCLAG_INTF_TABLE_NAME` を含む
テーブルリストを渡し、Consumer として登録。orchagent の主ループから `doTask()` が呼ばれる。

```
CONFIG_DB (keyspace notification) → orchagent Consumer → MlagOrch::doTask()
    → doMlagInterfaceTask()
    → addMlagInterface() / delMlagInterface()
    → notifyObservers(SUBJECT_TYPE_MLAG_INTF_CHANGE)
```

SAI 直接呼出はなし。FdbOrch が Observer として `SUBJECT_TYPE_MLAG_INTF_CHANGE` を受信し
FDB フラッシュ制御に使用する。

## 購読者・メッセージング全体図

```
CONFIG_DB MCLAG_INTERFACE
  ├─ MlagOrch (orchagent, Consumer)
  │    └─ notifyObservers(SUBJECT_TYPE_MLAG_INTF_CHANGE) → FdbOrch (Observer)
  └─ mclagsyncd (SubscriberStateTable, 動的登録)
       └─ TCP IPC (127.0.6.1:2626) → iccpd
            ├─ STATE_DB MCLAG_LOCAL_INTF_TABLE (port isolation)
            └─ STATE_DB MCLAG_REMOTE_INTF_TABLE (remote oper_status)
```

## タイムアウト

| デーモン | select タイムアウト | ソース |
|---------|-------------------|--------|
| mclagsyncd | 無限（Select::MAX） | `mclagsyncd.cpp:71` の `s.select(&temps)` にタイムアウト指定なし |
| orchagent | 1000 ms | `orchdaemon.cpp:23` |

## 接続断リカバリ

`mclagsyncd.cpp:44-124` の外側 `while(1)` が `MclagConnectionClosedException` を捕捉し
`accept()` から再試行する。再接続後に `mclagsyncdFetchMclagInterfaceConfigFromConfigdb()`
を呼んで全 MCLAG_INTERFACE を再送信する。

## 出典

- `mclagsyncd.cpp:41,57-58,66-110` (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `mclaglink.cpp:813-818,903-941` (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `mclaglink.cpp:989-1085` (sha: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `mclaglink.cpp:164-188` (mclagsyncdFetchMclagInterfaceConfigFromConfigdb)
