# TC_TO_PRIORITY_GROUP_MAP — Phase C 暗黙参照調査

## 調査対象

- `orchagent/qosorch.cpp` (sonic-swss)
- `orchagent/tunneldecaporch.cpp` (sonic-swss)
- `yang-models/sonic-port-qos-map.yang` (sonic-buildimage)
- `yang-models/sonic-tunnel.yang` (sonic-buildimage)
- `yang-models/sonic-tc-priority-group-map.yang` (sonic-buildimage)

## YANG leafref 分析

### TC_TO_PRIORITY_GROUP_MAP 自身

`sonic-tc-priority-group-map.yang` には他テーブルへの leafref なし。自己完結した named map 定義。

### PORT_QOS_MAP 側（参照元）

`sonic-port-qos-map.yang` の `PORT_QOS_MAP_LIST` に `tc_to_pg_map` の leafref あり:

```
path "/tpgm:sonic-tc-priority-group-map/tpgm:TC_TO_PRIORITY_GROUP_MAP/tpgm:TC_TO_PRIORITY_GROUP_MAP_LIST/tpgm:name"
```

YANG レベルで `PORT_QOS_MAP.tc_to_pg_map` が `TC_TO_PRIORITY_GROUP_MAP` の name を参照することが強制される。

### TUNNEL_DECAP_TABLE 側（参照元）

`sonic-tunnel.yang` の `TUNNEL_DECAP_TABLE` における `decap_tc_to_pg_map` フィールドは `type string`（leafref なし）。
YANG 制約なしで実装レベルのみで参照整合性を担保。

## 実装レベルの暗黙参照

### 1. PORT_QOS_MAP — TC_TO_PRIORITY_GROUP_MAP を参照する主テーブル

- **参照先テーブル**: `CONFIG_DB PORT_QOS_MAP`
- **参照方向**: `PORT_QOS_MAP.tc_to_pg_map` が `TC_TO_PRIORITY_GROUP_MAP` を名前参照（被参照）
- **参照解決**: `handlePortQosMapTable()` → `resolveFieldRefValue(m_qos_maps, CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME, ...)` で OID 解決。未登録の場合 `task_need_retry`
- **YANG leafref**: あり（`sonic-port-qos-map.yang`）
- **evidence**: `qosorch.cpp:106` (`qos_to_ref_table_map`), `qosorch.cpp:2120-2131`

### 2. TUNNEL_DECAP_TABLE — decap_tc_to_pg_map 経由の参照

- **参照先テーブル**: `CONFIG_DB TUNNEL_DECAP_TABLE`（APP_DB の `APP_TUNNEL_DECAP_TABLE` 経由）
- **参照方向**: `TUNNEL_DECAP_TABLE.decap_tc_to_pg_map` が `TC_TO_PRIORITY_GROUP_MAP` を名前参照（被参照）
- **参照解決**: `TunnelDecapOrch` が `decap_tc_to_pg_field_name` フィールドを受信時に `gQosOrch->resolveTunnelQosMap(table_name, key, decap_tc_to_pg_field_name, t)` を呼ぶ。OID 未解決時は `SAI_NULL_OBJECT_ID` 返却 → `task_need_retry`
- **YANG leafref**: なし（`sonic-tunnel.yang` は `type string`）
- **evidence**: `tunneldecaporch.cpp:230-242`, `qosorch.cpp:114`

### 3. doTask() 実行順序 — TC_TO_PRIORITY_GROUP_MAP は PORT_QOS_MAP より先に drain

- `QosOrch::doTask()` が `PORT_QOS_MAP` executor を最後に drain し、その他（`TC_TO_PRIORITY_GROUP_MAP` を含む全 QoS マップ）を先に drain
- 同一イベントループで `TC_TO_PRIORITY_GROUP_MAP` SET → `PORT_QOS_MAP` SET が来た場合、通常 `task_need_retry` なし
- **evidence**: `qosorch.cpp:2231-2252`

### 4. PortsOrch::allPortsReady() ゲート

- `QosOrch::doTask(Consumer&)` の冒頭ガード。`allPortsReady()` が false の間は QoS テーブル全体がブロック
- **evidence**: `qosorch.cpp:2253-2258`

## BUFFER_PG / PFC_PRIORITY_TO_PRIORITY_GROUP_MAP との関係

TC_TO_PRIORITY_GROUP_MAP が設定する「TC → PG マッピング」は:
- `BUFFER_PG`: 該当 PG のバッファプロファイルを定義（lossy/lossless の buffer admission control）
- `PFC_PRIORITY_TO_PRIORITY_GROUP_MAP`: PFC ビットマスクと PG の対応定義

これらは CONFIG_DB の別テーブルで定義されるが、orchagent 内での直接依存関係はない（SAI レベルで独立した操作）。

## 参照関係サマリ

| 参照先テーブル / コンポーネント | YANG leafref | 参照種別 | 非充足時の挙動 | evidence |
|---|:---:|---|---|---|
| `PORT_QOS_MAP.tc_to_pg_map` | ✅ | 被参照（PORT_QOS_MAP が OID を名前解決） | `task_need_retry`（自動再試行） | `qosorch.cpp:106,2120-2131` |
| `TUNNEL_DECAP_TABLE.decap_tc_to_pg_map` | ✗ | 被参照（TunnelDecapOrch が名前解決） | `task_need_retry`（自動再試行） | `tunneldecaporch.cpp:230-242` |
| `PortsOrch::allPortsReady()` | ✗ | 起動順序ガード | `false` の間は全 QoS 処理停止 | `qosorch.cpp:2253-2258` |
