# SWITCH_HASH — 副次 DB 書込 (Phase F) 調査証跡

## 調査対象

`sonic-swss/orchagent/switchorch.cpp` — `doCfgSwitchHashTableTask()` / `setSwitchHash()` / `setSwitchHashFieldListSai()` / `setSwitchHashAlgorithmSai()`

## 結論

`SWITCH_HASH` の SET 処理経路において、STATE_DB・APPL_DB・COUNTERS_DB への書き込みは一切発生しない。副次書き込みは ASIC_DB (syncd 経由 SAI) のみ。CRM カウンタも更新されない。

## 経路詳細

### SET 成功時

1. `setSwitchHashFieldListSai()` (L750-769): `sai_hash_api->set_hash_attribute(SAI_HASH_ATTR_NATIVE_HASH_FIELD_LIST, ...)` を呼ぶ → ASIC_DB (syncd 経由) の `ASIC_STATE:SAI_OBJECT_TYPE_HASH` を更新
2. `setSwitchHashAlgorithmSai()` (L771-780): `sai_switch_api->set_switch_attribute(SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_ALGORITHM / SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_ALGORITHM, ...)` を呼ぶ → ASIC_DB (syncd 経由) の `ASIC_STATE:SAI_OBJECT_TYPE_SWITCH` を更新
3. `swHlpr.setSwHash(hash)` (L940): **メモリ内キャッシュ更新のみ**。DB への書き込みなし。

### SET 失敗時

- STATE_DB / APPL_DB への書き込みなし
- `ERROR_TABLE` への書き込みなし
- syslog (SWSS_LOG_ERROR / SWSS_LOG_WARN) のみ

### DEL

- STATE_DB / APPL_DB への書き込みなし (DEL は常に拒否、ログのみ)

## FlexCounter / CRM

`doCfgSwitchHashTableTask()` は CrmOrch の `incCrmAclUsedCounter()` 等を呼ばない。`m_asicSensorsTable` (STATE_DB の ASIC 温度テーブル) や `m_asicSdkHealthEventTable` も SWITCH_HASH 処理とは無関係の別ハンドラで使用される。

## ASIC_DB 書込詳細

| SAI API | 属性 | 条件 |
|---------|------|------|
| `sai_hash_api->set_hash_attribute` | `SAI_HASH_ATTR_NATIVE_HASH_FIELD_LIST` | `ecmp_hash` / `lag_hash` SET 成功時 |
| `sai_switch_api->set_switch_attribute` | `SAI_SWITCH_ATTR_ECMP_DEFAULT_HASH_ALGORITHM` | `ecmp_hash_algorithm` SET 成功時 |
| `sai_switch_api->set_switch_attribute` | `SAI_SWITCH_ATTR_LAG_DEFAULT_HASH_ALGORITHM` | `lag_hash_algorithm` SET 成功時 |
