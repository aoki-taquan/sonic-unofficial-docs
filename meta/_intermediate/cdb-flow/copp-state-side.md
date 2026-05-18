# copp-state Phase F — 副次 DB 書込 スキャン証跡

## 調査対象ファイル

- `sonic-swss/orchagent/copporch.cpp`
- `sonic-swss/orchagent/copporch.h`

## grep 手順

```bash
grep -n "bindTrapCounter\|unbindTrapCounter\|COUNTERS_DB\|COUNTERS_TRAP\|FlexCounter\|m_counter_table\|setFlexCounterGroupParameter\|m_pendingAddToFlexCntr" copporch.cpp
```

## 発見した副次書き込み

### COUNTERS_DB: COUNTERS_TRAP_NAME_MAP

- `bindTrapCounter()` (L1418-1466): `m_counter_table->set("", nameMapFvs)` で `COUNTERS_TRAP_NAME_MAP` に `<trap-name>` → counter OID を書き込む (L1452-1456)
- `unbindTrapCounter()` (L1470-1501): `m_counter_table->hdel("", iter->second)` で削除 (L1494-1495)

### FLEX_COUNTER_DB: HOSTIF_TRAP_FLOW_COUNTER|<counter_oid>

- `doTask(SelectableTimer&)` (L935-965): `m_trap_counter_manager.setCounterIdList()` で `FLEX_COUNTER_DB` に書き込む (L950)
- `unbindTrapCounter()`: `m_trap_counter_manager.clearCounterIdList(counter_id)` で削除 (L1487)

### FLEX_COUNTER_DB: FLEX_COUNTER_GROUP_TABLE|HOSTIF_TRAP_FLOW_COUNTER

- `initTrapRatePlugin()` (L1375-1396): `setFlexCounterGroupParameter()` で Lua スクリプト SHA を設定。初回のみ呼ばれる。

## 副次書き込みが発生しないケース

- FlexCounter が無効の場合: `flex_counters_orch->getHostIfTrapCounterState()` == false → `bindTrapCounter()` が即 `return false`
- SAI `create_hostif_trap` 失敗時: `applyAttributesToTrapIds()` 内の `bindTrapCounter()` 呼び出し (L530) に到達しない

## 結論

副次書き込み先: COUNTERS_DB (`COUNTERS_TRAP_NAME_MAP`) と FLEX_COUNTER_DB (`HOSTIF_TRAP_FLOW_COUNTER|*`, `FLEX_COUNTER_GROUP_TABLE|HOSTIF_TRAP_FLOW_COUNTER`) の 3 テーブル。APPL_DB / CONFIG_DB / APPL_STATE_DB への書き戻しは存在しない。
