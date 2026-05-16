# VRF — Phase G 通信メカニズム 中間ファイル

生成日: 2026-05-15 (q67-f-phaseG-vrf)

## 調査ソース

- `sonic-swss/cfgmgr/vrfmgrd.cpp`
- `sonic-swss/cfgmgr/vrfmgr.cpp`
- `sonic-swss/cfgmgr/vrfmgr.h`
- `sonic-swss/orchagent/vrforch.cpp`
- `sonic-swss/orchagent/vrforch.h`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss/orchagent/orch.cpp` (`Orch::addConsumer`)
- `sonic-swss-common/common/subscriberstatetable.cpp` / `.h`

---

## CONFIG_DB → vrfmgrd の通信メカニズム

### SubscriberStateTable (keyspace notification)

`vrfmgrd` は `Orch(cfgDb, tableNames)` コンストラクタ経由で `Orch::addConsumer()` を呼ぶ。
`addConsumer` は `CONFIG_DB`（db_id=4）を検出して `SubscriberStateTable` を生成する
（orch.cpp:1186-1196）。

購読テーブル（vrfmgrd.cpp:29-34）:

| テーブル | 定数 |
|---------|------|
| `VRF` | `CFG_VRF_TABLE_NAME` |
| `VNET` | `CFG_VNET_TABLE_NAME` |
| `VXLAN_EVPN_NVO` | `CFG_VXLAN_EVPN_NVO_TABLE_NAME` |
| `MGMT_VRF_CONFIG` | `CFG_MGMT_VRF_CONFIG_TABLE_NAME` |

`SubscriberStateTable` コンストラクタ（subscriberstatetable.cpp:17-43）:

```cpp
m_keyspace = "__keyspace@" + to_string(db->getDbId()) + "__:" + tableName + "|*";
psubscribe(m_db, m_keyspace);
// 初期スキャン: getKeys() → m_buffer に積み込み
```

Redis パターン例:
```
PSUBSCRIBE __keyspace@4__:VRF|*
```

イベント到達フロー:
1. Redis が `hset` / `hdel` / `del` を検知してキー空間通知を発行
2. `Select::select()` が fd を wake-up
3. `readData()` が `redisGetReply()` でイベントをバッファへ蓄積
4. `pops()` がイベントから key を抽出し `TABLE.get(key)` で現在値取得
5. `Consumer::execute()` → `VrfMgr::doTask(Consumer&)` を呼び出し

### doTask 内のテーブル別 dispatch (vrfmgr.cpp:275-363)

| consumer.getTableName() | SET | DEL |
|------------------------|-----|-----|
| `VXLAN_EVPN_NVO` | `doVrfEvpnNvoAddTask()` | `doVrfEvpnNvoDelTask()` |
| `VRF` / `MGMT_VRF_CONFIG` | `setLink()` → `m_stateVrfTable.set()` → `m_appVrfTableProducer.set()` | `isVrfObjExist()` 待機 → `m_appVrfTableProducer.del()` → `delLink()` |
| `VNET` | `setLink()` → `m_appVnetTableProducer.set()` | `m_appVnetTableProducer.del()` |

---

## vrfmgrd → APPL_DB の通信メカニズム

### ProducerStateTable

`vrfmgr.h:46` に宣言:

```cpp
ProducerStateTable m_appVrfTableProducer;    // APP_DB::VRF_TABLE
ProducerStateTable m_appVnetTableProducer;   // APP_DB::VNET_TABLE
ProducerStateTable m_appVxlanVrfTableProducer; // APP_DB::VXLAN_VRF_TABLE
```

書き込み操作（vrfmgr.cpp:303 / 338）:

```cpp
// SET 時
m_appVrfTableProducer.set(vrfName, kfvFieldsValues(t));
// DEL 時
m_appVrfTableProducer.del(vrfName);
```

`ProducerStateTable::set/del` は Lua スクリプト（`EVALSHA`）でアトミックに実行:
```
SADD VRF_TABLE_KEY_SET <vrfName>
HSET _VRF_TABLE:<vrfName> <fields>
PUBLISH VRF_TABLE_CHANNEL@0 G
```

---

## APPL_DB → orchagent (VRFOrch) の通信メカニズム

### ConsumerStateTable

`orchdaemon.cpp:283`:
```cpp
VRFOrch *vrf_orch = new VRFOrch(m_applDb, APP_VRF_TABLE_NAME, m_stateDb, STATE_VRF_OBJECT_TABLE_NAME);
```

`VRFOrch` は `Orch2(appDb, APP_VRF_TABLE_NAME, request_)` → `Orch::addConsumer()` を呼ぶ。
APPL_DB（db_id=0）に対しては `ConsumerStateTable` が選択される（orch.cpp:1194）。

```
SUBSCRIBE VRF_TABLE_CHANNEL@0
```

通知受信 → `consumer_state_table_pops.lua` で `SPOP KEY_SET` + `HGETALL _VRF_TABLE:<key>`
→ `VRFOrch::addOperation()` / `delOperation()` → `sai_virtual_router_api`。

---

## STATE_DB への書き込み

`vrfmgr.h:45`:
```cpp
Table m_stateVrfTable;        // STATE_DB::VRF_TABLE
Table m_stateVrfObjectTable;  // STATE_DB::VRF_OBJECT_TABLE (read-only in vrfmgrd)
```

| テーブル | タイミング | 操作 |
|---------|-----------|------|
| `STATE_VRF_TABLE|<name>` | VRF setLink 成功後 | `hset("state", "ok")` (vrfmgr.cpp:288-289) |
| `STATE_VRF_TABLE|<name>` | VRF delLink 実行前 | `del()` (vrfmgr.cpp:339) |
| `STATE_VRF_OBJECT_TABLE|<name>` | orchagent SAI VR 作成成功 | `hset("state", "ok")` （VRFOrch 側が書く） |
| `STATE_VRF_OBJECT_TABLE|<name>` | orchagent SAI VR 削除完了 | `del()` （VRFOrch 側が消す） |

`vrfmgrd` は `isVrfObjExist()` で `STATE_VRF_OBJECT_TABLE` を読み取り専用参照し、
VRF DEL 実行タイミングを制御する（2 フェーズ非同期削除）。

---

## select() ループと retry

`vrfmgrd.cpp:49-84`:

```cpp
swss::Select s;
s.addSelectables(vrfmgr.getSelectables());

while (true) {
    ret = s.select(&sel, SELECT_TIMEOUT);  // SELECT_TIMEOUT = 1000 ms
    if (ret == Select::TIMEOUT) {
        vrfmgr.doTask();  // 未処理タスクを全 consumer で再試行
        continue;
    }
    auto *c = (Executor *)sel;
    c->execute();
}
```

DEL 時に `isVrfObjExist()` が true（orchagent 未完了）の場合、
`it++; continue;` でキューに残し次のループで再試行（タイムアウトなし）。

---

## 通信フロー全体図（サマリ）

```
CONFIG_DB[VRF|*]
  │  keyspace notification: PSUBSCRIBE __keyspace@4__:VRF|*
  ▼
vrfmgrd::VrfMgr::doTask
  │  (VRF/MGMT_VRF_CONFIG) ProducerStateTable::set/del
  │  EVALSHA → SADD KEY_SET + HSET _VRF_TABLE:<key>
  │            + PUBLISH VRF_TABLE_CHANNEL@0 G
  ├─→ STATE_DB[VRF_TABLE|<name>] hset(state=ok) / del
  ▼
APPL_DB[VRF_TABLE|*]
  │  ConsumerStateTable: SUBSCRIBE VRF_TABLE_CHANNEL@0
  │  consumer_state_table_pops.lua → SPOP + HGETALL
  ▼
orchagent::VRFOrch::addOperation / delOperation
  │  sai_virtual_router_api::create_virtual_router / remove_virtual_router
  ├─→ STATE_DB[VRF_OBJECT_TABLE|<name>] hset(state=ok) / del
  ▼
SAI (ハードウェア VRF)
```
