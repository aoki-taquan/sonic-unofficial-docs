# TC_TO_DSCP_MAP — Phase E ハードコード定数 調査ノート

## 調査対象ソース

- `sonic-swss/orchagent/qosorch.cpp` (ref: 4305596)
- `sonic-swss/orchagent/qosorch.h`
- `sonic-swss/tests/test_qos_map.py`
- `sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-types.yang.j2`

## テーブル名定数

`sonic-swss/tests/test_qos_map.py:6`:
```python
CFG_TC_TO_DSCP_MAP_TABLE_NAME = "TC_TO_DSCP_MAP"
```
swsscommon の C++ 実装でも同値で定義され、`qosorch.cpp:95,1339` で参照される。

## フィールド名定数 (`qosorch.cpp`)

```cpp
// qosorch.cpp:21
const string tc_to_dscp_field_name       = "tc_to_dscp_map";
// qosorch.cpp:37
const string encap_tc_to_dscp_field_name = "encap_tc_to_dscp_map";
```

- `tc_to_dscp_field_name` は `PORT_QOS_MAP` 側で `SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP` に解決される (qosorch.cpp:66)
- `encap_tc_to_dscp_field_name` は `TUNNEL` 側で `resolveTunnelQosMap()` が使用する参照フィールド名 (qosorch.cpp:115)

## 検証上限定数

```cpp
// qosorch.cpp:119
#define DSCP_MAX_VAL 63
```

`convertFieldValuesToAttributes()` (qosorch.cpp:1238-1241) で `value > DSCP_MAX_VAL` をチェックし超過は `task_invalid_entry`。

## SAI 型定数 (ハードコード)

```cpp
// qosorch.cpp:1271 — TcToDscpMapHandler::addQosItem()
qos_map_attr.value.u32 = SAI_QOS_MAP_TYPE_TC_AND_COLOR_TO_DSCP;
```

```cpp
// qosorch.cpp:66 — qos_to_attr_map
{tc_to_dscp_field_name, SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP},
```

これらの SAI 定数はコードに直接埋め込まれており、CONFIG_DB / DEVICE_METADATA で変更できない。

## YANG 型定数

```yang
// sonic-types.yang.j2:338-347
typedef tc_type {
    description "Traffic class identifier (0-15)";
    type uint8 {
        range "0..15";
    }
}
```

TC キーの有効範囲は YANG 上 0..15 だが、ASIC は 0..7 のみ対応する実装が多い（SAI task_failed）。

## ハードコードデフォルト一覧まとめ

| 定数 / 変数 | 値 | ファイル:行 | 動的変更可否 |
|---|---|---|---|
| `CFG_TC_TO_DSCP_MAP_TABLE_NAME` | `"TC_TO_DSCP_MAP"` | test_qos_map.py:6 / swsscommon | 不可 |
| `tc_to_dscp_field_name` | `"tc_to_dscp_map"` | qosorch.cpp:21 | 不可 |
| `encap_tc_to_dscp_field_name` | `"encap_tc_to_dscp_map"` | qosorch.cpp:37 | 不可 |
| `DSCP_MAX_VAL` | `63` | qosorch.cpp:119 | 不可 |
| `SAI_QOS_MAP_TYPE_TC_AND_COLOR_TO_DSCP` | SAI enum固定 | qosorch.cpp:1271 | 不可 |
| `SAI_PORT_ATTR_QOS_TC_AND_COLOR_TO_DSCP_MAP` | SAI enum固定 | qosorch.cpp:66 | 不可 |
| `tc_type` 範囲上限 | `15` (YANG) / 実質 `7` (ASIC) | sonic-types.yang.j2:338 | 不可 |
