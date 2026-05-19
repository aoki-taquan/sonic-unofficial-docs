# PBH_RULE テーブル — Phase G 通信メカニズム スキャンノート

対象テーブル: `CONFIG_DB PBH_RULE`
Producer: CLI (`config pbh rule`) / `sonic-cfggen` / gNMI Translib
Consumer: `PbhOrch` (`sonic-swss/orchagent/pbhorch.cpp`) → `AclOrch::addAclRule()` → SAI ACL entry

スキャン範囲:
- `sonic-swss/orchagent/pbhorch.cpp:88-96` (constructor, Orch 基底コンストラクタ呼び出し)
- `sonic-swss/orchagent/orchdaemon.cpp:552-565` (TableConnector 設定・PbhOrch インスタンス生成)
- `sonic-swss-common/common/orch.cpp:1186-1196` (addConsumer — SubscriberStateTable vs ConsumerStateTable 分岐)
- `sonic-utilities/show/plugins/pbh.py:191-206` (show pbh rule — CONFIG_DB 直読み)
- `sonic-utilities/show/plugins/pbh.py:365-391` (show pbh statistics — COUNTERS_DB 読み)
- `sonic-utilities/show/plugins/pbh.py:450-453` (read_acl_rule_counter_map — COUNTERS_DB ACL_COUNTER_RULE_MAP)

---

## 購読方式

`PbhOrch` は `Orch(connectorList)` でベースクラス `Orch` に 4 テーブル
(`CFG_PBH_TABLE_TABLE_NAME`, `CFG_PBH_RULE_TABLE_NAME`, `CFG_PBH_HASH_TABLE_NAME`, `CFG_PBH_HASH_FIELD_TABLE_NAME`)
の `TableConnector` リストを渡す（`pbhorch.cpp:88-92`, `orchdaemon.cpp:552-565`）。

`Orch::addConsumer()` は db ID で分岐する:
```cpp
// orch.cpp:1186-1196
void Orch::addConsumer(DBConnector *db, string tableName, int pri)
{
    if (db->getDbId() == CONFIG_DB || db->getDbId() == STATE_DB || db->getDbId() == CHASSIS_APP_DB)
        addExecutor(new Consumer(new SubscriberStateTable(db, tableName, ...), ...));
    else
        addExecutor(new Consumer(new ConsumerStateTable(db, tableName, gBatchSize, ...), ...));
}
```

CONFIG_DB は `SubscriberStateTable`（Redis keyspace 通知）を使用する。APPL_DB 等で使われる `ConsumerStateTable`（channel PUBLISH/SUBSCRIBE）とは異なる。

---

## 書き込み側（Producer）

`PBH_RULE` への書き込みは以下の経路から行われる:

1. **CLI**: `config pbh rule add/del/update` (`sonic-utilities/config/plugins/pbh.py`)
   - `db.cfgdb.set_entry("PBH_RULE", ...)` または `db.cfgdb.delete_entry("PBH_RULE", ...)` を呼ぶ
   - 内部では `swss::Table::set()` → Redis `HSET "PBH_RULE|<table>|<rule>" <fields>`
2. **sonic-cfggen**: JSON 設定ファイルの一括投入
3. **gNMI Translib**: REST / gNMI 経由での書き込み（`sonic-mgmt-common` がバックエンド）

いずれも明示的な `PUBLISH` は発行しない。CONFIG_DB の keyspace 通知（`__keyspace@4__:PBH_RULE|*` への `PSUBSCRIBE`）により `PbhOrch` がイベントを受信する。

---

## 読み取り側（Consumer）

### orchagent / PbhOrch（主 Consumer）

`PbhOrch::doTask(Consumer&)` (`pbhorch.cpp:1804-1837`) が `CFG_PBH_RULE_TABLE_NAME` のイベントを受信し `doPbhRuleTask()` を呼ぶ。`SubscriberStateTable::pops()` がバッチで取得する。バッチサイズは `DEFAULT_POP_BATCH_SIZE = 128`（`table.h:164`）でハードコードされ、`Orch::addConsumer()` がこの定数を渡す (`orch.cpp:1190`)。

### show pbh rule CLI（直読み）

`sonic-utilities/show/plugins/pbh.py:206`:
```python
table = db.cfgdb_pipe.get_table(pbh_rule_tbl_name)  # CONFIG_DB 直読み
```

`swsssdk` の `get_table()` が `HGETALL PBH_RULE|*` を一括取得する。orchagent の処理を経由せず CONFIG_DB を直接参照するため、SAI 反映状態と無関係に最新の Config を表示する。

### show pbh statistics CLI（COUNTERS_DB 読み）

`show pbh statistics` は以下を参照する:
1. CONFIG_DB `PBH_RULE` — `flow_counter=ENABLED` のルールを抽出
2. COUNTERS_DB `ACL_COUNTER_RULE_MAP` — `<table>:<rule>` → counter OID のマッピング
3. COUNTERS_DB `COUNTERS:<counter_oid>` — 実際のカウンタ値

`ACL_COUNTER_RULE_MAP` は `AclOrch::registerFlexCounter()` (`aclorch.cpp:6041`) が `flow_counter=ENABLED` の PBH RULE SET 成功時に `hset` する（Phase F 副次書込で記録済み）。

---

## TTL / 再試行 / バックプレッシャー

| 項目 | 値 |
|------|-----|
| TTL | なし（CONFIG_DB は永続） |
| バッチサイズ | `DEFAULT_POP_BATCH_SIZE = 128` (ハードコード, `table.h:164`) |
| SELECT タイムアウト | 1000 ms（`orchdaemon.cpp` の main loop） |
| retry | `pendingSetupMap` で自動再試行（依存未解決時） |
| backpressure | なし（Redis pub/sub はブロッキングなし） |

CONFIG_DB テーブルのため `gBatchSize`（`orchagent -b <n>` で変更可）は適用されない。
