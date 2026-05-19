# FABRIC_PORT テーブル — Phase G: 通信メカニズム 中間ファイル

生成日: 2026-05-19 (chore/q67-f-batch1014)

対象ページ: `docs/reference/config-db/fabric-port.md`
対象テーブル: `CONFIG_DB.FABRIC_PORT`
Producer: CLI (`config fabric`) / `sonic-cfggen` (init_cfg)
Consumer 1: `fabricmgrd` (`cfgmgr/fabricmgr.cpp`, `cfgmgr/fabricmgrd.cpp`)
Consumer 2: `FabricPortsOrch` (`orchagent/fabricportsorch.cpp`) — APPL_DB 経由

スキャン範囲:
- `fabricmgrd.cpp:14-72` — メインループと subscribe 登録
- `fabricmgr.cpp:14-21` — `FabricMgr` コンストラクタ (Orch 基底クラス初期化)
- `orchdaemon.cpp:601-611` — `FabricPortsOrch` 登録 (voq)
- `orchdaemon.cpp:1297-1303` — `FabricPortsOrch` 登録 (fabric)
- `fabricportsorch.cpp:80-133` — コンストラクタ、`Orch(appl_db, tableNames)` 初期化

---

## 購読方式の2段構成

`FABRIC_PORT` テーブルは CONFIG_DB → APPL_DB → orchagent の2段構成をとる。FABRIC_MONITOR と同じ
fabricmgrd / FabricPortsOrch パイプラインを共有する。

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

`FabricMgr` コンストラクタ (`fabricmgr.cpp:14`) が `Orch(cfgDb, tableNames)` として初期化される。`Orch` 基底クラスは各テーブル名に対して **`ConsumerStateTable`** を生成し、CONFIG_DB の keyspace notification (`PSUBSCRIBE __keyspace@{db_id}__:FABRIC_PORT|*`) でエントリ変化を検出する。`pops()` で `(key, op, fieldValues)` タプルを取り出し `FabricMgr::doTask(Consumer&)` に渡す。

| 区間 | 方式 | 購読テーブル |
|------|------|------------|
| CONFIG_DB → fabricmgrd | `ConsumerStateTable` (swsscommon Orch 基底) | `CFG_FABRIC_MONITOR_PORT_TABLE_NAME` (`FABRIC_PORT`) |
| fabricmgrd → APPL_DB | `ProducerStateTable` (`set()` 呼び出し) | `APP_FABRIC_MONITOR_PORT_TABLE_NAME` |

**メインループ**:

```
fabricmgrd.cpp:46-65:
while (true) {
  s.select(&sel, SELECT_TIMEOUT=1000ms)  // Redis fd を poll
  if (TIMEOUT) { fabricmgr.doTask(); continue; }  // 空ループタスク
  c->execute();  // Consumer::drain() → FabricMgr::doTask(Consumer&)
}
```

`select()` は 1000 ms タイムアウト。イベント到着時のみ `execute()` → `drain()` → `FabricMgr::doTask(Consumer&)` が呼ばれ、APPL_DB に中継される。

### 段階2: FabricPortsOrch — APPL_DB 購読

`FabricPortsOrch` は `Orch(appl_db, tableNames)` として初期化される。APPL_DB の以下テーブルを `SubscriberStateTable` で購読する:

```cpp
// orchdaemon.cpp:605-608 (voq)
vector<table_name_with_pri_t> fabric_port_tables = {
    { APP_FABRIC_MONITOR_PORT_TABLE_NAME, 30 },   // "APP_FABRIC_MONITOR_PORT_TABLE"
    { APP_FABRIC_MONITOR_DATA_TABLE_NAME, 30 }    // "APP_FABRIC_MONITOR_DATA_TABLE"
};
```

| 区間 | 方式 | 購読テーブル |
|------|------|------------|
| APPL_DB → FabricPortsOrch | `SubscriberStateTable` (Orch 基底, priority=30) | `APP_FABRIC_MONITOR_PORT_TABLE_NAME` / `APP_FABRIC_MONITOR_DATA_TABLE_NAME` |
| FabricPortsOrch → SAI | SAI API 直接呼び出し | SAI fabric port attributes (isolate, lane list) |
| FabricPortsOrch → STATE_DB | `Table::hset()` (直接書込) | `FABRIC_PORT_TABLE`, `FABRIC_CAPACITY_TABLE` |

`FabricPortsOrch` は APPL_DB イベントを受け取っても `doFabricPortTask()` で `checkFabricPortMonState()=true` でなければ early return する (`fabricportsorch.cpp:1396-1400`)。ポート状態の収集はタイマー (`FABRIC_POLL` 30秒、`FABRIC_DEBUG_POLL` 12秒) 主導であり、CONFIG_DB からのイベント到着は isolate/unisolate 操作のみトリガする。

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
CLI: config fabric port status enable/disable <port>
  ↓ sonic-db-cli / swsscommon HSET
  ↓ CONFIG_DB: FABRIC_PORT|<name>  ← 永続化
  ↓ keyspace notification: PSUBSCRIBE __keyspace@config_db_id__:FABRIC_PORT|*
fabricmgrd select() loop (1000ms poll)
  ↓ Consumer::drain() → FabricMgr::doTask(Consumer&)
  ↓ writeConfigToAppDb("APP_FABRIC_MONITOR_PORT_TABLE", key, fieldValues)
  ↓ APPL_DB: APP_FABRIC_MONITOR_PORT_TABLE|<name>  ← 中継バッファ
  ↓ keyspace notification: APPL_DB keyspace
FabricPortsOrch (orchdaemon select() loop)
  ↓ doFabricPortTask() — monState=enable チェック
  ↓ SAI set_port_attribute (SAI_PORT_ATTR_FABRIC_ISOLATE)
  ↓ STATE_DB: FABRIC_PORT_TABLE|PORT<lane> (isolate 状態フィールド群)
[タイマー主導 - 別パス]
  FABRIC_POLL (30秒): updateFabricPortState() → STATE_DB STATUS/REMOTE_MOD/REMOTE_PORT
  FABRIC_DEBUG_POLL (12秒): updateFabricDebugCounters() → STATE_DB CRC/FEC エラー関連
```

---

## ページ反映方針

- `<!-- pubsub -->` ブロックを `<!-- /side-effects -->` の直後、`<!-- ref-triangle:start -->` の前に挿入する。
- FABRIC_MONITOR と同じ 2段構成 (fabricmgrd → FabricPortsOrch) を明示する。
- タイマー主導 vs イベント主導の違いを補足する。
