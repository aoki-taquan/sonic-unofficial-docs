# CABLE_LENGTH — Phase D 失敗挙動メモ

ソース: `sonic-swss/cfgmgr/buffermgrdyn.cpp`, `cfgmgr/buffermgr.cpp`

## 1. dynamic モード (buffermgrdyn) の失敗パターン

### speed 未設定 → headroom 計算スキップ (no retry)
- `handleCableLenTable()` で `effectiveSpeed.empty()` の場合:
  - `SWSS_LOG_WARN("Speed for %s hasn't been configured yet, unable to calculate headroom", port.c_str())`
  - リトライキューに積まれず `continue` で次ポートへスキップ。
  - 「speed 設定時に `handlePortTable()` から再処理される」という設計意図で retry なし。
  - ソース: `buffermgrdyn.cpp:2155-2159`

### accumulative headroom 超過 → task_failed
- `refreshPgsForPort()` → `isHeadroomResourceValid()` でポートの累積 headroom が上限を超えた場合:
  - `SWSS_LOG_ERROR("Update speed (%s) and cable length (%s) for port %s failed, accumulative headroom size exceeds the limit", speed, cable_length, port)`
  - `releaseProfile(newProfile)` で新プロファイルを即時解放。
  - `task_process_status::task_failed` を返却。
  - **`handleCableLenTable()` はエラーを `failed_item_count` に加算し、全ポートを処理してから `task_failed` を返す**（途中中断しない）。
  - ソース: `buffermgrdyn.cpp:1541-1548`, `buffermgrdyn.cpp:2200-2208`

### BUFFER_POOL 未準備 → task_need_retry
- `allocateProfile()` で `getPgPoolMode()` が空文字列を返す（`ingress_lossless_pool` 未確立）場合:
  - `SWSS_LOG_INFO("BUFFER_PROFILE %s cannot be created because the buffer pool isn't ready")`
  - `task_process_status::task_need_retry` を返却。
  - Orch フレームワークが `BUFFERMGR_TIMER_PERIOD=10` 秒後に自動再試行。
  - ソース: `buffermgrdyn.cpp:978-979`

### Lua プラグイン実行失敗 → WARN のみ、プロファイル値は空のまま
- `calculateHeadroomSize()` の EVALSHA 呼び出し失敗:
  - `ret.empty()` の場合: `SWSS_LOG_WARN("Failed to calculate headroom for %s", headroom.name.c_str())`
  - `catch(...)` による例外: `SWSS_LOG_WARN("Lua scripts for headroom calculation were not executed successfully")`
  - いずれも `return` で関数を抜けるだけで例外は伝播しない。xon/xoff/size フィールドは空文字列のまま。
  - 空フィールドで APPL_DB に書き込まれると `bufferorch` 側でエラーが発生する可能性あり。
  - ソース: `buffermgrdyn.cpp:621-648`

### headroom チェック Lua 実行失敗 → WARN のみ、制約スキップ
- `isHeadroomResourceValid()` の EVALSHA 呼び出し失敗:
  - `SWSS_LOG_WARN("Failed to check headroom for %s", profile.name.c_str())`
  - エラー時は true を返却（＝headroom チェックなしで処理続行）。
  - ソース: `buffermgrdyn.cpp:1106`

### accumulated headroom check 失敗 → ERROR + task_failed
- `isHeadroomResourceValid()` が false の場合 (headroom 超過):
  - `SWSS_LOG_ERROR("Unable to update profile for port %s. Accumulative headroom size exceeds limit", port.c_str())`
  - `task_process_status::task_failed` を返却。
  - ソース: `buffermgrdyn.cpp:1117`

### PORT_ADMIN_DOWN 状態 → silent skip
- `refreshPgsForPort()` で `portInfo.state == PORT_ADMIN_DOWN` の場合:
  - `SWSS_LOG_INFO("Nothing to be done when port %s's cable length updated", port.c_str())`
  - `task_process_status::task_success` を返却（失敗扱いではない）。
  - ソース: `buffermgrdyn.cpp:2189-2193`

## 2. static モード (buffermgr) の失敗パターン

### speed 未設定 → task_need_retry
- `doSpeedUpdateTask()` で `m_cableLenLookup.count(port) == 0` の場合:
  - `SWSS_LOG_INFO("Unable to create/update PG profile for port %s. Cable length is not set")`
  - `task_process_status::task_need_retry` を返却。
  - ソース: `buffermgr.cpp:154-155`

### PORT_QOS_MAP 未着 → task_need_retry
- `m_portStatusLookup.count(port) == 0` の場合（`pfc_enable` 未取得）:
  - `SWSS_LOG_INFO("pfc_enable status is not available for port %s")`
  - `task_process_status::task_need_retry` を返却。
  - PORT_QOS_MAP が着信した時点で自動再処理される。
  - ソース: `buffermgr.cpp:168-170`

### pg_profile_lookup.ini に該当エントリなし → task_invalid_entry
- `m_pgProfileLookup.count(speed) == 0 || m_pgProfileLookup[speed].count(cable) == 0` の場合:
  - `SWSS_LOG_ERROR("Unable to create/update PG profile for port %s. No PG profile configured for speed %s and cable length %s", port, speed, cable)`
  - `task_process_status::task_invalid_entry` を返却（エントリが破棄され retry されない）。
  - **static モード固有の問題**: INI ファイルに存在しない speed/cable 組み合わせを設定すると、恒久的に lossless PG が設定されない。
  - ソース: `buffermgr.cpp:240-243`

### BUFFER_POOL 未準備 → task_need_retry (static)
- `getPgPoolMode()` が空文字列を返す場合:
  - `SWSS_LOG_INFO("PG lossless pool is not yet created")`
  - `task_process_status::task_need_retry` を返却。
  - ソース: `buffermgr.cpp:257-258`

## 3. 失敗時の挙動まとめ

| 条件 | モード | 返却ステータス | retry? | ログレベル |
|------|--------|--------------|--------|------------|
| speed 未設定 | dynamic | (ポートスキップ) | no (speed 設定時に再処理) | WARN |
| speed 未設定 | static | task_need_retry | yes (10 秒周期) | INFO |
| accumulative headroom 超過 | dynamic | task_failed | no | ERROR |
| BUFFER_POOL 未準備 | dynamic | task_need_retry | yes (10 秒周期) | INFO |
| Lua 実行失敗 | dynamic | (関数継続) | no | WARN |
| INI エントリなし | static | task_invalid_entry | no (エントリ破棄) | ERROR |
| PORT_QOS_MAP 未着 | static | task_need_retry | yes (PORT_QOS_MAP 着信時) | INFO |
| PORT_ADMIN_DOWN | dynamic | task_success | — (admin up 時に再処理) | INFO |
