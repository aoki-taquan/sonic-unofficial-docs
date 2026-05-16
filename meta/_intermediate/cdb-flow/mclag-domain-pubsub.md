# MCLAG_DOMAIN — 通信メカニズム (Phase G) 解析メモ

対象ページ: `docs/reference/config-db/mclag-domain.md`  
対象テーブル: `CONFIG_DB` の `MCLAG_DOMAIN` / `MCLAG_INTERFACE` / `MCLAG_UNIQUE_IP`

MCLAG の通信経路は二系統ある。**MlagOrch 系**（orchagent 内・Observer パターンで内部通知）と、**mclagsyncd 系**（独立デーモン・CONFIG_DB を SubscriberStateTable で購読し iccpd へ TCP IPC で転送）。

---

## 1. MlagOrch 系 — CONFIG_DB → orchagent (Consumer) → 内部 Observer 通知

### 1.1 Consumer 登録

`orchdaemon.cpp` L536-540:

```cpp
vector<string> mlag_tables = {
    CFG_MCLAG_TABLE_NAME,       // MCLAG_DOMAIN
    CFG_MCLAG_INTF_TABLE_NAME,  // MCLAG_INTERFACE
};
gMlagOrch = new MlagOrch(m_configDb, mlag_tables);
```

`MlagOrch` は `Orch(db, tableNames)` 継承により **ConsumerStateTable ではなく `Consumer`** を CONFIG_DB に対して接続する。  
→ swss-common の `Consumer` は Redis SUBSCRIBE チャネルを使う ProducerStateTable / ConsumerStateTable 形式**ではなく** `SubscriberStateTable`（keyspace 通知）経由でエントリを受け取る。

- 購読テーブル: `MCLAG_DOMAIN`（CFG_MCLAG_TABLE_NAME）, `MCLAG_INTERFACE`（CFG_MCLAG_INTF_TABLE_NAME）
- `MCLAG_UNIQUE_IP` は MlagOrch が購読しない（mclagsyncd のみが担当）

### 1.2 doTask() → 内部 Observer notify

`mlagorch.cpp` L45-66:

```cpp
void MlagOrch::doTask(Consumer &consumer) {
    if (!gPortsOrch->allPortsReady()) return;
    if (table_name == CFG_MCLAG_TABLE_NAME)       doMlagDomainTask(consumer);
    else if (table_name == CFG_MCLAG_INTF_TABLE_NAME) doMlagInterfaceTask(consumer);
}
```

`doMlagDomainTask()` は `peer_link` フィールドを抽出し `addIslInterface()` を呼ぶ。  
`doMlagInterfaceTask()` はメンバー LAG 名を取得し `addMlagInterface()` を呼ぶ。

どちらも SAI を**直接呼ばず**、orchagent 内の Observer 通知を使う:

| メソッド | notify する SubjectType | 受信者 |
|---------|------------------------|--------|
| `addIslInterface()` / `delIslInterface()` | `SUBJECT_TYPE_MLAG_ISL_CHANGE` | FdbOrch が `isIslInterface()` でポーリング |
| `addMlagInterface()` / `delMlagInterface()` | `SUBJECT_TYPE_MLAG_INTF_CHANGE` | FdbOrch が `isMlagInterface()` でポーリング |

FdbOrch は `gMlagOrch` グローバルポインタ経由で MLAG メンバー / ISL 判定を呼び出す。Observer `attach()` は現行コードでは確認されておらず、直接 `gMlagOrch` の API を参照する形式。

### 1.3 SAI bridge_port_api への経路

MlagOrch 自体は SAI を呼ばない。MCLAG に起因する SAI 操作は `FdbOrch` 経由で起きる:

- `fdborch.cpp` L1209: `gMlagOrch->isMlagInterface(p.m_alias)` が true の場合、ポートダウン時の FDB フラッシュをスキップ
- `fdborch.cpp` L1666: MCLAG メンバーが `SAI_PORT_OPER_STATUS_DOWN` のとき MAC 削除 origin を `FDB_ORIGIN_LEARN` に書き換えてから `sai_fdb_api->remove_fdb_entry()` を呼ぶ

mclagsyncd が ASIC_DB 上の `SAI_OBJECT_TYPE_BRIDGE_PORT` を直接参照する箇所:

```cpp
// mclaglink.cpp L79-95
auto keys = p_asic_db->keys("ASIC_STATE:SAI_OBJECT_TYPE_BRIDGE_PORT:*");
// SAI_BRIDGE_PORT_ATTR_PORT_ID / SAI_BRIDGE_PORT_ATTR_TUNNEL_ID を取得してマップ構築
oid_map->insert(pair<string, string>(bridge_port_id, attr_port_id->second));
```

これは FDB 同期時のポート OID 解決に使う参照で、mclagsyncd → ASIC_DB の**読み取り**経路（書き込みは orchagent が行う）。

---

## 2. mclagsyncd 系 — CONFIG_DB 購読 → iccpd へ TCP IPC

### 2.1 デーモン構成と接続先

`mclagsyncd` (`docker-iccpd` 内) は **iccpd と同一コンテナ**で動作し、iccpd の TCP サーバへ接続する。

```
mclagsyncd  ──TCP 127.0.6.1:2626──▶  iccpd
```

定数 (`sonic-swss/mclagsyncd/mclag.h`):

```c
#define MCLAG_DEFAULT_IP   0x7f000006   // 127.0.6.1 (loopback 内別 IP)
#define MCLAG_DEFAULT_PORT 2626
```

mclagsyncd が TCP **サーバ**として listen し (`mclaglink.cpp` L1754-1786)、iccpd 側が接続してくる。  
（mclagsyncd は `socket / bind / listen / accept` を行い、iccpd が connect する）

### 2.2 CONFIG_DB 購読

`mclagsyncd.cpp` L37-41:

```cpp
DBConnector config_db("CONFIG_DB", 0);
SubscriberStateTable mclag_cfg_tbl(&config_db, CFG_MCLAG_TABLE_NAME);
```

`addDomainCfgDependentSelectables()` が呼ばれると (`mclaglink.cpp` L903-921):

```cpp
p_mclag_intf_cfg_tbl      = new SubscriberStateTable(p_config_db.get(), CFG_MCLAG_INTF_TABLE_NAME);
p_mclag_unique_ip_cfg_tbl = new SubscriberStateTable(p_config_db.get(), CFG_MCLAG_UNIQUE_IP_TABLE_NAME);
```

`MCLAG_INTERFACE` / `MCLAG_UNIQUE_IP` は **MCLAG_DOMAIN の初回 SET 成功後** に動的に追加される:

```cpp
if (add_cfg_dependent_selectables) {
    addDomainCfgDependentSelectables(); // L903
}
```

購読チャネル（SubscriberStateTable = keyspace 通知）:

```
PSUBSCRIBE __keyspace@4__:MCLAG|*
PSUBSCRIBE __keyspace@4__:MCLAG_INTERFACE|*
PSUBSCRIBE __keyspace@4__:MCLAG_UNIQUE_IP|*
```

### 2.3 iccpd への IPC 送信

テーブル変化を受信するたびに `write(m_connection_socket, ...)` で iccpd へ送信する:

| テーブル | 処理関数 | IPC メッセージ |
|---------|---------|--------------|
| `MCLAG_DOMAIN` | `processMclagDomainCfg()` (`mclaglink.cpp` L626-902) | ドメイン設定 (source_ip, peer_ip, peer_link 等) |
| `MCLAG_INTERFACE` | `mclagsyncdSendMclagIfaceCfg()` (`mclaglink.cpp` L990-1090) | メンバー LAG 追加/削除 |
| `MCLAG_UNIQUE_IP` | `mclagsyncdSendMclagUniqueIpCfg()` (`mclaglink.cpp` L1092-1180) | unique-ip VLAN 追加/削除 |

差分更新 (`mclaglink.cpp` L743-803): 既存 domain エントリがある場合、変更があったフィールドのみを `MCLAG_CFG_OPER_ATTR_SET` / `MCLAG_CFG_OPER_ATTR_DEL` で送信する。

### 2.4 STATE_DB 購読 (参考)

mclagsyncd は CONFIG_DB に加えて STATE_DB も購読する:

```cpp
p_state_fdb_tbl               = new SubscriberStateTable(p_state_db.get(), STATE_FDB_TABLE_NAME);
p_state_vlan_mbr_subscriber_table
                              = new SubscriberStateTable(p_state_db.get(), STATE_VLAN_MEMBER_TABLE_NAME);
```

FDB エントリ変化は iccpd へ転送し、ピア ToR との MAC 同期に使う。

### 2.5 APPL_DB への書き込み (mclagsyncd → orchagent)

mclagsyncd は iccpd からの命令を受けて APPL_DB へ ProducerStateTable で書く:

```cpp
// mclaglink.cpp L1810-L1816
p_intf_tbl    = new ProducerStateTable(p_appl_db.get(), APP_INTF_TABLE_NAME);
p_iso_grp_tbl = new ProducerStateTable(p_appl_db.get(), APP_ISOLATION_GROUP_TABLE_NAME);
p_fdb_tbl     = new ProducerStateTable(p_appl_db.get(), APP_MCLAG_FDB_TABLE_NAME);
p_acl_table_tbl = new ProducerStateTable(p_appl_db.get(), APP_ACL_TABLE_TABLE_NAME);
p_acl_rule_tbl  = new ProducerStateTable(p_appl_db.get(), APP_ACL_RULE_TABLE_NAME);
p_lag_tbl     = new ProducerStateTable(p_appl_db.get(), APP_LAG_TABLE_NAME);
p_port_tbl    = new ProducerStateTable(p_appl_db.get(), APP_PORT_TABLE_NAME);
```

FDB フラッシュは `NotificationProducer flushFdb(p_appl_db.get(), "FLUSHFDBREQUEST")` で送信 (`mclaglink.cpp` L423)。

---

## 3. 主ループとタイムアウト

| デーモン | select タイムアウト | リトライ |
|---------|-------------------|--------|
| mclagsyncd | 無限（`std::numeric_limits<unsigned int>::max()`） | `MclagConnectionClosedException` 受信で即時再 `accept()` |
| orchagent | SELECT_TIMEOUT = 1000 ms (`orchdaemon.cpp` L23) | 特別なバックオフなし |
| iccpd | `CONNECT_INTERVAL_SEC = 1` 秒 (`scheduler.c`) | TCP 再接続周期 |

---

## 4. 通信経路サマリ

| 経路 | DB / チャネル | 書き込み元 | 消費者 |
|------|-------------|-----------|--------|
| CONFIG_DB → orchagent (MCLAG_DOMAIN / MCLAG_INTERFACE) | `__keyspace@4__:MCLAG\|*` など (SubscriberStateTable) | config CLI / REST | MlagOrch (Consumer) |
| CONFIG_DB → mclagsyncd (全 MCLAG テーブル) | `__keyspace@4__:MCLAG\|*` など (SubscriberStateTable) | 同上 | MclagLink |
| mclagsyncd → iccpd | TCP 127.0.6.1:2626 (MCLAG_DEFAULT_PORT) | mclagsyncd | iccpd |
| iccpd → mclagsyncd | TCP 同上 (双方向 IPC) | iccpd | mclagsyncd |
| mclagsyncd → APPL_DB | `MCLAG_FDB_TABLE_CHANNEL@0` 他 (ProducerStateTable) | mclagsyncd | FdbOrch / IsolationGroupOrch 他 |
| MlagOrch → FdbOrch | orchagent 内 Observer 通知 (SUBJECT_TYPE_MLAG_ISL/INTF_CHANGE) | MlagOrch | FdbOrch (gMlagOrch ポーリング) |
| mclagsyncd → ASIC_DB | ASIC_STATE:SAI_OBJECT_TYPE_BRIDGE_PORT:* (読み取りのみ) | orchagent (書き込み元) | mclagsyncd (OID 解決) |

---

## 5. 参照

- `sonic-swss/orchagent/mlagorch.cpp` L27-251
- `sonic-swss/orchagent/mlagorch.h` L38-66
- `sonic-swss/orchagent/orchdaemon.cpp` L536-540, L595
- `sonic-swss/orchagent/fdborch.cpp` L1209, L1666
- `sonic-swss/mclagsyncd/mclagsyncd.cpp` L37-114
- `sonic-swss/mclagsyncd/mclaglink.cpp` L79-95, L423, L626-902, L903-948, L990-1090, L1092-1180, L1742-1816
- `sonic-swss/mclagsyncd/mclag.h` L23, L56
- `sonic-swss-common/common/subscriberstatetable.cpp` (PSUBSCRIBE 購読パターン)
- `sonic-buildimage/src/iccpd/src/scheduler.c` (iccpd タイマー)
