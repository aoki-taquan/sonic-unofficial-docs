# copp-state Phase G 調査メモ (pubsub)

## 調査対象

STATE_DB の `COPP_GROUP_TABLE` / `COPP_TRAP_TABLE` / `COPP_TRAP_CAPABILITY_TABLE` における Redis 通信メカニズム

## Producer/Consumer パイプライン

### CONFIG_DB → CoppMgr (coppmgrd)

- `coppmgrd.cpp:28-31`: `CoppMgr` が `CFG_COPP_TRAP_TABLE_NAME`, `CFG_COPP_GROUP_TABLE_NAME`, `CFG_FEATURE_TABLE_NAME` の 3 テーブルに対し `SubscriberStateTable` を生成
- `Orch` 基底クラスの `addConsumer()` 経由
- keyspace notification で変化検出 → `CoppMgr::doTask()` → `doCoppTrapTask()` / `doCoppGroupTask()`

### CoppMgr → APPL_DB

- `coppmgr.h:71`: `ProducerStateTable m_appCoppTable`
- `coppmgr.cpp:301`: `m_appCoppTable(appDb, APP_COPP_TABLE_NAME)` で初期化
- `m_appCoppTable.set()` / `m_appCoppTable.del()` で APPL_DB の `COPP_TABLE|<group-name>` を操作

### APPL_DB → CoppOrch (orchagent)

- `orchdaemon.cpp:341`: `gCoppOrch = new CoppOrch(m_applDb, APP_COPP_TABLE_NAME)`
- `Consumer` (orchagent の Orch 基底) が `APP_COPP_TABLE_NAME` を keyspace notification で購読

### CoppOrch → STATE_DB

- `copporch.cpp:199-200`: コンストラクタで `Table m_trapCapabilityTable`, `Table m_trapTable` を STATE_DB に対して生成
- `Table::set()` / `Table::del()` の直接書き込み（通知なし）
- `COPP_TRAP_CAPABILITY_TABLE` のみ起動時 1 回 (`publishTrapIdsCapability()`, `copporch.cpp:208-215`)

## allPortsReady() ゲート

`copporch.cpp:885-888`:
```cpp
if (!gPortsOrch->allPortsReady()) {
    return;
}
```
全ポート初期化完了まで APPL_DB → STATE_DB の処理を保留。

## STATE_DB の読み出し側

- `show/copp.py:21`: `state_db.get_all(state_db.STATE_DB, f"COPP_TRAP_TABLE|{trap_id}")` — snapshot read
- `dump/plugins/copp.py:109-113`: `MatchRequest(db="STATE_DB", table="COPP_TRAP_TABLE")` 等 — snapshot read
- `SubscriberStateTable` による非同期購読はなし

## 検出事項

1. **3段パイプライン**: CONFIG_DB → coppmgrd (ProducerStateTable) → APPL_DB → orchagent (Consumer) → STATE_DB
2. **COPP_TRAP_CAPABILITY_TABLE の独立経路**: APPL_DB を経由せず orchagent 起動時の SAI クエリ結果を直接書き込み
3. **allPortsReady() による遅延**: PortsOrch が全ポート初期化を完了するまで STATE_DB への書き込みが始まらない
4. **STATE_DB 読み出しは poll のみ**: `show copp` / `dump copp` が snapshot read するだけで、非同期購読者は存在しない
