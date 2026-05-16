# CONFIG_DB 失敗挙動分析: AUTO_TECHSUPPORT (coredump_gen_handler 経由)

## 対象ハンドラ

- `sonic-utilities/scripts/coredump_gen_handler.py`
- `sonic-utilities/utilities_common/auto_techsupport_helper.py`

## 抽出した失敗挙動

### 1. core ファイル生成タイムアウト（Spurious Invocation）

- ソース: `coredump_gen_handler.py:73-75`
- `verify_recent_file_creation(file_path)` が `/var/core/<name>` の mtime を確認し、現在時刻との差が `TIME_BUF=20` 秒以上であれば古いファイルと判断。
- syslog INFO: `"Spurious Invocation. {} is not created within last {} sec"` を記録して即返却。
- techsupport 起動・cleanup いずれも実行されない。

### 2. GLOBAL state が disabled（AUTO_TECHSUPPORT 連携失敗）

- ソース: `coredump_gen_handler.py:17-19` (`handle_coredump_cleanup`)
- `coredump_gen_handler.py:47-49` (`handle_core_dump_creation_event`)
- CONFIG_DB `AUTO_TECHSUPPORT|GLOBAL` の `state` フィールドを `SonicV2Connector.get()` で取得し `!= "enabled"` を検査。
- cleanup 側: syslog NOTICE `"coredump_cleanup is disabled. No cleanup is performed."` を出力して return。
- techsupport 起動側: syslog NOTICE `"auto_invoke_ts is disabled. No cleanup is performed: core {}"` を出力して return。
- 注意: エラーではなく NOTICE レベルのログのみで無音スキップ。

### 3. feature state が disabled（AUTO_TECHSUPPORT_FEATURE 連携失敗）

- ソース: `coredump_gen_handler.py:54-57`
- `FEATURE_KEY = "AUTO_TECHSUPPORT_FEATURE|{container}"` の `state` が `"enabled"` でない場合。
- syslog NOTICE: `"auto-techsupport feature for {} is not enabled. Techsupport Invocation is skipped. core: {}"` を出力して return。
- masic suffix は `trim_masic_suffix()` で除去済み（`swss0` → `swss`）。

### 4. max_core_limit が不正値（float 変換不可または 0）

- ソース: `coredump_gen_handler.py:22-31`
- `db.get(CFG_DB, AUTO_TS, CFG_CORE_USAGE)` を `float()` 変換。`ValueError` の場合は `core_usage = 0.0` にフォールバック。
- `if not core_usage` 節で `0.0` の場合も cleanup スキップ（syslog NOTICE: `"core-usage argument is not set. No cleanup is performed"`）。
- 有効範囲は `cleanup_process()` 内で `0 < limit < 100` を検査（範囲外は syslog ERR + return）。

### 5. show techsupport 起動失敗

- ソース: `auto_techsupport_helper.py:232-254` (`invoke_ts_cmd`)
- `EXT_LOCKFAIL` (rc=2): 別インスタンスが実行中。syslog NOTICE: `"Another instance of techsupport running, aborting this."` → STATE_DB への書き込みなし。
- `EXT_RETRY` (rc=4) + 再試行上限超過 (`MAX_RETRY_LIMIT=2`): syslog ERR: `"MAX_RETRY_LIMIT for show techsupport invocation exceeded"` → STATE_DB への書き込みなし。
- rc=0 だが dump 名が stdout から取得できない: syslog ERR: `"no techsupport dump is found"` → STATE_DB への書き込みなし。

## 適用先

- `docs/reference/config-db/auto-techsupport.md` の `<!-- cdb-exceptions -->` ブロック内 `<!-- failure -->` サブセクションに追記済み。
- `docs/reference/config-db/coredump.md` は存在しない（CONFIG_DB に COREDUMP テーブルなし）。近 slug として `auto-techsupport.md` に適用。
