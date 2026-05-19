# LOGGER — Phase G 通信メカニズム調査ノート

## 調査対象

- `sonic-swss-common/common/logger.cpp` 全行
- `sonic-swss-common/common/loglevel.cpp` 全行
- `sonic-swss-common/common/subscriberstatetable.cpp` 全行
- `sonic-swss-common/common/schema.h` (CONFIG_DB dbId 確認)

## 購読方式の特定

### settingThread — `SubscriberStateTable` (keyspace PSUBSCRIBE)

`Logger::settingThread()` (`logger.cpp:192-262`) が CONFIG_DB の `LOGGER` テーブルを `SubscriberStateTable` で購読する:

```cpp
// logger.cpp:195-199
DBConnector db("CONFIG_DB", 0);
auto table = std::make_shared<SubscriberStateTable>(&db, CFG_LOGGER_TABLE_NAME);
selectables.emplace(CFG_LOGGER_TABLE_NAME, table);
select.addSelectable(table.get());
```

`SubscriberStateTable` は `subscriberstatetable.cpp:20-24` で:
```cpp
m_keyspace = "__keyspace@";
m_keyspace += to_string(db->getDbId()) + "__:" + tableName + m_table.getTableNameSeparator() + "*";
psubscribe(m_db, m_keyspace);
```
CONFIG_DB の dbId は `schema.h:16` で `4` と定義されているため、実際の PSUBSCRIBE パターンは:
```
__keyspace@4__:LOGGER|*
```

### 書き込み側 — `swss::Table::hset()` (直接書き込み)

`loglevel.cpp:42-44` の `setLoglevel()`:
```cpp
void setLoglevel(swss::Table& logger_tbl, const std::string& component, const std::string& loglevel) {
    logger_tbl.hset(component, "LOGLEVEL", loglevel);
}
```
`swss::Table::hset()` は Redis の `HSET` を直接発行する。CONFIG_DB の keyspace 通知設定 (`notify-keyspace-events`) が有効な場合、`HSET LOGGER|<component> LOGLEVEL <value>` により `__keyspace@4__:LOGGER|<component>` チャネルへ `hset` イベントが PUBLISH される。

同様に `linkToDbWithOutput()` (`logger.cpp:127`) も `swss::Table` を使い `table.set()` でデフォルト値を書き込む。

## タイムアウト・ループ構造

`settingThread` は `select.select(&selectable, 1000)` でタイムアウト 1000 ms のブロッキング select を実行する (`logger.cpp:208`)。

- `Select::TIMEOUT`: `SWSS_LOG_DEBUG` → `continue`（ポーリング継続）
- `Select::ERROR`: `SWSS_LOG_NOTICE` → `continue`（エラー後も継続）
- `m_stopEvent`: `break`（スレッド終了）
- keyspace 通知受信: `subscriberStateTable->pop(koValues)` → フィールド処理

## 起動時スナップショット

`SubscriberStateTable` 自体は起動時に既存エントリをバッファに流し込む機能を持たない。デーモン起動時の既存 LOGLEVEL は `linkToDbWithOutput()` の `table.hget()` (`logger.cpp:132-139`) で直接読み取る。スナップショットは `settingThread` ではなく初期化パスが担当する。

## 購読者一覧

| デーモン | 購読方法 | `m_settingChangeObservers` への登録 |
|---------|---------|-----------------------------------|
| `orchagent`、`syncd`、その他 swss 系全デーモン | 自プロセス内 `settingThread` が `SubscriberStateTable` で `LOGGER|<自デーモン名>` を購読 | `Logger::linkToDb()` 呼び出し時に自デーモン名で登録 |

外部の購読者（`orchagent` とは別プロセスが `LOGGER` テーブルを `SubscriberStateTable` で購読する実装）はソース内に存在しない。各デーモンが自プロセス内でのみ購読する設計。

## Redis primitive まとめ

| フェーズ | API | Redis コマンド |
|---------|-----|---------------|
| 書き込み (swssloglevel) | `swss::Table::hset()` | `HSET LOGGER\|<component> LOGLEVEL <value>` |
| 書き込み (初期自己書込) | `swss::Table::set()` | `HSET LOGGER\|<component> LOGLEVEL <value> LOGOUTPUT <value>` |
| 起動時読み取り | `swss::Table::hget()` | `HGET LOGGER\|<component> LOGLEVEL` / `LOGOUTPUT` |
| 変更受信 | `SubscriberStateTable::pop()` | PSUBSCRIBE `__keyspace@4__:LOGGER\|*` |
