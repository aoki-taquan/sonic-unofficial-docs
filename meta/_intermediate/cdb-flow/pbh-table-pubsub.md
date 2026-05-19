# PBH_TABLE pubsub 調査ノート (Phase G)

## 調査対象

- `sonic-swss/orchagent/orchdaemon.cpp:550-565`
- `sonic-swss/orchagent/pbhorch.cpp:88-97,1804-1831`
- `sonic-swss/orchagent/orch.cpp:1186-1195`
- `sonic-swss/orchagent/orch.h:277,290`

## 結論

`PBH_TABLE` / `PBH_RULE` / `PBH_HASH` / `PBH_HASH_FIELD` は CONFIG_DB を `SubscriberStateTable` で購読する。

## Consumer 登録

`orchdaemon.cpp:553-565`:
```cpp
TableConnector cfgDbPbhTable(m_configDb, "PBH_TABLE");
TableConnector cfgDbPbhRuleTable(m_configDb, "PBH_RULE");
TableConnector cfgDbPbhHashTable(m_configDb, "PBH_HASH");
TableConnector cfgDbPbhHashFieldTable(m_configDb, "PBH_HASH_FIELD");
gPbhOrch = new PbhOrch(pbhTableConnectorList, gAclOrch, gPortsOrch);
```

`Orch(vector<TableConnector>)` → `addConsumer(db, tableName)` →
CONFIG_DB の場合 `SubscriberStateTable` を選択 (`orch.cpp:1189`)。

## doTask ディスパッチ

`PbhOrch::doTask()` (`pbhorch.cpp:1804`):
1. `allPortsReady()` チェック — false なら return (保留)
2. テーブル名で handler を選択

## allPortsReady ゲート

`pbhorch.cpp:1808-1811` で `!portsOrch->allPortsReady()` → `return` でポート初期化待ち。
他の PBH テーブルも同じ select ループ内で allPortsReady 待ちを経由する。

## APPL_DB / STATE_DB への書き込みなし

PbhOrch は SAI 直接呼び出しのみ。APPL_DB / STATE_DB への書き込みなし。
