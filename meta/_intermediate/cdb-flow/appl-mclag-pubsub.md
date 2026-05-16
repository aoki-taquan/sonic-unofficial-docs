# appl-mclag — 通信メカニズム (Phase G) 中間調査

対象ページ: `docs/reference/config-db/appl-mclag.md`

APPL_DB MCLAG 関連テーブル群 (`MCLAG_FDB_TABLE`, `ISOLATION_GROUP_TABLE`, `ACL_TABLE_TABLE`, `ACL_RULE_TABLE`, `LAG_TABLE`, `PORT_TABLE`, `INTF_TABLE`) は **書き込み側 = `mclagsyncd`、消費側 = `orchagent`** という一方向の Producer / Consumer 関係である。CONFIG_DB / STATE_DB 側の subscribe ループは `mclagsyncd` が担い、APPL_DB は orchagent が ConsumerStateTable で受け取るパスとなる。

## 1. 書き込み側 (`mclagsyncd`) — Producer & subscribe 入口

### 1.1 ProducerStateTable で APPL_DB へ書く

`sonic-swss/mclagsyncd/mclaglink.cpp` L1810-L1816:

```cpp
p_intf_tbl      = unique_ptr<ProducerStateTable>(new ProducerStateTable(p_appl_db.get(), APP_INTF_TABLE_NAME));
p_iso_grp_tbl   = unique_ptr<ProducerStateTable>(new ProducerStateTable(p_appl_db.get(), APP_ISOLATION_GROUP_TABLE_NAME));
p_fdb_tbl       = unique_ptr<ProducerStateTable>(new ProducerStateTable(p_appl_db.get(), APP_MCLAG_FDB_TABLE_NAME));
p_acl_table_tbl = unique_ptr<ProducerStateTable>(new ProducerStateTable(p_appl_db.get(), APP_ACL_TABLE_TABLE_NAME));
p_acl_rule_tbl  = unique_ptr<ProducerStateTable>(new ProducerStateTable(p_appl_db.get(), APP_ACL_RULE_TABLE_NAME));
p_lag_tbl       = unique_ptr<ProducerStateTable>(new ProducerStateTable(p_appl_db.get(), APP_LAG_TABLE_NAME));
p_port_tbl      = unique_ptr<ProducerStateTable>(new ProducerStateTable(p_appl_db.get(), APP_PORT_TABLE_NAME));
```

`ProducerStateTable::set/del` は `<TABLE>_KEY_SET` / `_KEY_DEL` の中継ハッシュへ書き、`<TABLE>_CHANNEL@<db_id>` に PUBLISH する (swss-common `table.h` `getChannelName()`)。

### 1.2 subscribe 入口 — CONFIG_DB / STATE_DB の SubscriberStateTable

mclagsyncd は **iccpd からの IPC** に加えて CONFIG_DB と STATE_DB を `SubscriberStateTable` で購読する。`mclaglink.cpp` L912-L921:

```cpp
p_state_fdb_tbl               = new SubscriberStateTable(p_state_db.get(),  STATE_FDB_TABLE_NAME);
p_state_vlan_mbr_subscriber_table
                              = new SubscriberStateTable(p_state_db.get(),  STATE_VLAN_MEMBER_TABLE_NAME);
p_mclag_intf_cfg_tbl          = new SubscriberStateTable(p_config_db.get(), CFG_MCLAG_INTF_TABLE_NAME);
p_mclag_unique_ip_cfg_tbl     = new SubscriberStateTable(p_config_db.get(), CFG_MCLAG_UNIQUE_IP_TABLE_NAME);
```

`mclagsyncd.cpp` L41 で `CFG_MCLAG_TABLE_NAME` (MCLAG_DOMAIN) も購読する:

```cpp
SubscriberStateTable mclag_cfg_tbl(&config_db, CFG_MCLAG_TABLE_NAME);
```

`SubscriberStateTable` は `subscriberstatetable.cpp` 経由で Redis に対して以下を発行する:

```
PSUBSCRIBE __keyspace@4__:MCLAG|*
PSUBSCRIBE __keyspace@4__:MCLAG_INTERFACE|*
PSUBSCRIBE __keyspace@4__:MCLAG_UNIQUE_IP|*
PSUBSCRIBE __keyspace@6__:FDB_TABLE|*
PSUBSCRIBE __keyspace@6__:VLAN_MEMBER_TABLE|*
```

- DB 番号: CONFIG_DB = 4、STATE_DB = 6
- 起動時に `KEYS <pattern>` で既存エントリを SET イベントとして再生 (`subscriberstatetable.cpp` コンストラクタ)

### 1.3 主ループ — blocking select、retry interval は明示設定なし

`mclagsyncd.cpp` L66-L110:

```cpp
while (true)
{
    Selectable *temps;
    s.select(&temps);                   // blocking、タイムアウト無し
    if (temps == (Selectable *)mclag.getStateFdbTable())   { mclag.processStateFdb(...); }
    else if (temps == &mclag_cfg_tbl)                       { mclag.processMclagDomainCfg(entries); }
    else if (temps == mclag.getMclagIntfCfgTable())         { mclag.mclagsyncdSendMclagIfaceCfg(entries); }
    else if (temps == mclag.getMclagUniqueCfgTable())       { mclag.mclagsyncdSendMclagUniqueIpCfg(entries); }
    else if (temps == mclag.getStateVlanMemberTable())      { mclag.processStateVlanMember(...); }
    else { pipeline.flush(); }
}
```

- `s.select(&temps)` は `Select::select(Selectable**, unsigned int timeout = std::numeric_limits<unsigned int>::max())` 仕様 (swss-common `select.h`)。**MCLAG では明示的なタイムアウトを与えない** → 永続ブロック
- リトライは IPC 切断時のみ:
  ```cpp
  catch (MclagLink::MclagConnectionClosedException &e) {
      cout << "Connection lost, reconnecting..." << endl;
  }
  ```
  外側 `while (1)` で再接続する。retry interval は固定 sleep を入れず即時再 `accept()`。

### 1.4 iccpd 側のタイマー (参考)

iccpd は subscribe ではなく自前のスケジューラ (`sonic-buildimage/src/iccpd/src/scheduler.c`)。`select(fd+1, &read_fd, NULL, NULL, &tv)` を使う。タイマー定数:

| 定数 | 値 | 用途 |
|------|-----|------|
| `CONNECT_INTERVAL_SEC` | 1 秒 | TCP 再接続 / keepalive 周期 |
| `HEARTBEAT_TIMEOUT_SEC` | 15 秒 | セッションタイムアウト |

CONFIG_DB `MCLAG_DOMAIN.keepalive_interval` / `session_timeout` が空のとき mclagsyncd は `-1` で iccpd へ送り、iccpd 内で上記デフォルトにフォールバック (`iccp_csm.c` L125-126)。

## 2. 消費側 (`orchagent`) — Consumer / ConsumerStateTable

### 2.1 MCLAG_FDB_TABLE → FdbOrch

`orchdaemon.cpp` L229:

```cpp
{ APP_MCLAG_FDB_TABLE_NAME,  FdbOrch::fdborch_pri }
```

FdbOrch は APPL_DB の 3 テーブル (`FDB_TABLE`, `MCLAG_FDB_TABLE`, `VXLAN_FDB_TABLE`) をまとめて 1 つの Orch にバインド。`fdborch.cpp` L724:

```cpp
if (table_name == APP_MCLAG_FDB_TABLE_NAME)
    addMclagFdb(key, port_name, type);
```

### 2.2 ISOLATION_GROUP_TABLE → IsolationGroupOrch

`orchdaemon.cpp` L542:

```cpp
TableConnector appDbIsoGrpTbl(m_applDb, APP_ISOLATION_GROUP_TABLE_NAME);
```

`isolationgrouporch.cpp` L68 で `addExistingData()` 経由で SET 操作を消費。

### 2.3 LAG_TABLE / PORT_TABLE / INTF_TABLE / ACL_TABLE_TABLE / ACL_RULE_TABLE

これらは PortsOrch / IntfsOrch / AclOrch の通常の APPL_DB Consumer に相乗りする。MCLAG 専用フィールド (`traffic_disable`, `learn_mode`) は同一テーブルの汎用フィールドとして処理。

### 2.4 orchagent 主ループの select タイムアウト

`orchdaemon.cpp` L23, L959:

```cpp
#define SELECT_TIMEOUT 1000               // ミリ秒
ret = m_select->select(&s, SELECT_TIMEOUT);
```

orchagent は **1000 ms タイムアウト**で `Select::select` を回し、タイムアウト時に pipeline flush と executeTasks を呼ぶ。mclagsyncd 側は無タイムアウトの blocking ループ。

## 3. PUBSUB チャネルまとめ

| 経路 | DB | チャンネル / パターン | 書き込み元 | 消費者 |
|------|-----|---------------------|-----------|--------|
| iccpd → mclagsyncd | n/a | Unix ドメインソケット (IPC) | iccpd | mclagsyncd |
| mclagsyncd → APPL_DB MCLAG_FDB | 0 | `MCLAG_FDB_TABLE_CHANNEL@0` | ProducerStateTable | FdbOrch (ConsumerStateTable) |
| mclagsyncd → APPL_DB ISOLATION_GROUP | 0 | `ISOLATION_GROUP_TABLE_CHANNEL@0` | ProducerStateTable | IsolationGroupOrch |
| mclagsyncd → APPL_DB LAG / PORT / INTF / ACL_* | 0 | 各 `<TABLE>_CHANNEL@0` | ProducerStateTable | PortsOrch / IntfsOrch / AclOrch |
| CONFIG_DB → mclagsyncd | 4 | `__keyspace@4__:MCLAG\|*` 他 | configd / config CLI | SubscriberStateTable |
| STATE_DB → mclagsyncd | 6 | `__keyspace@6__:FDB_TABLE\|*`, `__keyspace@6__:VLAN_MEMBER_TABLE\|*` | FdbOrch / VlanMgr | SubscriberStateTable |

## 4. リトライ / バックオフの所在

- mclagsyncd: 明示 retry interval なし。`MclagConnectionClosedException` 受信で即時 `accept()` 再試行 (外側 `while(1)`)。CPU 暴走防止は iccpd 側の TCP listen の挙動依存。
- orchagent: `SELECT_TIMEOUT = 1000 ms`。MCLAG 起因の特別なバックオフはない。
- iccpd: TCP 再接続は `CONNECT_INTERVAL_SEC = 1` 秒 (scheduler.c 内で `select` の `tv_sec` に流用)。

## 5. 参照

- `sonic-swss/mclagsyncd/mclagsyncd.cpp` L37-L110
- `sonic-swss/mclagsyncd/mclaglink.cpp` L912-L948, L1810-L1816
- `sonic-swss/orchagent/orchdaemon.cpp` L23, L229, L542, L959
- `sonic-swss/orchagent/fdborch.cpp` L724
- `sonic-swss/orchagent/isolationgrouporch.cpp` L68
- `sonic-swss-common/common/subscriberstatetable.cpp` (PSUBSCRIBE パターン)
- `sonic-swss-common/common/select.h` (`select(Selectable**, unsigned int timeout)`)
- `sonic-buildimage/src/iccpd/include/scheduler.h` L40, L42
- `sonic-buildimage/src/iccpd/src/iccp_csm.c` L125-L126
