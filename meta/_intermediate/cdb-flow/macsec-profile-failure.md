# macsec-profile — Phase D 失敗挙動 中間調査ファイル

ソース調査対象:
- `sonic-swss/cfgmgr/macsecmgr.cpp`
- `sonic-swss/orchagent/macsecorch.cpp`

## 失敗パス一覧

| # | トリガー | 発生箇所 | 結果 | retry |
|---|---------|---------|------|-------|
| 1 | `cipher_suite` に不正値 | `lexical_convert()` → `throw std::invalid_argument("Invalid cipher_suite : ...")` | `catch(invalid_argument)` → `SWSS_LOG_WARN` → `task_failed` | なし |
| 2 | CAK 長が `cipher_suite` と不一致 | `decodeKey()` → `throw std::invalid_argument("Invalid length for cipher_string : ...")` | 同上 → `task_failed` | なし |
| 3 | `policy` に不正値 | `lexical_convert()` → `throw std::invalid_argument("Invalid policy : ...")` | 同上 → `task_failed` | なし |
| 4 | `wpa_supplicant` fork 失敗（`fork()` 返値 < 0） | `startWPASupplicant()` | `SWSS_LOG_WARN("Cannot start the wpa_supplicant of the port '%s' : %s")` + `errno` → `task_failed` | なし |
| 5 | `wpa_supplicant` 起動後 socket 接続タイムアウト | `startWPASupplicant()` retry ループ後 | `stopWPASupplicant()` 呼び出し + `SWSS_LOG_WARN("Cannot connect to wpa_supplicant.")` → `task_failed` | なし |
| 6 | MKA プロファイルロード失敗 | `loadMKAProfile()` → 例外 | `SWSS_LOG_WARN("The MACsec profile '%s' on the port '%s' loading fail")` → `task_failed` | なし |
| 7 | `enableMACsec()` 内 `runtime_error` | `catch(runtime_error)` | `SWSS_LOG_WARN("Enable MACsec fail : %s")` → ポートは非暗号化のまま継続 | なし |
| 8 | `disableMACsec()` で wpa_supplicant 停止失敗 | `stopMKASession()` / `stopWPASupplicant()` | `SWSS_LOG_WARN("Cannot stop MKA session ...")` / `SWSS_LOG_WARN("Cannot stop WPA_SUPPLICANT ...")` → `task_failed`、プロセス残留の可能性 | なし |
| 9 | SAI `create_macsec_*` / `set_macsec_*` 恒久エラー | `parseHandleSaiStatusFailure()` | `task_failed` または `task_need_retry`（一時エラーは無制限 retry） | 一時のみ無制限 |
| 10 | SAI MACsec POST 失敗通知 | `doPostCompletionTask()` | `setMacsecPostState(m_state_db, "fail")` + `SWSS_LOG_ERROR("MACSec POST failed")` → STATE_DB に "fail" を記録 | なし |
| 11 | プロファイル DEL 時にポートが使用中 | `removeProfile()` | `SWSS_LOG_DEBUG` のみ → `task_need_retry`（全ポート MACsec 無効化まで待機） | 無制限 |
| 12 | フィールド値の型変換失敗 | `GetValue()` → `SWSS_LOG_ERROR("Cannot convert value(%s) in field(%s)")` | デフォルト / 前回値を使用して続行 | — |

## task_failed 後の挙動

`macsecmgr` は `task_failed` を返すと Consumer がエントリを破棄。ポートは MACsec 無効のまま継続動作。
`macsecorch` も同様。SAI 一時エラー（`SAI_STATUS_NOT_READY` 等）は `task_need_retry` で無制限再試行。

## wpa_supplicant 起動失敗の詳細

`fork()` 後に子プロセスが `execv(WPA_SUPPLICANT_CMD, ...)` を実行。失敗ケース:
1. `/sbin/wpa_supplicant` バイナリが存在しない → `fork()` 失敗ではなく `execv` 失敗（`errno = ENOENT`）
2. Unix socket 接続を `WPA_CONNECT_RETRY_TIMES` 回試みて失敗 → `stopWPASupplicant()` + `wpa_supplicant_pid = 0` で番号クリア

## SAI POST 失敗の詳細

`macsecorch` 初期化時に `SAI_SWITCH_ATTR_MACSEC_POST_STATUS` を照会。
- `SAI_SWITCH_MACSEC_POST_STATUS_FAIL` → `STATE_DB` の `MACSEC_POST|switch` に `status: fail` 書き込み
- `macsec_post_status` 通知でも同様（個別 SAI MACsec オブジェクト単位の失敗も集約して "fail" 記録）

## evidence

- `macsecmgr.cpp` L428-431: `catch(invalid_argument)` → `task_failed`
- `macsecmgr.cpp` L544-558: `wpa_supplicant` 起動失敗処理
- `macsecmgr.cpp` L676: `Cannot connect to wpa_supplicant.`
- `macsecmgr.cpp` L838: `Enable MACsec fail`
- `macsecmgr.cpp` L918: `Disable MACsec fail`
- `macsecorch.cpp` L710-711: POST fail → STATE_DB
- `macsecorch.cpp` L791-792: POST fail via notification
