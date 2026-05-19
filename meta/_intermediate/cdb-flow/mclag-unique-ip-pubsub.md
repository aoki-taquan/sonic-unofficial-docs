# mclag-unique-ip — 通信メカニズム (Phase G) 中間調査ノート

## 調査対象

`MCLAG_UNIQUE_IP` テーブルの購読・通知経路を特定する。

## 購読クラス: SubscriberStateTable（遅延登録）

`mclagsyncd` は起動時に `CFG_MCLAG_TABLE_NAME`（`MCLAG_DOMAIN`）のみを購読する
（`mclagsyncd.cpp:41`）。

`MCLAG_UNIQUE_IP` の `SubscriberStateTable` は `addDomainCfgDependentSelectables()` の
中で生成され、MCLAG_DOMAIN の初回 SET 成功後にはじめて `Select` に追加される
（`mclaglink.cpp:921`, `mclaglink.cpp:944-948`）:

```cpp
p_mclag_unique_ip_cfg_tbl = new SubscriberStateTable(
    p_config_db.get(), CFG_MCLAG_UNIQUE_IP_TABLE_NAME);   // mclaglink.cpp:921

if (p_mclag_unique_ip_cfg_tbl) {
    m_select->addSelectable(getMclagUniqueCfgTable());
    SWSS_LOG_NOTICE("MCLagSYNCD Adding mclag_unique_ip_cfg_tbl to selectable");
}  // mclaglink.cpp:944-948
```

`SubscriberStateTable` は swss-common 実装により以下を Redis に発行する:

```
PSUBSCRIBE __keyspace@4__:MCLAG_UNIQUE_IP|*
```

DB 番号 4 = CONFIG_DB。コンストラクタ時に `KEYS MCLAG_UNIQUE_IP|*` で既存エントリを
走査し、SET イベントとして再生する（subscriberstatetable.cpp コンストラクタ）。

## 主ループのディスパッチ

`mclagsyncd.cpp:93-98`:

```cpp
else if (temps == (Selectable *)mclag.getMclagUniqueCfgTable()) {
    SWSS_LOG_DEBUG("MCLAGSYNCD processing mclag_unique_ip_cfg_tbl notifications");
    std::deque<KeyOpFieldsValuesTuple> entries;
    mclag.getMclagUniqueCfgTable()->pops(entries);
    mclag.mclagsyncdSendMclagUniqueIpCfg(entries);
}
```

`s.select(&temps)` はタイムアウト無しのブロッキング呼び出し
（`Select::select(Selectable**, unsigned int timeout = std::numeric_limits<unsigned int>::max())`）。

## iccpd への転送: TCP IPC

`mclagsyncdSendMclagUniqueIpCfg()` → `::write(m_connection_socket, ...)` により
`MCLAG_SYNCD_MSG_TYPE_CFG_MCLAG_UNIQUE_IP`（type=5）を送信する。

```
CONFIG_DB ──PSUBSCRIBE __keyspace@4__:MCLAG_UNIQUE_IP|*──▶ mclagsyncd
  ──TCP 127.0.0.6:2626──▶ iccpd: iccp_mclagsyncd_mclag_unique_ip_cfg_handler()
```

TCP 定数: `MCLAG_DEFAULT_IP=0x7f000006`（127.0.0.6）、`MCLAG_DEFAULT_PORT=2626`
（`mclag.h:23,56`）。

## 逆方向: iccpd → mclagsyncd → APPL_DB INTF_TABLE

STANDBY ノードかつ L3 モードの場合、iccpd が
`MCLAG_MSG_TYPE_SET_INTF_MAC` を mclagsyncd に返送し、
`setIntfMac()` → APPL_DB `INTF_TABLE|<vlan_if>` へ mac_addr を書き込む。
これは `ProducerStateTable` を使わず `p_intf_tbl->set()` 経由の
ProducerStateTable 書込み (`mclaglink.cpp:435-460`)。

## MCLAG_DOMAIN 削除時の購読解除

`delDomainCfgDependentSelectables()` で `removeSelectable()` + `delete` によって
`MCLAG_UNIQUE_IP` の SubscriberStateTable が解放される (`mclaglink.cpp:962-967`)。

## タイムアウト・リトライ

| デーモン    | select タイムアウト | リトライ |
|------------|-------------------|---------|
| mclagsyncd | 無限（明示設定なし）  | MclagConnectionClosedException で即時 accept() 再試行 |
| iccpd      | 自前スケジューラ     | CONNECT_INTERVAL_SEC=1 秒で TCP 再接続 |

## Sources

- sonic-swss/mclagsyncd/mclagsyncd.cpp L41, L93-98
- sonic-swss/mclagsyncd/mclaglink.cpp L910-948, L962-967, L1088-1180
- sonic-swss/mclagsyncd/mclag.h L23, L56, L91
- sonic-buildimage/src/iccpd/src/mlacp_link_handler.c L3186-3292
