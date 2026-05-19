# log-config failure-behavior (Phase D)

## 調査対象
- `sonic-swss-common/common/logger.cpp` (ref: 158de8d3463ff4b841653f6d57190bb142b80d9c)
- `sonic-swss-common/common/loglevel.h`

## 無効値への対処

### LOGLEVEL 無効値
- `swssPrioNotify()` (logger.cpp:77-91): `priorityStringMap` に存在しない文字列が渡された場合
  - `SWSS_LOG_ERROR("Invalid loglevel. Setting to NOTICE. %s", prioStr.c_str())` でエラーログ出力
  - `m_minPrio = SWSS_NOTICE` にフォールバック（デーモンは停止しない）
  - evidence: `logger.cpp:81-84`

### LOGOUTPUT 無効値
- `swssOutputNotify()` (logger.cpp:99-112): `outputStringMap` に存在しない文字列が渡された場合
  - `SWSS_LOG_ERROR("Invalid logoutput. Setting to SYSLOG. %s", outputStr.c_str())` でエラーログ出力
  - `m_output = SWSS_SYSLOG` にフォールバック（デーモンは停止しない）
  - evidence: `logger.cpp:103-106`

## settingThread エラー処理

### select() エラー (Select::ERROR)
- `settingThread()` (logger.cpp:210-214): `select()` が `Select::ERROR` を返した場合
  - `SWSS_LOG_NOTICE()` でエラーログを出力し `continue` — スレッドは終了しない
  - evidence: `logger.cpp:210-214`

### dynamic_cast 失敗
- `settingThread()` (logger.cpp:229-234): `dynamic_cast<SubscriberStateTable *>` が NULL を返した場合
  - `SWSS_LOG_ERROR("dynamic_cast returned NULL")` → `break` でスレッド終了
  - これは内部不整合を意味し、再起動は `restartSettingThread()` / デーモン再起動が必要
  - evidence: `logger.cpp:229-234`

## DB 接続失敗

- `linkToDbWithOutput()` は CONFIG_DB へ接続して `table.hget()` / `table.set()` を実行する
- DB 接続失敗時は `DBConnector` コンストラクタが例外をスローし、デーモン起動自体が失敗する可能性がある
- `settingThread()` 内で CONFIG_DB に再接続するロジックはなく、起動後の DB 切断は `select()` が `Select::ERROR` を繰り返すことで検知できるが、スレッドは継続する（自動リカバリなし）

## まとめ

| シナリオ | 挙動 | デーモン停止? |
|---|---|---|
| LOGLEVEL 無効値 | NOTICE にフォールバック + エラーログ | 停止しない |
| LOGOUTPUT 無効値 | SYSLOG にフォールバック + エラーログ | 停止しない |
| select() エラー | エラーログ + continue（スレッド継続） | 停止しない |
| dynamic_cast NULL | エラーログ + break（settingThread 終了） | settingThread 終了 |
| 未登録コンポーネント名 | silently ignored | 停止しない |
| DEL コマンド | silently ignored | 停止しない |
