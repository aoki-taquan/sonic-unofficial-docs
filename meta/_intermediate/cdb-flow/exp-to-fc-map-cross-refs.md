# EXP_TO_FC_MAP — Phase C 暗黙参照スキャンノート

対象テーブル: `EXP_TO_FC_MAP`
Consumer: `QosOrch::handleExpToFcTable()` / `QosOrch::handlePortQosMapTable()` (`sonic-swss/orchagent/qosorch.cpp`)
スキャン範囲: qosorch.cpp 全行精読、nhgmaporch.cpp:299-325、tunneldecaporch.cpp:100-302

---

## 検出した暗黙参照・クロス依存

### 1. PORT_QOS_MAP.exp_to_fc_map による参照

- `qos_to_attr_map` (qosorch.cpp:72): `exp_to_fc_field_name` → `SAI_PORT_ATTR_QOS_MPLS_EXP_TO_FORWARDING_CLASS_MAP`
- `qos_to_ref_table_map` (qosorch.cpp:112): `exp_to_fc_field_name` → `CFG_EXP_TO_FC_MAP_TABLE_NAME`
- `handlePortQosMapTable()` qosorch.cpp:2124-2129: PORT_QOS_MAP の `exp_to_fc_map` フィールドを `resolveFieldRefValue()` で解決し、OID を取得してポートへ SAI 適用。
- reference tracking: `setObjectReference(m_qos_maps, CFG_PORT_QOS_MAP_TABLE_NAME, ...)` で参照をトラッキング。
- DEL 時: `isObjectBeingReferenced()` が true なら `m_pendingRemove=true` + `task_need_retry`。

### 2. SWITCH グローバルレベルへの適用なし

- `handleGlobalQosMap()` qosorch.cpp:2011: `if (map_type_name != dscp_to_tc_field_name)` の分岐で EXP_TO_FC フィールドは `SWSS_LOG_WARN("Qos map type %s is not supported at global level")` として無視される。
- `PORT_QOS_MAP|global` に `exp_to_fc_map` を書いても SAI 適用なし。

### 3. FC 値上限の間接依存（NhgMapOrch）

- `ExpToFcMapHandler::convertFieldValuesToAttributes()` qosorch.cpp:1137: `NhgMapOrch::getMaxNumFcs()` を呼び出し FC 値の有効範囲上限を取得。
- `NhgMapOrch::getMaxNumFcs()` nhgmaporch.cpp:299-325: `SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES` を SAI から取得（初回のみ、以後キャッシュ）。スイッチ未サポートなら `max_num_fcs=0`。
- `EXP_TO_FC_MAP` の SET は SAI 初期化後でないと全エントリが reject される可能性あり。

### 4. TunnelDecapOrch による参照なし

- MPLS EXP→FC マッピングはトンネル decap 経路では使用されない。tunneldecaporch.cpp に EXP_TO_FC 参照なし。

### 5. NhgMapOrch / CbfNhgOrch との関係

- `CbfNhgOrch` は `NhgMapOrch` の SAI map OID（`CFG_NHG_MAP_TABLE_NAME` = `CBF_NHG_TABLE`）を参照するが、`EXP_TO_FC_MAP` を直接参照しない。
- `NhgMapOrch` は EXP_TO_FC_MAP の FC 値上限の情報源であり、EXP_TO_FC_MAP の OID を管理しているわけではない（独立した type_map エントリ）。

---

## 参照サマリ

| # | 参照元 | フィールド | SAI 属性 | 挙動 |
|---|--------|-----------|---------|------|
| 1 | PORT_QOS_MAP | exp_to_fc_map | SAI_PORT_ATTR_QOS_MPLS_EXP_TO_FORWARDING_CLASS_MAP | 参照解決後にポートへ適用 |
| 2 | PORT_QOS_MAP\|global | exp_to_fc_map | なし（WARN + 無視） | グローバル適用不可 |
| 3 | NhgMapOrch | getMaxNumFcs() | SAI_SWITCH_ATTR_MAX_NUMBER_OF_FORWARDING_CLASSES | FC 値の有効範囲を提供 |
