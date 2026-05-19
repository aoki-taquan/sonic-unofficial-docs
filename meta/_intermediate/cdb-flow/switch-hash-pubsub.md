# SWITCH_HASH — 通信メカニズム調査 (Phase G)

## 調査対象

- `sonic-swss/orchagent/orchdaemon.cpp` L199, L204-213
- `sonic-swss/orchagent/switchorch.cpp` L148-149, L1493-1510
- `sonic-swss-common/common/orch.cpp` L1186-1196

## 購読登録経路

`orchdaemon.cpp:199` で `TableConnector conf_switch_hash(m_configDb, CFG_SWITCH_HASH_TABLE_NAME)` を構築し、`switch_tables` ベクタの先頭要素として追加 (`orchdaemon.cpp:204-212`)。`SwitchOrch::SwitchOrch(DBConnector *db, vector<TableConnector>& connectors, ...)` の基底 `Orch(connectors)` (`switchorch.cpp:148-149`) が `Orch::addConsumer()` (`orch.cpp:1186-1196`) を呼ぶ。`m_configDb` は CONFIG_DB (`dbId=4`) であるため `SubscriberStateTable` ブランチが選択される。

## チャンネル一覧

| 区間 | DB | テーブル名 | 購読クラス | 発行元 |
|---|---|---|---|---|
| CLI/ConfigDB → SwitchOrch | CONFIG_DB (dbId=4) | `SWITCH_HASH` (`CFG_SWITCH_HASH_TABLE_NAME`) | `SubscriberStateTable` | `config switch-hash global ecmp/lag ...` (`sonic-utilities/config/plugins/sonic-hash.py`) |
| SwitchOrch → syncd | ASIC_DB 経由 | (SAI 直接呼び出し) | SAI API | `sai_hash_api->set_hash_attribute()` / `sai_switch_api->set_switch_attribute()` |

## SubscriberStateTable の動作

Redis keyspace 通知 `PSUBSCRIBE __keyspace@4__:SWITCH_HASH|*` を購読。CONFIG_DB への `HSET "SWITCH_HASH|GLOBAL" ...` が PUBLISH されると `SwitchOrch::doTask(Consumer&)` が `doCfgSwitchHashTableTask()` を呼ぶ (`switchorch.cpp:1507`)。

起動時スナップショット: `SubscriberStateTable` ctor は PSUBSCRIBE 直後に既存エントリを `SET_COMMAND` として buffer に充填する (`subscriberstatetable.cpp:26-44`)。orchagent 再起動時に存在する `SWITCH_HASH|GLOBAL` エントリは遅延なく再配信される。

## ProducerStateTable は不使用

CONFIG_DB 経路では `ProducerStateTable` を使用しない。CLI (`sonic-hash.py`) は `ConfigDBConnector.mod_entry()` → 直接 Redis `HSET` で書き込む。APPL_DB への中継もなし。
