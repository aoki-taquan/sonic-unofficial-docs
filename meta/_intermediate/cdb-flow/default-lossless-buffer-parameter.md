# CONFIG_DB 例外条件分析: DEFAULT_LOSSLESS_BUFFER_PARAMETER

## Consumer

- `buffermgrdyn` (`cfgmgr/buffermgrdyn.cpp`): dynamic buffer モード専用ハンドラ `handleDefaultLossLessBufferParam()` が処理。static buffer モード (`buffermgrd`) では参照されない。

## 例外条件

### 1. ingress lossless pg pool 未設定 → task_need_retry
- ソース: `buffermgrdyn.cpp` L1987-1991
- `INGRESS_LOSSLESS_PG_POOL_NAME` が `m_bufferPoolLookup` に未登録の場合 `SWSS_LOG_INFO("%s has not been configured, need to retry")` → `task_need_retry`。

### 2. DEL コマンド → over_subscribe_ratio をクリアして SHP 再計算
- ソース: `buffermgrdyn.cpp` L2007-2009
- DEL が来ると `newRatio = ""` として `over_subscribe_ratio` をリセットし Shared Headroom Pool (SHP) を再計算する。

### 3. SET / DEL 以外のコマンド → task_failed
- ソース: `buffermgrdyn.cpp` L2011-2013
- `SWSS_LOG_ERROR("Unsupported command %s received for DEFAULT_LOSSLESS_BUFFER_PARAMETER table")` → `task_failed`。

### 4. over_subscribe_ratio 変更時 SHP が未反映 → task_need_retry
- ソース: `buffermgrdyn.cpp` L2025-2031
- `over_subscribe_ratio` が 0→非0 に変わる (SHP 有効化) タイミングで、SAI への xoff 設定が未完了の場合 `isSharedHeadroomPoolEnabledInSai()` が false → `task_need_retry`。xoff が APPL_STATE_DB に反映されるまで待機。

### 5. xoff フィールドが ingress_lossless_pool 以外の pool に指定 → 無視
- ソース: `buffermgrdyn.cpp` L2625
- `over_subscribe_ratio` 処理中に xoff が ingress lossless pool 以外のプールに指定されると `SWSS_LOG_ERROR("Field xoff is supported for %s only, but got for %s, ignored")` → 無視 (xoff は ingress lossless 専用)。

### 6. static buffer モードでは無視
- ソース: `buffermgrd.cpp` (CFG_DEFAULT_LOSSLESS_BUFFER_PARAMETER への subscribe なし)
- static buffer モード (`-m static`) 時は `buffermgrd` が動作するが DEFAULT_LOSSLESS_BUFFER_PARAMETER は listen しない。テーブルは CONFIG_DB に書いても何も起きない。
