# TC_TO_DSCP_MAP — Phase H プラットフォーム差異 調査証跡

## 調査対象

`TC_TO_DSCP_MAP` テーブルのプラットフォーム差異。
`QosOrch` 側（qosorch.cpp）にプラットフォーム分岐はないが、ビルド時の qos_config.j2 展開時にプラットフォームごとのマクロ定義有無と値の差が CONFIG_DB の初期内容に直接現れる。

## 調査結果

### A. qosorch.cpp のプラットフォーム分岐

`qosorch.cpp` 内の `TcToDscpMapHandler` / `handleTcToDscpTable` に platform 文字列比較はない。
`SAI_QOS_MAP_TYPE_TC_AND_COLOR_TO_DSCP` は全プラットフォーム共通のハードコード定数（qosorch.cpp:1271）。
SAI capability 照会（`sai_query_attribute_capability`）も行っていないため、プラットフォームに関わらず
CONFIG_DB にエントリが存在すれば SAI QoS map 作成を試みる。

### B. qos_config.j2 のビルド時分岐

`files/build_templates/qos_config.j2:334-337` の条件分岐:

```jinja
{% if (generate_tc_to_dscp_map is defined) and tunnel_qos_remap_enable %}
    {{- generate_tc_to_dscp_map() }}
{% elif (generate_tc_to_dscp_map_per_sku is defined) %}
    {{ generate_tc_to_dscp_map_per_sku() }}
```

- `generate_tc_to_dscp_map` マクロを定義するプラットフォーム: arista, common (th2/7260), mellanox (SN4600C)
- `generate_tc_to_dscp_map_per_sku` マクロを定義するプラットフォーム: arista (7060X6), mellanox (SN5600)
- マクロ非定義プラットフォーム: `TC_TO_DSCP_MAP` テーブル自体が CONFIG_DB に生成されない

### C. `tunnel_qos_remap_enable` フラグ

`SYSTEM_DEFAULTS.tunnel_qos_remap.status == 'enabled'` のときのみ `tunnel_qos_remap_enable = true`。
`generate_tc_to_dscp_map` マクロがあっても `tunnel_qos_remap_enable` が false なら
`generate_tc_to_dscp_map_per_sku` ルートにフォールバックし、それも未定義なら TABLE 非生成。

### D. AZURE_TUNNEL マップの値差異（プラットフォーム別）

| プラットフォーム | マクロ | TC:DSCP マッピング（主要差分） |
|---|---|---|
| th2/7260 BALANCED | generate_tc_to_dscp_map | `0:8, 1:0, 2:0, 3:2, 4:6, 5:46, 6:0, 7:48, 8:33` |
| Arista 7050CX3 BALANCED | generate_tc_to_dscp_map | `0:8, 1:0, 2:0, 3:2, 4:6, 5:46, 6:0, 7:48, 8:33` (同上) |
| Mellanox SN4600C | generate_tc_to_dscp_map | `0:8, 1:0, 2:2, 3:2, 4:6, 5:46, 6:6, 7:48, 8:33` (TC2/6 差分あり) |

Arista 7060X6 (`generate_tc_to_dscp_map_per_sku`) は `AZURE_DOWNLINK_BT1` 等の別マップ名かつ
`DEVICE_METADATA.type` (ToRRouter / LeafRouter) に応じてマップ名を使い分ける。
NVIDIA SN5600 (`generate_tc_to_dscp_map_per_sku`) は `traffic_config.traffic_classification_enable` が
追加ゲートとして存在する。

### E. TC 8..15 の ASIC 実態差

YANG 定義は 0..15 を許可するが、ASIC 対応は 0..7 が標準。TC 8 を定義するプラットフォームは
th2 系（th2/7260、Arista 7050CX3、Mellanox SN4600C など）で、それ以外は TC 0..7 のみ。
TC 8 以上を SAI に投入した場合の動作は ASIC/SAI 実装に依存（task_failed の原因となる）。

### F. multi-asic / VOQ chassis

`QosOrch` は他 orch と同様、namespace ごとに独立インスタンスとして起動する。
`TC_TO_DSCP_MAP` の CONFIG_DB 書き込みは namespace ごとの CONFIG_DB に対して独立に行われる。
qos_config.j2 は namespace 単位で展開されるため、全 asic に同一マップ定義が投入される。
CHASSIS_APP_DB に QoS map 系テーブルは存在しない（chassis-wide 同期なし）。

## Evidence

- `sonic-swss/orchagent/qosorch.cpp:1262-1285` (TcToDscpMapHandler::addQosItem)
- `sonic-buildimage/files/build_templates/qos_config.j2:142-144,334-337`
- `sonic-buildimage/device/common/profiles/th2/7260/BALANCED/qos.json.j2:421-434`
- `sonic-buildimage/device/mellanox/x86_64-mlnx_msn4600c-r0/Mellanox-SN4600C-C64/qos.json.j2:260-272`
- `sonic-buildimage/device/arista/x86_64-arista_7050cx3_32s/Arista-7050CX3-32S-D48C8/BALANCED/qos.json.j2:269-282`
- `sonic-buildimage/device/mellanox/x86_64-nvidia_sn5600-r0/Mellanox-SN5600-C256S1/qos.json.j2:398-416`
- `sonic-buildimage/device/arista/x86_64-arista_7060x6_64pe_b/Arista-7060X6-64PE-B-C448O16/qos.json.j2:176-196`
