# FABRIC_PORT テーブル — Phase G: 通信メカニズム 中間ファイル

生成日: 2026-05-19 (chore/q67-f-batch1020)

対象ページ: `docs/reference/config-db/fabric-port.md`
対象テーブル: `CONFIG_DB.FABRIC_PORT`
Producer: CLI (`config fabric`) / `sonic-cfggen` (プラットフォーム init)
Consumer 1: `fabricmgrd` (`cfgmgr/fabricmgr.cpp`, `cfgmgr/fabricmgrd.cpp`)
Consumer 2: `FabricPortsOrch` (`orchagent/fabricportsorch.cpp`) — APPL_DB 経由

スキャン範囲:
- `fabricmgrd.cpp:14-72` — メインループと subscribe 登録
- `fabricmgr.cpp:14-21` — `FabricMgr` コンストラクタ
- `orchdaemon.cpp:604-610` — `FabricPortsOrch` 登録 (voq)
- `orchdaemon.cpp:1297-1303` — `FabricPortsOrch` 登録 (fabric)
- `fabricportsorch.cpp:80-133` — コンストラクタ、`Orch(appl_db, tableNames)` 初期化

---

## 購読方式の2段構成

`FABRIC_PORT` テーブルは CONFIG_DB → fabricmgrd → APPL_DB → FabricPortsOrch の 2 段中継構成をとる。

### 段階1: fabricmgrd — CONFIG_DB 購読

`fabricmgrd` は `swsscommon` の `Orch` 基底クラスを通じて CONFIG_DB を購読する。

```cpp
// fabricmgrd.cpp:27-35
vector<string> cfg_fabric_tables = {
    CFG_FABRIC_MONITOR_DATA_TABLE_NAME,   // "FABRIC_MONITOR"
    CFG_FABRIC_MONITOR_PORT_TABLE_NAME,   // "FABRIC_PORT"
};
FabricMgr fabricmgr(&cfgDb, &appDb, cfg_fabric_tables);
```

`FabricMgr` コンストラクタが `Orch(cfgDb, tableNames)` として初期化され、各テーブル名に対して `ConsumerStateTable` を生成する。CONFIG_DB の keyspace notification (`PSUBSCRIBE __keyspace@{db_id}__:FABRIC_PORT|*`) でエントリ変化を検出する。

| 購読元 | DB | テーブル定数 | 実テーブル名 | PSUBSCRIBE パターン |
|--------|----|------------|------------|-------------------|
| CONFIG_DB | CONFIG_DB (4) | `CFG_FABRIC_MONITOR_PORT_TABLE_NAME` | `FABRIC_PORT` | `__keyspace@4__:FABRIC_PORT|*` |

### 段階2: FabricPortsOrch — APPL_DB 購読

`fabricmgrd` は CONFIG_DB イベントを受けて APPL_DB の `APP_FABRIC_MONITOR_PORT_TABLE_NAME` ("FABRIC_PORT_TABLE") に `ProducerStateTable` 経由で書き込む（RPUSH + PUBLISH）。

`FabricPortsOrch` は APPL_DB の以下テーブルを `SubscriberStateTable` で購読する:

```cpp
// orchdaemon.cpp:605-608
vector<table_name_with_pri_t> fabric_port_tables = {
    { APP_FABRIC_MONITOR_PORT_TABLE_NAME, 30 },   // "FABRIC_PORT_TABLE"
    { APP_FABRIC_MONITOR_DATA_TABLE_NAME, 30 }    // "FABRIC_MONITOR_TABLE"
};
```

| 購読元 | DB | テーブル定数 | 実テーブル名 | PSUBSCRIBE パターン | 優先度 |
|--------|----|------------|------------|-------------------|-------|
| APPL_DB | APPL_DB (0) | `APP_FABRIC_MONITOR_PORT_TABLE_NAME` | `FABRIC_PORT_TABLE` | `__keyspace@0__:FABRIC_PORT_TABLE|*` | 30 |
| APPL_DB | APPL_DB (0) | `APP_FABRIC_MONITOR_DATA_TABLE_NAME` | `FABRIC_MONITOR_TABLE` | `__keyspace@0__:FABRIC_MONITOR_TABLE|*` | 30 |

---

## フルデータフロー

```
CLI: config fabric port status enable/disable <port>
  ↓ sonic-db-cli / swsscommon HSET
  ↓ CONFIG_DB: FABRIC_PORT|<port>   ← 永続化
  ↓ keyspace notification: PSUBSCRIBE __keyspace@4__:FABRIC_PORT|*
fabricmgrd select() loop (1000ms poll)
  ↓ Consumer::drain() → FabricMgr::doTask(Consumer&)
  ↓ m_appFabricPortTable.set(port, fieldValues)   (ProducerStateTable: RPUSH + PUBLISH)
  ↓ APPL_DB: FABRIC_PORT_TABLE|<port>   ← 中継バッファ
  ↓ channel PUBLISH: FABRIC_PORT_TABLE_CHANNEL@0
FabricPortsOrch (orchdaemon select() loop)
  ↓ doTask(Consumer&) → doFabricPortTask()
  ↓ checkFabricPortMonState() — APPL_DB FABRIC_MONITOR_TABLE.monState=enable チェック
  ↓ isolateFabricLink() / set_port_attribute(SAI_PORT_ATTR_FABRIC_ISOLATE)
  ↓ STATE_DB: FABRIC_PORT_TABLE|PORT<lane>
```

---

## ページ反映方針

- `<!-- pubsub -->` ブロックを `<!-- /side-effects -->` の直後（`<!-- ref-triangle:start -->` の前）に挿入する。
- 2段構成（fabricmgrd → FabricPortsOrch）と `ProducerStateTable` / `SubscriberStateTable` の使い分けを明示する。
- `monState` ゲートによる条件付き処理をフローに含める。
