# LOGGER — Phase F 副次 DB 書込スキャンノート

対象テーブル: `LOGGER`
Consumer: 各デーモン (`orchagent`・`syncd` 等) の `Logger::linkToDbWithOutput()` / `settingThread()`、`swssloglevel` コマンド
スキャン範囲: `sonic-swss-common/common/logger.cpp` 全行、`sonic-swss-common/common/loglevel.cpp` 全行

---

## 結論: 他 DB への副次書込なし（CONFIG_DB への自己書込あり）

`logger.cpp` の処理は `CONFIG_DB` の `LOGGER` テーブルのみを読み書きし、APPL_DB / STATE_DB / COUNTERS_DB / ASIC_DB への書き込みは一切発生しない。

唯一の副次書込は、デーモン起動時に `LOGGER` エントリが未作成だった場合にデフォルト値を **CONFIG_DB の同一テーブル自身** に書き戻す自己書込（`logger.cpp:149`）である。

## DB 別スキャン結果

| DB | 書込有無 | 根拠 |
|---|---|---|
| CONFIG_DB (LOGGER テーブル自身) | **あり（自己書込）** | `linkToDbWithOutput()` が `table.hget()` で既存値がない場合のみ `table.set(dbName, {LOGLEVEL, LOGOUTPUT})` を実行（`logger.cpp:132-149`） |
| APPL_DB | なし | `logger.cpp` / `loglevel.cpp` に `ProducerStateTable` の利用なし |
| STATE_DB | なし | `logger.cpp` / `loglevel.cpp` に `StateTable` 参照なし |
| COUNTERS_DB | なし | LOGGER テーブルは統計カウンタを持たない |
| ASIC_DB | なし | SAI 非経由。ログ verbosity 変更は ASIC プログラミングと無関係 |
| FLEX_COUNTER_DB | なし | FlexCounter 機能と無関係 |
| LOGLEVEL_DB | なし | LOGLEVEL_DB は旧名称。現行は CONFIG_DB の LOGGER テーブルに統合済み（`sonic-swss-common` v3 以降） |

## 副作用の範囲（DB 外）

DB 外副作用は以下に限定:

1. **デーモン内部の loglevel 変更**: `settingThread` が `prioNotify` / `outputNotify` コールバックを呼び出し、各デーモンのインメモリ変数（`Logger::m_minPrio` / `Logger::m_output`）を書き換える。出力先をファイルディスクリプタ経由で変更する場合、syslog / stdout / stderr ソケットへの書き込み先が即時切り替わる（`logger.cpp:250-258`）。
2. **SAI loglevel API 呼び出し**: `SAI_API_*` コンポーネントに対する LOGLEVEL 変更は `sai_log_set()` 呼び出しにより SAI ライブラリ内部の loglevel を変更する（`syncd` 側の `swssPrioNotify` 実装経由）。ASIC のハードウェアには影響しない。
3. **SIGHUP シグナル送信**: `config syslog level` CLI は LOGLEVEL を書き込んだ後、`require_manual_refresh=true` のデーモンに `supervisorctl signal HUP` または `kill -SIGHUP` を送信する（`sonic-utilities/config/syslog.py:684-696`）。`logger.cpp` 自体が送信するわけではなく、CLI ツール側の動作。
