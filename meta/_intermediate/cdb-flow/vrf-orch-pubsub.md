# vrf-orch — 通信メカニズム (pubsub) 調査メモ

## 調査対象

`docs/reference/config-db/vrf-orch.md` Phase G 追加分。
`vrfmgrd` の CONFIG_DB 購読方式と APPL_DB への書込み経路、および `VRFOrch` の APPL_DB 消費方式を調査する。

## 調査ファイル

- `sonic-swss/cfgmgr/vrfmgrd.cpp` — vrfmgrd エントリポイント
- `sonic-swss/cfgmgr/vrfmgr.cpp` — VrfMgr クラス（`Orch` 基底から `SubscriberStateTable` 継承）
- `sonic-swss/cfgmgr/vrfmgr.h` — VrfMgr クラス宣言
- `sonic-swss/orchagent/vrforch.cpp` + `vrforch.h` — VRFOrch クラス（`Orch2` 基底から `ConsumerStateTable` 継承）
- `sonic-swss/orchagent/orchdaemon.cpp` — VRFOrch の生成・登録

## 結果

### vrfmgrd 側: SubscriberStateTable で CONFIG_DB を購読

`VrfMgr` コンストラクタ (`vrfmgr.cpp:20`) は `Orch(cfgDb, tableNames)` を呼び出す。
`Orch` 基底の `addConsumer` は CONFIG_DB id (`db->getDbId() == CONFIG_DB`) に対して `SubscriberStateTable` を使用する。

購読テーブル一覧 (`vrfmgrd.cpp:29-33`):
- `CFG_VRF_TABLE_NAME` = `"VRF"` — 通常 VRF の追加・削除
- `CFG_VNET_TABLE_NAME` = `"VNET"` — VNET 統合エントリ
- `CFG_VXLAN_EVPN_NVO_TABLE_NAME` = `"VXLAN_EVPN_NVO"` — EVPN NVO/VTEP 設定
- `CFG_MGMT_VRF_CONFIG_TABLE_NAME` = `"MGMT_VRF_CONFIG"` — mgmt VRF 有効/無効

主ループのタイムアウト: `SELECT_TIMEOUT = 1000 ms`（1秒）。TIMEOUT ハンドラで `vrfmgr.doTask()` を呼び pending キューを処理する。

### vrfmgrd 側: APPL_DB への書込みは ProducerStateTable

`VrfMgr::doTask` が SET/DEL を処理した後:
- `m_appVrfTableProducer.set(vrfName, fields)` → `APPL_DB VRF_TABLE` (`APP_VRF_TABLE_NAME` = `"VRF_TABLE"`)
- `m_appVxlanVrfTableProducer.set/del()` → `APPL_DB VXLAN_VRF_TABLE` (EVPN VNI マッピング時のみ)
- `m_stateVrfTable.set/del()` → `STATE_DB VRF_TABLE` (書込み確認シグナル)

### vrfmgrd の STATE_DB VRF_OBJECT_TABLE 読み取り

`VrfMgr::isVrfObjExist()` は `m_stateVrfObjectTable.get(vrfName, temp)` (`vrfmgr.cpp:204-211`) で `STATE_DB VRF_OBJECT_TABLE` を直接 GET する（subscribe ではなく同期 GET）。
DEL フロー (`vrfmgr.cpp:331-346`) でループしながら `isVrfObjExist()` をポーリングし、VRFOrch が STATE_VRF_OBJECT_TABLE を削除するまで `ip link del` を保留する。

### VRFOrch 側: ConsumerStateTable で APPL_DB を消費

`VRFOrch` は `orchdaemon.cpp:283` で `new VRFOrch(m_applDb, APP_VRF_TABLE_NAME, m_stateDb, ...)` として生成される。
`Orch` 基底の `addConsumer` は APPL_DB id に対して `ConsumerStateTable` を使用（`orch.cpp:1186-1195`）。

`VRFOrch` は `Orch2` を継承し、`doTask(Consumer&)` を override してイベントを `addOperation` / `delOperation` に dispatch する。

## 結論

vrfmgrd は CONFIG_DB の `VRF`・`MGMT_VRF_CONFIG`・`VXLAN_EVPN_NVO`・`VNET` テーブルを `SubscriberStateTable` (Redis keyspace PSUBSCRIBE) で購読し、1 秒タイムアウトの select ループで処理する。
APPL_DB への書込みは `ProducerStateTable` 経由。
VRFOrch は APPL_DB の `VRF_TABLE` を `ConsumerStateTable` で消費する。
vrfmgrd は `STATE_DB VRF_OBJECT_TABLE` を同期 GET でポーリングし、VRFOrch の SAI 完了確認に使う。

## evidence

- `sonic-swss/cfgmgr/vrfmgrd.cpp:29-33`: cfg_vrf_tables 購読テーブル一覧
- `sonic-swss/cfgmgr/vrfmgrd.cpp:62`: `s.select(&sel, SELECT_TIMEOUT=1000)` — 1秒タイムアウトループ
- `sonic-swss/cfgmgr/vrfmgr.cpp:20-26`: VrfMgr コンストラクタ（`Orch(cfgDb, tableNames)` + ProducerStateTable 宣言）
- `sonic-swss/cfgmgr/vrfmgr.cpp:204-211`: `isVrfObjExist()` — STATE_DB VRF_OBJECT_TABLE の同期 GET ポーリング
- `sonic-swss/cfgmgr/vrfmgr.cpp:289,303`: `m_stateVrfTable.set()`, `m_appVrfTableProducer.set()` — ProducerStateTable 書込み
- `sonic-swss/orchagent/orchdaemon.cpp:283`: VRFOrch 生成
