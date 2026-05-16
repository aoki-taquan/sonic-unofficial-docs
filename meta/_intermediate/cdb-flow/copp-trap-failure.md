# COPP_TRAP — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-copp-trap)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/copporch.cpp` (ref: master)
補助: `sonic-net/sonic-swss/cfgmgr/coppmgr.cpp`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| 未知の `trap_id` 文字列 (`trap_id_map.at()` が `out_of_range` 例外送出) | `doTask()` L900 catch | ERROR ログ → `task_invalid_entry` → `erase(it)` → 次 entry へ continue (恒久スキップ) | `copporch.cpp:900-903, 916-918` |
| `getAttribsFromTrapGroup()` が false を返す (不明フィールド等) | `processCoppRule()` L749 | `task_invalid_entry` を即時 return → `erase(it)` | `copporch.cpp:749-753` |
| SAI `create_hostif_trap_group` 失敗 | `processCoppRule()` L780 | ERROR ログ → `handleSaiCreateStatus()` の戻り値に依存; `task_failed` なら erase + return、`task_need_retry` なら `it++` | `copporch.cpp:780-788` |
| SAI `set_hostif_trap_group_attribute` 失敗 | `processCoppRule()` L762 | ERROR ログ → `handleSaiSetStatus()` の戻り値に依存; `task_failed` → erase + return | `copporch.cpp:762-770` |
| ポリサー作成失敗 (`trapGroupUpdatePolicer()` が false) | `processCoppRule()` L796 | `task_failed` を即時 return → erase + `SWSS_LOG_ERROR("Processing copp task item failed, exiting.")` → loop 中断 | `copporch.cpp:796-800, 920-923` |
| SAI `create_hostif_trap` 失敗 | `addTrapIdsToGroup()` L515 | ERROR ログ → `handleSaiCreateStatus()`; 回復不可なら `parseHandleSaiStatusFailure()` → false → 呼び出し元へ伝播し `task_failed` | `copporch.cpp:516-523` |
| Genetlink hostif が既に存在する状態で再作成を試みた | `processCoppRule()` L835 | ERROR ログ → `task_failed` → loop 中断 | `copporch.cpp:835-840` |
| `createGenetlinkHostIf()` 失敗 | `processCoppRule()` L844 | `task_failed` → loop 中断 | `copporch.cpp:844-847` |
| `createGenetlinkHostIfTable()` 失敗 | `processCoppRule()` L848 | `task_failed` → loop 中断 | `copporch.cpp:848-851` |
| `trapGroupProcessTrapIdChange()` 失敗 | `processCoppRule()` L853 | `task_failed` → loop 中断 | `copporch.cpp:853-856` |
| 汎用 `exception` 送出 | `doTask()` L905 catch | ERROR ログ → `task_invalid_entry` → `erase(it)` | `copporch.cpp:905-908` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| default trap group の削除試行 | `processCoppRule()` L861 | WARN ログ → `task_ignore` → `erase(it)` (サイレント無視) | `copporch.cpp:861-865` |
| `processTrapGroupDel()` が false を返す (SAI 削除失敗等) | `processCoppRule()` L867 | `task_failed` → erase + return → loop 中断 | `copporch.cpp:867-870` |
| SAI `remove_hostif_trap` 失敗 | `removeTrap()` (内部) | ERROR ログ `"Failed to remove trap object"` → false 返却 | `copporch.cpp:1404` |
| SAI `remove_policer` 失敗 | `removePolicer()` L566 | ERROR ログ → `parseHandleSaiStatusFailure()` → false 返却 | `copporch.cpp:566` |

### coppmgr 側の失敗経路

| 失敗条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| init cfg ファイル (`copp_cfg.json`) が存在しない | `parseInitFile()` L26 | ERROR ログ → `return` (ファイルなしでも起動継続、デフォルトトラップなし) | `coppmgr.cpp:26-30` |
| `trap_group` または `trap_ids` が空 かつ `always_enabled` も空 | `doCoppTrapTask()` L609 | 不完全設定として `erase(it)` → スキップ | `coppmgr.cpp:609-615` |
| `trap_group` が `checkTrapGroupPending()` = true (全 trap が disabled) | `doCoppGroupTask()` | APPL_DB への書き込みを保留 (`checkTrapGroupPending` が false になるまで) | `coppmgr.cpp:62-79` |

### task_failed 時の挙動詳細

`doTask()` の switch 文において:
- `task_failed`: `erase(it)` → 即時 `return` → **ループ全体を中断**。未処理 entry が残っても次の `doTask` 呼び出しまで処理されない。
- `task_need_retry`: `it++` → 次 entry を処理、当該 entry は次サイクルで再試行。
- `task_invalid_entry`: `erase(it)` → 次 entry へ継続（ループ中断なし）。
- `task_ignore`: `erase(it)` → 次 entry へ継続。

`task_failed` は `SWSS_LOG_ERROR("Processing copp task item failed, exiting.")` を出力し、orchagent プロセスは `return` で `doTask` を抜けるが、即時プロセス終了はしない点に注意（systemd watchdog により再起動の可能性はある）。

### 検出ロジック補足

- **NAT trap_id スキップ**: `snat_miss` / `dnat_miss` は `gIsNatSupported == false` の場合 `continue` でスキップ — `task_failed` にはならない。他の trap_id は継続処理される。
- **SAI 非対応 trap_id スキップ**: `isTrapIdSupported()` が false の場合も `continue` — エントリ全体を棄却せず部分スキップ。
- **COPP_GROUP 未到着ガード**: `processCoppRule()` 内で `m_trap_group_map` に存在しない場合、SAI create 経路を通るが、`coppmgr` 側での保留チェック (`checkTrapGroupPending`) により APPL_DB 書き込み自体が抑制される。
- **`task_failed` → loop 中断**: 他テーブル (ACL など) と異なり、`CoppOrch::doTask` は `task_failed` で `return` するが、プロセス強制終了はしない。ただし残 entry の処理が止まる点で影響大。

### グレップカバレッジ

| 項目 | 証跡 |
|---|---|
| `task_failed` 返却箇所 | `copporch.cpp:799, 840, 846, 850, 855, 869` |
| `task_invalid_entry` 返却箇所 | `copporch.cpp:752, 903, 908` |
| `task_need_retry` 言及 | `copporch.cpp:924-926` |
| `SWSS_LOG_ERROR` 件数 | 20+ 件 |
| `out_of_range` catch | `copporch.cpp:900` |

<!-- /failure -->
