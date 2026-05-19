# COPP port-binding (genetlink フィールド) — Phase G 通信メカニズムスキャンノート

対象ページ: `docs/reference/config-db/copp-port.md`
対象フィールド: `COPP_GROUP.genetlink_name` / `COPP_GROUP.genetlink_mcgrp_name`
Producer/Consumer パス: CONFIG_DB → coppmgrd → APPL_DB → CoppOrch → SAI (genetlink HostIf)
スキャン範囲: `coppmgrd.cpp` 全行、`coppmgr.cpp` L298-310, L510-530、`copporch.cpp` L191-215, L880-935、`orchdaemon.cpp`

---

## 検出した通信メカニズム

### 1. CONFIG_DB → coppmgrd (SubscriberStateTable)

`coppmgrd.cpp:28-32` で `cfg_copp_tables = {CFG_COPP_TRAP_TABLE_NAME, CFG_COPP_GROUP_TABLE_NAME, CFG_FEATURE_TABLE_NAME}` を引数に `CoppMgr` を生成する。`CoppMgr` の基底クラス `Orch` が `SubscriberStateTable` を生成し、CONFIG_DB の `COPP_GROUP|*` エントリの変化を keyspace notification で受信する。

`genetlink_name` / `genetlink_mcgrp_name` は `COPP_GROUP` フィールドの一部として他のフィールドと一緒に受信される。`doCoppGroupTask()` が全フィールドを読み出し APPL_DB に転送する。

### 2. coppmgrd → APPL_DB (ProducerStateTable)

`coppmgr.cpp:301,304` の `m_appCoppTable(appDb, APP_COPP_TABLE_NAME)` および `m_coppTable(appDb, APP_COPP_TABLE_NAME)` が `ProducerStateTable` として APPL_DB `COPP_TABLE|<group-name>` への書き込みを担う。`genetlink_name` / `genetlink_mcgrp_name` は coppmgr が特別処理せずそのまま全フィールドとして転記される（`coppmgr.cpp:510-530`）。

### 3. APPL_DB → CoppOrch (Consumer / keyspace notification)

`orchdaemon.cpp:341` で `orchagent` が `CoppOrch` に対して APPL_DB `COPP_TABLE` の `Consumer` を生成する。orchagent の `Select::select()` ループで変化を検知し、`CoppOrch::doTask(Consumer&)` を呼び出す。

`doTask()` の冒頭 (`copporch.cpp:885-888`) で `gPortsOrch->allPortsReady()` をチェックし、全ポート初期化完了まで処理を保留する。これが genetlink HostIf 作成の最初のブロッキングポイント。

### 4. CoppOrch → SAI (直接 API 呼び出し)

`processCoppRule()` → `getAttribsFromTrapGroup()` で `genetlink_attribs` を構築し、`createGenetlinkHostIf()` → `sai_hostif_api->create_hostif()` および `createGenetlinkHostIfTable()` → `sai_hostif_api->create_hostif_table_entry()` を呼ぶ。SAI API は orchagent から直接呼ばれ、DB 経由ではない。

### 5. genetlink_name / genetlink_mcgrp_name を読む consumer

`genetlink_name` / `genetlink_mcgrp_name` の値を DB から直接読み出す外部 consumer（show コマンド等）は存在しない。APPL_DB `COPP_TABLE` に書き込まれた値を `CoppOrch` が読んで SAI 操作に使うのみ。`show copp config` は CONFIG_DB の `COPP_GROUP` フィールドをそのまま表示するため、間接的に値を見ることができる。

### 6. select() ループのタイムアウトと非同期性

- `coppmgrd`: `SELECT_TIMEOUT = 1000 ms` (`coppmgrd.cpp:17`)。タイムアウト時は `coppmgr.doTask()` を呼ぶ（定常ポーリング）。
- `orchagent`: orchagent 共通の `SELECT_TIMEOUT`（通常 1000 ms）。genetlink HostIf 作成は `processCoppRule()` が呼ばれた時点で同期的に完了（または失敗）する。

---

## 通信メカニズム サマリ

| 区間 | 方式 | チャンネル/テーブル |
|------|------|-------------------|
| CONFIG_DB `COPP_GROUP\|*` → `CoppMgr` | `SubscriberStateTable` | keyspace notification |
| `CoppMgr` → APPL_DB `COPP_TABLE\|*` | `ProducerStateTable` | Redis Streams |
| APPL_DB `COPP_TABLE\|*` → `CoppOrch` | `Consumer` (Orch 基底) | keyspace notification |
| `CoppOrch` → SAI | 直接 API 呼び出し | `sai_hostif_api` |

---

## ページ反映方針

`<!-- /side-effects -->` の直後、ファイル末尾に `<!-- pubsub -->` ブロックを追加する。
