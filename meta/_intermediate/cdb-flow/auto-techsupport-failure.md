# AUTO_TECHSUPPORT — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-auto-techsupport)

ソース:

- `sonic-net/sonic-utilities/scripts/coredump_gen_handler.py`
- `sonic-net/sonic-utilities/scripts/techsupport_cleanup.py`
- `sonic-net/sonic-utilities/utilities_common/auto_techsupport_helper.py`
- 補助: `sonic-net/sonic-utilities/scripts/memory_threshold_check.py` (`available_mem_threshold` / `min_available_mem` パス)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

### techsupport 起動失敗・retry (`auto_techsupport_helper.invoke_ts_cmd`)

`show techsupport` を `subprocess_exec` 経由で起動した直後の `returncode` を分岐させる。

| 条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `rc == EXT_LOCKFAIL` (`2`) — flock 取得失敗 (別 instance が `show techsupport` 実行中) | `invoke_ts_cmd()` | retry せず即時 abort・新規ダンプ作成なし・STATE_DB 書込なし | `LOG_NOTICE "Another instance of techsupport running, aborting this. stderr: ..."` | `auto_techsupport_helper.py:239-240` |
| `rc == EXT_RETRY` (`4`) かつ `num_retry <= MAX_RETRY_LIMIT` (`2`) | `invoke_ts_cmd()` | `invoke_ts_cmd(db, num_retry+1)` で再帰再試行 (最大 2 回追加) | なし | `auto_techsupport_helper.py:241-243,84` |
| `rc == EXT_RETRY` かつ `num_retry > MAX_RETRY_LIMIT` | `invoke_ts_cmd()` | retry 打ち切り・新規ダンプ作成なし | `LOG_ERR "MAX_RETRY_LIMIT for show techsupport invocation exceeded, stderr: ..."` | `auto_techsupport_helper.py:244-245` |
| `rc != EXT_SUCCESS` かつ上記以外 (汎用失敗) | `invoke_ts_cmd()` | retry なし・新規ダンプ作成なし | `LOG_ERR "show techsupport failed with exit code {rc}, stderr: ..."` | `auto_techsupport_helper.py:246-247` |
| `rc == EXT_SUCCESS` だが stdout に `sonic_dump_.*tar.*` 正規表現マッチなし | `parse_ts_dump_name()` → `invoke_ts_cmd()` | 空文字返却・`write_to_state_db()` 不呼出 (STATE_DB 更新なし) | `LOG_ERR "stdout of the 'show techsupport' cmd doesn't have the dump name"`, `LOG_ERR "{cmd} was run, but no techsupport dump is found"` | `auto_techsupport_helper.py:228-229,250-251` |
| `show techsupport --global-timeout 60` の **60 秒** タイムアウト経過 | `show techsupport` 内部 (本スクリプトは exit code のみ観測) | `subprocess_exec` は完了し非 0 返却 → 上記 `rc != EXT_SUCCESS` パスへ流入 | `LOG_ERR "show techsupport failed with exit code ..."` | `auto_techsupport_helper.py:71` (`TS_GLOBAL_TIMEOUT="60"`), `235` |

!!! note "Python レベルの subprocess timeout は未指定"
    `subprocess_exec()` (`auto_techsupport_helper.py:87-94`) は `subprocess.run` に `timeout=` を渡さない。
    タイムアウト制御は `show techsupport` CLI 側の `--global-timeout 60` だけが effective。
    Python 側で `subprocess.TimeoutExpired` が raise されることはなく、`try/except` も置かれていない。

### rate-limit による skip (失敗ではないが「techsupport が作られない」分岐)

`invoke_ts_command_rate_limited()` が `invoke_ts_cmd()` 呼出前に評価する。

| 条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `time.time() - mtime(<最新ts_dump>) < GLOBAL.rate_limit_interval` | `verify_rate_limit_intervals()` | グローバル rate-limit 未経過 → `False` 返却 → `invoke_ts_cmd()` をスキップ | `syslog "Global rate_limit_interval period has not passed. Techsupport Invocation is skipped"` | `auto_techsupport_helper.py:285-290` |
| `time.time() - <container 最古 entry> < FEATURE.rate_limit_interval` | `verify_rate_limit_intervals()` | コンテナ単位 rate-limit 未経過 → `False` 返却 → 同上 | `syslog "Per Container rate_limit_interval for {container} has not passed. Techsupport Invocation is skipped"` | `auto_techsupport_helper.py:292-298` |
| `GLOBAL.rate_limit_interval` / `FEATURE.rate_limit_interval` が `ValueError` (非数値) | `invoke_ts_command_rate_limited()` | `0.0` に fallback → rate-limit 実質無効化 (skip ではなく無効化) | なし | `auto_techsupport_helper.py:323-331` |

### CONFIG_DB state ガードによる skip

| 条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `AUTO_TECHSUPPORT|GLOBAL.state != "enabled"` (未設定含む) | `CriticalProcCoreDumpHandle.handle_core_dump_creation_event()` | techsupport 起動スキップ・cleanup もスキップ | `LOG_NOTICE "auto_invoke_ts is disabled. No cleanup is performed: core ..."` | `coredump_gen_handler.py:47-48` |
| `AUTO_TECHSUPPORT_FEATURE|<container>.state != "enabled"` | `handle_core_dump_creation_event()` | 当該 feature の techsupport 起動スキップ | `LOG_NOTICE "auto-techsupport feature for {container} is not enabled. Techsupport Invocation is skipped. core: ..."` | `coredump_gen_handler.py:55-57` |
| `coredump_gen_handler.main()` で `verify_recent_file_creation()` が False (core ファイル mtime が 20 秒以上前) | `verify_recent_file_creation()` | spurious invocation として早期 return・techsupport 起動なし | `LOG_INFO "Spurious Invocation. {file_path} is not created within last 20 sec"` | `coredump_gen_handler.py:73-74`, `auto_techsupport_helper.py:115-125` |
| `core_file_path` の `os.path.getmtime()` が `Exception` (ファイル不在等) | `verify_recent_file_creation()` | `False` 返却 → 上記 spurious 分岐 | なし | `auto_techsupport_helper.py:118-121` |

### cleanup (disk full / max_core_limit / max_techsupport_limit) 失敗

`cleanup_process()` は `/var/core` `/var/dump` 配下の disk 使用率を限界内に保つ。

| 条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `core_usage` / `max_techsupport_limit` が `ValueError` (非数値) | `handle_coredump_cleanup()` / `handle_techsupport_creation_event()` | `0.0` に fallback → `if not max_ts` ガードで cleanup スキップ | `LOG_NOTICE "max-techsupport-limit argument is not set. No cleanup is performed, current size occupied: ..."` / `"core-usage argument is not set. ..."` | `coredump_gen_handler.py:23-30`, `techsupport_cleanup.py:33-40` |
| `limit` が `(0,100)` 範囲外 (`<=0` または `>=100`) | `cleanup_process()` | cleanup 実施せず即時 return | `LOG_ERR "core_usage_limit can only be between 1 and 100, whereas the configured value is: {limit}"` | `auto_techsupport_helper.py:173-175` |
| `curr_size <= max_limit_bytes` (まだ閾値未到達) | `cleanup_process()` | 削除せず early return | なし | `auto_techsupport_helper.py:181-182` |
| `os.remove(<oldest dump>)` が `OSError` (権限 / 既に削除済 / disk error) | `cleanup_process()` | `continue` で当該ファイル skip・次の古いファイルへ進む (raise しない) | なし (silent skip) | `auto_techsupport_helper.py:193-194` |
| `len(fs_stats) <= 1` (最新ダンプ 1 個のみ) | `cleanup_process()` | 最新は必ず保持 — 閾値未達成のままループ脱出 | `LOG_INFO "{deleted} deleted from {dir}"` (削除量 0 でも emit) | `auto_techsupport_helper.py:188,196` |
| disk full で新規 techsupport 作成自体が `show techsupport` 内部で失敗 | (本スクリプト外) | `invoke_ts_cmd()` の `rc != EXT_SUCCESS` 経路に流入 | `LOG_ERR "show techsupport failed with exit code ..."` | `auto_techsupport_helper.py:246-247` |

### memory check 失敗 (`memory_threshold_check.py`)

`available_mem_threshold` / `min_available_mem` の評価は本ハンドラ群と独立したスクリプトで実施され、techsupport 起動可否を exit code で返す。

| 条件 | 検出箇所 | exit code | 挙動 | evidence |
|---|---|---|---|---|
| `available_mem_threshold` / `min_available_mem` が `float()` 変換失敗 | `MemoryChecker.check_*()` | `EXIT_FAILURE` (`1`) | `MemoryCheckerException` raise → 呼出元で catch・techsupport 不起動 | `memory_threshold_check.py:36-37,154-156,232-235` |
| `MemAvailable` が `/proc/meminfo` 取得不能 (`KeyError`/`ValueError`) | `MemoryChecker._get_meminfo()` | `EXIT_FAILURE` (`1`) | 同上 | `memory_threshold_check.py:104-108` |
| 空きメモリ < `min_available_mem` または `< available_mem_threshold` % | `MemoryChecker.check_*()` | `EXIT_THRESHOLD_CROSSED` (`2`) | techsupport を起動しない通常スキップ (失敗ではなく抑止) | `memory_threshold_check.py:11-12,177,232` |
| `available_mem_threshold == 0` | `MemoryChecker.check_*()` | (チェック自体スキップ) | システムメモリチェック全体をバイパス。feature 単位チェックのみ実施 | `memory_threshold_check.py` (本ページ「例外条件」表参照) |

### PATH 注入失敗

| 条件 | 検出箇所 | 結果 | evidence |
|---|---|---|---|
| `CROSS_BUILD_ENVIRON=y` が環境変数として設定 | `auto_techsupport_helper.py` import 時 | `/usr/local/sbin:...:/bin:` の `PATH` 注入をスキップ → クロスビルド環境では `show` / `date` が見つからない可能性 | `auto_techsupport_helper.py:74-78` |

### 部分成功・冪等性

- `cleanup_process()` は OSError を `continue` で握り潰すため、一部ファイル削除失敗があっても残りの削除は続行する。`removed_files` リストには成功分のみ append される。
- `clean_state_db_entries()` は `cleanup_process()` 返却の `removed_files` のみを反復するため、削除失敗ファイルに対応する STATE_DB の `AUTO_TECHSUPPORT_DUMP_INFO|<name>` は残存する。次回 cleanup ループで再試行される。
- `invoke_ts_cmd()` は再帰 retry を採用しているため、`EXT_RETRY` が 3 回連続 (初回 + `MAX_RETRY_LIMIT`=2 回再帰) で必ず打ち切られる (`num_retry == 0,1,2,3` で `3 > 2` を満たして抜ける)。
- `write_to_state_db()` は `new_file` が truthy のときのみ呼ばれる。techsupport 起動が失敗した場合は STATE_DB に entry が作られず、次回 rate-limit 判定はその起動失敗を「未起動」として扱う (rate-limit リセットされない)。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `LOG_ERR` (auto-techsupport 関連) | 4 | `auto_techsupport_helper.py:174,228,245,247,251` |
| `LOG_NOTICE` (skip 系) | 4 | `coredump_gen_handler.py:19,48,57`, `techsupport_cleanup.py:29,40`, `auto_techsupport_helper.py:240` |
| `try/except` | 6 | `coredump_gen_handler.py:23-26`, `techsupport_cleanup.py:33-36`, `auto_techsupport_helper.py:118-121,193-194,269-272,323-326,328-331` |
| `MAX_RETRY_LIMIT` 参照 | 2 | `auto_techsupport_helper.py:84,242,245` |
| `EXT_LOCKFAIL` / `EXT_RETRY` / `EXT_SUCCESS` 参照 | 4 | `auto_techsupport_helper.py:81-83,239,241,246,248` |
| `raise` (例外送出) | 1 (補助スクリプト側) | `memory_threshold_check.py:108,156,235` |

> **Evidence**:
> `sonic-net/sonic-utilities/scripts/coredump_gen_handler.py:17,22-30,47-48,55-57,73-74`;
> `sonic-net/sonic-utilities/scripts/techsupport_cleanup.py:23,27-30,33-43`;
> `sonic-net/sonic-utilities/utilities_common/auto_techsupport_helper.py:71,74-78,81-84,87-94,115-125,171-197,232-254,282-299,313-337`;
> 補助: `sonic-net/sonic-utilities/scripts/memory_threshold_check.py:11-12,36-37,104-108,154-156,177,232-235`
<!-- /failure -->
