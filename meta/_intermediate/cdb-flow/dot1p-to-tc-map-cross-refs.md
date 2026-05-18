# DOT1P_TO_TC_MAP — 暗黙参照調査 (Phase C)

## 調査対象

- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-swss/orchagent/qosorch.h`

## 抽出結果

### 被参照テーブル

| 参照方向 | 参照元テーブル | フィールド | SAI 属性 | evidence |
|---------|-------------|-----------|---------|---------|
| 被参照 (referenced by) | `PORT_QOS_MAP` | `dot1p_to_tc_map` | `SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP` | `qosorch.h:13`, `qosorch.cpp:63` |
| 参照管理 | `handlePortQosMapTable` | SET 時 object_id 解決 / DEL 時参照解除 | — | `qosorch.cpp:2046,2077,2108,2133` |
| SWITCH レベル適用 | なし | DOT1P マップは SWITCH 直接適用なし | — | `qosorch.cpp:1956`（DSCP_TO_TC のみ） |

### 詳細

- `qos_to_ref_table_map`（`qosorch.cpp:99-102`）: `dot1p_to_tc_field_name` →
  `CFG_DOT1P_TO_TC_MAP_TABLE_NAME` と対応付けており、`PORT_QOS_MAP` SET 時の `resolveFieldRefValue()` でこの map が参照される。
- `isObjectBeingReferenced()` での参照チェック（`qosorch.cpp:181`）は `PORT_QOS_MAP.dot1p_to_tc_map`
  から参照中に DOT1P_TO_TC_MAP を DEL しようとした際に true を返す。
- SWITCH レベルへの直接適用は `DSCP_TO_TC_MAP` (`PORT_QOS_MAP|global` 経路) のみ。
  `DOT1P_TO_TC_MAP` は SWITCH 直接適用なし（`querySwitchCapability` 判定対象外）。
