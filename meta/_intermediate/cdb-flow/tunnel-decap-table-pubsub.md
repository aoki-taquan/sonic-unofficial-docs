# TUNNEL_DECAP_TABLE (APPL_DB) — Phase G: 通信メカニズム (pubsub)

対象ドキュメント: `docs/reference/config-db/tunnel-decap-table.md`
解析日: 2026-05-17
根拠ソース:
- `sonic-swss/orchagent/tunneldecaporch.cpp` (sha 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/orchdaemon.cpp` (sha 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 目的

`TUNNEL_DECAP_TABLE` (APPL_DB) が `tunneldecaporch` によってどの通信メカニズム
（Redis Pub/Sub・ConsumerStateTable・SubscriberStateTable）を介して消費されるかを整理する。

---

## 1. Consumer 登録経路

### orchdaemon 側の登録

`orchdaemon.cpp` が `TunnelDecapOrch` を構築する際に APPL_DB テーブル名リストを渡す:

```cpp
// orchdaemon.cpp (TunnelDecapOrch 生成箇所)
vector<string> tunnel_tables = {
    APP_TUNNEL_DECAP_TABLE_NAME,        // "TUNNEL_DECAP_TABLE"
    APP_TUNNEL_DECAP_TERM_TABLE_NAME    // "TUNNEL_DECAP_TERM_TABLE"
};
gTunneldecapOrch = new TunnelDecapOrch(m_applDb, m_stateDb, m_configDb, tunnel_tables);
```

`Orch` 基底クラスが各テーブル名に対して `ConsumerStateTable` を自動生成し
`m_consumerMap` に登録する。新しいエントリが書き込まれると Redis keyspace notification
経由で orchagent の select ループが起床し `doTask(Consumer&)` が呼ばれる。

### tunneldecaporch コンストラクタ側の追加登録

```cpp
// tunneldecaporch.cpp L39-48
auto cfgSubnetDecapSubTable = new SubscriberStateTable(
    configDb, CFG_SUBNET_DECAP_TABLE_NAME,
    TableConsumable::DEFAULT_POP_BATCH_SIZE, 0);
deque<KeyOpFieldsValuesTuple> entries;
cfgSubnetDecapSubTable->pops(entries);
// init: 起動時に現在エントリを即取得
for (auto &entry : entries) { doSubnetDecapTask(entry); }

Orch::addExecutor(new Consumer(cfgSubnetDecapSubTable, this, CFG_SUBNET_DECAP_TABLE_NAME));
```

`SUBNET_DECAP_TABLE` (CONFIG_DB) は `SubscriberStateTable` で個別購読される。
起動時に現在値を一括 pops して初期化し、その後は keyspace notification で更新を受け取る。

---

## 2. 購読テーブルと API 種別

| テーブル | DB | 購読 API | Handler |
|---------|----|---------|----|
| `TUNNEL_DECAP_TABLE` | APPL_DB | `ConsumerStateTable` (Orch 基底) | `doDecapTunnelTask()` |
| `TUNNEL_DECAP_TERM_TABLE` | APPL_DB | `ConsumerStateTable` (Orch 基底) | `doDecapTunnelTermTask()` |
| `SUBNET_DECAP_TABLE` | CONFIG_DB | `SubscriberStateTable` + `addExecutor` | `doSubnetDecapTask()` |

CONFIG_DB の `TUNNEL` テーブルは **orchagent が直接購読しない**。
`tunnelmgrd` が CONFIG_DB → APPL_DB へ変換し、orchagent は APPL_DB 側を
ConsumerStateTable で受け取る二段構成（CONFIG_DB → tunnelmgrd → APPL_DB → TunnelDecapOrch）。

---

## 3. PortsOrch ゲート（受動的待機）

```cpp
// tunneldecaporch.cpp L55-58
void TunnelDecapOrch::doTask(Consumer &consumer)
{
    if (!gPortsOrch->allPortsReady()) return;
    ...
}
```

`gPortsOrch->allPortsReady()` が `false` の間は APPL_DB からのイベントをすべてスキップ。
PortsOrch が ready 状態になると orchagent のメインループが次の select サイクルで
`doTask()` を再呼び出しし、スタックしていたエントリを処理する（受動的待機パターン）。

---

## 4. SAI API 呼び出し（出力方向）

```cpp
// tunneldecaporch.cpp L853 付近
status = sai_tunnel_api->create_tunnel(
    &tunnel_id, gSwitchId, tunnel_attrs.size(), tunnel_attrs.data());
task_process_status handle_status = handleSaiCreateStatus(SAI_API_TUNNEL, status);
```

- `task_need_retry` → ConsumerStateTable のキューにエントリを残留し次サイクルでリトライ（QoS map 未解決時）
- `task_success` → エントリ消費完了、STATE_DB へ書き戻し
- `task_failed` → エントリ消費、エラーログのみ

---

## 5. STATE_DB 書き戻し（Pub 方向）

SAI create 成功後、`stateTunnelDecapTable` / `stateTunnelDecapTermTable` へ書き戻す:

```cpp
// tunneldecaporch.cpp L1531 / L1560
stateTunnelDecapTable->set(tunnel_name, fv);       // STATE_TUNNEL_DECAP_TABLE
stateTunnelDecapTermTable->set(tunnel_term_key, fv); // STATE_TUNNEL_DECAP_TERM_TABLE
```

これらは `Table`（非 ProducerStateTable）のため、SET/DEL は Redis hset/del を
直接発行する。別プロセスが STATE_DB を参照する際は通常の `Table::get()` で読む。
NotificationProducer / Consumer 型のチャンネル通知は使用しない。

---

## evidence

- `tunneldecaporch.cpp` L39-48 (SubscriberStateTable 個別登録 + 起動時 pops)
- `tunneldecaporch.cpp` L55-58 (`allPortsReady()` ゲート)
- `tunneldecaporch.cpp` L1521-1566 (`setDecapTunnelStatus` / `setDecapTunnelTermStatus`)
- orchagent `Orch` 基底クラス: `ConsumerStateTable` 自動登録パターン
