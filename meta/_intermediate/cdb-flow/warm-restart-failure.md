# WARM_RESTART — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-19 (chore/q67-f-batch1031)

調査対象:
- `sonic-net/sonic-swss-common` `common/warm_restart.cpp` (全291行)
  - `WarmStart::checkWarmStart()` L86-147
  - `WarmStart::getWarmStartTimer()` L149-172
  - `WarmStart::setWarmStartState()` L227-235
- `sonic-net/sonic-swss` `orchagent/orchdaemon.cpp`
  - `warmRestoreAndSyncUp()` L1092-1170

<!-- failure -->
## Phase D: 失敗挙動マトリクス

`WARM_RESTART` テーブルは `buffermgrdyn` や `bufferorch` のような
`task_process_status` ベースの retry ループとは異なる経路で参照される。
`WarmStart::checkWarmStart()` および `WarmStart::getWarmStartTimer()` が
起動時に一回だけ CONFIG_DB から同期的に読み取る設計であり、
失敗は「コールドスタートへのフォールバック」として表れる。

### A. `checkWarmStart()` 内のフォールバック経路 (warm_restart.cpp:86-147)

| 失敗条件 | 検出箇所 | 結果 | ログ | evidence |
|---|---|---|---|---|
| `STATE_DB WARM_RESTART_ENABLE_TABLE\|system.enable` が `"true"` 以外（未設定・disabled 含む）かつ `STATE_DB WARM_RESTART_ENABLE_TABLE\|<docker>.enable` も `"true"` 以外 | L88-101 | `m_enabled = false` → `hset(app_name, "restore_count", "0")` → `return false`（コールドスタート） | なし | `warm_restart.cpp:103-107` |
| warm start 有効だが `STATE_DB WARM_RESTART_TABLE\|<app>.restore_count` が空（DB フラッシュ済み等） | L110-121 | `m_enabled = false`, `m_systemWarmRebootEnabled = false` → `hset(..., "restore_count", "0")` → `return false`（コールドスタートフォールバック） | `SWSS_LOG_WARN "%s doing warm start, but restore_count not found in stateDB %s table, fall back to cold start"` | `warm_restart.cpp:111-121` |
| CONFIG_DB / STATE_DB 接続失敗（Redis 不到達） | `initialize()` 内 DBConnector コンストラクタ例外 | 例外が呼び元に伝播 → アプリプロセスが abort | 各アプリ側のクラッシュハンドラに依存 | `warm_restart.cpp:44-60` |

### B. `getWarmStartTimer()` 内のフォールバック経路 (warm_restart.cpp:149-172)

| 失敗条件 | 検出箇所 | 結果 | ログ | evidence |
|---|---|---|---|---|
| CONFIG_DB `WARM_RESTART\|<docker>.<app>_timer` が未設定 (`timer_value_str` が空) | L159-170 | `strtoul("", NULL, 0)` = 0 → `temp_value == 0` → `return 0`（タイマー値なし扱い） | `SWSS_LOG_NOTICE "warmStartTimer is not configured or invalid for docker: %s, app: %s"` | `warm_restart.cpp:168-171` |
| タイマー値が `MAXIMUM_WARMRESTART_TIMER_VALUE` (= 9999 秒) 超過 | L163-165 | `return 0`（無効値として無視） | 同上 | `warm_restart.cpp:168-171` |
| タイマー値が数値変換不能文字列 (`strtoul` が `ULONG_MAX` 返却) | L163-165 | `return 0` | 同上 | `warm_restart.cpp:168-171` |

`getWarmStartTimer()` が `0` を返した場合、呼び元（各プロセスの reconciliation ロジック）は
ハードコードデフォルト値（`bgp_timer` = 120 秒、`neighsyncd_timer` = 5 秒 等）にフォールバックする。

### C. `orchagent` warm start 再収束失敗 (orchdaemon.cpp:1092-1170)

`warmRestoreAndSyncUp()` 内では `WarmStart::setWarmStartState()` が
STATE_DB に直接書き込む（`swss::Table::hset()` → void）。
Redis 接続障害時は例外が伝播し orchagent プロセス abort → systemd 再起動が起動経路となる。

| 失敗条件 | 結果 | ログ | evidence |
|---|---|---|---|
| `warmRestoreValidation()` で未処理タスクが残存 | NOTICE ログのみ、abort せず reconciliation を継続 | `SWSS_LOG_NOTICE "Unfinished tasks..."` | `orchdaemon.cpp:1150-1152` |
| `syncd_apply_view()` 失敗（syncd との通信失敗） | orchagent プロセス abort | `SWSS_LOG_ERROR "..." + assert/exit` | `orchdaemon.cpp:1154-1157` |

### D. 失敗パターンサマリ

| # | トリガー | 直接挙動 | 自動回復 |
|---|---------|---------|---------|
| 1 | warm restart enable 未設定 / STATE_DB enable=false | `checkWarmStart()` が false → コールドスタート実行 | なし（設計上の正常経路） |
| 2 | `restore_count` 未存在（DB フラッシュ後等） | WARN ログ → コールドスタートフォールバック | なし（コールドスタートで自己回復） |
| 3 | タイマー未設定 / 無効値 | `getWarmStartTimer()` が 0 → ハードコードデフォルト使用 | なし（デフォルト値で継続） |
| 4 | Redis DB 接続失敗 | `initialize()` が例外 → プロセス abort → systemd 再起動 | systemd autorestart により自己回復 |
| 5 | `syncd_apply_view()` 失敗 | orchagent abort → systemd 再起動 | systemd autorestart により自己回復 |

> **重要**: `WARM_RESTART` テーブルの読み取りは各プロセスの**起動時一回**のみ。
> テーブル内容を変更しても実行中プロセスには反映されない。次回プロセス再起動時に有効になる。

### スキャン証跡

- `warm_restart.cpp` 全291行読了
- `checkWarmStart()` L86-147 全行読了
- `getWarmStartTimer()` L149-172 全行読了
- `orchdaemon.cpp` `warmRestoreAndSyncUp()` L1092-1170 参照

<!-- /failure -->
