# TUNNEL テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `TUNNEL` テーブル（Dual-ToR IPinIP トンネル定義）。

## 1. Consumer 登録経路

`TunnelDecapOrch` は `orchdaemon` から以下の形式で初期化される:

```cpp
// orchdaemon.cpp L343-347
vector<string> tunnel_tables = {
    APP_TUNNEL_DECAP_TABLE_NAME,       // "TUNNEL_DECAP_TABLE"
    APP_TUNNEL_DECAP_TERM_TABLE_NAME   // "TUNNEL_DECAP_TERM_TABLE"
};
gTunneldecapOrch = new TunnelDecapOrch(m_applDb, m_stateDb, m_configDb, tunnel_tables);
```

`TunnelDecapOrch` コンストラクタ内では APPL_DB テーブルを `Orch(appDb, tableNames)` で継承登録しつつ、**CONFIG_DB** の `CFG_SUBNET_DECAP_TABLE_NAME` を追加で `SubscriberStateTable` として購読する:

```cpp
// tunneldecaporch.cpp L39-48
auto cfgSubnetDecapSubTable = new SubscriberStateTable(
    configDb, CFG_SUBNET_DECAP_TABLE_NAME,
    TableConsumable::DEFAULT_POP_BATCH_SIZE, 0);
// 起動時スナップショット取得
deque<KeyOpFieldsValuesTuple> entries;
cfgSubnetDecapSubTable->pops(entries);
for (auto &entry : entries) { doSubnetDecapTask(entry); }
// Consumer として登録
Orch::addExecutor(new Consumer(cfgSubnetDecapSubTable, this, CFG_SUBNET_DECAP_TABLE_NAME));
```

## 2. 購読テーブルと Consumer API

| テーブル | DB | 購読 API | Handler メソッド |
|---------|----|---------|----|
| `TUNNEL_DECAP_TABLE` (APPL_DB) | `m_applDb` | `Orch` 基底クラス経由 `ConsumerStateTable` | `doDecapTunnelTask()` |
| `TUNNEL_DECAP_TERM_TABLE` (APPL_DB) | `m_applDb` | `Orch` 基底クラス経由 `ConsumerStateTable` | `doDecapTunnelTermTask()` |
| `SUBNET_DECAP_TABLE` (CONFIG_DB) | `m_configDb` | `SubscriberStateTable` + `addExecutor` | `doSubnetDecapTask()` |

`TUNNEL` テーブル (CONFIG_DB) は **直接 orchagent が購読しない**。  
`tunnelmgrd` (cfgmgr) が CONFIG_DB `TUNNEL` → APPL_DB `TUNNEL_DECAP_TABLE` / `TUNNEL_DECAP_TERM_TABLE` へ変換し、orchagent はこの APPL_DB 側を `ConsumerStateTable` で受け取る。

## 3. Orch::doTask() ディスパッチ

```cpp
// tunneldecaporch.cpp L51-75
void TunnelDecapOrch::doTask(Consumer &consumer)
{
    if (!gPortsOrch->allPortsReady()) return; // Observer パターン: PortsOrch ゲート
    string table_name = consumer.getTableName();
    if (table_name == APP_TUNNEL_DECAP_TABLE_NAME)
        doDecapTunnelTask(consumer);
    else if (table_name == APP_TUNNEL_DECAP_TERM_TABLE_NAME)
        doDecapTunnelTermTask(consumer);
    else if (table_name == CFG_SUBNET_DECAP_TABLE_NAME)
        doSubnetDecapTask(consumer);
}
```

- **Observer ゲート**: `gPortsOrch->allPortsReady()` が `false` の間は全 tunnel タスクが処理されない。PortsOrch が「全ポート ready」状態に到達すると orchagent の select ループが再び `doTask()` を呼ぶ。
- テーブル名によるディスパッチ（switch-on-string 相当）で各 sub-handler へ委譲。

## 4. SAI tunnel_api — 非同期呼び出しパターン

```cpp
// tunneldecaporch.cpp L853, L767-769 (抜粋)
extern sai_tunnel_api_t* sai_tunnel_api;

// トンネルオブジェクト作成
sai_status_t status = sai_tunnel_api->create_tunnel(
    &tunnel_id, gSwitchId, (uint32_t)tunnel_attrs.size(), tunnel_attrs.data());
task_process_status handle_status = handleSaiCreateStatus(SAI_API_TUNNEL, status);

// decap term 作成
status = sai_tunnel_api->create_tunnel_term_table_entry(
    &tunnel_term_id, gSwitchId, (uint32_t)term_attrs.size(), term_attrs.data());
```

- SAI API 呼び出しは `sai_tunnel_api` グローバルポインタ経由（`orchdaemon` 初期化時に `sai_api_query()` で取得）。
- `handleSaiCreateStatus()` が SAI エラーを `task_process_status` (`task_success` / `task_need_retry` / `task_failed`) に変換。
- `task_need_retry` の場合、Orch 基底クラスが当該エントリをキューに残し次サイクルで再試行（QoS map 未作成時の無限待機がこれ）。

## 5. 通信フロー全体図

```
CONFIG_DB
 TUNNEL|MuxTunnel0          SUBNET_DECAP (CONFIG_DB)
       │                              │
       ▼                              │
  tunnelmgrd                         │ SubscriberStateTable
  (cfgmgr)                           │
       │                             │
       │ ProducerStateTable          │
       ▼                             ▼
  APPL_DB                    TunnelDecapOrch
  TUNNEL_DECAP_TABLE ──────► doDecapTunnelTask()
  TUNNEL_DECAP_TERM_TABLE ──► doDecapTunnelTermTask()
  (ConsumerStateTable)       doSubnetDecapTask()
                                     │
                              gPortsOrch::allPortsReady() ゲート
                                     │
                                     ▼
                             sai_tunnel_api
                             create_tunnel()
                             create_tunnel_term_table_entry()
                                     │
                                     ▼
                               STATE_DB
                          STATE_TUNNEL_DECAP_TABLE
                          STATE_TUNNEL_DECAP_TERM_TABLE
```

## 6. STATE_DB 書き戻し (Observer 逆方向)

`tunneldecaporch.cpp` L287 付近:

```cpp
stateTunnelDecapTable->set(key, fvs);
// "Fields for TUNNEL_DECAP_TABLE entry '%s' have been synchronised in STATE_DB"
```

SAI `create_tunnel()` 成功後、`stateTunnelDecapTable`（STATE_DB）と `stateTunnelDecapTermTable` にエントリを書き戻す。これが「orchagent → STATE_DB」方向の Observer パターン出力。

## 7. 参考行番号

- `orchdaemon.cpp`: L343-347 (`TunnelDecapOrch` 初期化)
- `tunneldecaporch.cpp`:
  - L30-48: コンストラクタ（`SubscriberStateTable` + `addExecutor`）
  - L51-75: `doTask()` ディスパッチ
  - L81-336: `doDecapTunnelTask()`
  - L338-551: `doDecapTunnelTermTask()`
  - L553-766: `doSubnetDecapTask()`
  - L767-858: `addDecapTunnel()` → `sai_tunnel_api->create_tunnel()`
  - L282-291: STATE_DB 書き戻し
