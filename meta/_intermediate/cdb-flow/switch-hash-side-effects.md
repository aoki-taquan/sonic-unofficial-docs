# switch-hash side-effects scan

## 対象

`docs/reference/config-db/switch-hash.md` — `SWITCH_HASH` テーブル (Phase F)

## 調査方針

`sonic-swss/orchagent/switchorch.cpp` の `doCfgSwitchHashTableTask()` および
`setSwitchHash()` / `setSwitchHashFieldListSai()` / `setSwitchHashAlgorithmSai()` を全行精読。

## 結果

### Redis DB への副次書込

| DB | 書込 | 備考 |
|----|------|------|
| APPL_DB | なし | `doCfgSwitchHashTableTask()` に ProducerStateTable の呼び出しなし |
| STATE_DB | なし | m_asicSensorsTable / m_asicSdkHealthEventTable は ASIC センサー専用 |
| COUNTERS_DB | なし | m_counterManager はスイッチ統計専用でハッシュ処理経路から非呼び出し |
| FLEX_COUNTER_DB | なし | 同上 |
| ASIC_DB | 間接（syncd 経由） | sai_hash_api->set_hash_attribute() / sai_switch_api->set_switch_attribute() |

### SAI 呼び出しトレース

1. `ecmp_hash` フィールドリスト → `setSwitchHashFieldListSai(hash, true)` → `sai_hash_api->set_hash_attribute(oid, &attr)` (SAI_HASH_ATTR_NATIVE_HASH_FIELD_LIST)
2. `ecmp_hash_algorithm` → `setSwitchHashAlgorithmSai(hash, true)` → `sai_switch_api->set_switch_attribute(gSwitchId, &attr)` (SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_ALGORITHM)
3. `lag_hash` フィールドリスト → `setSwitchHashFieldListSai(hash, false)` (SAI_HASH_ATTR_NATIVE_HASH_FIELD_LIST)
4. `lag_hash_algorithm` → `setSwitchHashAlgorithmSai(hash, false)` (SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_ALGORITHM)

DEL 操作: `SWSS_LOG_ERROR` のみ出力してエントリ erase。SAI も DB も書かない。

## grep 証跡

```
grep -n "ProducerState\|Table::set\|hset\|m_stateDb\|COUNTERS_DB\|FlexCounter" switchorch.cpp | hash
→ ヒットなし (hash 処理経路)

grep -n "doCfgSwitchHashTableTask\|setSwitchHash" switchorch.cpp
→ L943 (定義), L750, L771, L782 (呼び出し先)
```
