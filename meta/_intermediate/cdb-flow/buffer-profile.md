# CONFIG_DB 例外条件分析: BUFFER_PROFILE

## Consumer

- `orchagent` の `BufferOrch::doBufferProfileTask`: BUFFER_PROFILE テーブルの変更を処理し SAI buffer profile オブジェクトを生成・更新・削除する。
- `buffermgrd` / `buffermgrdyn`: dynamic buffer mode 時は buffermgrdyn が BUFFER_PROFILE を自動生成・管理。

## 例外条件

### 1. pool 参照未解決 → task_need_retry
- ソース: `bufferorch.cpp` L645-651
- `pool` フィールドに参照する BUFFER_POOL が未存在の場合 `SWSS_LOG_INFO("Missing or invalid pool reference specified")` → `task_need_retry`。

### 2. pending remove エントリへの SET → task_need_retry
- ソース: `bufferorch.cpp` L618-620
- 削除待ち状態 (`m_pendingRemove==true`) のエントリに SET が来ると `SWSS_LOG_NOTICE("Entry ... is pending remove, need retry")` → `task_need_retry`。

### 3. pool / threshold_type は create-only → 更新スキップ
- ソース: `bufferorch.cpp` L655-659, L694-714
- 既存 profile オブジェクト (`sai_object != SAI_NULL_OBJECT_ID`) への更新で `pool` や `dynamic_th` / `static_th` の threshold_type 変更は **スキップ** (`SWSS_LOG_INFO("Skip setting buffer profile's pool/threshold type ...")`。pool ID と threshold mode は SAI create-only 属性。

### 4. packet_discard_action の不正値 → task_failed
- ソース: `bufferorch.cpp` L733-745
- `packet_discard_action` が `drop` / `trim` 以外の場合 `SWSS_LOG_ERROR("Failed to parse buffer profile ... invalid value")` → `task_failed`。

### 5. trimming 禁止制約チェック失敗 → task_failed
- ソース: `bufferorch.cpp` L757-762
- `packet_discard_action=trim` のプロファイルが ingress profile list や PG に既に関連付けられている場合 `isTrimmingProhibited()` が true → `SWSS_LOG_ERROR("trimming is prohibited by dependency constraint check")` → `task_failed`。

### 6. SAI SET が ATTR_NOT_IMPLEMENTED → task_ignore
- ソース: `bufferorch.cpp` L776
- `sai_buffer_api->set_buffer_profile_attribute()` が `SAI_STATUS_ATTR_NOT_IMPLEMENTED_0` を返した場合 `task_ignore` (警告ログのみ。処理継続)。

### 7. 不明フィールド → エラーログして continue
- ソース: `bufferorch.cpp` L746-748
- `pool`, `xon`, `xon_offset`, `xoff`, `size`, `dynamic_th`, `static_th`, `packet_discard_action` 以外のフィールドは `SWSS_LOG_ERROR("Unknown buffer profile field specified:..., ignoring")` して当該フィールドをスキップ。
