# CONFIG_DB 例外条件分析: BUFFER_POOL

## Consumer

- `buffermgrd` (static モード): `sonic-swss/cfgmgr/buffermgr.cpp`
- `buffermgrd` (dynamic モード): `sonic-swss/cfgmgr/buffermgrdyn.cpp`

## 例外条件

### 1. xoff フィールドが ingress_lossless_pool 以外に設定 → LOG_ERROR + ignored
- `handleBufferPoolTable()`: `xoff` フィールドが `INGRESS_LOSSLESS_PG_POOL_NAME` 以外のプールに設定された場合:
  `SWSS_LOG_ERROR("Field xoff is supported for %s only, but got for %s, ignored")`.
  xoff は無視されるが他フィールドは処理される。
- ソース: `buffermgrdyn.cpp` L2625

### 2. xoff が MMU サイズ超過 → LOG_ERROR + xoff 無視・pool size は更新
- `SWSS_LOG_ERROR("Buffer pool %s: Invalid xoff %s, exceeding the mmu size %s, ignored xoff but the pool size will be updated")`.
- ソース: `buffermgrdyn.cpp` L757

### 3. Shared headroom pool 設定が変化なし → skip (no APPL_DB write)
- `SWSS_LOG_INFO("Shared headroom pool size updated without change (new %s vs current %s), skipped")`.
- ソース: `buffermgrdyn.cpp` L2614

### 4. Zero buffer profile が複数登録 → 最初を使用、後続を無視
- 同一 pool に複数の zero profile が検出された場合:
  `SWSS_LOG_ERROR("Multiple zero profiles (%s, %s) detected for pool %s, takes the former and ignores the latter")`.
- ソース: `buffermgrdyn.cpp` L338-339

### 5. Buffer pools が準備できていない状態でのプロファイル設定 → pending
- `SWSS_LOG_NOTICE("Buffer pools are not ready when configuring buffer profile %s, pending")` → 処理遅延。
- ソース: `buffermgrdyn.cpp` L894

### 6. 共有バッファプール未設定 → headroom 計算スキップ
- `SWSS_LOG_INFO("No shared buffer pool configured, skip calculating shared buffer pool size")`.
- ソース: `buffermgrdyn.cpp` L684

### 7. task_invalid_entry → drop (ログのみ)
- buffermgr.cpp の main loop: `task_invalid_entry` の場合 `SWSS_LOG_ERROR("Failed to process invalid entry, drop it")` としてエントリを破棄。
- ソース: `buffermgr.cpp` L585-586

### 8. static モード: プロファイルが既存の場合 skip creation
- `// check if profile already exists - if yes - skip creation` — 既存プロファイルは BUFFER_POOL 作成をスキップ。
- ソース: `buffermgr.cpp` L246
