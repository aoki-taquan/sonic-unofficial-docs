# CABLE_LENGTH テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `CABLE_LENGTH` テーブル。
ソース: `sonic-swss/cfgmgr/buffermgr.cpp`, `buffermgrdyn.cpp`, `cfgmgr/buffermgrd.cpp`

---

## 1. 購読登録 — TableConnector / Orch フレームワーク

`buffermgrd` (デーモンプロセス) は起動時に buffer モードを判定し、モードに応じて購読テーブルを登録する。

### dynamic buffer モード (`buffermgrdyn`)

```cpp
// buffermgrd.cpp:174-186
vector<TableConnector> buffer_table_connectors = {
    TableConnector(&cfgDb, CFG_PORT_TABLE_NAME),
    TableConnector(&cfgDb, CFG_PORT_CABLE_LEN_TABLE_NAME),   // ← CABLE_LENGTH
    TableConnector(&cfgDb, CFG_BUFFER_POOL_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PROFILE_TABLE_NAME),
    TableConnector(&cfgDb, CFG_BUFFER_PG_TABLE_NAME),
    ...
    TableConnector(&stateDb, STATE_BUFFER_MAXIMUM_VALUE_TABLE),
    TableConnector(&stateDb, STATE_PORT_TABLE_NAME)
};
cfgOrchList.emplace_back(new BufferMgrDynamic(&cfgDb, &stateDb, &applDb, &applStateDb, buffer_table_connectors, ...));
```

- `TableConnector` は内部で `swsscommon::SubscriberStateTable` を生成し、`Select` オブジェクトに登録する。
- `BufferMgrDynamic` は `Orch` サブクラスで、`select()` ループが各 `Consumer` からイベントを取り出す。

### static buffer モード (`buffermgr`)

```cpp
// buffermgrd.cpp:192-203
vector<string> cfg_buffer_tables = {
    CFG_PORT_TABLE_NAME,
    CFG_PORT_CABLE_LEN_TABLE_NAME,   // ← CABLE_LENGTH
    CFG_BUFFER_POOL_TABLE_NAME,
    ...
};
cfgOrchList.emplace_back(new BufferMgr(&cfgDb, &applDb, pg_lookup_file, cfg_buffer_tables));
```

- `Orch(cfgDb, tableNames)` コンストラクタが各テーブルに `SubscriberStateTable` を作成する。

---

## 2. CONFIG_DB SubscriberStateTable 購読フロー

```
CONFIG_DB (Redis db=4)
  └── CABLE_LENGTH|<name> (例: CABLE_LENGTH|AZURE)
        │
        │  [keyspace notification → SubscriberStateTable::pops()]
        ▼
  Consumer::m_toSync キュー
        │
        │  [Orch::execute() ループ]
        ▼
  BufferMgr::doTask(Consumer &)        ... static モード
  BufferMgrDynamic::doTask(Consumer &) ... dynamic モード
```

### dynamic モード: ハンドラマップディスパッチ

```cpp
// buffermgrdyn.cpp:450
m_bufferTableHandlerMap.insert(
    buffer_handler_pair(CFG_PORT_CABLE_LEN_TABLE_NAME,
                        &BufferMgrDynamic::handleCableLenTable));

// buffermgrdyn.cpp:3574-3610 (doTask)
string table_name = consumer.getTableName();
auto it = consumer.m_toSync.begin();
while (it != consumer.m_toSync.end()) {
    auto task_status = (this->*(m_bufferTableHandlerMap[table_name]))(it->second);
    // task_success → erase, task_need_retry → it++, task_failed → erase
}
```

---

## 3. CABLE_LENGTH イベント処理 — `handleCableLenTable()`

```cpp
// buffermgrdyn.cpp:2124-2200
task_process_status BufferMgrDynamic::handleCableLenTable(KeyOpFieldsValuesTuple &tuple)
{
    string op = kfvOp(tuple);
    if (op == SET_COMMAND) {
        m_cableLengths.clear();
        for (auto i : kfvFieldsValues(tuple)) {
            auto &port = fvField(i);
            auto &cable_length = fvValue(i);
            port_info_t &portInfo = m_portInfoLookup[port];

            m_cableLengths[port] = cable_length;
            if (portInfo.cable_length == cable_length) continue;  // no-op if unchanged
            portInfo.cable_length = cable_length;

            if (effectiveSpeed.empty()) { /* WARN, skip */ continue; }
            if (mtu.empty()) { mtu = DEFAULT_MTU_STR; }  // "9100" fallback

            switch (portInfo.state) {
            case PORT_INITIALIZING:
                portInfo.state = PORT_READY;
                // fall through
            case PORT_READY:
                task_status = refreshPgsForPort(port, effectiveSpeed, cable_length, mtu);
                break;
            case PORT_ADMIN_DOWN:
                /* skip */  break;
            }
        }
    }
    return task_status;
}
```

### ポートステート別の分岐

| `portInfo.state` | 処理 |
|-----------------|------|
| `PORT_INITIALIZING` | `PORT_READY` に遷移 → `refreshPgsForPort()` 呼び出し |
| `PORT_READY` | 即時 `refreshPgsForPort()` 呼び出し |
| `PORT_ADMIN_DOWN` | スキップ（ログのみ, `buffermgrdyn.cpp:2191-2194`） |

---

## 4. Lua plugin 経路 — headroom 計算

`refreshPgsForPort()` → `calculateHeadroomSize()` でベンダー固有の Lua スクリプトを Redis EVALSHA 経由で実行する。

### Lua スクリプトのロード

```cpp
// buffermgrdyn.cpp:76-115
string headroomPluginName = "buffer_headroom_" + platform + ".lua";
string bufferpoolPluginName = "buffer_pool_" + platform + ".lua";
string checkHeadroomPluginName = "buffer_check_headroom_" + platform + ".lua";

m_headroomSha = swss::loadRedisScript(applDb, headroomLuaScript);
m_bufferpoolSha = swss::loadRedisScript(applDb, bufferpoolLuaScript);
m_checkHeadroomSha = swss::loadRedisScript(applDb, checkHeadroomLuaScript);
```

- スクリプトは **APPL_DB** の Redis インスタンスにロードされる (`SCRIPT LOAD`)。
- ロード失敗時: `buffermgrd` は起動を中断する (`SWSS_LOG_ERROR`, `buffermgrdyn.cpp:121`)。
- プラットフォーム例: `buffer_headroom_mellanox.lua`, `buffer_headroom_broadcom.lua` 等。

### headroom 計算の EVALSHA 呼び出し

```cpp
// buffermgrdyn.cpp:603-648
void BufferMgrDynamic::calculateHeadroomSize(buffer_profile_t &headroom) {
    vector<string> keys = { headroom.name };
    vector<string> argv = {
        headroom.speed,
        headroom.cable_length,
        headroom.port_mtu,
        m_identifyGearboxDelay,
        to_string(headroom.lane_count)
    };
    auto ret = swss::runRedisScript(*m_applDb, m_headroomSha, keys, argv);
    // ret: ["xon:18432", "xoff:18432", "size:36864", "xon_offset:2048"]
    for (auto i : ret) {
        auto pairs = tokenize(i, ':');
        if (pairs[0] == "xon")    headroom.xon = pairs[1];
        if (pairs[0] == "xoff")   headroom.xoff = pairs[1];
        if (pairs[0] == "size")   headroom.size = pairs[1];
        if (pairs[0] == "xon_offset") headroom.xon_offset = pairs[1];
    }
}
```

- `EVALSHA m_headroomSha 1 <profile_name> <speed> <cable_length> <mtu> <gearbox_delay> <lane_count>`
- 結果は `buffer_profile_t` に格納され、後続の `allocateProfile()` で APPL_DB に書き込まれる。

---

## 5. APPL_DB ProducerStateTable 書き込み

headroom 計算後、`allocateProfile()` / `refreshPgsForPort()` が APPL_DB へ書き込む。

### 関連する ProducerStateTable メンバ (dynamic モード)

```cpp
// buffermgrdyn.cpp:46-47
m_applBufferObjectTables{
    ProducerStateTable(applDb, APP_BUFFER_PG_TABLE_NAME),      // BUFFER_PG_TABLE
    ProducerStateTable(applDb, APP_BUFFER_QUEUE_TABLE_NAME)    // BUFFER_QUEUE_TABLE
};
m_applBufferProfileListTables{
    ProducerStateTable(applDb, APP_BUFFER_PORT_INGRESS_PROFILE_LIST_NAME),
    ProducerStateTable(applDb, APP_BUFFER_PORT_EGRESS_PROFILE_LIST_NAME)
};
```

### static モードの ProducerStateTable (buffermgr.h:48-51)

```cpp
ProducerStateTable m_applBufferProfileTable;    // APP_BUFFER_PROFILE_TABLE_NAME
ProducerStateTable m_applBufferPgTable;         // APP_BUFFER_PG_TABLE_NAME
ProducerStateTable m_applBufferPoolTable;       // APP_BUFFER_POOL_TABLE_NAME
ProducerStateTable m_applBufferQueueTable;      // APP_BUFFER_QUEUE_TABLE_NAME
```

### 書き込み先テーブルと後続処理

| APPL_DB テーブル | 後続コンシューマ |
|----------------|----------------|
| `BUFFER_PROFILE_TABLE` | `bufferorch` の `ConsumerStateTable` → SAI `sai_buffer_api` |
| `BUFFER_PG_TABLE` | `bufferorch` → SAI PG headroom 設定 |
| `BUFFER_POOL_TABLE` | `bufferorch` → SAI buffer pool 設定 |

---

## 6. ConsumerStateTable — 下流 (`bufferorch`)

CABLE_LENGTH テーブル自体は APPL_DB に存在しない。`bufferorch` は APPL_DB の `BUFFER_PG_TABLE` / `BUFFER_PROFILE_TABLE` を `ConsumerStateTable` で購読し、`orchagent` 内の SAI 呼び出しへ変換する。このパスは `sonic-swss/orchagent/bufferorch.cpp` が担当する（本ファイルのスコープ外）。

---

## 7. 全体フロー図

```
CONFIG_DB
  CABLE_LENGTH|AZURE
     │
     │ SubscriberStateTable (Orch フレームワーク)
     ▼
  buffermgrd
  └── BufferMgrDynamic::handleCableLenTable()
        │
        ├─ portInfo.cable_length 更新
        ├─ refreshPgsForPort()
        │     └─ calculateHeadroomSize()
        │           └─ EVALSHA buffer_headroom_<platform>.lua
        │                 (APPL_DB Redis インスタンス上で実行)
        │                 → xon / xoff / size / xon_offset を返す
        │
        └─ ProducerStateTable::set()
              APPL_DB:BUFFER_PROFILE_TABLE
              APPL_DB:BUFFER_PG_TABLE
                    │
                    │ ConsumerStateTable (bufferorch)
                    ▼
              SAI buffer API
              (チップの PG headroom を設定)
```

---

## 8. static モードとの差異

| 項目 | static (`buffermgr`) | dynamic (`buffermgrdyn`) |
|-----|---------------------|------------------------|
| ケーブル長ハンドラ | `doCableTask()` (buffermgr.cpp) | `handleCableLenTable()` (buffermgrdyn.cpp) |
| headroom 計算 | `pg_profile_lookup.ini` 参照 (テーブルルックアップ) | Lua スクリプト EVALSHA (speed/cable/mtu/lane を入力) |
| APPL_DB 書き込み | `m_applBufferProfileTable.set()` 等 | `m_applBufferObjectTables[].set()` 等 |
| STATE_DB 参照 | なし | `STATE_PORT_TABLE` (lane 数), `STATE_BUFFER_MAXIMUM_VALUE_TABLE` (MMU サイズ) |

---

## 9. 参考行番号

| ファイル | 行番号 | 内容 |
|---------|-------|------|
| `cfgmgr/buffermgrd.cpp` | 174-186 | dynamic モード TableConnector 登録 (CFG_PORT_CABLE_LEN_TABLE_NAME 含む) |
| `cfgmgr/buffermgrd.cpp` | 191-203 | static モード cfg_buffer_tables 登録 |
| `cfgmgr/buffermgrdyn.cpp` | 46-47 | `m_applBufferObjectTables` ProducerStateTable 初期化 |
| `cfgmgr/buffermgrdyn.cpp` | 76-115 | Lua スクリプトロード (`loadLuaScript` / `loadRedisScript`) |
| `cfgmgr/buffermgrdyn.cpp` | 130 | `Orch::addExecutor(executor)` タイマー登録 |
| `cfgmgr/buffermgrdyn.cpp` | 450 | `m_bufferTableHandlerMap` への `handleCableLenTable` 登録 |
| `cfgmgr/buffermgrdyn.cpp` | 603-648 | `calculateHeadroomSize()` — `runRedisScript` EVALSHA |
| `cfgmgr/buffermgrdyn.cpp` | 2124-2200 | `handleCableLenTable()` 本体 |
| `cfgmgr/buffermgrdyn.cpp` | 3574-3610 | `doTask(Consumer &)` ディスパッチループ |
| `cfgmgr/buffermgr.h` | 48-51 | `m_applBuffer*Table` ProducerStateTable メンバ宣言 |
| `cfgmgr/buffermgr.cpp` | 21-33 | `BufferMgr` コンストラクタ — DB 接続と ProducerStateTable 初期化 |
| `cfgmgr/buffermgr.cpp` | 337 | `doBufferTableTask(Consumer &, ProducerStateTable &)` |
