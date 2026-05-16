# Phase A: LOGGER テーブル — フィールドのコード由来デフォルト調査

対象ページ: `docs/reference/config-db/log-config.md`
調査日: 2026-05-14

## 調査対象フィールド

| フィールド | YANG 定義 | コード由来デフォルト | 根拠 |
|-----------|-----------|-------------------|------|
| `LOGLEVEL` | `mandatory true` / union(swss_loglevel, sai_loglevel) | swss コンポーネント: `"NOTICE"` / SAI コンポーネント: `"SAI_LOG_LEVEL_NOTICE"` | `loglevel.h`: `#define DEFAULT_LOGLEVEL "NOTICE"` / `#define SAI_DEFAULT_LOGLEVEL "SAI_LOG_LEVEL_NOTICE"`. `logger.cpp:linkToDb()` は `defPrio` として各コンポーネントが渡した値を使い、DB 未登録時に書き込む |
| `LOGOUTPUT` | `default SYSLOG` | `"SYSLOG"` | YANG `default SYSLOG`. `logger.cpp:linkToDb()` は `defOutput="SYSLOG"` を固定引数で `linkToDbWithOutput()` に渡す。`logger.h`: `m_output = { SWSS_SYSLOG }` で内部初期値も SYSLOG |
| `require_manual_refresh` | `stypes:boolean_type` / デフォルトなし | なし（フィールド自体が省略可能。未設定時は false 相当として動作） | YANG に default 節なし。コード側で読み取り処理を確認できず（settingThread は LOGLEVEL/LOGOUTPUT のみ読む） |

## コード根拠詳細

### LOGLEVEL デフォルト

- `sonic-swss-common/common/loglevel.h:4`: `#define DEFAULT_LOGLEVEL "NOTICE"`
- `sonic-swss-common/common/loglevel.h:5`: `#define SAI_DEFAULT_LOGLEVEL "SAI_LOG_LEVEL_NOTICE"`
- `sonic-swss-common/common/logger.cpp:94`: `linkToDbNative(const std::string& dbName, const char * defPrio="NOTICE")` — デフォルト引数が `"NOTICE"`
- `sonic-swss-common/common/logger.cpp:132-136`: DB に `LOGLEVEL` キーがなければ `defPrio` を使い書き込む

### LOGOUTPUT デフォルト

- `sonic-swss-common/common/logger.cpp:161`: `linkToDb(...)` → `linkToDbWithOutput(dbName, prioNotify, defPrio, swssOutputNotify, "SYSLOG")` — 固定で `"SYSLOG"`
- YANG `sonic-logger.yang:69`: `default SYSLOG;`
- `sonic-swss-common/common/logger.h:162`: `std::atomic<Output> m_output = { SWSS_SYSLOG };` — 内部初期値も SYSLOG

### require_manual_refresh

- YANG に default 節なし。コード(`settingThread`)は LOGLEVEL と LOGOUTPUT のみ参照し、`require_manual_refresh` を直接読むコードは sonic-swss-common 内に見当たらない。
- 実質的にオプションフィールドで、未設定 = false 相当（SIGHUP 不要）。

## invalid 値時のフォールバック

- `LOGLEVEL` に未知の文字列が入った場合: `swssPrioNotify()` が `"NOTICE"` にフォールバック（`logger.cpp:83-84`）
- `LOGOUTPUT` に未知の文字列が入った場合: `swssOutputNotify()` が `SYSLOG` にフォールバック（`logger.cpp:105-106`）

## 出典

- `sonic-swss-common` @ `158de8d3463ff4b841653f6d57190bb142b80d9c`
  - `common/logger.h`
  - `common/logger.cpp`
  - `common/loglevel.h`
  - `common/loglevel.cpp`
- `sonic-buildimage` @ `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd`
  - `src/sonic-yang-models/yang-models/sonic-logger.yang`
