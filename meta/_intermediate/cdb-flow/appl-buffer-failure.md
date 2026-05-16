# APPL_DB BUFFER_* — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-appl-buffer)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/bufferorch.cpp` (ref `4305596156d70e9797e8a881b3d19b46de0bce0d`, 全 2138 行)

bufferorch は per-task handler が `task_process_status` enum を返し、ディスパッチャ (L2096-2129) が一律処理する設計。返却ステータスごとの最終アクションは以下のとおり。

### ディスパッチャの最終ハンドリング (L2107-2128)

| ステータス | 動作 | 追加ログ | evidence |
|---|---|---|---|
| `task_success` | `m_toSync` から該当エントリを削除して次へ | なし | `bufferorch.cpp:2109-2111` |
| `task_ignore` | `m_toSync` から削除して次へ (= 成功扱い) | なし | `bufferorch.cpp:2110-2111` |
| `task_invalid_entry` | エントリ削除・**ループ継続**して次タスクへ | `LOG_ERROR ("Failed to process invalid buffer task")` | `bufferorch.cpp:2113-2115` |
| `task_failed` | エントリ削除・**`doTask` 全体を `return` で打ち切り** (残タスク未処理) | `LOG_ERROR ("Failed to process buffer task, drop it")` | `bufferorch.cpp:2117-2120` |
| `task_need_retry` | エントリ残置・`it++` で次回 doTask 呼び出しまで保留 | `LOG_INFO ("Failed to process buffer task, retry it")` | `bufferorch.cpp:2121-2123` |
| default (enum 値外) | エントリ削除・ループ継続 | `LOG_ERROR ("Invalid task status %d")` | `bufferorch.cpp:2125-2128` |
| handler 未登録テーブル | エントリ削除・ループ継続 (handler dispatch 自体回避) | `LOG_ERROR ("No handler for key:%s found")` | `bufferorch.cpp:2099-2103` |

> `task_failed` のみ doTask を打ち切るため、その回の `m_toSync` 中の以降のキーは次回のディスパッチまで処理されない。`task_invalid_entry` との差はここのみ (両方ともエントリは drop される)。

### `processBufferPool()` (L391-596) 失敗・retry 経路

| 失敗条件 | 検出箇所 | 返却 | ログ | evidence |
|---|---|---|---|---|
| 削除対象 pool が pending-remove 状態 | L407-410 | `task_need_retry` | `LOG_NOTICE ("...pending remove, need retry")` | `bufferorch.cpp:407-410` |
| `type` フィールドが `ingress`/`egress` 以外 | L457 | `task_invalid_entry` | `LOG_ERROR ("Unknown pool type specified:%s")` | `bufferorch.cpp:456-458` |
| `mode` フィールドが `static`/`dynamic` 以外 | L484 | `task_invalid_entry` | `LOG_ERROR ("Unknown pool mode specified:%s")` | `bufferorch.cpp:483-485` |
| 未知フィールド (e.g. `pool` 以外の未対応 key) | L499 | continue (フィールドのみ skip、handler 全体は失敗にしない) | `LOG_ERROR ("Unknown pool field specified:%s, ignoring")` | `bufferorch.cpp:498-500` |
| SAI `set_buffer_pool_attribute` が `SAI_STATUS_ATTR_NOT_IMPLEMENTED_0` | L508-512 | `task_ignore` | `LOG_NOTICE ("Buffer pool SET ... not implemented")` | `bufferorch.cpp:508-512` |
| SAI `set_buffer_pool_attribute` がその他失敗 | L513-521 | `handleSaiSetStatus()` の戻り (例: `task_need_retry`/`task_failed`) | `LOG_ERROR ("Failed to modify buffer pool")` | `bufferorch.cpp:513-521` |
| SAI `create_buffer_pool` 失敗 | L527-537 | `handleSaiCreateStatus()` の戻り | `LOG_ERROR ("Failed to create buffer pool ...")` | `bufferorch.cpp:527-537` |
| 削除対象 pool が他オブジェクト (profile 等) から参照中 | L559-566 | `task_need_retry` | `LOG_NOTICE ("Can't remove object ... due to being referenced")` | `bufferorch.cpp:559-566` |
| SAI `remove_buffer_pool` 失敗 | L572-580 | `handleSaiRemoveStatus()` の戻り | `LOG_ERROR ("Failed to remove buffer pool ...")` | `bufferorch.cpp:572-580` |
| op が SET/DEL 以外 | L593-594 | `task_invalid_entry` | `LOG_ERROR ("Unknown operation type %s")` | `bufferorch.cpp:593-594` |

### `processBufferProfile()` (L602-888) 失敗・retry 経路

| 失敗条件 | 検出箇所 | 返却 | ログ | evidence |
|---|---|---|---|---|
| 削除対象 profile が pending-remove | L616-619 | `task_need_retry` | `LOG_NOTICE ("...pending remove, need retry")` | `bufferorch.cpp:616-619` |
| `pool` 参照解決で `not_resolved` (= 参照先 pool が未登録) | L647-649 | `task_need_retry` | (debug log のみ) | `bufferorch.cpp:647-649` |
| `pool` 参照解決でその他失敗 | L651-652 | `task_failed` | `LOG_ERROR ("Resolving pool reference failed")` | `bufferorch.cpp:651-652` |
| 数値フィールド (`size`/`xon`/`xoff`/`xon_offset`/`dynamic_th`/`static_th`) パース失敗 | L740-743 | `task_failed` | `LOG_ERROR ("Failed to parse buffer profile(%s) field(%s): invalid value(%s)")` | `bufferorch.cpp:738-743` |
| 未知フィールド (e.g. `headroom_type`) | L748-752 | continue (フィールド単位 skip) | `LOG_ERROR ("Unknown buffer profile field specified:%s, ignoring")` | `bufferorch.cpp:748-752` |
| `packet_discard_action` に `drop`/`trim` 以外 | L758-763 | `task_failed` | `LOG_ERROR` | `bufferorch.cpp:758-763` |
| SAI `set_buffer_profile_attribute` 1 回目で `SAI_STATUS_ATTR_NOT_IMPLEMENTED_0` | L773-777 | `task_ignore` | `LOG_NOTICE ("...not implemented")` | `bufferorch.cpp:773-777` |
| SAI `set_buffer_profile_attribute` 1 回目失敗 → **同 attr で即 retry** | L778-787 | (retry 後の結果で分岐) | `LOG_NOTICE ("...will retry one more time")` | `bufferorch.cpp:778-787` |
| SAI `set_buffer_profile_attribute` 2 回目も失敗 | L788-797 | `handleSaiSetStatus()` の戻り | `LOG_ERROR ("...will retry once")` | `bufferorch.cpp:788-797` |
| SAI `create_buffer_profile` 失敗 | L802-812 | `handleSaiCreateStatus()` の戻り | `LOG_ERROR ("Failed to create buffer profile ...")` | `bufferorch.cpp:802-812` |
| 削除対象 profile が PG/Queue 等から参照中 | L836-843 | `task_need_retry` | `LOG_NOTICE ("Can't remove object ... due to being referenced")` | `bufferorch.cpp:836-843` |
| SAI `remove_buffer_profile` 失敗 | L859-867 | `handleSaiRemoveStatus()` の戻り | `LOG_ERROR ("Failed to remove buffer profile ...")` | `bufferorch.cpp:859-867` |
| op が SET/DEL 以外 | L885-886 | `task_invalid_entry` | `LOG_ERROR ("Unknown operation type %s")` | `bufferorch.cpp:885-886` |

> **2 段 retry の特殊性**: `set_buffer_profile_attribute` 失敗時に bufferorch 自身がもう一度同じ attr で SAI 呼び出しを行う (`will retry one more time`)。これは `task_need_retry` ではなく **handler 内ループ retry**。SAI ベンダ実装の transient エラー吸収用。

### `processQueue()` (L914-1015) 失敗・retry 経路

| 失敗条件 | 検出箇所 | 返却 | ログ | evidence |
|---|---|---|---|---|
| VoQ モード時 key が 4 トークン (`host\|asic\|port\|range`) でない | L920-921 | `task_invalid_entry` | `LOG_ERROR ("malformed key:%s. Must contain 4 tokens")` | `bufferorch.cpp:918-921` |
| VoQ モード時 system-port が見つからない | L925-927 | `task_invalid_entry` | (debug log のみ) | `bufferorch.cpp:925-927` |
| 通常モード時 key が 2 トークンでない | L944-946 | `task_invalid_entry` | `LOG_ERROR ("malformed key:%s. Must contain 2 tokens")` | `bufferorch.cpp:944-946` |
| `range` パース失敗 | L950-952 | `task_invalid_entry` | (debug log のみ) | `bufferorch.cpp:950-952` |
| `profile` 参照が未解決 (profile 未登録) | L967-969 | `task_need_retry` | `LOG_INFO ("Missing or invalid queue buffer profile reference")` | `bufferorch.cpp:967-969` |
| `profile` 参照解決その他失敗 | L972-973 | `task_failed` | `LOG_ERROR ("Resolving queue profile reference failed")` | `bufferorch.cpp:972-973` |
| 同じ profile を再 set | L981-982 | `task_success` (no-op) | `LOG_INFO` | `bufferorch.cpp:981-982` |
| port alias 未登録 | L1034-1036 / L1112-1114 | `task_invalid_entry` | `LOG_ERROR ("Port with alias:%s not found")` | `bufferorch.cpp:1034-1036, 1112-1114` |
| voq index が範囲外 | L1053-1055 | `task_invalid_entry` | `LOG_ERROR ("Invalid voq index specified:%zd")` | `bufferorch.cpp:1053-1055` |
| queue index が範囲外 | L1062-1064 | `task_invalid_entry` | `LOG_ERROR ("Invalid queue index specified:%zd")` | `bufferorch.cpp:1062-1064` |
| queue がロック中 (他 orch が触っている) | L1068-1070 | `task_need_retry` | `LOG_WARN ("Queue %zd on port %s is locked, will retry")` | `bufferorch.cpp:1068-1070` |
| SAI `set_attribute` (queue) 失敗 | L1122-1132 | `handleSaiSetStatus()` の戻り | `LOG_ERROR ("Failed to set queue's buffer profile attribute")` | `bufferorch.cpp:1122-1132` |
| op が SET/DEL 以外 | L1013-1014 / L1188-1189 | `task_invalid_entry` | `LOG_ERROR ("operation value is not SET or DEL")` | `bufferorch.cpp:1013-1014, 1188-1189` |
| port が link-up 後にプロファイル適用 (警告のみ) | L1220-1227 | (handler は処理続行) | `LOG_WARN ("Queue profile '%s' applied after port %s is up")` | `bufferorch.cpp:1220-1227` |

### `processPriorityGroup()` (L1305-1495) 失敗・retry 経路

| 失敗条件 | 検出箇所 | 返却 | ログ | evidence |
|---|---|---|---|---|
| key が 2 トークンでない | L1322-1325 | `task_invalid_entry` | `LOG_ERROR ("malformed key:%s. Must contain 2 tokens")` | `bufferorch.cpp:1322-1325` |
| `range` パース失敗 | L1328-1331 | `task_invalid_entry` | `LOG_ERROR ("Failed to obtain pg range values")` | `bufferorch.cpp:1328-1331` |
| `profile` 参照が未解決 (profile 未登録) | L1342-1347 | `task_need_retry` | `LOG_INFO ("Missing or invalid pg profile reference specified")` | `bufferorch.cpp:1342-1347` |
| `profile` 参照解決その他失敗 | L1350-1351 | `task_failed` | `LOG_ERROR ("Resolving pg profile reference failed")` | `bufferorch.cpp:1350-1351` |
| 参照 profile が trimming-eligible (PG に trim 系 profile を貼ろうとした) | L1382-1388 | `task_failed` | `LOG_ERROR ("Failed to configure ingress priority group(...): buffer profile(...) is trimming eligible")` | `bufferorch.cpp:1382-1388` |
| SAI ingress PG 設定失敗 | L1418 / L1434 / L1446 / L1491 系 | `task_invalid_entry` | `LOG_ERROR` 系 | `bufferorch.cpp:1418, 1434, 1446, 1491` |

### `processIngressBufferProfileList()` / `processEgressBufferProfileList()` (L1663-1956)

| 失敗条件 | 検出箇所 | 返却 | ログ | evidence |
|---|---|---|---|---|
| profile-list 参照未解決 (ingress) | L1685-1688 | `task_need_retry` | `LOG_INFO ("Missing or invalid ingress buffer profile reference specified")` | `bufferorch.cpp:1685-1688` |
| profile-list 参照解決その他失敗 (ingress) | L1690-1691 | `task_failed` | `LOG_ERROR ("Failed resolving ingress buffer profile reference")` | `bufferorch.cpp:1690-1691` |
| profile-list に trimming-eligible profile 混在 (ingress) | L1725-1731 | `task_failed` | `LOG_ERROR ("...buffer profile(...) is trimming eligible")` | `bufferorch.cpp:1725-1731` |
| port alias 未登録 (ingress) | L1765 | `task_invalid_entry` | `LOG_ERROR` | `bufferorch.cpp:1765` |
| profile-list 参照未解決 (egress) | L1876-1878 | `task_need_retry` | `LOG_INFO` | `bufferorch.cpp:1876-1878` |
| profile-list 参照解決その他失敗 (egress) | L1880-1881 | `task_failed` | `LOG_ERROR` | `bufferorch.cpp:1880-1881` |
| profile-list に trimming-eligible profile 混在 (egress) | L1918-1921 | `task_failed` | `LOG_ERROR` | `bufferorch.cpp:1918-1921` |
| port alias 未登録 (egress) | L1955 | `task_invalid_entry` | `LOG_ERROR` | `bufferorch.cpp:1955` |

### 共通の retry / SAI ステータスハンドリング補足

- **`handleSaiSetStatus()` / `handleSaiCreateStatus()` / `handleSaiRemoveStatus()`**: `orch.cpp` 共通実装。SAI 戻り値を `task_need_retry` / `task_failed` / `task_success` / `task_ignore` に翻訳する。`SAI_STATUS_ITEM_NOT_FOUND` 等は `task_ignore`、リトライ可能エラーは `task_need_retry`、致命的エラーは abort (`exit(1)`) するケースもある。bufferorch 自身が分岐するのではなくこの共通関数経由で扱う。
- **bulk 処理 retry (queue / pg / profile_list)**: bulk 系 handler は `if (task_status == task_need_retry)` で個別タスクを `m_toSync` に再投入する明示的ループあり (L1292, L1649, L1840, L2030)。
- **doTask の `task_failed` で全体打ち切り** の挙動は他 orch (e.g. orchagent 大半) と同じ。次回 `doTask()` 呼び出し時に残タスクから再開する。
- **flushCounters は handler 結果に関係なく必ず呼ばれる** (L2137)。失敗時もカウンタ更新は走る。

### grep カバレッジ (bufferorch.cpp 全 2138 行)

| 項目 | hit 数 | 備考 |
|---|---|---|
| `task_need_retry` | 12 | pool/profile pending-remove、pool removal blocked、profile pool 参照未解決、PG profile 参照未解決、queue profile 参照未解決、queue lock、ingress/egress profile_list 参照未解決、bulk dispatcher 再投入 4 箇所 |
| `task_failed` | 10 | pool/PG/profile-list resolve fail、profile field parse fail、profile `packet_discard_action` 不正、PG/profile_list trimming-eligible 違反 3 件、bulk 集約 |
| `task_invalid_entry` | 17 | 不正 op、malformed key、未知 enum (`type`/`mode`)、port/queue/voq index 不正、port alias 未登録、ingress PG SAI 設定不可 |
| `task_ignore` | 3 | SAI `ATTR_NOT_IMPLEMENTED_0` (pool/profile)、ディスパッチャ集約 |
| `SWSS_LOG_ERROR` | ~30 | 主に malformed/invalid 系と SAI 失敗 |
| `SWSS_LOG_WARN` | 3 | queue lock、port up 後の profile 適用 (×2) |
| `handleSaiSetStatus` / `handleSaiCreateStatus` / `handleSaiRemoveStatus` | 計 9 箇所 | pool/profile/queue/PG/profile_list の SAI 失敗共通経路 |

<!-- /failure -->
