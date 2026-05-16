# BUFFER_PG — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-buffer-pg)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `sonic-swss/cfgmgr/buffermgr.cpp`
- `sonic-swss/orchagent/bufferorch.cpp`

### SET 処理における失敗経路 (buffermgrdyn.cpp)

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `profile` フィールドの参照形式が空文字 (`profileName.empty()`) | `handleSingleBufferPgEntry()` | `task_invalid_entry`（エントリ drop、`m_portPgLookup` からも削除） | `SWSS_LOG_ERROR("BUFFER_PG: Invalid format of reference to profile: %s")` | `buffermgrdyn.cpp:3133` |
| 参照 BUFFER_PROFILE が `m_bufferProfileLookup` に未登録 | `handleSingleBufferPgEntry()` | `task_need_retry`（再試行。`m_portPgLookup` からも削除） | `SWSS_LOG_INFO("Profile %s hasn't been configured yet, skip")` | `buffermgrdyn.cpp:3144-3151` |
| 参照 BUFFER_PROFILE の direction が `BUFFER_EGRESS`（egress profile） | `handleSingleBufferPgEntry()` | `task_failed`（永続 drop、`m_portPgLookup` からも削除） | `SWSS_LOG_ERROR("Egress buffer profile configured on PG %s")` | `buffermgrdyn.cpp:3156-3163` |
| lossy PG の累積 headroom がリソース上限超過 | `handleSingleBufferPgEntry()` (`isHeadroomResourceValid()`) | `task_failed` | `SWSS_LOG_ERROR("Unable to configure lossy PG %s, accumulative headroom size exceeds the limit")` | `buffermgrdyn.cpp:3170-3171` |
| `profile` 以外の不明フィールドが SET で到達 | `handleSingleBufferPgEntry()` | `task_invalid_entry`（エントリ drop） | `SWSS_LOG_ERROR("BUFFER_PG: Invalid field %s")` | `buffermgrdyn.cpp:3180` |
| PORT が `PORT_READY` でない（speed/cable_length 未設定）— 動的計算時 | `refreshPgsForPort()` | 該当 PG をスキップ（silent skip、retry はしない） | `SWSS_LOG_INFO("Nothing to be done for %s since port is not ready")` | `buffermgrdyn.cpp:1485-1487` |
| cable_length = `"0m"` かつ lossless PG | `refreshPgsForPort()` | APPL_DB から lossless PG を削除（バッファ回収） | `SWSS_LOG_INFO("No lossless profile found for port %s when cable length is set to '0m'.")` | `buffermgrdyn.cpp:1492-1509` |
| speed + cable_length + mtu 組み合わせで動的 headroom 計算失敗（`allocateProfile()` 非 success） | `refreshPgsForPort()` | `task_failed`（該当 profile を release） | 内部 `allocateProfile()` が SWSS_LOG_ERROR を出力 | `buffermgrdyn.cpp:1530-1534` |
| 動的計算後の累積 headroom がリソース上限超過 | `refreshPgsForPort()` (`isHeadroomResourceValid()`) | `task_failed`（profile を release） | `SWSS_LOG_ERROR("Update speed (%s) and cable length (%s) for port %s failed, accumulative headroom size exceeds the limit")` | `buffermgrdyn.cpp:1541-1546` |
| PORT admin down 時の SET（pureDynamic/lossless 問わず） | `handleSingleBufferPgEntry()` → `handleSetSingleBufferObjectOnAdminDownPort()` | APPL_DB 書き込みをスキップし内部状態のみ保持。PORT up 時に再適用 | なし（silent defer） | `buffermgrdyn.cpp:3198-3202` |
| zero profile が pool に未設定でバッファ回収不可 | `handleZeroProfilesUpdate()` | LOG_ERROR のみ・処理は継続（SAI call なし） | `SWSS_LOG_ERROR("Zero profile is not provided for pool %s while removing buffer items is not supported")` | `buffermgrdyn.cpp:384` |

### SET 処理における失敗経路 (buffermgr.cpp)

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| cable_length が未設定（`m_cableLenLookup` に port なし） | `doSpeedUpdateTask()` | `task_need_retry` | `SWSS_LOG_INFO("Unable to create/update PG profile for port %s. Cable length is not set")` | `buffermgr.cpp:155` |
| `admin_status` が未取得（`m_portStatusLookup` に port なし） | `doSpeedUpdateTask()` | `task_need_retry` | `SWSS_LOG_INFO("pfc_enable status is not available for port %s")` | `buffermgr.cpp:170` |
| `PORT_QOS_MAP.pfc_enable` 未設定（`m_portPfcStatus` に port なし） | `doSpeedUpdateTask()` | `task_success`（silent skip。pfc_enable 設定時に再ハンドル） | `SWSS_LOG_INFO("pfc_enable status is not available for port %s")` | `buffermgr.cpp:175-179` |
| speed + cable_length が `m_pgProfileLookup` の lookup table に未定義 | `doSpeedUpdateTask()` | `task_invalid_entry`（永続 drop） | `SWSS_LOG_ERROR("Unable to create/update PG profile for port %s. No PG profile configured for speed %s and cable length %s")` | `buffermgr.cpp:240` |
| lossless pool モード（PG pool）が未作成 | `doSpeedUpdateTask()` | `task_need_retry` | `SWSS_LOG_INFO("PG lossless pool is not yet created")` | `buffermgr.cpp:258` |
| PORT admin down（mellanox/barefoot platform）かつデフォルトプロファイル一致 | `doSpeedUpdateTask()` | CONFIG_DB の BUFFER_PG エントリを削除（バッファ回収） | `SWSS_LOG_NOTICE("Removing PG %s from port %s which is administrative down")` | `buffermgr.cpp:228` |
| PORT admin down かつ非デフォルトプロファイル設定済み | `doSpeedUpdateTask()` | 削除せず `task_success`（silent skip） | `SWSS_LOG_NOTICE("Not default profile %s is configured on PG %s, won't reclaim buffer")` | `buffermgr.cpp:231` |
| PG ID が `uint8_t` に変換不可（`std::invalid_argument`） | `doSpeedUpdateTask()` PFC bitmap 生成ループ | 該当 PG ID を silent skip・ループ継続 | なし | `buffermgr.cpp:197` |
| 全 item 処理後 failed_item_count > 0 | `doTask()` | `task_failed` を返却 | なし（個別 item の LOG_ERROR が先行） | `buffermgr.cpp:2216-2218` |

### SET 処理における失敗経路 (bufferorch.cpp — processPriorityGroup)

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| key が `port:pg_range` 形式 2 トークンでない | `processPriorityGroup()` | `task_invalid_entry` | `SWSS_LOG_ERROR("malformed key:%s. Must contain 2 tokens")` | `bufferorch.cpp:1324` |
| pg_range のパース失敗（`parseIndexRange()` false） | `processPriorityGroup()` | `task_invalid_entry` | `SWSS_LOG_ERROR("Failed to obtain pg range values")` | `bufferorch.cpp:1330` |
| BUFFER_PROFILE 参照が未解決（`ref_resolve_status::not_resolved`） | `processPriorityGroup()` | `task_need_retry` | `SWSS_LOG_INFO("Missing or invalid pg profile reference specified")` | `bufferorch.cpp:1347` |
| BUFFER_PROFILE 参照の解決が他エラーで失敗 | `processPriorityGroup()` | `task_failed` | `SWSS_LOG_ERROR("Resolving pg profile reference failed")` | `bufferorch.cpp:1350-1351` |
| BUFFER_PROFILE が trimming eligible（ingress trimming 設定済み） | `processPriorityGroup()` | `task_failed` | `SWSS_LOG_ERROR("Failed to configure ingress priority group(%s): buffer profile(%s) is trimming eligible")` | `bufferorch.cpp:759-763` |
| ポート名 `port_name` が PortsOrch に未登録 | `processPriorityGroup()` | `task_invalid_entry` | `SWSS_LOG_ERROR("Port with alias:%s not found")` | `bufferorch.cpp:1035` |
| PG インデックスがポートの `m_priority_group_ids` サイズ超過 | `processPriorityGroup()` | `task_invalid_entry` | `SWSS_LOG_ERROR("Invalid pg index specified:%zd")` | `bufferorch.cpp:1063` |
| SAI `sai_set_attribute` が `SAI_STATUS_SUCCESS` 以外を返却 | `processPriorityGroupPost()` | `handleSaiSetStatus()` を呼び出して retryable か判定。retry 対象外は `task_failed` | `SWSS_LOG_ERROR("Failed to set port:%s pg:%zd buffer profile attribute, status:%d")` | `bufferorch.cpp:1507-1512` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| DEL 対象エントリが APPL_DB に存在しない | `processPriorityGroup()` DEL 分岐 | SAI call をスキップ（`need_update_sai = false`） | `SWSS_LOG_INFO("%s doesn't not exist, don't need to notfiy SAI")` | `bufferorch.cpp:1409-1413` |

### 検出ロジック補足

- **retry / failed の境界**: `buffermgrdyn` は「依存リソース未到着」を `task_need_retry`、「設定不正・リソース超過」を `task_failed` / `task_invalid_entry` として明確に分離。`task_need_retry` は次のイベントで再試行されるが `task_failed` / `task_invalid_entry` は drop される。
- **SAI 失敗の伝播**: `bufferorch.cpp:processPriorityGroupPost()` で SAI call 失敗時は `handleSaiSetStatus()` を経由し、SAI status code に応じて retry / failed を振り分ける（`SAI_STATUS_NOT_SUPPORTED` 系は notice で継続、他は failed）。
- **m_portPgLookup のロールバック**: `handleSingleBufferPgEntry()` が `task_invalid_entry` / `task_need_retry` / `task_failed` を返す場合、`needRemoveOnFailure = true` の条件下では `m_portPgLookup[port].erase(key)` を実行してルックアップテーブルをクリーンアップする。

### grep カバレッジ

| ファイル | 検索対象 | hit 数 | 主な証跡行 |
|---|---|---|---|
| `buffermgrdyn.cpp` | `task_invalid_entry` (BUFFER_PG 関連) | 3 | L3133, L3163, L3180 |
| `buffermgrdyn.cpp` | `task_need_retry` | 1 | L3151 |
| `buffermgrdyn.cpp` | `task_failed` | 3 | L3163, L3171, L1546 |
| `buffermgr.cpp` | `task_need_retry` | 3 | L155, L170, L258 |
| `buffermgr.cpp` | `task_invalid_entry` | 1 | L240 |
| `bufferorch.cpp` | `task_need_retry` | 1 | L1347 |
| `bufferorch.cpp` | `task_failed` | 2 | L1351, L763 |
| `bufferorch.cpp` | `task_invalid_entry` | 3 | L1324, L1330, L1063 |

<!-- /failure -->
