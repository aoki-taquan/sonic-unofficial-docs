# CONFIG_DB 例外条件分析: BUFFER_PG

## Consumer

- `buffermgrd` (static モード): `sonic-swss/cfgmgr/buffermgr.cpp`
- `buffermgrd` (dynamic モード): `sonic-swss/cfgmgr/buffermgrdyn.cpp`
- `orchagent` (`flexcounterorch.cpp`): PG ウォーターマークカウンタ有効化時に参照

## 例外条件

### 1. profile フィールド参照形式不正 → task_invalid_entry (drop)
- dynamic モード: `handleSingleBufferPgEntry()` で `profile` フィールドの参照形式が `[BUFFER_PROFILE|name]` でない場合:
  `SWSS_LOG_ERROR("BUFFER_PG: Invalid format of reference to profile: %s", value.c_str())` → `task_invalid_entry`。
- ソース: `buffermgrdyn.cpp` L3133-3138

### 2. 参照プロファイルが未設定 → task_need_retry (再試行)
- `profileName` が `m_bufferProfileLookup` に存在しない場合:
  `SWSS_LOG_INFO("Profile %s hasn't been configured yet, skip")` → `task_need_retry`。
- ソース: `buffermgrdyn.cpp` L3150-3151

### 3. 不正フィールド名 → task_invalid_entry (drop)
- `profile` 以外のフィールドが SET で来た場合:
  `SWSS_LOG_ERROR("BUFFER_PG: Invalid field %s", field.c_str())` → `task_invalid_entry`。
- ソース: `buffermgrdyn.cpp` L3180-3185

### 4. PG ID パース失敗 (std::invalid_argument) → Ignore
- static モード: PG ID を `to_uint<uint8_t>()` でパース失敗時、`// Ignore invalid value` としてその PG をスキップ。
- ソース: `buffermgr.cpp` L197-200

### 5. speed / cable_length 組み合わせ未定義 → task_invalid_entry
- static モード: `m_pgProfileLookup[speed][cable]` が存在しない:
  `SWSS_LOG_ERROR("Unable to create/update PG profile for port %s. No PG profile configured for speed %s and cable length %s")` → `task_invalid_entry`。
- ソース: `buffermgr.cpp` L238-242

### 6. 管理 down ポートでの非デフォルトプロファイル → 削除しない
- static モード: ポートが admin down で、かつプロファイルがデフォルト (`pg_lossless_<speed>_<cable>_profile`) でない場合:
  `SWSS_LOG_NOTICE("Not default profile %s is configured on PG %s, won't reclaim buffer")` → BUFFER_PG エントリを削除しない。
- ソース: `buffermgr.cpp` L228

### 7. ポート admin_status 不明 → デフォルト down 扱い
- `SWSS_LOG_INFO("admin_status is not available for port %s, assuming default down")` → down として扱う。
- ソース: `buffermgr.cpp` L565

### 8. zero buffer profile 未設定でバッファ回収不可 → LOG_ERROR
- dynamic モード: zero_profile が pool に未設定で `removing buffer items` が未サポートの場合:
  `SWSS_LOG_ERROR("Zero profile is not provided for pool %s while removing buffer items is not supported")`.
- ソース: `buffermgrdyn.cpp` L381-384

### 9. admin down ポートへの BUFFER_PG 直接 APPL_DB 書き込み
- ポートが admin down の場合、APPL_DB への書き込みをスキップして内部状態のみ保持。
  ポートが up したとき APPL_DB に反映される (`handleSetSingleBufferObjectOnAdminDownPort`)。
- ソース: `buffermgrdyn.cpp` L3202, L3245
