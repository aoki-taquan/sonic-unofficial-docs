# TC_TO_PRIORITY_GROUP_MAP — プラットフォーム差異調査 (Phase H)

調査日: 2026-05-19
調査対象:
- `sonic-swss/orchagent/qosorch.cpp` (master)
- `sonic-buildimage/files/build_templates/qos_config.j2` (master)

## orchagent 実行時コードパス — プラットフォーム差異

`TcToPgHandler::convertFieldValuesToAttributes()` (`qosorch.cpp:888-900`) および
`TcToPgHandler::addQosItem()` (`qosorch.cpp:905-930`) のいずれにも `gMySwitchType` 参照が存在しない。

`QosOrch::doTask(Consumer&)` (`qosorch.cpp:2254`) および `handlePortQosMapTable()`
(`qosorch.cpp:2046`) にも TC_TO_PRIORITY_GROUP_MAP に関連する platform 分岐はない。

`gMySwitchType == "voq"` 分岐は `applySchedulerToQueueSchedulerGroup()`
(`qosorch.cpp:1637`)・`applyWredProfileToQueue()` (`qosorch.cpp:1715`)・
`applySchedulerToVoqGroup()` (`qosorch.cpp:1772`) にのみ存在し、
TC_TO_PRIORITY_GROUP_MAP 処理パスには適用されない。

全 switch_type（standard / voq / dpu）で同一 SAI 経路
（`sai_qos_map_api->create_qos_map(SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP)`
→ `sai_port_api->set_port_attribute(SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP)`）が実行される。

## 初期設定注入のプラットフォーム差異（qos_config.j2）

`qos_config.j2` は以下の優先順位で TC_TO_PRIORITY_GROUP_MAP を生成する（`qos_config.j2:170-204`）:

### 優先度 1: tunnel_qos_remap_enable + generate_tc_to_pg_map()

プラットフォームが `generate_tc_to_pg_map()` マクロを定義し、かつ
`tunnel_qos_remap_enable` が有効な場合、マクロの出力を使用する。

### 優先度 2: backend_device_types + ComputeAI + generate_tc_to_pg_map()

`DEVICE_METADATA['localhost']['type']` が `backend_device_types` に該当し、
`resource_type == 'ComputeAI'` の場合も `generate_tc_to_pg_map()` マクロを使用する。

### 優先度 3: generate_tc_to_pg_map_per_sku()

上記に該当しないが `generate_tc_to_pg_map_per_sku()` マクロが定義されている場合、
SKU 固有の TC→PG マッピングを使用する。

### 優先度 4: フォールバック（大多数の platform）

上記マクロが未定義の場合、ハードコードされた `AZURE` マップ
（TC 0,1,2,5,6→PG0 / TC3→PG3 / TC4→PG4 / TC7→PG7）を生成する。
`PORT_DPC` 環境では追加で `AZURE_DPC` マップ（TC7→PG7、他は PG0）も生成される。

## プラットフォーム条件まとめ

| プラットフォーム条件 | TC_TO_PRIORITY_GROUP_MAP 生成内容 |
|--------------------|---------------------------------|
| `generate_tc_to_pg_map()` 定義 + `tunnel_qos_remap_enable` | マクロ出力（platform 固有） |
| `backend_device_types` + `resource_type == 'ComputeAI'` + `generate_tc_to_pg_map()` 定義 | マクロ出力（platform 固有） |
| `generate_tc_to_pg_map_per_sku()` 定義 | SKU 固有マクロ出力 |
| `PORT_DPC` 有効（フォールバック） | `AZURE` + `AZURE_DPC` |
| 上記以外（大多数） | `AZURE` のみ |

orchagent のランタイムコードパスは全 platform で共通。
