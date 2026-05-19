# redis-db-config — Phase F side-effects 調査メモ

## 調査対象

- `sonic-net/sonic-swss-common` `common/dbconnector.cpp` (SHA: 158de8d3463ff4b841653f6d57190bb142b80d9c)
- `sonic-net/sonic-swss-common` `common/dbconnector.h`

## 結論

`database_config.json` は CONFIG_DB テーブルではなくインフラ層ファイル。
`SonicDBConfig::parseDatabaseConfig()` / `initialize()` / `initializeGlobalConfig()` は
すべて読み込み専用処理であり、いかなる Redis DB への書込も発生しない。

副次効果はプロセス内インメモリキャッシュ (`m_inst_info`, `m_db_info`, `m_db_separator`) の
更新のみ。

## grep 結果

```
# dbconnector.cpp 内の書込系呼出検索
grep -n "hset\|HSET\|set(\|SET \|publish\|PUBLISH\|Producer\|Table(" dbconnector.cpp
# ヒット: L789 (DEL), L810 (HDEL), L851 (FLUSHDB), L1021 (publish) —
#         すべて DBConnector の汎用メソッドであり SonicDBConfig の初期化コードとは無関係
```

## reset() 副次効果

`SonicDBConfig::reset()` (L209-218) は以下をクリア:
- `m_init = false`
- `m_global_init = false`
- `m_inst_info.clear()`
- `m_db_info.clear()`
- `m_db_separator.clear()`

既存 `DBConnector` インスタンスの TCP/UNIX 接続は切断されないが、
リセット後の `getDbInfo()` 系 API は再初期化または abort を引き起こす。
