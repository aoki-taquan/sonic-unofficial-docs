# dot1p-to-pg-map — Phase F 副次 DB 書込み 調査証跡

## 調査対象

`DOT1P_TO_PG_MAP` は実在しないテーブルであるため、副次 DB 書込みは 2 段マッピングパイプライン
(`DOT1P_TO_TC_MAP` → `TC_TO_PRIORITY_GROUP_MAP`) および `PORT_QOS_MAP` の処理に由来する。

主要ハンドラ:
- `Dot1pToTcMapHandler::addQosItem()` — `qosorch.cpp:399-420`
- `TcToPgHandler::processWorkItem()` — `qosorch.cpp:933`
- `QosOrch::handlePortQosMapTable()` — `qosorch.cpp:2046-2229`

## SAI 呼び出し (ASIC_DB 書込み)

### DOT1P_TO_TC_MAP SET

`Dot1pToTcMapHandler::addQosItem()` が `sai_qos_map_api->create_qos_map()` を呼び出す
(`qosorch.cpp:412`):

- `SAI_QOS_MAP_ATTR_TYPE = SAI_QOS_MAP_TYPE_DOT1P_TO_TC`
- `SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` (dot1p → tc マッピングリスト)

成功時に SAI OID が ASIC_DB へ書き込まれる。

### TC_TO_PRIORITY_GROUP_MAP SET

`TcToPgHandler` が `sai_qos_map_api->create_qos_map()` を呼び出す
(`qosorch.cpp:920`):

- `SAI_QOS_MAP_ATTR_TYPE = SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP`
- `SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` (tc → pg マッピングリスト)

### PORT_QOS_MAP SET — ポートへのアタッチ

`QosOrch::handlePortQosMapTable()` が各ポートに `sai_port_api->set_port_attribute()` を呼び出す
(`qosorch.cpp:2193`):

| フィールド | SAI 属性 |
|-----------|---------|
| `dot1p_to_tc_map` | `SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP` |
| `tc_to_pg_map` | `SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` |

### PORT_QOS_MAP DEL — PFC 無効化

`PORT_QOS_MAP` DEL 時、`gPortsOrch->setPortPfc(port.m_port_id, 0)` が呼ばれ
PFC ビットマスクが 0 にクリアされる (`qosorch.cpp:2100`)。

## TUNNEL_DECAP_TABLE への波及

`TC_TO_PRIORITY_GROUP_MAP` が `APP_TUNNEL_DECAP_TABLE` からも参照される場合
(`decap_tc_to_pg_field_name`, `qosorch.cpp:114`)、`resolveTunnelQosMap()` が同一 OID を解決して
トンネルデカップ処理に適用する。

## STATE_DB / COUNTERS_DB / FLEX_COUNTER_DB

`QosOrch` は DOT1P_TO_TC_MAP / TC_TO_PRIORITY_GROUP_MAP の SET/DEL において
STATE_DB・COUNTERS_DB・FLEX_COUNTER_DB への直接書き込みを行わない。

## 参照コード

- `sonic-swss/orchagent/qosorch.cpp:399-420` (Dot1pToTcMapHandler::addQosItem)
- `sonic-swss/orchagent/qosorch.cpp:888-933` (TcToPgHandler)
- `sonic-swss/orchagent/qosorch.cpp:2046-2229` (handlePortQosMapTable)
- `sonic-swss/orchagent/qosorch.cpp:2100-2105` (DEL 時 PFC クリア)
- `sonic-swss/orchagent/qosorch.cpp:2314-2330` (resolveTunnelQosMap)
