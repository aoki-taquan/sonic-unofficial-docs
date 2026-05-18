# srv6-state — Phase D 失敗挙動 調査ノート

## 調査対象

- `sonic-net/sonic-swss` `orchagent/srv6orch.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- COUNTERS_DB テーブル: `COUNTERS_SRV6_NAME_MAP`, `COUNTERS:<oid>`

## 検出された失敗経路

### SAI カウンタ能力クエリ失敗 (initializeCounters)

`queryMySidCountersCapability()` (srv6orch.cpp:144-155):
`sai_query_attribute_capability()` が非 SUCCESS を返すか、
`capability.set_implemented && capability.create_implemented` が false の場合、
`m_mysid_counters_supported = false` に確定。
その後 `addMySidCounter()` は一切呼ばれない → COUNTERS_DB への書き込み発生なし。
この判断は起動時一回限りで、実行中変更不可。

### SAI generic counter 作成失敗

`addMySidCounter()` (srv6orch.cpp:188-192):
`FlowCounterHandler::createGenericCounter(counter_oid)` が false を返すと、
`addMySidCounter` も false を返す。
呼び出し元 `createUpdateMysidEntry()` (srv6orch.cpp:1593-1598) は false を受けてすぐに return false し、
**MySID エントリ自体が ASIC に作成されない**。

### setMySidEntryCounter の SAI 失敗

`setMySidEntryCounter()` (srv6orch.cpp:244-248):
`sai_srv6_api->set_my_sid_entry_attribute()` 失敗時は SWSS_LOG_ERROR のみ。
カウンタ OID は `COUNTERS_SRV6_NAME_MAP` に書き込み済みだが
SAI MY_SID_ENTRY へのカウンタ紐付けは失敗状態となる。
ロールバックなし。

### FLEX_COUNTER_TABLE|SRV6 disable 時

`setCountersState(false)` (srv6orch.cpp:273-280):
`setMySidEntryCounter(sai_entry, SAI_NULL_OBJECT_ID)` → SAI からカウンタ切り離し
`removeMySidCounter()` → `COUNTERS_SRV6_NAME_MAP` から削除、FlexCounter 解除
この間の `SWSS_LOG_ERROR` は `setMySidEntryCounter` 失敗時のみ。
失敗しても `removeMySidCounter()` は続行され、`COUNTERS_SRV6_NAME_MAP` からは削除される。

## 方向性サマリ

| 失敗条件 | 結果 | 自動回復 |
|----------|------|----------|
| SAI 能力クエリ非対応 | カウンタ機能全体が無効（起動時確定） | orchagent 再起動 |
| generic counter 作成失敗 | MySID エントリ自体が ASIC 未作成 | なし |
| setMySidEntryCounter SAI 失敗 | カウンタ OID 登録済みだが SAI リンク切れ | なし |
