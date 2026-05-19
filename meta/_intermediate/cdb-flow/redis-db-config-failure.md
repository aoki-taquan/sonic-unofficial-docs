# redis-db-config — Phase D 失敗挙動 調査メモ

## 対象ソース
- `sonic-net/sonic-swss-common` `common/dbconnector.cpp` ref: 158de8d3463ff4b841653f6d57190bb142b80d9c
- `sonic-net/sonic-swss-common` `common/dbconnector.h` ref: 158de8d3463ff4b841653f6d57190bb142b80d9c

## 失敗パターン整理

### A. parseDatabaseConfig() のファイル読み込み失敗

`ifstream i(file)` が `i.good() == false` のとき（ファイル不在・権限エラー等）:
- `SWSS_LOG_ERROR("Sonic database config file doesn't exist at %s\n", ...)` 出力
- `throw runtime_error("Sonic database config file doesn't exist at " + file)` で上位に伝播
- L83-85 の実装

`ignore_nonexistent=true` かつ `access(file, F_OK) == -1` の場合:
- `SWSS_LOG_NOTICE` を出力して `return`（例外なし、エントリ空で続行）
- L33-36 の実装

### B. parseDatabaseConfig() の JSON 解析失敗

JSON に必須キーが存在しない（`domain_error`）:
- `SWSS_LOG_ERROR` + `throw runtime_error("key doesn't exist ...")` で上位に伝播
- L71-74 の実装

その他 JSON パース例外:
- `SWSS_LOG_ERROR` + `throw runtime_error("Sonic database config file syntax error ...")` で上位に伝播
- L76-79 の実装

### C. initialize() の二重初期化

`m_init == true` のとき `initialize()` を呼ぶと:
- `SWSS_LOG_ERROR("SonicDBConfig already initialized")` 出力
- `throw runtime_error("SonicDBConfig already initialized")` で上位に伝播
- L193-194 の実装
- 呼び出し元は例外をキャッチしなければプロセス abort → systemd 再起動

### D. initializeGlobalConfig() の動作

グローバル設定ファイルが存在しない場合:
- `SWSS_LOG_ERROR("Sonic database config global file doesn't exist ...")` 出力
- **例外なし** — `m_global_init = true` をセットして続行（L174-179）
- `ignore_nonexistent=true` の場合は `SWSS_LOG_NOTICE` で `return`（各 include ファイルごとに適用）

二重初期化は `m_global_init` チェックで早期リターン（例外なし）（L96-99）

### E. getDbInfo() / getRedisInfo() の namespace・DB 名解決失敗

namespace 非空かつ `m_global_init == false`:
- `SWSS_LOG_THROW("Initialize global DB config using API SonicDBConfig::initializeGlobalConfig")` でプロセス abort
- L229-231, L257-260 の実装

キーまたは DB 名が設定ファイルに存在しない:
- `SWSS_LOG_ERROR` + `throw out_of_range(msg)` で上位に伝播
- L263-275 の実装

無効な namespace 名:
- `SWSS_LOG_THROW("Namespace %s is not a valid namespace ...")` でプロセス abort
- L242 の実装

## 自己回復の仕組み

- `getDbInfo()` / `getDbId()` 等の API は `m_init == false` のとき自動的に `initialize(DEFAULT_SONIC_DB_CONFIG_FILE)` を呼ぶ（L252-253）
- これにより、明示的な `initialize()` 呼び出しなしにデフォルトパスからの自動読み込みが行われる
- Redis 接続層（`DBConnector` クラス）の失敗は `system_error` として伝播し、各アプリが個別に処理

## 結論

`parseDatabaseConfig()` や `initialize()` の失敗は例外として上位に伝播し、
呼び出し元（各デーモン）がキャッチしなければプロセス abort → systemd 再起動という
自己回復経路を取る。namespace 解決失敗は `SWSS_LOG_THROW` で即 abort（プログラミングエラー）。
