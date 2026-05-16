# BUFFER_PORT_INGRESS_PROFILE_LIST — Phase D: 失敗挙動

ソース: `sonic-swss/cfgmgr/buffermgrdyn.cpp`, `sonic-swss/orchagent/bufferorch.cpp`

## 失敗分岐一覧

### 1. profile 未解決 → task_need_retry (buffermgrdyn.cpp)

`checkBufferProfileDirection()` 内で `m_bufferProfileLookup.find(profileName)` が `end()` を返す場合、
`SWSS_LOG_INFO("Profile %s doesn't exist, need retry")` を出力して `task_need_retry` を返す。

エントリはキューに残り、プロファイルが登録されるまでサイレントにリトライされる。

evidence: `buffermgrdyn.cpp:3281-3285`

### 2. direction mismatch (ingress 専用) → task_failed (buffermgrdyn.cpp)

`checkBufferProfileDirection()` 内でプロファイルの `direction` が期待方向 (`BUFFER_INGRESS`) と一致しない場合、
`SWSS_LOG_ERROR("Profile %s's direction is %s but %s is expected")` を出力して `task_failed` を返す。
エントリは消去される。これは dynamic buffer model のみに適用される制約（static model は方向チェックなし）。

evidence: `buffermgrdyn.cpp:3289-3295`

### 3. PORT 未準備 → task_invalid_entry (bufferorch.cpp)

`processIngressBufferProfileList()` 内で `gPortsOrch->getPort(port_name, port)` が失敗した場合、
`SWSS_LOG_ERROR("Port with alias:%s not found")` を出力して `task_invalid_entry` を返す。

evidence: `bufferorch.cpp:1762-1765`

### 4. profile 参照未解決 (orchagent 側) → task_need_retry (bufferorch.cpp)

`resolveFieldRefArray()` が `ref_resolve_status::not_resolved` を返す場合、
`SWSS_LOG_INFO("Missing or invalid ingress buffer profile reference")` を出力して `task_need_retry` を返す。
それ以外の失敗時は `task_failed`。

evidence: `bufferorch.cpp:1683-1691`

### 5. trim 禁止 → task_failed (bufferorch.cpp)

`profCfg.isTrimmingEligible == true` のプロファイルを profile_list に設定しようとした場合、
`SWSS_LOG_ERROR("Failed to configure ingress buffer profile list: buffer profile is trimming eligible")` を出力して `task_failed` を返す。
SAI 仕様上 ingress 側でのパケットトリミングは禁止されており、エントリは消去される。

evidence: `bufferorch.cpp:1725-1731`

### 6. SAI Bulk 部分失敗 → task_need_retry (bufferorch.cpp)

`processIngressBufferProfileListBulk()` で `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` を使用して複数ポートの bulk SET を実行する。
個別ポートの SAI status が `SAI_STATUS_SUCCESS` でない場合、`handleSaiSetStatus()` が `task_need_retry` を返すと
そのエントリは `consumer.m_toSync` に再投入される。成功ポートはそのまま確定。

evidence: `bufferorch.cpp:1823-1843`

### 7. admin-down 期間 → zero profile list へ silent 置換 (buffermgrdyn.cpp)

`handleSingleBufferPortProfileListEntry()` 内で `portInfo.state == PORT_ADMIN_DOWN` の場合、
ユーザー設定の `profile_list` を APPL_DB に書かず、代わりに `constructZeroProfileListFromNormalProfileList()` で
ゼロプロファイルリストを生成して APPL_DB に書き込む。これはエラーではなく silent 置換。
ポートが admin-up になると通常のプロファイルリストが適用される。

evidence: `buffermgrdyn.cpp:3418-3438`

### 8. buffer pool 未準備 → pending (buffermgrdyn.cpp)

`m_bufferPoolReady == false` の場合、`m_bufferObjectsPending = true` をセットして `task_success` を返す（pending）。
APPL_DB への書き込みは保留される。エラーログなし。

evidence: `buffermgrdyn.cpp:3408-3414`

### 9. 無効キー形式 → task_invalid_entry (buffermgrdyn.cpp)

`handleBufferObjectTables()` で `parseObjectNameFromKey(key)` が空文字を返す場合、
`SWSS_LOG_ERROR("Invalid key format")` を出力して `task_invalid_entry` を返す。

evidence: `buffermgrdyn.cpp:3509-3513`

## まとめ表

| 失敗条件 | 検出場所 | 返却値 | エントリ消去 |
|--------|---------|-------|------------|
| profile 未解決（buffermgrd） | `buffermgrdyn.cpp:3281-3285` | `task_need_retry` | なし（retry） |
| direction mismatch (egress profile を ingress に) | `buffermgrdyn.cpp:3289-3295` | `task_failed` | あり |
| PORT 未登録（orchagent） | `bufferorch.cpp:1762-1765` | `task_invalid_entry` | あり |
| profile 未解決（orchagent） | `bufferorch.cpp:1685-1688` | `task_need_retry` | なし（retry） |
| trim 禁止プロファイル | `bufferorch.cpp:1725-1731` | `task_failed` | あり |
| SAI Bulk 部分失敗 | `bufferorch.cpp:1839-1843` | `task_need_retry` | なし（retry） |
| admin-down 期間 | `buffermgrdyn.cpp:3418-3438` | (silent 置換) | なし |
| buffer pool 未準備 | `buffermgrdyn.cpp:3408-3414` | (pending) | なし |
| 無効キー形式 | `buffermgrdyn.cpp:3509-3513` | `task_invalid_entry` | あり |
