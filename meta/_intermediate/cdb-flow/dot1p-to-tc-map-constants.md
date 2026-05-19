# dot1p-to-tc-map: Phase E ハードコード定数 調査メモ

## 対象ページ

`docs/reference/config-db/dot1p-to-tc-map.md`

## 調査ソース

- `sonic-swss/orchagent/qosorch.h` — フィールド名定数
- `sonic-swss/orchagent/qosorch.cpp` — Dot1pToTcMapHandler 実装・SAI 定数使用箇所
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dot1p-tc-map.yang`
- `sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-types.yang.j2`

## 検出定数

### qosorch.h フィールド名定数

- L13: `dot1p_to_tc_field_name = "dot1p_to_tc_map"` — PORT_QOS_MAP フィールド名。`qos_to_ref_table_map` / `qos_to_attr_map` のキーとして使用

### qosorch.cpp SAI 定数 (Dot1pToTcMapHandler)

- L405-406: `attr.id = SAI_QOS_MAP_ATTR_TYPE; attr.value.u32 = SAI_QOS_MAP_TYPE_DOT1P_TO_TC` — create 時の type 固定値
- L391: `attr.id = SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` — マップエントリリスト属性 ID
- L63: `SAI_PORT_ATTR_QOS_DOT1P_TO_TC_MAP` — ポートバインド属性 ID (`qos_to_attr_map` エントリ)

### 型変換ハードコード

- L372: `dot1p_map_list.list[i].key.dot1p = static_cast<sai_uint8_t>(stoi(fvField(fv)))`
  - dot1p キーは `sai_uint8_t` (uint8) に変換。YANG pattern `[0-7]?` は 0..7 を許容
- L373: `dot1p_map_list.list[i].value.tc = static_cast<sai_cos_t>(stoi(fvValue(fv)))`
  - TC 値は `sai_cos_t` (uint8) に変換。YANG tc_type は uint8 range 0..15

### スイッチレベル適用なし

- `qosorch.cpp:1956` 付近 (`applyDscpToTcMapToSwitch`) を確認: DSCP_TO_TC_MAP のみスイッチレベル SAI 属性あり
- DOT1P_TO_TC_MAP にスイッチレベルバインド (`SAI_SWITCH_ATTR_QOS_DOT1P_TO_TC_MAP`) は実装なし

### デフォルトマップ名

- `"AZURE"` — ストレージバックエンドプラットフォームで `qos_config.j2` が注入するデフォルトマップ名（Phase A / defaults セクション参照）

## 非存在の定数

- DSCP_TO_TC_MAP にある `DSCP_MAX_VAL` (63) に相当する dot1p 最大値定数は存在しない。YANG pattern `[0-7]?` で制約し、qosorch は `stoi` 変換後の SAI sai_uint8_t キャストのみ（範囲チェック定数なし）
