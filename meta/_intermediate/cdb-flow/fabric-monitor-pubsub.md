# FABRIC_MONITOR テーブル — Phase G: 通信メカニズム 中間ファイル

生成日: 2026-05-19 (q67-f-batch903b)

対象ページ: `docs/reference/config-db/fabric-monitor.md`
対象テーブル: `CONFIG_DB.FABRIC_MONITOR`
Producer: CLI (`config fabric`) / ランタイム書込なし
Consumer 1: `fabricmgrd` (`cfgmgr/fabricmgr.cpp`, `cfgmgr/fabricmgrd.cpp`)
Consumer 2: `FabricPortsOrch` (`orchagent/fabricportsorch.cpp`) — APPL_DB 経由

スキャン範囲:
- `fabricmgrd.cpp:14-72` — メインループと subscribe 登録
- `fabricmgr.cpp:14-21` — `FabricMgr` コンストラクタ (Orch 基底クラス初期化)
- `orchdaemon.cpp:604-610` — `FabricPortsOrch` 登録 (voq)
- `orchdaemon.cpp:1297-1303` — `FabricPortsOrch` 登録 (fabric)
- `fabricportsorch.cpp:80-133` — コンストラクタ、`Orch(appl_db, tableNames)` 初期化

---

## 購読方式の2段構成

`FABRIC_MONITOR` テーブルは CONFIG_DB → APPL_DB → orchagent の2段構成をとる。

### 段階1: fabricmgrd — CONFIG_DB 購読

`fabricmgrd` は `swsscommon` の `Orch` 基底クラスを通じて CONFIG_DB を購読する。

```cpp
// fabricmgrd.cpp:27-35
vector<string> cfg_fabric_tables = {
    CFG_FABRIC_MONITOR_DATA_TABLE_NAME,     // "FABRIC_MONITOR"
    CFG_FABRIC_MONITOR_PORT_TABLE_NAME,     // "FABRIC_PORT"
};
FabricMgr fabricmgr(&cfgDb, &appDb, cfg_fabric_tables);
```

`FabricMgr` コンストラクタ (`fabricmgr.cpp:14`) が `Orch(cfgDb, tableNames)` として初期化される。`Orch` 基底クラスは各テーブル名に対して **`ConsumerStateTable`** を生成し、CONFIG_DB の keyspace notification (`PSUBSCRIBE __keyspace@{db_id}__:FABRIC_MONITOR|*`) でエントリ変化を検出する。`pops()` で `(key, op, fieldValues)` タプルを取り出し `FabricMgr::doTask(Consumer&)` に渡す。

| 区間 | 方式 | 購読テーブル |
|------|------|------------|
| CONFIG_DB → fabricmgrd | `ConsumerStateTable` (swsscommon Orch 基底) | `CFG_FABRIC_MONITOR_DATA_TABLE_NAME` / `CFG_FABRIC_MONITOR_PORT_TABLE_NAME` |
| fabricmgrd → APPL_DB | `ProducerStateTable` (`set()` 呼び出し) | `APP_FABRIC_MONITOR_DATA_TABLE_NAME` / `APP_FABRIC_MONITOR_PORT_TABLE_NAME` |

**メインループ**:

```
fabricmgrd.cpp:46-65:
while (true) {
  s.select(&sel, SELECT_TIMEOUT=1000ms)  // Redis fd を poll
  if (TIMEOUT) { fabricmgr.doTask(); continue; }  // 空ループタスク
  c->execute();  // Consumer::drain() → FabricMgr::doTask(Consumer&)
}
```

`select()` は 1000 ms タイムアウト。タイムアウト時は `fabricmgr.doTask()` (引数なし) が呼ばれるが、`Orch::doTask()` のデフォルト実装は空なのでオーバーヘッドなし。イベント到着時のみ `execute()` → `drain()` → `FabricMgr::doTask(Consumer&)` が呼ばれる。

### 段階2: FabricPortsOrch — APPL_DB 購読

`FabricPortsOrch` は `Orch(appl_db, tableNames)` として初期化される。APPL_DB の以下テーブルを `SubscriberStateTable` で購読する:

```cpp
// orchdaemon.cpp:605-608
vector<table_name_with_pri_t> fabric_port_tables = {
    { APP_FABRIC_MONITOR_PORT_TABLE_NAME, 30 },   // "APP_FABRIC_MONITOR_PORT_TABLE"
    { APP_FABRIC_MONITOR_DATA_TABLE_NAME, 30 }    // "APP_FABRIC_MONITOR_DATA_TABLE"
};
```

| 区間 | 方式 | 購読テーブル |
|------|------|------------|
| APPL_DB → FabricPortsOrch | `SubscriberStateTable` (Orch 基底, priority=30) | `APP_FABRIC_MONITOR_PORT_TABLE_NAME` / `APP_FABRIC_MONITOR_DATA_TABLE_NAME` |
| FabricPortsOrch → SAI | SAI API 直接呼び出し | SAI fabric port / switch attributes |
| FabricPortsOrch → STATE_DB | `Table::hset()` (直接書込) | `FABRIC_PORT_TABLE`, `FABRIC_CAPACITY_TABLE` |

ただし `FabricPortsOrch` は APPL_DB イベントを受け取っても `doFabricPortTask()` で `checkFabricPortMonState()=true` でなければ early return する (`fabricportsorch.cpp:1396-1400`)。閾値・monState の読み込みはタイマー (`FABRIC_DEBUG_POLL` 12秒, `FABRIC_POLL` 30秒) 主導であり、APPL_DB イベントは補助的な役割。

---

## 購読方式の比較

| 観点 | `ConsumerStateTable` (fabricmgrd) | `SubscriberStateTable` (FabricPortsOrch) |
|------|-----------------------------------|------------------------------------------|
| 通知源 DB | CONFIG_DB | APPL_DB |
| Redis 機構 | keyspace notification (PSUBSCRIBE) | keyspace notification (PSUBSCRIBE) |
| 初回起動時先読み | Orch 基底クラス経由で `getKeys()` | Orch 基底クラス経由で `getKeys()` |
| メインループ | `Select` + `select()` (fabricmgrd.cpp:46) | orchdaemon `Select` ループ (SELECT_TIMEOUT=1000ms) |
| DEL コマンド処理 | ハンドラなし (doTask で `erase()` のみ) | ハンドラなし (同) |

---

## フルデータフロー

```
CLI: config fabric monitoring error-threshold <val>
  ↓ sonic-db-cli / swsscommon HSET
  ↓ CONFIG_DB: FABRIC_MONITOR|FABRIC_MONITOR_DATA  ← 永続化
  ↓ keyspace notification: PSUBSCRIBE __keyspace@config_db_id__:FABRIC_MONITOR|*
fabricmgrd select() loop (1000ms poll)
  ↓ Consumer::drain() → FabricMgr::doTask(Consumer&)
  ↓ writeConfigToAppDb("FABRIC_MONITOR_DATA", field, value)
  ↓ APPL_DB: APP_FABRIC_MONITOR_DATA_TABLE|FABRIC_MONITOR_DATA  ← 中継バッファ
  ↓ keyspace notification: APPL_DB keyspace
FabricPortsOrch (orchdaemon select() loop)
  ↓ doFabricPortTask() — monState=enable チェック
  [または FABRIC_DEBUG_POLL タイマー (12秒)]
  ↓ updateFabricDebugCounters() — APPL_DB から hgetall で閾値を一括読込
  ↓ SAI set_port_attribute (isolate/unisolate)
  ↓ STATE_DB: FABRIC_PORT_TABLE|PORT<n>, FABRIC_CAPACITY_TABLE
```

---

## ページ反映方針

- `<!-- pubsub -->` ブロックを `<!-- /platform -->` の直後に挿入する。
- 2段構成（fabricmgrd → FabricPortsOrch）を明示する。
- タイマー主導 vs イベント主導の違いを補足する。
