# AUTO_TECHSUPPORT_FEATURE — 失敗挙動 / retry 分析 (Phase D)

対象テーブル: `AUTO_TECHSUPPORT_FEATURE`
対象消費者: `scripts/coredump_gen_handler.py`, `scripts/techsupport_cleanup.py`, `utilities_common/auto_techsupport_helper.py`

本テーブルは OrchAgent 経由ではなく Python ワンショットスクリプトが `HGET` で参照する。
従って Orch の `task_need_retry` / `task_invalid_entry` パターンは適用されない。
失敗時の挙動は (a) syslog ログ出力 + 早期 return / 終了、(b) `EXT_RETRY` 終了コードによる `invoke_ts_cmd` 再呼び出し、(c) 内部 `try/except` での fallback 値置換、の 3 系統に整理できる。

## 1. 失敗カテゴリ概要

| カテゴリ | 代表トリガ | retry 有無 | 影響 |
|---|---|---|---|
| **設定欠落 / 不正値** | `state` / `rate_limit_interval` / `available_mem_threshold` が空・非数値 | なし (内部 fallback) | techsupport 抑止 or rate-limit 無効化 |
| **disabled 状態** | `AUTO_TECHSUPPORT\|GLOBAL.state != enabled` / `AUTO_TECHSUPPORT_FEATURE\|<feat>.state != enabled` | なし | early return、NOTICE ログのみ |
| **container offline / feature 名不一致** | `<feat>` キー不在、`trim_masic_suffix` 後も不一致 | なし | `HGET` が None → `!= "enabled"` 評価で skip |
| **core 上限超過 (disk full)** | `/var/core` 配下が `core_usage` 比率超過 | なし (削除のみ) | 古い core を順次 unlink。`OSError` は continue で握り潰し |
| **techsupport tarball 上限超過** | `/var/dump` 配下が `max_techsupport_limit` 超過 | なし | 古い tarball を unlink + STATE_DB から `AUTO_TECHSUPPORT_DUMP_INFO` 削除 |
| **`generate_dump` lock 失敗 (`EXT_LOCKFAIL=2`)** | 別 techsupport が同時実行中 | retry なし | NOTICE ログ出して abort |
| **`generate_dump` retry 要求 (`EXT_RETRY=4`)** | `show techsupport` が内部リトライ要求 | 最大 `MAX_RETRY_LIMIT=2` 回再帰呼び出し | 上限超過で ERR ログのみ |
| **`generate_dump` その他 rc != 0** | subprocess 失敗、SIGKILL 等 | なし | ERR ログのみ |
| **`show techsupport` 成功も dump 名 parse 失敗** | stdout に `sonic_dump_.*tar.*` パターン無し | なし | ERR ログ。STATE_DB に書かれない |
| **`verify_recent_file_creation` false** | core / dump が直近 `TIME_BUF=20` 秒以内に作られていない | なし | 即 return (spurious invocation 防止) |
| **rate-limit 未経過** | `time.time() - last_creation < cooloff` | なし | `verify_rate_limit_intervals → False` で skip。次回 core dump 時に再評価 |
| **`cleanup_process` の `OSError`** | unlink 失敗 (権限・disk error) | なし (continue) | 失敗ファイルを飛ばして次の候補へ |
| **`cleanup_process` limit 範囲外** | `0 < limit < 100` を外れる | なし | ERR ログ出して return。cleanup スキップ |

## 2. retry の存在経路は 1 か所のみ

```
invoke_ts_cmd(db, num_retry=0)
  ↓ subprocess_exec(["show", "techsupport", ...])
  rc == EXT_RETRY (=4) かつ num_retry <= MAX_RETRY_LIMIT (=2)
    ↓ return invoke_ts_cmd(db, num_retry+1)   # 再帰
  上限超過 → syslog.LOG_ERR "MAX_RETRY_LIMIT ... exceeded"
```

- 再帰 retry は `show techsupport` 本体に対する内部リクエストであり、`AUTO_TECHSUPPORT_FEATURE` の field 評価には戻らない (rate-limit cooloff は 1 回目の判定でのみ評価)。
- `EXT_LOCKFAIL` (=2) は再試行せず即 abort。複数 core dump 同時発生時に 2 個目以降が握り潰される設計。

## 3. subprocess 失敗の詳細

`auto_techsupport_helper.py:invoke_ts_cmd` の分岐:

| `rc` | 定数 | 値 | 動作 |
|---|---|---|---|
| `EXT_LOCKFAIL` | 2 | NOTICE ログ "Another instance of techsupport running, aborting this" | 即 abort、retry なし |
| `EXT_RETRY` | 4 | 最大 2 回 再帰 retry | 上限超で ERR ログ |
| `EXT_SUCCESS` | 0 | stdout から dump 名 parse | parse 失敗時のみ ERR ログ |
| その他 | - | "show techsupport failed with exit code N" | retry なし |

`subprocess_exec` 自体は `subprocess.run` をラップ。例外は補足せず raise されると上位 main で uncaught (`coredump_gen_handler.py` は exception handler を持たない → プロセス異常終了、syslog に traceback)。

## 4. ファイルシステム失敗

### `cleanup_process` (auto_techsupport_helper.py:170-193)

- `0 < limit < 100` でない場合: ERR ログ "core_usage_limit can only be between 1 and 100" を出して return。**cleanup されず disk full のまま残る** (core 上限保護が無効化される事故パターン)。
- `os.remove(stat[2])` 失敗 (`OSError`): `continue` で握り潰し。次の古いファイルへ進む。失敗統計は記録されない。
- `len(fs_stats) > 1` 条件で最新 1 ファイルは必ず温存。disk full で残 1 ファイルしか無い場合、cleanup が 0 byte 削除で抜ける可能性あり。

### `verify_recent_file_creation`

- `os.path.getmtime` が `FileNotFoundError` / `PermissionError` を投げると `except Exception` で握り潰し `False` 返却 → 即 return。core ファイル消失・読み取り不可ケースで silent skip。

## 5. CONFIG_DB 読み取り失敗

### `state` 欠落 / 非 `enabled`

- `coredump_gen_handler.py:47` で `AUTO_TECHSUPPORT|GLOBAL.state != "enabled"` なら `auto_invoke_ts is disabled` NOTICE ログ出して return。
- `coredump_gen_handler.py:55` で `AUTO_TECHSUPPORT_FEATURE|<feat>.state != "enabled"` なら `auto-techsupport feature for <feat> is not enabled` NOTICE ログ出して return。
- `HGET` が `None` を返した場合も `!= "enabled"` 比較で `True` → skip。空文字も同様。
- `techsupport_cleanup.py:27` でも GLOBAL.state チェック。disabled なら cleanup スキップ (= disk full リスク)。

### `rate_limit_interval` の `try/except ValueError`

- `invoke_ts_command_rate_limited` (auto_techsupport_helper.py:317-331):
  - `float(global_cooloff)` 失敗 → `0.0` 代入 → cooloff 無効
  - `float(container_cooloff)` 失敗 → `0.0` 代入 → cooloff 無効
- 空文字・None・"abc" 等は ValueError で fallback。**ログ出力なし** (silent fallback)。

### `core_usage` / `max_techsupport_limit` の `try/except ValueError`

- `coredump_gen_handler.py:23-26`: `float(core_usage)` 失敗 → `0.0` → 後段の `if not core_usage` で cleanup スキップ + NOTICE。
- `techsupport_cleanup.py:33-36`: 同パターン。`max_ts = 0.0` で cleanup スキップ + NOTICE。

## 6. container 名不一致

- `trim_masic_suffix` (auto_techsupport_helper.py:200-210) が末尾連続数字を削除 (`swss0` → `swss`)。
- 削除後の名前で `FEATURE.format(container)` (= `AUTO_TECHSUPPORT_FEATURE|<name>`) を `HGET`。
- key 不在 → `db.get()` が None → `!= "enabled"` → skip。エラーログも出ない (NOTICE のみ)。

## 7. STATE_DB / rate-limit 未経過

- `verify_rate_limit_intervals` (auto_techsupport_helper.py:285-301):
  - `STATE_DB` の `AUTO_TECHSUPPORT_DUMP_INFO` から container 別 dump timestamp を取得。
  - `time.time() - last_creation < cooloff` なら NOTICE ログ "Per Container rate_limit_interval ... has not passed" を出して `False` 返却 → techsupport skip。
  - 失敗 (skip) でも次回 core dump 発生時に再評価されるため、cooloff 経過後の次回イベントで自動的に invoke される (eventual progress)。retry ループは無い。

## 8. 部分適用・冪等性

- `cleanup_process` は incremental unlink。途中で OSError が出ても他ファイルは削除続行 → 部分削除残存あり。
- `write_to_state_db` (auto_techsupport_helper.py:303-310) は `db.set` を field ごとに呼ぶため、途中で Redis 接続切れが起きると `AUTO_TECHSUPPORT_DUMP_INFO|<name>` が partial fields のまま残る (timestamp あり / container 無し等)。これにより `get_ts_map` の `try/except` (creation_time int 変換失敗) で entry skip → rate-limit が当該 dump を無視。
- `coredump_gen_handler.handle_core_dump_creation_event` と `handle_coredump_cleanup` は独立。後者が早期 return しても前者の cleanup は実行される。

## 9. evidence 行

- `coredump_gen_handler.py:17,47,55` — state 評価早期 return
- `coredump_gen_handler.py:23-31` — core_usage ValueError fallback
- `coredump_gen_handler.py:73-75` — verify_recent_file_creation false で spurious skip
- `techsupport_cleanup.py:27-44` — disabled / max_ts ValueError fallback + cleanup
- `auto_techsupport_helper.py:115-124` — verify_recent_file_creation の except 握り潰し
- `auto_techsupport_helper.py:170-193` — cleanup_process の limit 範囲チェック + OSError continue
- `auto_techsupport_helper.py:232-256` — invoke_ts_cmd の EXT_LOCKFAIL / EXT_RETRY / その他 rc 分岐
- `auto_techsupport_helper.py:285-301` — verify_rate_limit_intervals
- `auto_techsupport_helper.py:317-331` — global/container cooloff の ValueError fallback
