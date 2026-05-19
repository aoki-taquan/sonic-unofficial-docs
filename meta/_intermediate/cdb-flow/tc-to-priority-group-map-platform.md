# tc-to-priority-group-map platform-diff phase (Phase H)

## 調査対象
- `sonic-swss/orchagent/qosorch.cpp` (ref: master)
- `sonic-swss/orchagent/tunneldecaporch.cpp` (ref: master)
- `sonic-buildimage/files/build_templates/qos_config.j2` (ref: master)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-tc-priority-group-map.yang` (ref: master)

## qos_config.j2 — マップ生成の条件分岐

`qos_config.j2:170-179` の TC_TO_PRIORITY_GROUP_MAP 生成ロジック:

```jinja2
{% if (generate_tc_to_pg_map is defined) and tunnel_qos_remap_enable %}
    {{- generate_tc_to_pg_map() }}
{% elif (generate_tc_to_pg_map is defined) and
        ('type' in DEVICE_METADATA['localhost'] and
          DEVICE_METADATA['localhost']['type'] in backend_device_types) and
        ('resource_type' in DEVICE_METADATA['localhost'] and
          DEVICE_METADATA['localhost']['resource_type'] == 'ComputeAI') %}
    {{- generate_tc_to_pg_map() }}
{% elif generate_tc_to_pg_map_per_sku is defined %}
    {{- generate_tc_to_pg_map_per_sku() }}
{% else %}
    "TC_TO_PRIORITY_GROUP_MAP": { "AZURE": {...}, ... }
{% endif %}
```

## 条件分岐の意味

1. **tunnel_qos_remap_enable** (qos_config.j2:142-144): DEVICE_METADATA に `tunnel_qos_remap_enable: "true"` が設定されている場合 true。トンネル QoS 再マッピング対応プラットフォーム (例: Broadcom で VxLAN トンネル decap 後の TC→PG 再マッピングをサポートする環境) で SKU 固有マップを使用する。

2. **backend_device_types + ComputeAI**: `BackEndToRRouter` / `BackEndLeafRouter` かつ `resource_type == "ComputeAI"` のデバイスは `generate_tc_to_pg_map()` で SKU 固有マップを生成する（Microsoft Azure の AI ラック向け構成）。

3. **generate_tc_to_pg_map_per_sku**: 一部 Mellanox / Broadcom ベンダーが HWSKU ごとに Jinja2 マクロを定義。AZURE デフォルトに代わって SKU 固有の TC→PG マッピングが生成される。

4. **デフォルト (`else`)**: 上記条件に当てはまらない標準プラットフォームは `AZURE` マップ (TC0,1,2,5,6→PG0 / TC3→PG3 / TC4→PG4 / TC7→PG7) を使用する。PORT_DPC が存在する場合は `AZURE_DPC` も追加生成される。

## AZURE_DPC マップ

`PORT_DPC` (DPU 接続ポート) が存在する環境では `AZURE_DPC` マップも生成される (qos_config.j2:182-193):

```json
"AZURE_DPC": {
    "0": "0", "1": "0", "2": "0", "3": "0",
    "4": "0", "5": "0", "6": "0", "7": "7"
}
```

SmartSwitch の DPU 接続ポートは全 TC を PG0 (ベストエフォート) にマッピングし、TC7 のみ PG7 に割り当てる。PFC は TC7/PG7 のみ対象。

## orchagent 側の差異

`QosOrch::handleTcToPgTable` / `TcToPgHandler` は SAI API `SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP` でマップを作成する。SAI の実装差異:

- **Broadcom (BRCM SAI)**: `SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP` をサポート。TC 0..7 の全マッピングが ASIC に適用される。
- **ASIC が TC 8..15 を拒否**: YANG の `tc_type` は uint8 (0..15) を許容するが、多くの ASIC は TC 0..7 のみサポートし SAI create_qos_map() が TC 8..15 エントリに対してエラーを返す (orchagent はエントリ単位でなくマップ全体を create するためマップ全体が失敗する場合がある)。
- **VS (仮想スイッチ)**: `sai_qos_map_api->create_qos_map()` は通常成功するが ASIC への実際の反映はなし。

## tunneldecaporch — tunnel_qos_remap_enable との関係

`tunnel_qos_remap_enable` が true の環境では `TUNNEL_DECAP_TABLE.decap_tc_to_pg_map` フィールドが使用される。この場合、`TC_TO_PRIORITY_GROUP_MAP` テーブルに `generate_tc_to_pg_map()` で生成された SKU 固有マップが存在し、トンネル decap 後のパケットに異なる TC→PG マッピングが適用される。一般プラットフォーム (tunnel_qos_remap_enable=false) では `decap_tc_to_pg_map` フィールドは使用されない。

## まとめ

| 観点 | 標準プラットフォーム | SKU 固有 (per_sku マクロあり) | SmartSwitch DPU ポート | トンネル QoS 対応プラットフォーム |
|------|------------------|----------------------------|-----------------------|-------------------------------|
| マップ名 | `AZURE` | SKU 定義に依存 | `AZURE_DPC` (TC7→PG7, 他は PG0) | SKU 定義 (`generate_tc_to_pg_map()`) |
| TC→PG デフォルト | TC3→PG3, TC4→PG4, 他→PG0 | プラットフォーム依存 | TC7→PG7, 他→PG0 | プラットフォーム依存 |
| decap_tc_to_pg_map 使用 | なし | なし | なし | 使用 (TUNNEL_DECAP_TABLE 参照) |
| ASIC TC 範囲 | 0..7 有効 | 0..7 有効 | 0..7 有効 | 0..7 有効 |
