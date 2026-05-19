# log-config (LOGGER) — Phase F side-effects スキャン記録

## 調査対象

- `sonic-net/sonic-swss-common` (master)
  - `common/logger.cpp`
  - `common/logger.h`

## スキャン手順

### 1. DB 書き込み呼び出しの grep

```bash
grep -rn "HSet\|hset\|ProduceKeyVal\|Publish\|STATE_DB\|APPL_DB\|ProducerStateTable" \
  sonic-swss-common/common/logger.cpp | grep -v "_test\|^//"
```

ヒット箇所:
- `logger.cpp:126`: `DBConnector db("CONFIG_DB", 0)` — linkToDbWithOutput 内
- `logger.cpp:149`: `table.set(dbName, fieldValues)` — CONFIG_DB LOGGER テーブルへの自己登録

### 2. APPL_DB / STATE_DB / COUNTERS_DB への書き込みチェック

ヒットなし。`logger.cpp` が接続する DB は CONFIG_DB のみ。

### 3. settingThread の動作確認

`settingThread()` (`logger.cpp:192-`) は `SubscriberStateTable` で CONFIG_DB の `LOGGER` テーブルを購読し、変化を受け取ってデーモン内部の loglevel を更新する。外部 DB への書き込みなし。

## 結論

副次書き込みは CONFIG_DB `LOGGER|<component>` への自己登録（エントリ未存在時のみ）のみ。
APPL_DB / STATE_DB / COUNTERS_DB への書き込みは存在しない。
