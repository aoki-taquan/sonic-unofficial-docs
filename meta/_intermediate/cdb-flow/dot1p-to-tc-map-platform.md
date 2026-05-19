# DOT1P_TO_TC_MAP — プラットフォーム差分調査

## 調査対象

- `sonic-swss/orchagent/qosorch.cpp`
- `sonic-buildimage/files/build_templates/qos_config.j2`

## 1. SWITCH レベル適用の有無

`DSCP_TO_TC_MAP` は `applyDscpToTcMapToSwitch()` / `handleGlobalQosMap()` でスイッチレベル
(`SAI_SWITCH_ATTR_QOS_DSCP_TO_TC_MAP`) への適用を持つ。

`DOT1P_TO_TC_MAP` は対応する `applyDot1pToTcMapToSwitch()` 関数を持たない。
`handleGlobalQosMap()` 内の対象フィールドは `dscp_to_tc_field_name` のみ
（`qosorch.cpp:2011` の `if (map_type_name != dscp_to_tc_field_name)` 分岐）。

→ **DOT1P_TO_TC_MAP はスイッチレベル適用なし。PORT_QOS_MAP 経由のポートバインドのみ。**

## 2. ビルド時デフォルト注入のプラットフォーム条件

`qos_config.j2:240-253`:

```jinja
{% if 'type' in DEVICE_METADATA['localhost'] and
      DEVICE_METADATA['localhost']['type'] in backend_device_types and
      'storage_device' in DEVICE_METADATA['localhost'] and
      DEVICE_METADATA['localhost']['storage_device'] == 'true' %}
    "DOT1P_TO_TC_MAP": {
        "AZURE": {
            "0": "1", "1": "0", "2": "2", "3": "3",
            "4": "4", "5": "5", "6": "6", "7": "7"
        }
    },
```

`backend_device_types = ['BackEndToRRouter', 'BackEndLeafRouter']`（`qos_config.j2:164`）

条件: `type in ['BackEndToRRouter', 'BackEndLeafRouter'] AND storage_device == 'true'`

Mellanox 向け `qos.json.j2` や `generate_dscp_to_tc_map()` マクロは
`DOT1P_TO_TC_MAP` を生成しない（dot1p は L2 QoS のため、トンネル QoS remap 対象外）。

## 3. TC 範囲の ASIC 差分

YANG: `tc_type = uint8 range 0..15`。ASIC 対応は製品依存。

| ASIC 系統 | 実用 TC 範囲 | 備考 |
|-----------|------------|------|
| Broadcom (多数) | 0..7 | TC8 以上は SAI エラー |
| Mellanox (多数) | 0..7 | 同上 |
| 一部高性能 ASIC | 0..15（可能性） | SAI ベンダー実装依存 |

## 4. db_migrator の DOT1P 扱い

`db_migrator.py:575-577` で `PORT_QOS_MAP` の `dot1p_to_tc_map` フィールドの
ABNF 形式参照削除 (`migrate_qos_db_fieldval_reference_remove`) を実施するが、
`DOT1P_TO_TC_MAP` テーブル自体の migration は存在しない。

## Evidence

- `sonic-swss/orchagent/qosorch.cpp:1979-2054` (handleGlobalQosMap — DOT1P 非対象確認)
- `sonic-buildimage/files/build_templates/qos_config.j2:164,240-253` (backend_device_types 条件)
- `sonic-utilities/scripts/db_migrator.py:575-577` (dot1p_to_tc_map の ABNF 参照削除)
