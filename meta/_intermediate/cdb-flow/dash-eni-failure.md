# DASH_ENI_TABLE — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-17 (q67-f-dash-eni2-next)

<!-- failure -->
## 失敗挙動マトリクス (Phase D)

ソース: `sonic-net/sonic-swss/orchagent/dash/dashorch.cpp`

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | retry | evidence |
|---|---|---|---|---|---|
| Protobuf メッセージのパース失敗 | `doTaskEniTable()` L1061-1065 | `m_toSync` から erase（再試行なし） | `SWSS_LOG_WARN "Requires protobuff at ENI"` | なし | `dashorch.cpp:1063-1065` |
| `vnet` フィールドが未登録（`gVnetNameToId` miss） | `addEniObject()` L572-576 | `addEni()` が `false` → `it++` → `DASH_RESULT_FAILURE` を APPL_STATE_DB に書込 | `SWSS_LOG_INFO "Retry as vnet not found"` | VNET 登録まで無制限 | `dashorch.cpp:572-576` |
| `appliance_entries_` が空（DASH_APPLIANCE_TABLE 未登録） | `addEniObject()` L578-582 | `addEni()` が `false` → `it++` → `DASH_RESULT_FAILURE` | `SWSS_LOG_INFO "Retry as no appliance table entry found"` | Appliance 登録まで無制限 | `dashorch.cpp:578-582` |
| `v4_meter_policy_id` が未登録（`getMeterPolicyOid` = SAI_NULL） | `addEniObject()` L590-597 | `addEni()` が `false` → `it++` → `DASH_RESULT_FAILURE` | `SWSS_LOG_INFO "Retry as v4 meter_policy not found"` | MeterPolicy 登録まで無制限 | `dashorch.cpp:590-597` |
| `v6_meter_policy_id` が未登録（`getMeterPolicyOid` = SAI_NULL） | `addEniObject()` L599-606 | `addEni()` が `false` → `it++` → `DASH_RESULT_FAILURE` | `SWSS_LOG_INFO "Retry as v6 meter_policy not found"` | MeterPolicy 登録まで無制限 | `dashorch.cpp:599-606` |
| `underlay_ip` の IP アドレス変換失敗（`to_sai()` が `false`） | `addEniObject()` L638-641 | `addEniObject()` が `false` → `addEni()` が `false` → `it++` → `DASH_RESULT_FAILURE` | なし（`to_sai` 内部でのみ処理） | なし | `dashorch.cpp:638-640` |
| SAI `create_eni()` 失敗 | `addEniObject()` L738-748 | `handleSaiCreateStatus()` で evaluate → `parseHandleSaiStatusFailure()` → `false` または retry | `SWSS_LOG_ERROR "Failed to create ENI object"` | SAI ステータス依存 | `dashorch.cpp:740-747` |
| SAI `create_eni_ether_address_map_entry()` 失敗 | `addEniAddrMapEntry()` L785-792 | `addEni()` が `false` → `it++` → `DASH_RESULT_FAILURE` | `SWSS_LOG_ERROR "Failed to create ENI ether address map entry"` | SAI ステータス依存 | `dashorch.cpp:785-792` |
| `trusted_vnis_list` に無効な VNI レンジ（`to_sai()` = `false`） | `addEniTrustedVnis()` L814-818 | 当該エントリをスキップして継続。全 VNI 失敗時は `addEni()` が ENI を `removeEni()` でロールバック | `SWSS_LOG_ERROR "Failed to convert trusted vni range for ENI"` | なし（個別エントリスキップ） | `dashorch.cpp:814-831` |
| SAI `create_eni_trusted_vni_entry()` 失敗 | `addEniTrustedVnis()` L823-832 | 当該エントリをスキップして継続。全失敗時に `removeEni()` でロールバック | `SWSS_LOG_ERROR "Failed to create ENI trusted vni entry"` | なし | `dashorch.cpp:823-831` |
| trusted VNI 追加が一部でも失敗（`all_trusted_vnis_added = false`） | `addEni()` L871-877 | `removeEni()` でロールバック（ENI + ether address map entry を削除）→ `false` → `it++` | `SWSS_LOG_ERROR "Failed to add all trusted vni entries for ENI. Removing ENI entry."` | なし（ロールバック後に再試行なし） | `dashorch.cpp:872-876` |
| ENI 既存で `admin_state` のみ変更（setEniAdminState 失敗） | `setEniAdminState()` L551-553 | `false` → `addEni()` → `false` → `it++` | `SWSS_LOG_ERROR "Failed to set ENI admin state"` | SAI ステータス依存 | `dashorch.cpp:551-553` |
| ENI 既存で他フィールドが変更（UPDATE 相当） | `addEni()` L856-858 | `SWSS_LOG_WARN` のみ。フィールド更新は行わず `true` を返す（変更無視）| `SWSS_LOG_WARN "ENI already exists"` | なし（silent ignore） | `dashorch.cpp:854-858` |
| 不明な操作コマンド（SET/DEL 以外） | `doTaskEniTable()` L1092-1095 | `m_toSync` から erase（再試行なし） | `SWSS_LOG_ERROR "Unknown operation"` | なし | `dashorch.cpp:1093-1094` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | retry | evidence |
|---|---|---|---|---|---|
| ENI が存在しない（`eni_entries_` miss） | `removeEni()` L1019-1023 | `true` を返して正常終了（べき等）。APPL_STATE_DB から結果エントリ削除 | `SWSS_LOG_WARN "ENI does not exist"` | なし | `dashorch.cpp:1019-1022` |
| trusted VNI エントリ削除失敗（一部でも失敗） | `removeEniTrustedVnis()` L988-1006 | `removeEni()` が `false` → `it++` (retry)。部分的に削除された VNI は内部キャッシュから都度消去 | `SWSS_LOG_ERROR "Failed to remove ENI trusted vni entry"` | 無制限 | `dashorch.cpp:997-1004` |
| `removeEniAddrMapEntry()` で `SAI_STATUS_ITEM_NOT_FOUND` または `SAI_STATUS_INVALID_PARAMETER` | `removeEniAddrMapEntry()` L956-959 | `true` を返して正常終了（べき等処理） | なし（silent return true） | なし | `dashorch.cpp:956-959` |
| `remove_eni_ether_address_map_entry()` SAI 失敗（上記以外） | `removeEniAddrMapEntry()` L961-966 | `removeEni()` が `false` → `it++` (retry) | `SWSS_LOG_ERROR "Failed to remove ENI ether address map entry"` | 無制限 | `dashorch.cpp:961-965` |
| `remove_eni()` で `SAI_STATUS_OBJECT_IN_USE` | `removeEniObject()` L911-913 | `removeEni()` が `false` → `it++` (retry)。参照元（ACL / Route 等）の解放を待つ | なし（silent `false`） | 無制限 | `dashorch.cpp:911-913` |
| `remove_eni()` SAI 失敗（OBJECT_IN_USE 以外） | `removeEniObject()` L915-920 | `parseHandleSaiStatusFailure()` → `false` → `it++` (retry) | `SWSS_LOG_ERROR "Failed to remove ENI object"` | SAI ステータス依存 | `dashorch.cpp:915-920` |

### 結果テーブル（APPL_STATE_DB）

`doTaskEniTable()` は SET 処理の成否を `APPL_STATE_DB:DASH_ENI_TABLE:<eni_mac>` に `result` フィールドとして書き込む。

| 状態 | `result` 値 | 条件 |
|---|---|---|
| SET 成功 | `DASH_RESULT_SUCCESS` (0) | `addEni()` が `true` | 
| SET 失敗（依存未解決 / SAI エラー） | `DASH_RESULT_FAILURE` (1) | `addEni()` が `false` |
| DEL 成功 | エントリ削除 | `removeEni()` が `true` → `removeResultFromDB()` |
| DEL 失敗 | 前回の値を保持 | `removeEni()` が `false` → `it++` |

確認コマンド: `sonic-db-cli APPL_STATE_DB hgetall 'DASH_ENI_TABLE:<eni_mac>'`

エラーはすべて `SWSS_LOG_ERROR` または `SWSS_LOG_WARN` でサイログ出力される。CONFIG_DB (APP_DB) のエントリは失敗後も残存する（orchagent は書き戻さない）。

> **証跡**: `doTaskEniTable()` L1045-1097, `addEni()` L841-881, `addEniObject()` L566-768, `addEniAddrMapEntry()` L770-800, `addEniTrustedVnis()` L802-839, `removeEni()` L1015-1043, `removeEniObject()` L896-941, `removeEniAddrMapEntry()` L944-974, `removeEniTrustedVnis()` L976-1013

<!-- /failure -->
