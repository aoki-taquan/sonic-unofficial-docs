# DSCP_TO_TC_MAP — 暗黙参照分析 (Phase C)

ソース: `sonic-swss/orchagent/qosorch.cpp`

## 参照先テーブル一覧

| 参照先テーブル | 参照フィールド / 用途 | ソース行 |
|---------------|----------------------|---------|
| `PORT_QOS_MAP` | `dscp_to_tc_map` フィールドで名前参照。ポートへ `SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP` としてバインド | `qosorch.cpp:61,100` |
| `PORT_QOS_MAP\|global` | スイッチレベル `SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP` 設定時の参照元エントリ | `qosorch.cpp:1988,2030-2032` |
| `SWITCH_TABLE` (capability) | `querySwitchCapability(SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)` でスイッチ対応確認 | `qosorch.cpp:1956` |
| `TC_TO_QUEUE_MAP` | `PORT_QOS_MAP` 同一エントリ内で `tc_to_queue_map` フィールドに並列参照される（DSCP→TC→Queue 2 段連鎖） | `qosorch.cpp:64,103,1332` |

## PORT_QOS_MAP 参照メカニズム

`QosOrch::handlePortQosMapTable()` (`qosorch.cpp:2049`) が `PORT_QOS_MAP` の SET イベントを受け取り、
`resolveFieldRefValue(m_qos_maps, dscp_to_tc_field_name, CFG_DSCP_TO_TC_MAP_TABLE_NAME, ...)` で
対応する `DSCP_TO_TC_MAP` オブジェクト ID を解決する。

- 解決成功 → `sai_port_api->set_port_attribute(port.m_port_id, SAI_PORT_ATTR_QOS_DSCP_TO_TC_MAP, id)`
- 解決失敗（未作成）→ `task_need_retry`（自動再試行）

`PORT_QOS_MAP|global` の場合は `handleGlobalQosMap()` が分岐し、
`applyDscpToTcMapToSwitch(SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP, id)` でスイッチ全体に適用。

## SWITCH_TABLE capability 参照メカニズム

`QosOrch::applyDscpToTcMapToSwitch()` (`qosorch.cpp:1951`) が呼ばれると、最初に
`gSwitchOrch->querySwitchCapability(SAI_OBJECT_TYPE_SWITCH, SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP)` を実行する。

- 対応 → `sai_switch_api->set_switch_attribute(gSwitchId, SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP, map_id)`
- 非対応 → ログ出力のみ、エラーなしで `true` を返す（適用スキップ）

## TC_TO_QUEUE_MAP との 2 段連鎖

`qos_to_ref_table_map` にて:
- `dscp_to_tc_field_name` → `CFG_DSCP_TO_TC_MAP_TABLE_NAME`
- `tc_to_queue_field_name` → `CFG_TC_TO_QUEUE_MAP_TABLE_NAME`

の両エントリが同列定義されている。`PORT_QOS_MAP` の SET 処理では両フィールドを一括解決し、
いずれかが未解決なら `task_need_retry` を返す。
DSCP→TC と TC→Queue は独立した SAI map オブジェクトだが、同一 `PORT_QOS_MAP` エントリで管理されるため
実質的に連動して設定される。

## 結論 (cross-refs ブロックへの反映内容)

1. **PORT_QOS_MAP** — `dscp_to_tc_map` フィールド経由でポートバインド（ポートレベル）
2. **PORT_QOS_MAP|global** — スイッチレベル DSCP map 設定。Broadcom 限定で `db_migrator` が自動生成
3. **SWITCH_TABLE (capability)** — スイッチ対応確認。非対応 ASIC は silent スキップ
4. **TC_TO_QUEUE_MAP** — DSCP→TC→Queue の 2 段マッピング連鎖において `PORT_QOS_MAP` を介して間接連動

> **Evidence**: `sonic-swss/orchagent/qosorch.cpp:61,64,81,84,100,103,1329,1332,1955-1975,1988,2030-2032`
