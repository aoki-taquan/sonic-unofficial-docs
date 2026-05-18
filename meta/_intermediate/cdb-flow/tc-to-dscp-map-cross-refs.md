# TC_TO_DSCP_MAP — 暗黙参照スキャン (Phase C)

調査日: 2026-05-18
調査者: Claude (batch398)

## スキャン方針

`TC_TO_DSCP_MAP` を参照する上流テーブル、および TC_TO_DSCP_MAP が間接的に依存するパイプライン上流/下流テーブルを `qosorch.cpp` / `tunneldecaporch.cpp` / `qosorch.h` を grep して網羅的に列挙した。

## 上流参照元

### qos_to_ref_table_map エントリ (qosorch.cpp:105,115)

```cpp
{tc_to_dscp_field_name, CFG_TC_TO_DSCP_MAP_TABLE_NAME},      // PORT_QOS_MAP.tc_to_dscp_map
{encap_tc_to_dscp_field_name, CFG_TC_TO_DSCP_MAP_TABLE_NAME}, // TUNNEL.encap_tc_to_dscp_map
```

| 参照元テーブル | フィールド | 処理ロジック | evidence |
|---|---|---|---|
| `PORT_QOS_MAP` | `tc_to_dscp_map` | `handlePortQosMapTable()` の `resolveFieldRefValue()` で OID 解決。未作成なら `task_need_retry` | qosorch.cpp:105, 2077-2133 |
| `TUNNEL` | `encap_tc_to_dscp_map` | `tunneldecaporch.cpp:247` で `gQosOrch->resolveTunnelQosMap()` 呼出し。未解決なら `task_need_retry` | tunneldecaporch.cpp:245-250, qosorch.cpp:115 |

### m_qos_maps 参照カウンタ (qosorch.cpp:95)

`CFG_TC_TO_DSCP_MAP_TABLE_NAME` エントリが `m_qos_maps` 内の `object_reference_map` に登録されており、
`PORT_QOS_MAP` / `TUNNEL` が参照している間は DEL が `m_pendingRemove=true` で保留される (qosorch.cpp:181-186)。

## パイプライン上流 (TC を生成するテーブル)

| テーブル | 役割 | TC_TO_DSCP_MAP との関係 |
|---|---|---|
| `DSCP_TO_TC_MAP` | ingress DSCP → TC 変換 | 受信パケットの DSCP を TC に変換したものが egress 時に TC_TO_DSCP_MAP で DSCP に再マップされる |
| `MPLS_TC_TO_TC_MAP` | MPLS EXP → TC 変換 | MPLS パケットの TC 源泉。egress 書き換えで TC_TO_DSCP_MAP が使われる |
| `DOT1P_TO_TC_MAP` | 802.1p PCP → TC 変換 | L2 フレームの TC 源泉 |

これらは TC_TO_DSCP_MAP のハンドラが直接参照するわけではなく、パイプライン文脈上の依存。

## パイプライン下流 (egress side-effect)

| テーブル | 役割 |
|---|---|
| `PORT_QOS_MAP` | bind 先ポート — `SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP` が設定される |
| `TUNNEL` (APPL_DB) | トンネル encap — `encap_tc_to_dscp_map_id` が tunneldecaporch に反映される |

## qos_to_attr_map (SAI 属性マッピング)

```cpp
// qosorch.cpp:66
{tc_to_dscp_field_name, SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP},
```

ポートレベルの egress DSCP リマーキングに使用される SAI 属性。

## 範囲外

- `DSCP_TO_FC_MAP` / `EXP_TO_FC_MAP`: Forwarding Class 系は別系統
- `TC_TO_QUEUE_MAP`: TC → egress queue 方向のマップであり、TC_TO_DSCP_MAP ハンドラからの参照なし
- `WRED_PROFILE`: DROP profile。TC_TO_DSCP_MAP ハンドラからの参照なし
