# Phase D 中間ファイル — STATE_DB COPP 関連テーブルの失敗挙動

作成日: 2026-05-18
対象ページ: `docs/reference/config-db/copp-state.md`

## 調査方針

copp-state.md の STATE_DB 書き手は 2 プロセス:
- `coppmgrd` (coppmgr.cpp): `COPP_GROUP_TABLE` / `COPP_TRAP_TABLE.state` を書く
- `orchagent` (copporch.cpp): `COPP_TRAP_TABLE.hw_status` / `COPP_TRAP_CAPABILITY_TABLE` を書く

それぞれの失敗分岐を調査した。

## A. CoppOrch 初期化失敗 (orchagent 起動時)

### publishTrapIdsCapability — SAI capability query 失敗 (非致死)

- `sai_query_attribute_enum_values_capability()` が失敗した場合
- SWSS_LOG_NOTICE で "SAI capability query is failed" を記録
- `default_supported_trap_ids` (42 種、neighbor_miss 除く) にフォールバック
- `COPP_TRAP_CAPABILITY_TABLE|traps` は必ず書き込まれる (フォールバック値)
- orchagent は継続する (例外なし)
- evidence: `copporch.cpp:L262-299`

### initDefaultHostIntfTable — SAI 失敗 (致死)

- `sai_hostif_api->create_hostif_table_entry()` が失敗
- `handleSaiCreateStatus()` が `task_success` 以外を返すと `throw "CoppOrch initialization failure"`
- orchagent プロセスが abort → systemd が再起動
- `COPP_TRAP_CAPABILITY_TABLE` は publishTrapIdsCapability 後に呼ばれるため既に書き込み済み
- 再起動後に再書き込みされる
- evidence: `copporch.cpp:L318-326`

### initDefaultTrapGroup / initDefaultTrapIds — SAI 失敗 (致死)

- SAI get_switch_attribute / applyAttributesToTrapIds 失敗 → `throw "CoppOrch initialization failure"`
- 同上、orchagent abort → systemd 再起動
- evidence: `copporch.cpp:L377-385, L361-365`

## B. CoppOrch doTask — processCoppRule の失敗分岐

### allPortsReady() false (起動シーケンス待機)

- `doTask()` 冒頭で `gPortsOrch->allPortsReady()` をチェック
- false の場合は即 return (全 APPL_DB アイテムが保留)
- `COPP_TRAP_TABLE.hw_status` は書き込まれない
- PortsOrch が ready になるまで繰り返しチェック
- evidence: `copporch.cpp:L885-888`

### create_hostif_trap SAI 失敗 → hw_status 未書き込み

- `applyAttributesToTrapIds()` 内で `sai_hostif_api->create_hostif_trap()` が失敗
- `handleSaiCreateStatus()` → `parseHandleSaiStatusFailure(handle_status)` を return
- `updateTrapOperStatus()` (= hw_status 書き込み) は呼ばれない
- 呼び出し元 `processCoppRule()` が `task_failed` または `task_need_retry` を返す
- evidence: `copporch.cpp:L515-526`

### task_failed — 処理停止

- `processCoppRule()` が `task_failed` を返した場合
- `doTask()` は当該アイテムを `m_toSync.erase(it)` した後に `return` (以降のアイテムを処理しない)
- SWSS_LOG_ERROR "Processing copp task item failed, exiting."
- 該当グループの `COPP_TRAP_TABLE.hw_status` は書き込まれない
- 次イテレーションで残アイテムの処理が再開される
- evidence: `copporch.cpp:L920-923`

### task_need_retry — 次サイクルで再試行

- `processCoppRule()` が `task_need_retry` を返した場合
- `doTask()` は `it++` でアイテムを保留したまま次アイテムへ
- SWSS_LOG_ERROR "Processing copp task item failed, will retry."
- 次のセレクタイテレーションで同じアイテムが再処理される
- evidence: `copporch.cpp:L924-927`

### task_invalid_entry — サイレントドロップ + 継続

- 例外 (out_of_range / std::exception) が発生した場合
- SWSS_LOG_ERROR "Invalid copp task item was encountered, removing from queue."
- `m_toSync.erase(it)` で永久にキューから除去
- 次アイテムの処理は継続
- evidence: `copporch.cpp:L916-918`

### Genetlink 重複作成 — task_failed

- `m_trap_group_hostif_map` に既存エントリがある場合
- SWSS_LOG_ERROR "Genetlink hostif exists for the trap group %s"
- `task_failed` を返す → 処理停止
- evidence: `copporch.cpp:L835-840`

## C. coppmgrd — STATE_DB 書き込みの失敗挙動

### setCoppGroupStateOk / setCoppTrapStateOk — 戻り値なし

- `m_stateCoppGroupTable.set()` / `m_stateCoppTrapTable.set()` は void
- Redis I/O 失敗時は `swss::DBConnector` が例外を throw
- coppmgrd プロセスが abort → systemd 再起動で自己回復
- STATE_DB 不整合が永続することは設計上ない

### trap_group / trap_ids が空の場合のサイレントスキップ (coppmgrd)

- `doCoppTrapTask()` で `trap_group.empty() || trap_ids.empty()` の場合
- `m_toSync.erase(it)` で恒久スキップ (エラーログなし)
- `setCoppTrapStateOk()` は呼ばれない → `COPP_TRAP_TABLE.state` は書き込まれない
- evidence: `coppmgr.cpp:L609-613`

## D. STATE_DB 不整合が発生しうるケース

| ケース | 結果 |
|--------|------|
| `state=ok` あり、`hw_status` なし | coppmgrd 書き込み完了、orchagent の SAI 操作未完了 (正常な中間状態) |
| `hw_status=installed` あり、`state` なし | coppmgrd が DEL 後、orchagent の remove_hostif_trap が未実行 (過渡的) |
| SAI init で create_hostif_trap 失敗 | `hw_status` 未書き込み。orchagent 再起動後に再試行 |
| coppmgrd: trap_group/trap_ids 欠落 | `state` 未書き込み (サイレントスキップ) |

## 証跡

- `copporch.cpp:L222-236, L240-300, L315-390, L499-532, L880-934` 読了
- `coppmgr.cpp:L424-451, L531-815` 読了
- task_status 分岐: `copporch.cpp:L910-932`
