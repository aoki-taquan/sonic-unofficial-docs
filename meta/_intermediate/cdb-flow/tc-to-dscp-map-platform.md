# TC_TO_DSCP_MAP — プラットフォーム差分調査 (Phase H)

調査日: 2026-05-19
対象ファイル:
- sonic-buildimage/files/build_templates/qos_config.j2
- sonic-buildimage/device/common/profiles/th2/7260/BALANCED/qos.json.j2
- sonic-buildimage/device/common/profiles/th2/7260/RDMA-CENTRIC/qos.json.j2
- sonic-buildimage/device/arista/x86_64-arista_7050cx3_32s/*/BALANCED/qos.json.j2
- sonic-buildimage/device/arista/x86_64-arista_7060x6_64pe_b/*/qos.json.j2
- sonic-buildimage/device/mellanox/x86_64-mlnx_msn4600c-r0/*/qos.json.j2
- sonic-buildimage/device/mellanox/x86_64-nvidia_sn5600-r0/*/qos.json.j2
- sonic-swss/orchagent/qosorch.cpp

## ビルド時注入分岐

`qos_config.j2:334-337` に以下の分岐がある:

```jinja
{% if (generate_tc_to_dscp_map is defined) and tunnel_qos_remap_enable %}
    {{- generate_tc_to_dscp_map() }}
{% elif (generate_tc_to_dscp_map_per_sku is defined) %}
    {{ generate_tc_to_dscp_map_per_sku() }}
```

`tunnel_qos_remap_enable` は `SYSTEM_DEFAULTS.tunnel_qos_remap.status == 'enabled'` のとき `true` になる
(qos_config.j2:142-145)。

## プラットフォーム別マップ内容

### Broadcom TH2 系 (common/profiles/th2/7260/BALANCED および RDMA-CENTRIC)

`generate_tc_to_dscp_map()` を定義。tunnel_qos_remap_enable が true の場合のみ注入。

```json
"TC_TO_DSCP_MAP": {
    "AZURE_TUNNEL": {
        "0": "8", "1": "0", "2": "0", "3": "2",
        "4": "6", "5": "46", "6": "0", "7": "48", "8": "33"
    }
}
```

TC 8 (DSCP 33) を含む — YANG 上 0..15 は valid だが、この TC 8 は ASIC 依存。

### Arista 7050CX3-32S 系

`generate_tc_to_dscp_map()` を定義。マップ内容は TH2 系と同一 (AZURE_TUNNEL、TC 0-8)。

### Arista 7060X6-64PE-B 系

`generate_tc_to_dscp_map_per_sku()` を定義。こちらは `tunnel_qos_remap_enable` 条件なし、常に注入。

```json
"TC_TO_DSCP_MAP": {
    "AZURE_DOWNLINK_BT1": { "8": "11" }
}
```

TC 8 のみ定義。PORT_QOS_MAP でポートごとに方向（downlink/uplink）に応じたマップを割り当て。

### Mellanox SN4600C-C64

`generate_tc_to_dscp_map()` を定義。AZURE_TUNNEL マップを生成するが値が TH2 系と異なる:

```json
"TC_TO_DSCP_MAP": {
    "AZURE_TUNNEL": {
        "0": "8", "1": "0", "2": "2", "3": "2",
        "4": "6", "5": "46", "6": "6", "7": "48", "8": "33"
    }
}
```

TC 1→0、TC 2→2、TC 6→6 が Broadcom 系と相違（TC 2: 0 vs 2、TC 6: 0 vs 6）。

### Mellanox SN5600 (NVIDIA)

`generate_tc_to_dscp_map_per_sku()` を定義。`traffic_config.traffic_classification_enable` かつ `DEVICE_METADATA.localhost.type` による分岐あり:

- ToRRouter: `AZURE_DOWNLINK_BT0` (TC 8 → DSCP 21) と `AZURE_UPLINK_BT0` (TC 8 → DSCP 11)
- LeafRouter: `AZURE_DOWNLINK_BT1` (TC 8 → DSCP 11)

ロール（ToRRouter / LeafRouter）によってマップ名と DSCP 値が変化する。

### デフォルト未定義プラットフォーム

両マクロが未定義の場合、`TC_TO_DSCP_MAP` は CONFIG_DB に生成されない。これは正常動作（TC→DSCP リマーキングが不要なプラットフォーム）。フォールバック else 節なし。

## multi-ASIC / VOQ chassis 差分

- `qosorch.cpp` の TC_TO_DSCP_MAP ハンドラ (`handleTcToDscpTable()`) に multi-ASIC 判定なし。`orchdaemon.cpp` の `qos_tables` に `CFG_TC_TO_DSCP_MAP_TABLE_NAME` を含むが、namespace 分岐なし。
- VOQ chassis: `qosorch.cpp:1637,1715,1772` に `gMySwitchType == "voq"` 分岐があるが、これは SCHEDULER / QUEUE 系のみで TC_TO_DSCP_MAP は対象外。
- 結論: multi-ASIC 環境でも各 ASIC の orchagent が独立して自 ASIC の CONFIG_DB を購読し TC_TO_DSCP_MAP を処理する。クロス namespace 伝播はない。
