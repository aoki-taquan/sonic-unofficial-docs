# DASH_VNET — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-17 (q67-f-dash-vnet-extra)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/dash/dashvnetorch.cpp`

### DASH_VNET SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| protobuf フィールド `pb` が欠如または不正 | `parsePbMessage()` (SET前) | エントリを consumer から即除去・SAI 反映なし | SWSS_LOG_WARN ("Requires protobuff at Vnet :%s") | `dashvnetorch.cpp:204-209` |
| `DASH_APPLIANCE` エントリが未設定 | `addVnet()` L63-68 | `return false` でリトライ待ち。`vnet_table_` / `gVnetNameToId` 未更新。SAI 未反映 | SWSS_LOG_INFO ("Retry as no appliance table entry found") | `dashvnetorch.cpp:63-68` |
| 同名 VNET が既に存在する (`vnet_table_` に同 key) | `addVnet()` L57-62 | 重複として `return true`・bulker には渡さない。既存エントリを上書きせず consumer から除去 | SWSS_LOG_WARN ("Vnet already exists for %s") | `dashvnetorch.cpp:57-62` |
| SAI `create_entry` がバルク処理後に `SAI_NULL_OBJECT_ID` を返す | `addVnetPost()` L93-97 | `return false`・`vnet_table_` / `gVnetNameToId` 未更新・CRM カウンタ増加なし | SWSS_LOG_ERROR ("Failed to create vnet entry for %s") | `dashvnetorch.cpp:93-97` |
| 不明コマンド (`op` が SET でも DEL でもない) | `doTaskVnetTable()` L238-239 | エントリを即除去。処理なし | SWSS_LOG_ERROR ("Invalid command %s") | `dashvnetorch.cpp:238-239` |

### DASH_VNET DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| 存在しない VNET を DEL | `removeVnet()` L114-119 | `return true` で consumer から即除去 (no-op)。`vnet_table_` は変化なし | SWSS_LOG_WARN ("Failed to find vnet entry %s to remove") | `dashvnetorch.cpp:114-119` |
| SAI remove が `SAI_STATUS_NOT_EXECUTED` を返す | `removeVnetPost()` L152-155 | `return false` でリトライ待ち。`vnet_table_` / `gVnetNameToId` 未クリア | なし | `dashvnetorch.cpp:152-155` |
| SAI remove がその他のエラーステータスを返す | `removeVnetPost()` L156-161 | `SWSS_LOG_ERROR` + `handleSaiRemoveStatus()` 呼び出し。`parseHandleSaiStatusFailure()` が `task_failed` なら `return false` | SWSS_LOG_ERROR ("Failed to remove vnet entry for %s") | `dashvnetorch.cpp:156-161` |
| PA validation エントリに `SAI_STATUS_OBJECT_IN_USE` | `removePaValidationPost()` L689-695 | そのエントリだけリトライ待ち・`underlay_ips` から消去されない。`removeVnetPost()` は呼ばれず VNET 削除もリトライ待ち | SWSS_LOG_INFO ("PA validation entry for Vnet %s IP %s still in use") | `dashvnetorch.cpp:689-695` |

### DASH_VNET_MAPPING_TABLE SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `gVnetNameToId` に対象 VNET 名が未登録 | `addVnetMap()` L489-494 | `return false` でリトライ待ち | SWSS_LOG_INFO ("Not creating VNET map for %s since VNET %s doesn't exist") | `dashvnetorch.cpp:489-494` |
| `routing_type` が `DASH_ROUTE_TYPE` に未登録 | `addOutboundCaToPa()` L315-319 | `return false` でリトライ待ち | SWSS_LOG_INFO ("Failed to get route type actions for %s") | `dashvnetorch.cpp:315-319` |
| `encap_type` が VXLAN / NVGRE 以外の STATICENCAP アクション | `addOutboundCaToPa()` L335-339 | `return true` で consumer から即除去 (破棄)。SAI 未反映 | SWSS_LOG_ERROR ("Invalid encap type %d for %s") | `dashvnetorch.cpp:335-339` |
| `has_tunnel()` = true だが `DashTunnelOrch::getTunnelOid()` が `SAI_NULL_OBJECT_ID` | `addOutboundCaToPa()` L356-361 | `return false` でリトライ待ち | SWSS_LOG_INFO ("Tunnel %s for VnetMap %s does not exist yet") | `dashvnetorch.cpp:356-361` |
| PRIVATELINK + `has_port_map()` = true だが `DashPortMapOrch::getPortMapOid()` が `SAI_NULL_OBJECT_ID` | `addOutboundCaToPa()` L411-418 | `return false` でリトライ待ち | SWSS_LOG_ERROR ("Portmap %s for VnetMap %s does not exist yet") | `dashvnetorch.cpp:411-418` |
| SAI `create_entry` (outbound_ca_to_pa) が `SAI_STATUS_ITEM_ALREADY_EXISTS` を返す | `addOutboundCaToPaPost()` L512-515 | `return true` (冪等成功扱い)。CRM カウンタ増加なし | なし | `dashvnetorch.cpp:512-515` |
| SAI `create_entry` (outbound_ca_to_pa) がその他エラー | `addOutboundCaToPaPost()` L517-522 | `SWSS_LOG_ERROR` + `handleSaiCreateStatus()` 呼び出し | SWSS_LOG_ERROR ("Failed to create CA to PA entry for %s") | `dashvnetorch.cpp:517-522` |
| SAI `create_entry` (pa_validation) が `SAI_STATUS_ITEM_ALREADY_EXISTS` を返す | `addPaValidationPost()` L548-551 | `return true` (冪等成功扱い) | なし | `dashvnetorch.cpp:548-551` |
| SAI `create_entry` (pa_validation) がその他エラー | `addPaValidationPost()` L553-558 | `SWSS_LOG_ERROR` + `handleSaiCreateStatus()` 呼び出し | SWSS_LOG_ERROR ("Failed to create PA validation entry for %s") | `dashvnetorch.cpp:553-558` |
| `addVnetMapPost()` の `addOutboundCaToPaPost()` か `addPaValidationPost()` のいずれかが `false` | `addVnetMapPost()` L572-577 | `return false`・DASH_RESULT_FAILURE を result table に書き込み | SWSS_LOG_ERROR ("addVnetMapPost failed for %s") | `dashvnetorch.cpp:572-577` |

### DASH_VNET_MAPPING_TABLE DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| SAI remove (outbound_ca_to_pa) が `SAI_STATUS_NOT_EXECUTED` | `removeOutboundCaToPaPost()` L643-645 | `return false` でリトライ待ち | なし | `dashvnetorch.cpp:643-645` |
| SAI remove (outbound_ca_to_pa) が `SAI_STATUS_ITEM_NOT_FOUND` | `removeOutboundCaToPaPost()` L648-651 | `return true` (冪等成功扱い) | SWSS_LOG_WARN ("Outbound CA to PA entry for %s already removed") | `dashvnetorch.cpp:648-651` |
| SAI remove (outbound_ca_to_pa) がその他エラー | `removeOutboundCaToPaPost()` L654-659 | SWSS_LOG_ERROR + handleSaiRemoveStatus + `parseHandleSaiStatusFailure()` | SWSS_LOG_ERROR ("Failed to remove outbound CA to PA entry for %s") | `dashvnetorch.cpp:654-659` |
| `removeVnetMapPost()` の `removeOutboundCaToPaPost()` が `false` | `removeVnetMapPost()` L715-719 | `return false`・リトライ待ち | SWSS_LOG_ERROR ("removeVnetMapPost failed for %s") | `dashvnetorch.cpp:715-719` |

### 補足

- **リトライ待ちのメカニズム**: `return false` は consumer の `m_toSync` からエントリを消費せずにイテレータを進める。次のイベントループで再度処理が試みられる。依存リソースが追加されると自動的に解消する。
- **`return true` (即除去) の意味**: `addVnet()` で既存 VNET を検出した場合や `removeVnet()` で存在しない VNET を削除しようとした場合は冪等処理として consumer から除去。SAI 反映は行わない。
- **DASH_RESULT_FAILURE の書き込み**: `addVnetPost()` / `addVnetMapPost()` が `false` を返した場合、`doTaskVnetTable()` / `doTaskVnetMapTable()` は `DASH_RESULT_FAILURE` を APP_STATE_DB の result table に書き込む (`dashvnetorch.cpp:280-283, 848-851`)。
- **protobuf メッセージ不正の非リトライ**: `parsePbMessage()` 失敗時は `return false` ではなく即 `erase` されるため、不正な protobuf エントリはリトライされない (破棄)。
- **PA validation の参照カウント保護**: `removePaValidationPost()` で `SAI_STATUS_OBJECT_IN_USE` が返された IP エントリは `underlay_ips` に残り、VNET 削除もブロックされる。これは `DASH_VNET_MAPPING_TABLE` エントリが先に削除されていない状態で `DASH_VNET` を削除しようとした際に発生する典型的な順序違反の結果。

<!-- /failure -->
