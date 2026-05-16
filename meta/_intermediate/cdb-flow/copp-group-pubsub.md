# COPP_GROUP 通信メカニズム (Phase G)

## 対象テーブル

`CONFIG_DB COPP_GROUP`

## pub/sub 全経路

```
CONFIG_DB
  └─ COPP_GROUP テーブル
       │  (SubscriberStateTable / Consumer)
       ▼
  [docker-swss] coppmgrd
       │  CoppMgr::doTask() → doCoppGroupTask()
       │  Consumer: CFG_COPP_GROUP_TABLE_NAME
       │  ProducerStateTable: APP_COPP_TABLE_NAME
       ▼
  APP_DB
  └─ COPP_TABLE テーブル (APP_COPP_TABLE_NAME)
       │  (Consumer / OrchAgent)
       ▼
  [docker-swss] orchagent
       │  CoppOrch::processCoppTrapGroup()
       │  Consumer: APP_COPP_TABLE_NAME (= "COPP_TABLE")
       │  SAI API: sai_hostif_api
       ▼
  SAI / ASIC
  ├─ sai_hostif_api->create_hostif_trap_group()
  ├─ sai_hostif_api->set_hostif_trap_group_attribute()
  ├─ sai_policer_api->create_policer()
  └─ sai_hostif_api->create_hostif_trap()
```

## Consumer 登録詳細

### coppmgr (CONFIG_DB 購読)

- **クラス**: `CoppMgr` (`cfgmgr/coppmgr.cpp`)
- **購読テーブル**: `CFG_COPP_GROUP_TABLE_NAME` ("COPP_GROUP")、`CFG_COPP_TRAP_TABLE_NAME`、`CFG_FEATURE_TABLE_NAME`
- **登録方法**: コンストラクタ `CoppMgr::CoppMgr(cfgDb, appDb, stateDb, tableNames, copp_init_file)` で `Orch(cfgDb, tableNames)` に渡す
  - evidence: `coppmgr.cpp L296-297`
- **ハンドラ**: `doTask(Consumer &consumer)` → `doCoppGroupTask(consumer)`
  - evidence: `coppmgr.cpp L968-984`
- **書き込み先**: `m_appCoppTable.set(key, modified_fvs)` → `APP_DB COPP_TABLE`
  - evidence: `coppmgr.cpp L874, L891, L914`

### CoppOrch (APP_DB 購読)

- **クラス**: `CoppOrch` (`orchagent/copporch.cpp`)
- **購読テーブル**: `APP_COPP_TABLE_NAME` ("COPP_TABLE")
- **登録方法**: `CoppOrch::CoppOrch(DBConnector* db, string tableName) : Orch(db, tableName)` で APP_DB Consumer を登録
  - evidence: `copporch.cpp L191-192`
- **ハンドラ**: `processCoppTrapGroup()` (SET / DEL 分岐)
  - evidence: `copporch.cpp L737, L858`

## SAI hostif_trap_group_api 呼び出し

| 操作 | SAI API | 条件 | evidence |
|------|---------|------|----------|
| トラップグループ新規作成 | `sai_hostif_api->create_hostif_trap_group()` | `m_trap_group_map` に未登録 | `copporch.cpp L780` |
| トラップグループ属性更新 | `sai_hostif_api->set_hostif_trap_group_attribute()` | `m_trap_group_map` に登録済み | `copporch.cpp L762` |
| ポリサー作成 | `sai_policer_api->create_policer()` | `policer_attribs` が非空 | `copporch.cpp L795-801` |
| Genetlink hostif 作成 | `sai_hostif_api->create_hostif()` | `genetlink_attribs` が非空 | `copporch.cpp L664` |
| hostif テーブルエントリ作成 | `sai_hostif_api->create_hostif_table_entry()` | Genetlink hostif 作成後 | `copporch.cpp L453` |
| trap 作成 | `sai_hostif_api->create_hostif_trap()` | trap_id 追加時 | `copporch.cpp L515` |

## STATE_DB 書き込み

- `coppmgr` は `STATE_COPP_GROUP_TABLE_NAME` / `STATE_COPP_TRAP_TABLE_NAME` に状態 (`ok`) を書き込む
  - evidence: `coppmgr.cpp L302-303, setCoppGroupStateOk()`

## 特記事項

1. **init_cfg との統合**: `coppmgr` は起動時に `copp_cfg.json` (デフォルト) と CONFIG_DB 設定をマージする。`g_copp_init_set` に含まれるキーは CONFIG_DB イベントとして来ても無視される (`coppmgr.cpp L855-859`)
2. **ProducerStateTable vs Table**: `coppmgr` は `m_appCoppTable` として `ProducerStateTable` ではなく `Table` を使うため、APP_DB への書き込みは直接 SET/DEL となる
3. **グループ削除時の init 再投入**: CONFIG_DB から DEL が来ても、`m_coppGroupInitCfg` にエントリが存在する場合は init 設定で APP_DB を再設定する (`coppmgr.cpp L899-914`)
