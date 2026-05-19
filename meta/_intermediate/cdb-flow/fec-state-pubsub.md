# FEC_STATE 通信メカニズム調査メモ (Phase G)

調査日: 2026-05-19
対象: STATE_DB `PORT_TABLE` の FEC 関連フィールド（`fec`, `supported_fecs`）
調査ファイル:
- `sonic-swss/orchagent/portsorch.cpp`
- `sonic-utilities/scripts/intfutil`

---

## 通信経路の概要

### `fec` フィールドの書込み経路

```
SAI → syncd → ASIC_DB[NOTIFICATIONS]
  ↓ NotificationConsumer (SUBSCRIBE NOTIFICATIONS)
PortsOrch::doTask(NotificationConsumer&)
  ↓ op="port_state_change", status=UP
  ↓ getPortOperFec → SAI SAI_PORT_ATTR_OPER_PORT_FEC_MODE
  ↓ updateDbPortOperFec(port, fec_str)
STATE_DB[PORT_TABLE|<port> → fec]  (Table::set, TTL なし)
```

### `supported_fecs` フィールドの書込み経路

```
SAI create_port() 完了 → PortsOrch::addPort() → postPortInit()
  ↓ initPortSupportedFecModes(alias, port_id)
  ↓ SAI_PORT_ATTR_SUPPORTED_FEC_MODE クエリ
  ↓ m_portStateTable.set(alias, v)  (Table::set, TTL なし)
STATE_DB[PORT_TABLE|<port> → supported_fecs]
```

## 検出した通信メカニズム

### 1. oper_status UP 通知: syncd → PortsOrch (NotificationConsumer)

`PortsOrch` は ASIC_DB の `NOTIFICATIONS` チャンネルを `NotificationConsumer` で購読する (portsorch.cpp:961-963)。
syncd は SAI 側のポート状態変化を `port_state_change` イベントとして PUBLISH する。

| 項目 | 値 |
|------|----|
| 購読チャンネル | `NOTIFICATIONS` (ASIC_DB) |
| Consumer クラス | `NotificationConsumer` |
| 通知方式 | Redis SUBSCRIBE (通常 pub/sub) |
| ペイロード | JSON: `[{"id": "<sai_oid>", "state": "up"|"down"}]` |
| 処理エントリポイント | `PortsOrch::doTask(NotificationConsumer&)` |

`allPortsReady()` が false の間はイベントを処理せずに即リターンする (portsorch.cpp:9618)。
初期化完了前に届いた `port_state_change` 通知は再試行せず破棄される（lost event の可能性がある）。

### 2. STATE_DB への書込み: Table::set() (直接書込み、非 ProducerStateTable)

`updateDbPortOperFec()` と `initPortSupportedFecModes()` はどちらも `swss::Table::set()` を直接呼ぶ (portsorch.cpp:9868, 3318-3320)。

- ProducerStateTable（EVALSHA + PUBLISH）を使わない
- Redis HSET コマンドが直接発行される
- TTL（EXPIRE）は設定されない (`DEFAULT_DB_TTL = -1`)
- consumer への通知（PUBLISH）は発生しない → consumer は polling か `SubscriberStateTable` (keyspace notification) で変化を検出する

### 3. intfutil による読み取り: Table::get() (直接読取り)

`intfutil` は `db.get(db.STATE_DB, "PORT_TABLE|<port>", "fec")` で STATE_DB を直接読む (intfutil:911)。
Redis の HGET コマンドに相当する。pub/sub 購読ではなくポーリング相当（コマンド実行時点のスナップショット）。

`admin_fec` は APPL_DB を参照: `db.get(db.APPL_DB, "PORT_TABLE:<port>", "fec")` (intfutil:910)。

### 4. TTL

FEC 関連フィールドへの書込みに TTL は設定されない。`Table::set()` は `DEFAULT_DB_TTL = -1` を使い `EXPIRE` コマンドを発行しない。
フィールドの削除は orchagent 再起動時の `m_portStateTable.del()` によるポート全削除か、`doPortTask` での明示的 del 操作によってのみ発生する。

---

## 通信メカニズムサマリ

| 区間 | 方式 | 経路 |
|------|------|------|
| syncd → PortsOrch (`fec` 書込み起因) | `NotificationConsumer` (SUBSCRIBE) | `ASIC_DB NOTIFICATIONS` |
| PortsOrch → `STATE_DB PORT_TABLE.fec` | `Table::set()` (HSET 直接) | TTL なし |
| PortsOrch → `STATE_DB PORT_TABLE.supported_fecs` | `Table::set()` (HSET 直接) | TTL なし (lazy init, 1 回限り) |
| `intfutil` → STATE_DB (読取り) | `Table::get()` (HGET 直接) | polling/snapshot 相当 |
| `intfutil` → APPL_DB (FEC Admin 読取り) | `Table::get()` (HGET 直接) | polling/snapshot 相当 |
