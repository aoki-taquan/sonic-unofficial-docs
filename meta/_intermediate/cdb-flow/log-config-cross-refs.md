# LOGGER — Phase C 暗黙参照調査メモ

調査対象:
- `sonic-net/sonic-swss-common` `common/logger.cpp`
- `sonic-net/sonic-buildimage` `src/sonic-yang-models/yang-models/sonic-logger.yang`
- `sonic-net/sonic-utilities` `config/syslog.py`
- `sonic-net/sonic-utilities` `scripts/db_migrator.py`

## LOGGER テーブル自体の外部依存

`logger.cpp:linkToDbWithOutput()` は CONFIG_DB の `LOGGER` テーブルのみを読み書きする。
他の CONFIG_DB テーブル（`DEVICE_METADATA`・`FEATURE`・`PORT` 等）へのアクセスは一切ない。

YANG `sonic-logger.yang` にも `leafref` は存在しない。

結論: **LOGGER テーブルは他テーブルを参照しない（上流依存なし）**。

## LOGGER テーブルを参照する側（下流）

### 1. `config syslog level` CLI (`config/syslog.py:684-696`)

`cfg_db.mod_entry('LOGGER', identifier, {'LOGLEVEL': level})` で LOGLEVEL を書き込んだ後、
`cfg_db.get_entry('LOGGER', identifier)` で同エントリを再読し、
`require_manual_refresh` フィールドが `true` の場合に SIGHUP を送信する。

CLI は LOGGER テーブルのみを参照しており、他テーブルとの結合処理はない。

### 2. `db_migrator.py` (`scripts/db_migrator.py:1207`)

DB マイグレーション時に `LOGGER` テーブルを走査し、スキーマ互換性確認を行う。
他テーブルとの JOIN は行わない。

### 3. 各デーモン（`orchagent`、`syncd` 等）

`Logger::linkToDbNative()` 経由で `LOGGER` エントリを自己登録し、
`settingThread` で購読する。
自己登録は起動時に 1 回のみ実行され、他テーブルへのアクセスはない。

## YANG leafref 検査

`sonic-logger.yang` の `LOGGER_LIST` は list-key `name` のみ持ち、
他モジュールへの `leafref` / `augment` は存在しない。

## 結論サマリ

| 方向 | テーブル | 根拠 |
|------|---------|------|
| LOGGER → 他テーブル | なし | logger.cpp は LOGGER テーブルのみ操作 |
| 他テーブル → LOGGER | （DB データとして依存なし） | — |
| CLI が LOGGER を読み取る | `config syslog level` | syslog.py:684-696 |
| マイグレーション対象 | `db_migrator.py` | db_migrator.py:1207 |
