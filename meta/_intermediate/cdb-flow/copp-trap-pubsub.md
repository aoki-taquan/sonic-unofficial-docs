# COPP_TRAP — Phase G: Redis PUBSUB / keyspace / ConsumerStateTable / Notification

## 調査対象ファイル

- `sonic-swss/cfgmgr/coppmgrd.cpp` — エントリポイント、Select ループ
- `sonic-swss/cfgmgr/coppmgr.h` — CoppMgr クラス定義、ProducerStateTable
- `sonic-swss/cfgmgr/coppmgr.cpp` — CoppMgr::CoppMgr() コンストラクタ、doCoppTrapTask()
- `sonic-swss/orchagent/copporch.cpp` — CoppOrch::doTask()、processCoppRule()
- `sonic-swss/orchagent/orchdaemon.cpp` — CoppOrch 初期化 (L341)

## 購読メカニズム全体像

COPP_TRAP テーブルの変更通知は **SubscriberStateTable（keyspace PSUBSCRIBE）→ CoppMgr → ProducerStateTable → ConsumerStateTable → CoppOrch** の 2 段構成で伝達される。

```
CONFIG_DB[COPP_TRAP|*]
  ↓ SubscriberStateTable (PSUBSCRIBE __keyspace@{db_id}__:COPP_TRAP|*)
CoppMgr (coppmgrd) :: doCoppTrapTask()
  ↓ ProducerStateTable (EVALSHA: SADD + HSET + PUBLISH COPP_TABLE_CHANNEL@0)
APPL_DB[COPP_TABLE|<group>]  ← COPP_TRAP が COPP_GROUP 単位に再集計されて書き込まれる
  ↓ ConsumerStateTable (SUBSCRIBE COPP_TABLE_CHANNEL@0 → pops.lua)
CoppOrch (orchagent) :: doTask(Consumer&) → processCoppRule() → SAI sai_hostif_api
```

## 段階別詳細

### 1. CONFIG_DB → CoppMgr (SubscriberStateTable / keyspace notification)

`coppmgrd.cpp` の `main()` (L37-49) は `DBConnector` を 3 本 (CONFIG_DB / APPL_DB / STATE_DB) 接続し、
`CoppMgr` に渡す:

```cpp
DBConnector cfgDb("CONFIG_DB", 0);
DBConnector appDb("APPL_DB", 0);
DBConnector stateDb("STATE_DB", 0);
CoppMgr coppmgr(&cfgDb, &appDb, &stateDb, cfg_copp_tables);
```

`cfg_copp_tables` に登録されるテーブル名 (coppmgrd.cpp:28-32):

| テーブル名 | 定数 |
|-----------|------|
| `COPP_TRAP` | `CFG_COPP_TRAP_TABLE_NAME` |
| `COPP_GROUP` | `CFG_COPP_GROUP_TABLE_NAME` |
| `FEATURE` | `CFG_FEATURE_TABLE_NAME` |

`Orch` 基底クラスがこれらテーブルに対し `SubscriberStateTable` を生成し、Redis keyspace notification を PSUBSCRIBE する:

```
PSUBSCRIBE __keyspace@4__:COPP_TRAP|*
PSUBSCRIBE __keyspace@4__:COPP_GROUP|*
PSUBSCRIBE __keyspace@4__:FEATURE|*
```

### 2. Select ループ (coppmgrd.cpp L45-70)

```cpp
swss::Select s;
s.addSelectables(coppmgr.getSelectables());

while (true) {
    ret = s.select(&sel, SELECT_TIMEOUT);  // SELECT_TIMEOUT = 1000 ms
    if (ret == Select::TIMEOUT) {
        coppmgr.doTask();  // 未処理タスクの再試行
        continue;
    }
    auto *c = (Executor *)sel;
    c->execute();  // → Orch::execute() → doTask(Consumer&)
}
```

- タイムアウト 1000 ms ごとに `doTask()` を呼んで pending タスクを再試行
- イベント受信時は `c->execute()` → `CoppMgr::doTask(Consumer&)` → `doCoppTrapTask()` / `doCoppGroupTask()` / `doFeatureTask()` に分岐

### 3. CoppMgr::doCoppTrapTask() — COPP_TRAP → APPL_DB 変換

`coppmgr.cpp:531-835` の主要フロー:

- `SET` コマンド: `m_coppTrapConfMap` にエントリを記録し、`addTrapIdsToTrapGroup()` 経由で trap_group の `trap_ids` リストを再構築して APPL_DB に書き込む
- `DEL` コマンド: `removeTrapIdsFromTrapGroup()` で該当 trap_ids を削除し、グループが空になれば `m_appCoppTable.del(key)`

**重要**: CONFIG_DB の COPP_TRAP エントリは **1 trap/key** だが、APPL_DB の `COPP_TABLE` エントリは **1 group/key** (group に属す全 trap_ids を集約)。CoppMgr がこの変換を担う。

### 4. CoppMgr → APPL_DB (ProducerStateTable / PUBLISH)

`coppmgr.h:71` で `ProducerStateTable m_appCoppTable` として宣言。
書き込み (`m_appCoppTable.set(trap_group, fvs)`) は Lua スクリプト (`EVALSHA`) で原子的に実行:

1. `SADD COPP_TABLE_KEY_SET <trap_group>` — 変更キーをセットに追加
2. `HSET _COPP_TABLE:<trap_group> <fields>` — 一時 hash に値を書き込む
3. `PUBLISH COPP_TABLE_CHANNEL@0 G` — orchagent を wake-up する通知を送信

### 5. APPL_DB → CoppOrch (ConsumerStateTable / SUBSCRIBE)

`orchdaemon.cpp:341` で CoppOrch を初期化:

```cpp
gCoppOrch = new CoppOrch(m_applDb, APP_COPP_TABLE_NAME);
// APP_COPP_TABLE_NAME = "COPP_TABLE"
```

`CoppOrch` は `Orch(db, tableName)` 基底コンストラクタ経由で `ConsumerStateTable` を登録:

```
SUBSCRIBE COPP_TABLE_CHANNEL@0
→ wake-up → EVALSHA pops.lua → SPOP KEY_SET + HGETALL _COPP_TABLE:<group>
→ CoppOrch::doTask(Consumer&)
```

### 6. CoppOrch::doTask() — ポート初期化ガード

`copporch.cpp:885`:

```cpp
if (!gPortsOrch->allPortsReady()) {
    return;  // ポート初期化完了まで全タスクを保留
}
```

全ポートが ready になるまで Consumer 内のタスクはキューに積まれたまま保留される。

### 7. STATE_DB への書き込み

CoppMgr は `m_stateCoppTrapTable` / `m_stateCoppGroupTable` を通じて STATE_DB にも書き込む:

- `setCoppTrapStateOk(key)`: COPP_TRAP エントリが APPL_DB に正常書き込まれた際に STATE_DB `COPP_TRAP_TABLE|<key>` に `state=ok` を書き込む
- `delCoppTrapStateOk(key)`: エントリ削除時に STATE_DB からも削除

CoppOrch は SAI trap 適用後に STATE_DB `COPP_TRAP_TABLE|<key>` の `hw_status` フィールドを更新する (`updateTrapOperStatus()`)。

### 8. FEATURE テーブルとの連携

`doFeatureTask()` (coppmgr.cpp:928-967) は `FEATURE` テーブルの変化を購読し、feature state 変化のたびに `setFeatureTrapIdsStatus(key, enable)` を呼び出して影響する COPP_TRAP を再評価・再書き込みする。`always_enabled=true` の trap はこの影響を受けない (`coppmgr.cpp:90`)。

### 9. TTL と永続性

APPL_DB・STATE_DB への書き込みはいずれも TTL なし (`DEFAULT_DB_TTL = -1`)。ProducerStateTable の `EXPIRE` コマンドは発行されない。

## メカニズム種別まとめ

| 区間 | メカニズム | 実装クラス | 証跡 |
|------|-----------|-----------|------|
| CONFIG_DB `COPP_TRAP` → CoppMgr | keyspace PSUBSCRIBE | `SubscriberStateTable` | coppmgrd.cpp:28-49 |
| CoppMgr → APPL_DB `COPP_TABLE` | ProducerStateTable (EVALSHA + PUBLISH) | `ProducerStateTable` | coppmgr.h:71, coppmgr.cpp:511 |
| APPL_DB `COPP_TABLE` → CoppOrch | ConsumerStateTable (SUBSCRIBE + pops.lua) | `ConsumerStateTable` | orchdaemon.cpp:341 |
| CoppOrch → SAI | 同期 SAI API 呼び出し | `sai_hostif_api` | copporch.cpp:880-934 |
| CoppMgr → STATE_DB | 直接 `Table::set()` | `Table` | coppmgr.cpp:367,450 |
| FEATURE 変化 → trap 再評価 | keyspace PSUBSCRIBE (FEATURE テーブル) | `SubscriberStateTable` | coppmgrd.cpp:31, coppmgr.cpp:928 |
