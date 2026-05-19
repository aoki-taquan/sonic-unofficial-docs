# DOT1P_TO_TC_MAP — 副次 DB 書込調査 (Phase F)

調査日: 2026-05-19
対象ソース: `sonic-swss/orchagent/qosorch.cpp`

## 調査手順

1. `Dot1pToTcMapHandler::addQosItem()` (qosorch.cpp:399-420) を確認
   - `sai_qos_map_api->create_qos_map()` のみ呼び出し
   - APPL_DB / STATE_DB / COUNTERS_DB への直接書込みなし

2. `QosMapHandler::modifyQosItem()` (qosorch.cpp:204-213) を確認
   - `sai_qos_map_api->set_qos_map_attribute()` のみ呼び出し

3. `QosMapHandler::removeQosItem()` (qosorch.cpp:216-228) を確認
   - `sai_qos_map_api->remove_qos_map()` のみ呼び出し

4. `qosorch.cpp` 全体を `COUNTERS_DB`, `FLEX_COUNTER`, `APPL_DB`, `STATE_DB` でスキャン
   - `COUNTERS_DB` 参照: 0 件
   - `FLEX_COUNTER` 参照: 0 件
   - `APPL_DB` 直接書込: 0 件（QosOrch は CONFIG_DB 直接購読）
   - `STATE_DB` 書込: 0 件

## 結論

DOT1P_TO_TC_MAP の SET/DEL は ASIC_DB (`SAI_OBJECT_TYPE_QOS_MAP`) への書込みのみを副次的に引き起こす。
COUNTERS_DB, FLEX_COUNTER_DB, STATE_DB, APPL_DB への副次書込みは一切なし。
