# log-config side-effects scan

## 対象

`docs/reference/config-db/log-config.md` — `LOGGER` テーブル (Phase F)

## 調査方針

`sonic-swss-common/common/logger.cpp`、`loglevel.cpp`、`sonic-sairedis/syncd/Syncd.cpp`
の全行精読と `grep -rn "LOGLEVEL_DB"` による横断スキャン。

## 結果

### Redis DB への副次書込

| DB | 書込 | 備考 |
|----|------|------|
| CONFIG_DB `LOGGER` | ○（自テーブル限定） | `linkToDbWithOutput()` が起動時にエントリが欠損していれば `table.set(dbName, fieldValues)` でデフォルト値を書き戻す（`logger.cpp:143-149`）。自テーブル内の書き戻しであり「他テーブルへの副次書込」には該当しない |
| STATE_DB | なし | — |
| APPL_DB | なし | — |
| COUNTERS_DB | なし | — |
| FLEX_COUNTER_DB | なし | — |
| ASIC_DB | なし | — |
| LOGLEVEL_DB (DB#3) | なし（通常運用時） | `db_migrator.py` がスキーマ移行時に読み取り専用アクセスする（`db_migrator.py:1210-1226`）が、LOGGER テーブルへの SET 操作をトリガーとする副次書込ではない |

### SAI API 副次呼び出し（DB 外）

`syncd` は起動時に全 `SAI_API_*` コンポーネントを `linkToDb()` で LOGGER テーブルに登録し、
`saiLoglevelNotify` コールバックを設定する（`Syncd.cpp:5583-5587`）。

LOGGER テーブルで `SAI_API_*` エントリの `LOGLEVEL` が変更されると:
1. `settingThread` が変更を検知
2. `saiLoglevelNotify(api, level)` が呼ばれる
3. `m_vendorSai->logSet(api, logLevel)` = `sai_log_set()` が実行される（`Syncd.cpp:5551`）

これは SAI アダプタ内部の verbosity 変更であり Redis への書込は発生しない。

### 結論

`LOGGER` テーブルへの SET/DEL 操作は **他の Redis DB への副次書込を一切発生させない**。

副次作用は:
- 起動時のデーモン自己登録による CONFIG_DB `LOGGER` への書き戻し（自テーブル）
- `SAI_API_*` コンポーネント向け: syncd 経由の `sai_log_set()` 呼び出し（DB 外）

## grep 証跡

```
grep -rn "LOGLEVEL_DB" .cache/sonic-sources/ --include="*.cpp" --include="*.h" --include="*.py"
→ schema.h:15, table.cpp:27, db_migrator.py:94,1210-1226, hostapdmgr_main.cpp:30
  （いずれも LOGGER テーブルへの SET トリガーによる副次書込でない）

grep -n "DBConnector\|Table\|hset\|set(" .cache/sonic-sources/sonic-swss-common/common/logger.cpp
→ CONFIG_DB への table.set() のみ（自テーブル書き戻し, L149）

grep -n "SAI_API_\|saiLoglevelNotify\|sai_log_set\|linkToDb" .cache/sonic-sources/sonic-sairedis/syncd/Syncd.cpp
→ L5583-5587 (linkToDb SAI_API_*), L5551 (m_vendorSai->logSet)
```
