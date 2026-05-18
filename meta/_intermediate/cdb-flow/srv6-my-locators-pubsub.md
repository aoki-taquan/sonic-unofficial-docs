# srv6-my-locators — Phase G: Pub/Sub・イベント通知

## 調査対象

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/runner.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_srv6.py`
- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/main.py`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `sonic-swss/orchagent/srv6orch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`
- `sonic-swss-common/common/subscriberstatetable.cpp`

調査日: 2026-05-18

---

## 1. bgpcfgd パス — SubscriberStateTable

### 購読メカニズム（runner.py:49, main.py:109）

`Runner.add_manager()` が `swsscommon.SubscriberStateTable(conn, "SRV6_MY_LOCATORS")` を生成し
`swsscommon.Select()` セレクタに登録する（`runner.py:49-51`）。

```python
# main.py:109
SRv6Mgr(common_objs, "CONFIG_DB", "SRV6_MY_LOCATORS")
```

`Runner.run()` (`runner.py:54-73`) は 1000 ms タイムアウトの `selector.select()` ループで動作する:
- タイムアウト (`TIMEOUT`): continue（再 select）
- エラー (`ERROR`): 例外送出
- イベント受信: `subscriber.pop()` でキュードレインし `Manager.handler()` を呼出し

イベントごとに `SRv6Mgr.set_handler()` または `SRv6Mgr.del_handler()` が呼ばれ、
ループ末尾で `cfg_mgr.commit()` が FRR vtysh コマンドを一括送信する。

### PSUBSCRIBE パターン（subscriberstatetable.cpp:20-24）

```cpp
m_keyspace = "__keyspace@" + to_string(db->getDbId()) + "__:" + tableName + "|*";
psubscribe(m_db, m_keyspace);
```

`SRV6_MY_LOCATORS` の PSUBSCRIBE パターン:

| DB | テーブル | PSUBSCRIBE パターン |
|----|---------|-------------------|
| CONFIG_DB (DB id=4) | `SRV6_MY_LOCATORS` | `__keyspace@4__:SRV6_MY_LOCATORS|*` |

`SRV6_MY_LOCATORS|<locator_name>` への HSET / DEL 操作で Redis が対応 keyspace 通知を自動 PUBLISH する。
`SubscriberStateTable.pops()` はフィールド値を通知ペイロードではなく **HGETALL で別途取得**するため、
通知→取得の間に更新があれば常に最新値が読まれる（lost-update 耐性あり）。

### 起動時スナップショット

`SubscriberStateTable` ctor (`subscriberstatetable.cpp:26-42`) は PSUBSCRIBE 直後に `m_table.getKeys()` で
既存全エントリを HGETALL し `SET_COMMAND` として `m_buffer` に積む。
bgpcfgd 起動時に `SRV6_MY_LOCATORS` が既に CONFIG_DB に存在すれば、PSUBSCRIBE 待ち不要で即座に処理される。

### インプロセス Directory 購読（bgpcfgd 内部）

ロケータ未存在時に `SRV6_MY_SIDS` の `sids_set_handler()` が追加登録する内部サブスクリプション
(`managers_srv6.py:67-68`):

```python
self.directory.subscribe([(self.db_name, "SRV6_MY_LOCATORS", locator_name)], self.on_deps_change)
```

これは Redis Pub/Sub ではなく bgpcfgd **インプロセスの Directory オブジェクト**内通知機構。
ロケータが Directory に登録されると `on_deps_change()` が発火し、保留中 SID が自動再処理される。
外部プロセスには見えない。

---

## 2. frrcfgd パス — SubscriberStateTable（zebra 経路）

`frrcfgd.py:121` にテーブル → ルータデーモンのマッピング:

```python
'SRV6_MY_LOCATORS': ['zebra'],
```

`frrcfgd.py:2335` でテーブルと共通ハンドラを登録:

```python
('SRV6_MY_LOCATORS', self.bgp_table_handler_common),
```

frrcfgd も同様に SubscriberStateTable で `SRV6_MY_LOCATORS` を購読し、
bgpcfgd と独立して vtysh コマンド（`locator <name> prefix ... block-len ...`）を zebra に送信する。
二重送信となるが FRR 設定は冪等なため実害はない。

---

## 3. Srv6Orch パス — Table（直接 GET、イベント購読なし）

`Srv6Orch` は `m_locatorCfgTable`（`srv6orch.cpp:107`）として CONFIG_DB の `SRV6_MY_LOCATORS` を
`Table` 型（`CFG_SRV6_MY_LOCATOR_TABLE_NAME`）で保持する:

```cpp
m_locatorCfgTable(cfgDb, CFG_SRV6_MY_LOCATOR_TABLE_NAME),  // srv6orch.cpp:107
```

**これは Consumer / SubscriberStateTable ではなく単純な GET 専用テーブル**。
`getLocatorCfgFromDb()` (`srv6orch.cpp:331-350`) が APPL_DB MySID イベント処理中に必要に応じて直接 GET する。
`SRV6_MY_LOCATORS` の変更イベントを Srv6Orch が受け取ることはない。

---

## 4. 購読チェーン全体像

```
CONFIG_DB SRV6_MY_LOCATORS
  ├─[bgpcfgd] SubscriberStateTable (PSUBSCRIBE __keyspace@4__:SRV6_MY_LOCATORS|*)
  │    → Runner.select(1000ms) → Manager.handler() → SRv6Mgr.locators_set/del_handler()
  │    → cfg_mgr.commit() → FRR vtysh: locator <name> prefix ...
  │
  ├─[frrcfgd] SubscriberStateTable (独立購読)
  │    → bgp_table_handler_common() → vtysh zebra: locator <name> prefix ...
  │
  └─[Srv6Orch] Table.get() (直接 GET のみ、イベント購読なし)
         → getLocatorCfgFromDb() が APPL_DB MySID 処理時に呼出し

bgpcfgd 内部 (Directory 購読):
  SRV6_MY_LOCATORS エントリ登録 → SRv6Mgr.on_deps_change() → 保留中 SID の自動再処理
  ※ Redis Pub/Sub ではなくインプロセス通知
```

---

## 5. 競合・レース

| 競合 | 影響 | 対策 |
|------|------|------|
| keyspace 通知 → HGETALL の間に更新 | 最新値が読まれる | SubscriberStateTable 仕様（lost-update なし） |
| bgpcfgd / frrcfgd 二重送信 | 同一 FRR コマンドを重複発行 | FRR 設定が冪等なため実害なし |
| Srv6Orch がロケータ変更を検知しない | MySID 処理はロケータ SET 後のイベントで自然解消 | ロケータ先行書き込みで回避 |

---

## 6. 参照コード

| ファイル | 行 | 内容 |
|---------|-----|------|
| `sonic-bgpcfgd/bgpcfgd/runner.py` | 27, 49-51 | `swsscommon.SubscriberStateTable` 生成・セレクタ登録 |
| `sonic-bgpcfgd/bgpcfgd/runner.py` | 54-73 | 1000ms `selector.select()` メインループ |
| `sonic-bgpcfgd/bgpcfgd/main.py` | 109 | `SRv6Mgr(... "SRV6_MY_LOCATORS")` 登録 |
| `sonic-bgpcfgd/bgpcfgd/managers_srv6.py` | 67-68 | Directory 内部購読（ロケータ待ち SID 向け） |
| `sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` | 121, 2335 | frrcfgd 独立 SubscriberStateTable 購読 |
| `sonic-swss/orchagent/srv6orch.cpp` | 107 | `m_locatorCfgTable` = Table GET 専用 |
| `sonic-swss/orchagent/srv6orch.cpp` | 331-338 | `getLocatorCfgFromDb()` — 直接 HGET |
| `sonic-swss-common/common/subscriberstatetable.cpp` | 17-43 | ctor — PSUBSCRIBE + 起動時スナップショット |
