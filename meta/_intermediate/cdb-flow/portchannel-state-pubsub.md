# portchannel-state — Phase G Redis 通知メカニズムスキャンノート

対象テーブル: `STATE_DB LAG_TABLE` (db id=6)
書き手: `teamsyncd` (`sonic-swss/teamsyncd/teamsync.cpp`) / `tlm_teamd` / `intfmgrd`（サブインタフェース時のみ）
読み手（購読者）: `tlm_teamd` (`sonic-swss/tlm_teamd/main.cpp`)、`intfmgrd`、`stpmgrd`、`vlanmgrd`、`nbrmgrd`
スキャン範囲: tlm_teamd/main.cpp, teamsync.cpp, intfmgr.cpp (L43-55), subscriberstatetable.cpp 精読

---

## 1. SubscriberStateTable の仕組み（共通基盤）

`SubscriberStateTable` (`sonic-swss-common/common/subscriberstatetable.cpp:L17-43`) はコンストラクタ内で以下を実行する:

1. `PSUBSCRIBE __keyspace@<db_id>__:<TABLE_NAME>|*` を Redis に送信し、keyspace notification を有効化
2. 起動時点で既存のすべてのキーを `getKeys()` で取得し `m_buffer` に `SET_COMMAND` として積む（既存エントリの初期同期）

`LAG_TABLE` に対する keyspace notification パターン:
```
__keyspace@6__:LAG_TABLE|*
```

(STATE_DB の db_id = 6 、`database_config.json:L10-12`)

---

## 2. tlm_teamd — SubscriberStateTable で LAG_TABLE を購読（主要購読者）

`tlm_teamd` (`main.cpp:L91-108`) は起動時に STATE_DB に接続し、`LAG_TABLE` の変化を `SubscriberStateTable` で購読する。

```cpp
swss::DBConnector db("STATE_DB", 0);
swss::SubscriberStateTable sst_lag(&db, STATE_LAG_TABLE_NAME);  // main.cpp:L98
s.addSelectable(&sst_lag);                                        // main.cpp:L99
```

### イベントループ（main.cpp:L101-127）

| `s.select()` 戻り値 | 処理 | タイムアウト |
|--------------------|------|------------|
| `OBJECT` | `update_interfaces(sst_lag, teamdctl_mgr)` → `values_store.update(mgr.get_dumps(false))` | なし（即時） |
| `TIMEOUT` | `teamdctl_mgr.process_add_queue()` + `values_store.update(mgr.get_dumps(true))` | 1000 ms |
| `ERROR` | SWSS_LOG_ERROR、rc=-2 | — |

- `select` タイムアウト: **1000 ms** (`ms_select_timeout = 1000`、`main.cpp:L68`)
- `OBJECT` 受信時: 即時 `update_interfaces()` で SET/DEL を処理し `get_dumps(false)` で teamdctl dump を取得して STATE_DB に書き込む
- `TIMEOUT` 時: `get_dumps(true)` でエラー許容モードで dump を取得し、定期的に STATE_DB を更新

### update_interfaces() の処理 (main.cpp:L24-52)

`sst_lag.pops(entries)` で全保留エントリを一括取得し:
- `op == "SET"` → `mgr.add_lag(lag_name)`（`VLAN_SUB_INTERFACE_SEPARATOR` を含むキーはスキップ）
- `op == "DEL"` → `mgr.remove_lag(lag_name)`

---

## 3. intfmgrd — SubscriberStateTable で LAG_TABLE を購読（副次購読者）

`intfmgrd` (`intfmgr.cpp:L50-53`) は `STATE_LAG_TABLE_NAME` に対して `SubscriberStateTable` を登録する:

```cpp
auto subscriberStateLagTable = new swss::SubscriberStateTable(stateDb,
        STATE_LAG_TABLE_NAME, DEFAULT_POP_BATCH_SIZE, 200);  // priority=200
auto stateLagConsumer = new Consumer(subscriberStateLagTable, this, STATE_LAG_TABLE_NAME);
Orch::addExecutor(stateLagConsumer);
```

- `doTask(Consumer)` が `STATE_LAG_TABLE_NAME` のイベントを受信すると `doPortTableTask()` を呼び出す（`intfmgr.cpp:L1183-1186`）
- `doPortTableTask()` は SET 時に `admin_status` / `mtu` 変化を検知してサブインタフェース (`PortChannelN.VID`) へカスケード更新する

---

## 4. stpmgrd / vlanmgrd / nbrmgrd — Table::get() によるポーリング（非購読）

`stpmgrd` / `vlanmgrd` / `nbrmgrd` は `SubscriberStateTable` による push 通知ではなく、自身のメインタスクループ内で **`m_stateLagTable.get(alias, temp)`** を呼び出してポーリングする方式:

- **vlanmgrd** (`vlanmgr.cpp:L497`): `VLAN_MEMBER` SET 処理のたびに `m_stateLagTable.get(alias)` を呼ぶ
- **stpmgrd** (`stpmgr.cpp:L1296`): STP ポート SET 処理のたびに `m_stateLagTable.get(alias)` を呼ぶ
- **nbrmgrd** (`nbrmgr.cpp:L47`): `m_stateLagTable` を保持し必要時に参照

これらのデーモンは LAG_TABLE の変化通知を受け取るわけではなく、それぞれのトリガーイベント（VLAN_MEMBER SET、STP ポート追加等）の処理タイミングで LAG_TABLE の現在値を参照する。

---

## 5. 通知フロー全体図

```
teamsyncd
  ├─ RTM_NEWLINK → m_stateLagTable.set(lagName, fvVector)
  │      ↓ Redis keyspace notification: __keyspace@6__:LAG_TABLE|<lag>
  │      ↓ PSUBSCRIBE パターン: __keyspace@6__:LAG_TABLE|*
  ├──→ [tlm_teamd] sst_lag.pops() → update_interfaces() → mgr.add_lag()
  │                                  → values_store.update(get_dumps())
  │                                    → STATE_DB LAG_TABLE に setup.*/runner.*/team_device.* 追記
  │                                    → STATE_DB LAG_MEMBER_TABLE に各メンバフィールド書込み
  └──→ [intfmgrd] stateLagConsumer → doPortTableTask()
                                       → updateSubIntfAdminStatus() / updateSubIntfMtu()
                                         → APP_DB INTF_TABLE|PortChannelN.VID に書込み

teamsyncd
  └─ RTM_DELLINK → m_stateLagTable.del(lagName)
         ↓ Redis keyspace notification: DEL event
         ↓
    [tlm_teamd] update_interfaces() → mgr.remove_lag(lag_name)
                                       → teamdctl 接続解除
    [intfmgrd] DEL イベント → doPortTableTask() でサブインタフェース状態クリーンアップ
```

---

## 6. 通知タイミング特性

| 項目 | 値 / 動作 |
|------|----------|
| tlm_teamd select タイムアウト | **1000 ms** (`main.cpp:L68`) |
| intfmgrd LAG_TABLE 購読 priority | **200** (`intfmgr.cpp:L51`) |
| intfmgrd PORT_TABLE 購読 priority | **100** (`intfmgr.cpp:L46`) |
| keyspace notification パターン | `__keyspace@6__:LAG_TABLE|*` |
| 起動時初期同期 | `SubscriberStateTable` コンストラクタが既存キーを `m_buffer` に積む |
| tlm_teamd DEL 後の teamdctl disconnect | `mgr.remove_lag()` が即時実行（select OBJECT / TIMEOUT どちらでも） |
| LAG_TABLE エントリの削除主体 | teamsyncd の `RTM_DELLINK` 処理のみ（tlm_teamd は LAG_TABLE を削除しない） |

---

## 順序依存サマリ（pubsub 観点）

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | teamsyncd `LAG_TABLE` SET → tlm_teamd `SubscriberStateTable` 通知 | push（keyspace notification） | select OBJECT で即時、TIMEOUT で最大 1 秒遅延 |
| 2 | teamsyncd `LAG_TABLE` SET → intfmgrd `SubscriberStateTable` 通知 | push（keyspace notification、priority=200） | 受信後 `doPortTableTask()` で即時処理 |
| 3 | teamsyncd `LAG_TABLE` SET → vlanmgrd / stpmgrd / nbrmgrd 認識 | ポーリング（Table::get() 呼び出し時） | 各デーモン自身のタスクループが次のイベントを受信したときに参照 |
| 4 | tlm_teamd `teamdctl` dump 取得失敗 → LAG_TABLE エントリは削除しない | 保護設計（`values_store.cpp:L284-291`） | teamsyncd の RTM_DELLINK が削除担当 |
