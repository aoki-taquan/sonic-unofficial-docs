# srv6-my-sids — Phase G: Pub/Sub・イベント通知

## 調査対象

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/manager.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`
- `sonic-swss/orchagent/srv6orch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

---

## 1. bgpcfgd パス — SubscriberStateTable ポーリング

### 購読メカニズム

`Runner.add_manager()` (`runner.py:31-52`):
- `swsscommon.SubscriberStateTable(conn, table_name)` を生成し `swsscommon.Select()` セレクタに登録。
- テーブル単位で 1 つの subscriber が共有される（重複生成なし）。
- `runner.py:49-51`: 同 DB・同テーブルを複数の Manager が購読する場合は、callbacks リストに追記するだけで subscriber は再作成されない。

`Runner.run()` (`runner.py:54-73`):
- `selector.select(SELECT_TIMEOUT=1000ms)` でイベントを待受け。
- イベント受信時: `subscriber.pop()` でキュードレインし、登録済みコールバック (`manager.handler()`) を順次呼び出す。
- 各イテレーションの末尾で `cfg_manager.commit()` を呼び出し、積み上がった FRR vtysh コマンドを一括送信。

### SRV6_MY_SIDS の登録（main.py:108）

```python
SRv6Mgr(common_objs, "CONFIG_DB", "SRV6_MY_SIDS")
```

- `add_manager()` を通じて `CONFIG_DB` の `SRV6_MY_SIDS` テーブルを SubscriberStateTable で購読。
- イベント形式: `(key, op, fvs)` — `op` は `"SET"` または `"DEL"`。
- コールバック先: `Manager.handler()` → `SRv6Mgr.set_handler()` / `SRv6Mgr.del_handler()`。

### インプロセス Directory 購読（bgpcfgd 内部）

`managers_srv6.py:67-68` でロケータ未存在時に追加登録される:

```python
self.directory.subscribe([(self.db_name, "SRV6_MY_LOCATORS", locator_name)], self.on_deps_change)
```

- これは Redis Pub/Sub ではなく **bgpcfgd インプロセスの Directory オブジェクト**（`directory.py`）内の通知機構。
- `SRV6_MY_LOCATORS` エントリが Directory に登録されると `on_deps_change()` が呼ばれ、保留中の SID エントリを再処理する。
- Redis チャンネルを使用しない（外部プロセスには見えない）。

---

## 2. Srv6Orch パス — Consumer/TableConnector

### orchdaemon での登録（orchdaemon.cpp:312-324）

```cpp
TableConnector srv6_sid_list_table(m_applDb, APP_SRV6_SID_LIST_TABLE_NAME);
TableConnector srv6_my_sid_table(m_applDb, APP_SRV6_MY_SID_TABLE_NAME);
TableConnector pic_context_table(m_applDb, APP_PIC_CONTEXT_TABLE_NAME);
TableConnector srv6_my_sid_cfg_table(m_configDb, CFG_SRV6_MY_SID_TABLE_NAME);

vector<TableConnector> srv6_tables = { ... };
gSrv6Orch = new Srv6Orch(m_configDb, m_applDb, srv6_tables, ...);
```

- `Orch(tables)` ベースクラスが各 `TableConnector` を `Consumer` としてラップし、swss Select ループに登録。
- `CFG_SRV6_MY_SID_TABLE_NAME` (`"SRV6_MY_SIDS"`) は CONFIG_DB の Consumer として直接購読。
- `APP_SRV6_MY_SID_TABLE_NAME` (`"SRV6_MY_SID_TABLE"`) は APP_DB の Consumer として購読。

### イベントルーティング（srv6orch.cpp:2352-2394）

```cpp
void Srv6Orch::doTask(Consumer &consumer) {
    const string &table_name = consumer.getTableName();
    ...
    if (table_name == APP_SRV6_SID_LIST_TABLE_NAME)       doTaskSidTable(t);
    else if (table_name == APP_SRV6_MY_SID_TABLE_NAME)    doTaskMySidTable(t);
    else if (table_name == APP_PIC_CONTEXT_TABLE_NAME)    doTaskPicContextTable(t);
    else if (table_name == CFG_SRV6_MY_SID_TABLE_NAME)    doTaskCfgMySidTable(t);
}
```

- `CFG_SRV6_MY_SID_TABLE_NAME` → `doTaskCfgMySidTable()`: dscp_mode キャッシュへの登録/削除のみ。SAI 操作なし。
- `APP_SRV6_MY_SID_TABLE_NAME` → `doTaskMySidTable()`: SAI MY_SID_ENTRY の作成/更新/削除。

### NeighOrch Observer パターン

`srv6orch.cpp:110`: `m_neighOrch->attach(this)` でオブザーバ登録。
`srv6orch.cpp:117`: デストラクタで `detach(this)`。

- Neighbor ADD/DEL イベント発生時、NeighOrch が `Srv6Orch::update(SUBJECT_TYPE_NEIGH_CHANGE, ...)` を呼び出す（`srv6orch.cpp:1346-1363`）。
- `update()` → `updateNeighbor()` (`srv6orch.cpp:1212-`) で `m_pendingSRv6MySIDEntries` の自動再インストールと、Neighbor 消失時の MY_SID ASIC 削除を行う。
- この Observer パターンは Redis Pub/Sub ではなく C++ オブジェクト間の直接コールバック。

---

## 3. FlexCounter タイマー通知

`srv6orch.cpp:138-139`: カウンタ有効時に 1 秒周期の `SelectableTimer` を登録。
`srv6orch.cpp:286-313` (`doTask(SelectableTimer&)`):
- `m_pending_counters` をポーリングし、ASIC_DB VIDTORID が解決されたエントリに対して `FlexCounter` カウンタ ID リストを設定。
- `gTraditionalFlexCounter` が false の場合は VIDTORID チェックをスキップしてすぐ登録。

---

## 4. 外部通知（Redis Keyspace / Pub/Sub チャンネル）

SRV6_MY_SIDS テーブルの変更は以下の Redis 書込みを通じて間接的に通知される:

| 通知先 | チャンネル/手段 | 発火タイミング |
|-------|--------------|------------|
| COUNTERS_DB `COUNTERS_SRV6_NAME_MAP` | `hset` / `hdel` | MySID 作成/削除時（カウンタ有効時のみ） |
| FLEX_COUNTER_DB | `setCounterIdList` / `clearCounterIdList` | カウンタ有効かつ VIDTORID 解決後 |
| APP_DB `SRV6_MY_SID_TABLE` | fpmsyncd が SET/DEL を発行（FRR → zebra → fpmsyncd 経路） | FRR の RIB 変化時（bgpcfgd パスとは別経路） |

CONFIG_DB から直接 Redis Pub/Sub チャンネルへの通知は行わない。

---

## 5. 購読チェーン全体像

```
CONFIG_DB SRV6_MY_SIDS
  ├─[bgpcfgd] SubscriberStateTable → Runner.select() → SRv6Mgr.handler()
  │    └─ FRR vtysh commit
  └─[Srv6Orch] Consumer(CFG_SRV6_MY_SID_TABLE) → doTaskCfgMySidTable()
         └─ dscp_mode キャッシュ更新のみ（SAI 操作なし）

APP_DB SRV6_MY_SID_TABLE
  └─[Srv6Orch] Consumer(APP_SRV6_MY_SID_TABLE) → doTaskMySidTable()
         └─ createUpdateMysidEntry() / deleteMysidEntry() → SAI

NeighOrch (C++ Observer)
  └─ Srv6Orch::update(SUBJECT_TYPE_NEIGH_CHANGE) → updateNeighbor()
         ├─ ADD: pending SID エントリ自動再インストール
         └─ DEL: pending SID エントリ ASIC 削除 → pending 移動
```
