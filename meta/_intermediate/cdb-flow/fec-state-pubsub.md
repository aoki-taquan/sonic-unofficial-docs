# fec-state Phase G — 通信メカニズムスキャン証跡

調査日: 2026-05-19
対象: STATE_DB `PORT_TABLE` の FEC 関連フィールド（`fec`, `supported_fecs`）

## 調査ファイル
- `sonic-swss/orchagent/portsorch.cpp` / `portsorch.h`
- `sonic-utilities/scripts/intfutil`
- `sonic-utilities/generic_config_updater/field_operation_validators.py`
- `sonic-swss/cfgmgr/intfmgr.cpp` / `portmgr.cpp`

---

## A. 書き手の通信 API

`portsorch.h:320`:
```cpp
Table m_portStateTable;
```

`portsorch.cpp:725`:
```cpp
m_portStateTable(stateDb, STATE_PORT_TABLE_NAME),
```

`swss::Table` (非 ProducerStateTable) — HSET / HSET / DEL のみ。PUBLISH 通知は発行しない。

書込ポイント:
- `updateDbPortOperFec()` (L9864): `m_portStateTable.set(port.m_alias, tuples)` — `fec` フィールド
- `initPortSupportedFecModes()` (L3320): `m_portStateTable.set(alias, v)` — `supported_fecs` フィールド

---

## B. 読み手の通信 API

### intfutil (`show interfaces fec status`)

`scripts/intfutil:911`:
```python
oper_fec = self.db.get(self.db.STATE_DB, PORT_STATE_TABLE_PREFIX + key, PORT_FEC)
```
→ オンデマンド `HGET`。CLI 起動時 1 回のみ。keyspace 通知は購読しない。

### generic_config_updater (CONFIG_DB 変更検証)

`field_operation_validators.py:216`:
```python
supported_fecs_str = read_statedb_entry(scope, "PORT_TABLE", port, "supported_fecs")
```
→ `PATCH` 適用前の FEC 値バリデーション時に 1 回のみ `HGET`。イベント駆動ではない。

---

## C. STATE_PORT_TABLE を Subscribe するプロセスが FEC フィールドを読まないことの確認

- `intfmgr.cpp:46-47`: `SubscriberStateTable(stateDb, STATE_PORT_TABLE_NAME)` → 購読あり。
  ただし FEC フィールドを参照するコードはなし (grep: "fec" → ヒットなし)。
- `portmgr.h:27`: `Table m_statePortTable` → 読み取り専用使用あり。FEC 参照なし。
- `nbrmgr.cpp:512`: `m_statePortTable.hget(alias, "netdev_oper_status", oper)` → FEC フィールドは参照しない。
- `buffermgrdyn.h` / `teammgr.cpp`: STATE_PORT_TABLE を読むが FEC フィールドは参照しない。

---

## D. 通信経路まとめ

| 区間 | 方式 | チャンネル/API | タイミング |
|------|------|--------------|---------|
| `PortsOrch` → STATE_DB `PORT_TABLE\|<port>.fec` | `swss::Table::set()` (HSET) | なし (PUBLISH 非発行) | ポート UP イベント時 / warm boot refreshPortStatus() 時 |
| `PortsOrch` → STATE_DB `PORT_TABLE\|<port>.supported_fecs` | `swss::Table::set()` (HSET) | なし (PUBLISH 非発行) | postPortInit() 時 1 回 (lazy init) |
| `intfutil` ← STATE_DB `PORT_TABLE\|<port>.fec` | `db.get()` (HGET, on-demand polling) | — | CLI 起動毎 1 回 |
| `generic_config_updater` ← STATE_DB `PORT_TABLE\|<port>.supported_fecs` | `read_statedb_entry()` (HGET) | — | PATCH 適用検証時 1 回 |

---

## E. ProducerStateTable / NotificationProducer 非使用の確認

PortsOrch は STATE_DB アクセスに `ProducerStateTable` を使用しない (`portsorch.h` 全体 grep で確認)。
`NotificationProducer` も FEC 書込みとは無関係 (`m_portStatusNotificationConsumer` は受信専用)。
