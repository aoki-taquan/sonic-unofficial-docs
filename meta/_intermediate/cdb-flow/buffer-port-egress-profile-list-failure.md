# buffer-port-egress-profile-list — Phase D: 失敗挙動 (intermediate)

対象ページ: `docs/reference/config-db/buffer-port-egress-profile-list.md`

ソース:
- `sonic-swss/cfgmgr/buffermgrdyn.cpp` L3275-3449, L3502-3572, L3588-3608
- `sonic-swss/orchagent/bufferorch.cpp` L1853-1984

---

## 失敗・retry 分岐まとめ

### 1. profile 未解決 (Dynamic model: buffermgrdyn.cpp)

`checkBufferProfileDirection()` (L3281-3285):
- `m_bufferProfileLookup` に profile が存在しない → `task_need_retry`
- ログ: `SWSS_LOG_INFO("Profile %s doesn't exist, need retry")`
- retry 条件: 参照 BUFFER_PROFILE が CONFIG_DB に未登録のまま

### 2. direction mismatch (Dynamic model: buffermgrdyn.cpp)

`checkBufferProfileDirection()` (L3289-3295):
- profile の direction が egress でない (ingress profile を egress list に指定) → `task_failed`
- ログ: `SWSS_LOG_ERROR("Profile %s's direction is %s but %s is expected, applying profile failed")`
- ドロップ: エントリを消去して再試行なし

### 3. buffer pool 未準備 (Dynamic model: buffermgrdyn.cpp)

`handleSingleBufferPortProfileListEntry()` (L3408-3414):
- `!m_bufferPoolReady` の場合 → `m_bufferObjectsPending=true` を立て `task_success` 返却
- APPL_DB には書き込まない (silent pending)
- ログ: `SWSS_LOG_NOTICE("Buffer pools are not ready when configuring buffer %s profile list %s, pending")`

### 4. admin-down 期間のゼロプロファイル置換 (Dynamic model: buffermgrdyn.cpp)

`handleSingleBufferPortProfileListEntry()` (L3418-3438):
- `PORT_ADMIN_DOWN == portInfo.state` の場合、CONFIG_DB の profile_list の代わりに zero profile list を APPL_DB に書く
- ゼロプロファイルが未ロードの場合は `loadZeroPoolAndProfiles()` を呼ぶ
- ログなし (silent substitution)

### 5. キー形式不正 (Dynamic model: buffermgrdyn.cpp)

`handleBufferObjectTables()` (L3509-3513):
- `parseObjectNameFromKey()` がポート名として空を返す → `task_invalid_entry`
- ログ: `SWSS_LOG_ERROR("Invalid key format %s for %s table")`

### 6. 複数ポートキー途中 retry (Dynamic model: buffermgrdyn.cpp)

`handleBufferObjectTables()` (L3538-3547):
- カンマ区切りポートリスト処理中にいずれかが `task_need_retry` → 即 return、後続ポートは未処理
- 部分失敗シナリオ

### 7. プロファイル参照未解決 (orchagent: bufferorch.cpp)

`processEgressBufferProfileList()` (L1870-1881):
- `resolveFieldRefArray()` が `not_resolved` → `task_need_retry`
- ログ: `SWSS_LOG_INFO("Missing or invalid egress buffer profile reference specified for:%s")`
- その他失敗 → `task_failed`
- ログ: `SWSS_LOG_ERROR("Failed resolving egress buffer profile reference specified for:%s")`

### 8. trimming-eligible profile 指定 (orchagent: bufferorch.cpp)

`processEgressBufferProfileList()` (L1907-1921):
- `profCfg.isTrimmingEligible == true` → `task_failed`
- ログ: `SWSS_LOG_ERROR("Failed to configure egress buffer profile list(%s): buffer profile(%s) is trimming eligible")`

### 9. PORT 未準備 (orchagent: bufferorch.cpp)

`processEgressBufferProfileList()` (L1950-1955):
- `gPortsOrch->getPort()` で port_name が未登録 → `task_invalid_entry`
- ログ: `SWSS_LOG_ERROR("Port with alias:%s not found")`

### 10. SAI 失敗 / Bulk SAI エラー (orchagent: bufferorch.cpp)

`processEgressBufferProfileListPost()` (L1971-1980):
- `sai_status != SAI_STATUS_SUCCESS` → `handleSaiSetStatus()` 呼び出し
- ログ: `SWSS_LOG_ERROR("Failed to set egress buffer profile list on port, status:%d, key:%s")`
- Bulk モード: `SAI_BULK_OP_ERROR_MODE_IGNORE_ERROR` で他ポートはブロックされない
- retry 返却時は `consumer.m_toSync` に再登録 (L2031-2032)

### 11. 不明コマンド (orchagent: bufferorch.cpp)

`processEgressBufferProfileList()` (L1942-1944):
- SET/DEL 以外の op → ログのみで処理続行 (エラーとして扱わない)
- ログ: `SWSS_LOG_ERROR("Unknown command %s when handling BUFFER_PORT_EGRESS_PROFILE_LIST_TABLE key %s")`
