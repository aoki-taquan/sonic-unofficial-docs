# CONFIG_DB 例外条件分析: BUFFER_PORT_EGRESS_PROFILE_LIST

## Consumer

- `orchagent` の `BufferOrch::processEgressBufferProfileList`: APPL_DB 経由で `SAI_PORT_ATTR_QOS_EGRESS_BUFFER_PROFILE_LIST` に設定。

## 例外条件

### 1. プロファイル参照未解決 → task_need_retry
- ソース: `bufferorch.cpp` `processEgressBufferProfileList` L1869-1876
- `profile_list` フィールドに参照するプロファイルが BUFFER_PROFILE テーブルにまだ存在しない場合 `SWSS_LOG_INFO("Missing or invalid egress buffer profile reference specified for:%s")` → `task_need_retry`。

### 2. プロファイル参照解決失敗 → task_failed
- ソース: `bufferorch.cpp` L1876-1880
- `not_resolved` 以外の失敗 (フィールド名欠如等) の場合 `SWSS_LOG_ERROR("Failed resolving egress buffer profile reference specified for:%s")` → `task_failed`。

### 3. プロファイルリスト変更なし → スキップ (task_success)
- ソース: `bufferorch.cpp` L1882-1886
- `profile_name_list` が既存キャッシュと同一の場合 `SWSS_LOG_INFO("Skip setting buffer egress profile list ...")` → そのまま返却。SAI 呼び出しなし。

### 4. trimming-eligible プロファイルの使用禁止 → task_failed
- ソース: `bufferorch.cpp` L1907-1921
- `packet_discard_action = trim` のプロファイルは egress profile list に設定不可。`SWSS_LOG_ERROR("Failed to configure egress buffer profile list(%s): buffer profile(%s) is trimming eligible")` → `task_failed`。

### 5. ポートが未存在 → task_invalid_entry
- ソース: `bufferorch.cpp` L1950-1954
- ポート名がPortsOrchのポートマップに存在しない場合 `SWSS_LOG_ERROR("Port with alias:%s not found")` → `task_invalid_entry`。

### 6. 不明コマンド → エラーログのみ
- ソース: `bufferorch.cpp` L1944
- SET / DEL 以外のコマンドが来た場合 `SWSS_LOG_ERROR("Unknown command %s ...")` のみでタスクバッファに積まれる。
