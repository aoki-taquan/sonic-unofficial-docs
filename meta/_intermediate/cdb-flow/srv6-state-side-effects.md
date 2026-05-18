# srv6-state Phase F: 副次 DB 書込 (side-effects)

調査対象: `srv6orch.cpp` `addMySidCounter()` L184-210、`removeMySidCounter()` L212-234、
`setMySidEntryCounter()` L236-248、`setCountersState()` L251-283、`doTask(SelectableTimer)` L286-313、
`createUpdateMysidEntry()` L1589-1614 全行精読。

## COUNTERS_DB への副次書込みトリガー

COUNTERS_DB の `COUNTERS_SRV6_NAME_MAP` / `COUNTERS:<oid>` はユーザーが直接書くテーブルではなく、
`Srv6Orch` が `SRV6_MY_SIDS` (CONFIG_DB) および `FLEX_COUNTER_TABLE|SRV6_STAT_COUNTER` の変化を受けて書き込む。

### トリガー 1: SRV6_MY_SIDS SET

`createUpdateMysidEntry()` が `addMySidCounter()` を呼び出す条件:
- `getMySidCountersSupported()` が true（起動時 SAI capability クエリで確定）
- `getMySidCountersEnabled()` が true（`FLEX_COUNTER_TABLE|SRV6_STAT_COUNTER enable`）

副次書込み:
1. COUNTERS_DB `COUNTERS_SRV6_NAME_MAP` hset — OID マッピング登録（即時）
2. `m_pending_counters` に OID 積み → 1 秒タイマー後に FLEX_COUNTER_DB `SRV6_STAT_COUNTER:<oid>` setCounterIdList
3. SAI `set_my_sid_entry_attribute(SAI_MY_SID_ENTRY_ATTR_COUNTER_ID, oid)` — ASIC カウンタ紐付け

### トリガー 2: SRV6_MY_SIDS DEL

`deleteMysidEntry()` が `removeMySidCounter()` を呼び出す:
1. COUNTERS_DB `COUNTERS_SRV6_NAME_MAP` hdel — OID マッピング削除
2. FLEX_COUNTER_DB `SRV6_STAT_COUNTER:<oid>` clearCounterIdList（pending に無い場合のみ）
3. SAI generic counter `remove_counter` — ASIC リソース解放

### トリガー 3: FLEX_COUNTER_TABLE|SRV6_STAT_COUNTER enable

`setCountersState(true)` が全既存 MySID を走査して `addMySidCounter()` を一括呼び出し。
副次書込みはトリガー 1 と同一。

### トリガー 4: FLEX_COUNTER_TABLE|SRV6_STAT_COUNTER disable

`setCountersState(false)` が全既存 MySID を走査:
1. SAI `set_my_sid_entry_attribute(SAI_MY_SID_ENTRY_ATTR_COUNTER_ID, SAI_NULL_OBJECT_ID)` — ASIC カウンタ切離し
2. COUNTERS_DB `COUNTERS_SRV6_NAME_MAP` hdel
3. FLEX_COUNTER_DB clearCounterIdList（pending 外の場合のみ）

### 副次書込みが発生しない DB

- STATE_DB: 書き込みなし
- APPL_DB: 書き込みなし
- CONFIG_DB（書き戻し）: なし

## 備考

`gTraditionalFlexCounter=true` 時は `doTask(timer)` が ASIC_DB `VIDTORID` を確認してから
FLEX_COUNTER_DB へ書き込む（`srv6orch.cpp:293-295`）。
`gTraditionalFlexCounter=false` (SAI redis モード) 時は VID 確認不要で即時登録。

冪等性: `m_mysid_counters_enabled` フラグにより連続 enable/disable は no-op で保護。
