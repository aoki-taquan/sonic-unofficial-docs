# SFLOW テーブル — 通信メカニズム (Phase G) 解析メモ

対象: `CONFIG_DB` の `SFLOW` / `SFLOW_SESSION` / `SFLOW_COLLECTOR` テーブル。

## 1. 購読 API — `TableConnector` + `swss::Orch` フレームワーク

`sflowmgrd` は `swsscommon` C++ ライブラリの **`swss::Orch`** (ConsumerStateTable ベース) フレームワークを使い、`TableConnector` でラップした 4 つのテーブルを一括購読する。

```cpp
// sonic-swss/cfgmgr/sflowmgrd.cpp:31-43
TableConnector conf_port_table(&cfgDb, CFG_PORT_TABLE_NAME);
TableConnector state_port_table(&stateDb, STATE_PORT_TABLE_NAME);
TableConnector conf_sflow_table(&cfgDb, CFG_SFLOW_TABLE_NAME);
TableConnector conf_sflow_session_table(&cfgDb, CFG_SFLOW_SESSION_TABLE_NAME);

vector<TableConnector> sflow_tables = {
    conf_port_table,
    state_port_table,
    conf_sflow_table,
    conf_sflow_session_table
};

SflowMgr sflowmgr(&appDb, sflow_tables);
```

- `Orch` 基底クラスが各 `TableConnector` に対して `SubscriberStateTable` (keyspace 通知) または `ConsumerStateTable` (channel PUBLISH/SUBSCRIBE) を生成し、内部 `Select` ループに登録する。
- CONFIG_DB テーブル (`conf_sflow_table` / `conf_sflow_session_table` / `conf_port_table`) はキースペース通知で変更を受信する。
- STATE_DB テーブル (`state_port_table`) はオペレーション速度変化 (`oper_speed`) を受信するために購読する。

### 書込側 (Producer)

`SflowMgr` は `ProducerStateTable` で APPL_DB に書き込む:

```cpp
// sonic-swss/cfgmgr/sflowmgr.h:39-40
ProducerStateTable     m_appSflowTable;          // APPL_DB SFLOW_TABLE
ProducerStateTable     m_appSflowSessionTable;   // APPL_DB SFLOW_SESSION_TABLE
```

## 2. 購読者一覧

| 購読者プロセス | DB | 購読テーブル | 受信 API |
|---------------|----|------------|---------|
| `sflowmgrd` (`SflowMgr`) | CONFIG_DB | `SFLOW` (`CFG_SFLOW_TABLE_NAME`) | `Orch`/`SubscriberStateTable` |
| `sflowmgrd` (`SflowMgr`) | CONFIG_DB | `SFLOW_SESSION` (`CFG_SFLOW_SESSION_TABLE_NAME`) | 同上 |
| `sflowmgrd` (`SflowMgr`) | CONFIG_DB | `PORT` (`CFG_PORT_TABLE_NAME`) | 同上 |
| `sflowmgrd` (`SflowMgr`) | STATE_DB | `PORT_TABLE` (`STATE_PORT_TABLE_NAME`) | 同上 (oper_speed 受信) |
| `orchagent` (`SflowOrch`) | APPL_DB | `SFLOW_TABLE` (`APP_SFLOW_TABLE_NAME`) | `Orch`/ConsumerStateTable |
| `orchagent` (`SflowOrch`) | APPL_DB | `SFLOW_SESSION_TABLE` (`APP_SFLOW_SESSION_TABLE_NAME`) | 同上 |
| `orchagent` (`SflowOrch`) | APPL_DB | `SFLOW_SAMPLE_RATE_TABLE` | 同上 |

`SFLOW_COLLECTOR` テーブルは `sflowmgrd` が直接読み込み（`hsflowd.conf` 設定ファイル生成時に参照）するが、イベント駆動購読は `SFLOW` / `SFLOW_SESSION` 変更時の副次処理として発生する。

## 3. doTask 分岐とテーブル名ルーティング

`SflowMgr::doTask(Consumer &consumer)` はテーブル名でハンドラを振り分ける:

```cpp
// sonic-swss/cfgmgr/sflowmgr.cpp:403-410
void SflowMgr::doTask(Consumer &consumer)
{
    auto table = consumer.getTableName();
    if (table == CFG_PORT_TABLE_NAME)   { sflowUpdatePortInfo(consumer); return; }
    if (table == STATE_PORT_TABLE_NAME) { sflowProcessOperSpeed(consumer); return; }
    // SFLOW / SFLOW_SESSION は以降のコードで処理
}
```

`SflowOrch::doTask(Consumer &consumer)` の APPL_DB 側:

```cpp
// sonic-swss/orchagent/sfloworch.cpp:359-369
if (table_name == APP_SFLOW_TABLE_NAME)
{
    sflowStatusSet(consumer);  // m_sflowStatus フラグ更新のみ
    return;
}
// APP_SFLOW_SESSION_TABLE_NAME → SAI samplepacket セッション操作
```

## 4. イベントフロー

```
CLI/gNMI/db_migrator
  ↓ HSET "SFLOW|global" / "SFLOW_SESSION|<port>"
CONFIG_DB  (keyspace 通知)
  ↓ sflowmgrd::SflowMgr::doTask()
  ↓ ProducerStateTable::set()  →  APPL_DB SFLOW_TABLE / SFLOW_SESSION_TABLE
APPL_DB  (ConsumerStateTable channel)
  ↓ orchagent::SflowOrch::doTask()
  ↓ sai_samplepacket_api->create_samplepacket()  /  set_port_attribute()
SAI / ASIC
```

STATE_DB → sflowmgrd フロー (oper_speed 変化時のみ):

```
PORT oper_speed 変化
  ↓ STATE_DB PORT_TABLE 更新
  ↓ sflowmgrd::SflowMgr::sflowProcessOperSpeed()
  ↓ local_rate_cfg == false のポートにのみレート自動更新を反映
APPL_DB SFLOW_SESSION_TABLE  (上書き)
```

## 5. 起動時スナップショット

`sflowmgrd.cpp:46` の `sflowmgr.readPortConfig()` が起動時に CONFIG_DB の `PORT` テーブルを一括スキャンして `m_sflowPortConfMap` を構築する。Subscribe ループ前に実行されるため起動順序依存はない。

## 6. SFLOW_COLLECTOR の特殊扱い

`SFLOW_COLLECTOR` は `sflowmgrd` の `doTask` 購読テーブルに含まれない。SFLOW グローバル (`admin_state=up`) または SFLOW_SESSION の変化で `sflowHandleService(true)` が呼ばれた際に `hsflowd` 設定生成ルーティン内で CONFIG_DB から直接 `HGETALL "SFLOW_COLLECTOR|*"` で読み込む（スナップショット参照）。コレクタ単体の追加・変更に対しては `hsflowd` の再起動は自動では起きない—SFLOW グローバルの変更を別途加える必要がある点に注意。

## 7. 参考行番号

- `sonic-swss/cfgmgr/sflowmgrd.cpp:31-46`: テーブル登録・起動時スナップショット
- `sonic-swss/cfgmgr/sflowmgr.h:39-40`: ProducerStateTable 宣言
- `sonic-swss/cfgmgr/sflowmgr.cpp:13-16`: SflowMgr コンストラクタ (appSflowTable / appSflowSessionTable 初期化)
- `sonic-swss/cfgmgr/sflowmgr.cpp:403-410`: `doTask` テーブル名ルーティング
- `sonic-swss/orchagent/orchdaemon.cpp:439-444`: SflowOrch 登録 (APP_SFLOW_TABLE / SESSION / SAMPLE_RATE)
- `sonic-swss/orchagent/sfloworch.cpp:359-369`: `doTask` APPL_DB 振り分け
