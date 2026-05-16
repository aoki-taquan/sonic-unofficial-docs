# DHCP_RELAY — Phase G 通信メカニズム (Redis PUBSUB / keyspace notification)

対象ページ: `docs/reference/config-db/dhcp-relay.md`
調査日: 2026-05-14
Evidence: `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp`, `sonic-swss-common/common/subscriberstatetable.cpp`

---

## 概要

`dhcp6relay` は CONFIG_DB の `DHCP_RELAY` テーブルを **`swss::SubscriberStateTable`** 経由で購読する。
内部実装は Redis の **keyspace notification (PUBSUB PSUBSCRIBE)** を使用しており、ConsumerStateTable / NotificationConsumer は使用しない。
TTL/keyevent 系の expire 通知も使用しない。

---

## 通信シーケンス

### 1. 初期化 — `initialize_swss()` (config_interface.cpp:18-29)

```
dhcp6relay プロセス起動
  └─ initialize_swss(vlans)
       └─ DBConnector("CONFIG_DB", 0)       ← Redis DB #4 (CONFIG_DB)
       └─ SubscriberStateTable(db, "DHCP_RELAY")
            └─ [ctor] psubscribe(db, "__keyspace@4__:DHCP_RELAY|*")
                      ─ PSUBSCRIBE __keyspace@4__:DHCP_RELAY|*
            └─ [ctor] Table::getKeys()       ← KEYS "DHCP_RELAY|*" で起動時スナップショット取得
            └─ [ctor] m_buffer に全エントリを SET_COMMAND として積む
       └─ swssSelect.addSelectable(&ipHelpersTable)
       └─ get_dhcp(vlans, &ipHelpersTable, dynamic=false, config_db)
```

### 2. keyspace notification パターン

`SubscriberStateTable` が発行する PSUBSCRIBE パターン:

```
__keyspace@4__:DHCP_RELAY|*
```

- `@4__` は CONFIG_DB の Redis DB 番号 (通常 4)
- `|` は SONiC テーブルセパレータ (GetTableNameSeparator)
- `*` はすべての VLAN キーにマッチ

Redis サーバ側では `notify-keyspace-events = "KEA"` を設定 (sonic-swss-common/dbinterface.cpp:345)。  
`K` = keyspace 通知、`E` = keyevent 通知、`A` = すべての操作 (= g$lszxetd の省略形)。

### 3. Select ループ — `get_dhcp()` (config_interface.cpp:63-80)

```
swssSelect.select(&selectable, timeout_ms=1000)
  ├─ TIMEOUT (1000ms 無通知) → 何もしない
  ├─ ERROR → LOG_WARNING "Select: returned ERROR"
  └─ データあり && selectable == ipHelpersTable
       ├─ dynamic=false (起動時) → handleRelayNotification()
       └─ dynamic=true  (実行時) → LOG_WARNING "relay config changed, need restart container"
                                   (設定変更は無視 = dead consumer)
```

### 4. pops → processRelayNotification

```
handleRelayNotification(ipHelpersTable, vlans, config_db)
  └─ ipHelpersTable.pops(entries)          ← std::deque<KeyOpFieldsValuesTuple>
       ├─ m_buffer に cached data があれば flush (起動時スナップショット)
       └─ m_keyspace_event_buffer を処理:
            event.type="pmessage"
            event.channel = "__keyspace@4__:DHCP_RELAY|<vlan>"
            event.data    = "set" | "del" | "hset" など
            → op = "del" → kfvOp = DEL_COMMAND
            → それ以外 → Table::get(key) で最新値を再取得 → kfvOp = SET_COMMAND
  └─ processRelayNotification(entries, vlans, config_db)
       └─ for entry in entries:
            vlan      = kfvKey(entry)
            operation = kfvOp(entry)   ← "SET" or "DEL"
            fields    = kfvFieldsValues(entry)
            ...
```

---

## 重要な特性

| 特性 | 内容 |
|------|------|
| 通知種別 | Redis keyspace notification (PUBSUB PSUBSCRIBE) |
| パターン | `__keyspace@4__:DHCP_RELAY\|*` |
| notify-keyspace-events | `KEA` (keyspace + keyevent + all commands) |
| SWSS abstraction | `swss::SubscriberStateTable` → `swss::Select` (1000ms timeout poll) |
| ConsumerStateTable | **不使用** |
| NotificationConsumer | **不使用** |
| TTL / keyspace expire 通知 | **不使用** |
| 起動時スナップショット | `Table::getKeys()` + `Table::get()` で全エントリ即時読み込み (m_buffer) |
| 実行時変更検知 | keyspace event 受信するが `dynamic=true` フラグにより **無視**。ログのみ |
| 設定反映 | **コンテナ再起動必須** (config_interface.cpp:76-78) |

---

## TTL / expire の非使用

`DHCP_RELAY` エントリには TTL が設定されず、keyevent の `expired` / `evicted` 通知も監視しない。
`notify-keyspace-events = "KEA"` には `x` (expired) も含まれるが (`A` = all の一部)、
dhcp6relay は op 種別を見て `del` のみ DEL_COMMAND として扱い、それ以外は SET_COMMAND として処理する。
実質的に expire による削除は `del` 通知として届くが、通常運用では TTL 設定がないため発生しない。

---

## 参照コード

| ファイル | 行 | 内容 |
|---|---|---|
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 18-29 | `initialize_swss()` — SubscriberStateTable 生成と Select 登録 |
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 63-80 | `get_dhcp()` — Select ループ本体 |
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 93-100 | `handleRelayNotification()` — pops 呼び出し |
| `sonic-dhcp-relay/dhcp6relay/src/config_interface.cpp` | 113-184 | `processRelayNotification()` — entries 処理 |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 17-43 | SubscriberStateTable ctor — psubscribe + 起動時スナップショット |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 95-165 | `pops()` — keyspace event バッファ処理 |
| `sonic-swss-common/common/dbinterface.h` | 83 | `KEYSPACE_PATTERN = "__key*__:*"` |
| `sonic-swss-common/common/dbinterface.h` | 102 | `KEYSPACE_EVENTS = "KEA"` |
