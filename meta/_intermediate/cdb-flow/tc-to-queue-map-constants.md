# TC_TO_QUEUE_MAP — ハードコード定数抽出 (Phase E)

ソース: `sonic-swss/orchagent/qosorch.cpp`、`sonic-swss/orchagent/qosorch.h`

## TC / queue インデックス範囲

- TC 有効範囲: `0`〜`7`（YANG `tc_type` typedef 制約、`stoi()` キャストのみで上限チェックなし）
- queue インデックス有効範囲: YANG は `0..9` を pattern で制約するが実装 (`stoi()`) は上限チェックを行わない。実際の上限はプラットフォームの物理キュー数（典型値 8〜12）に依存

## デフォルトマップ名

- `"AZURE"`: `qos_config.j2` フォールバック（恒等写像 TC 0-7 → queue 0-7）
- `"AZURE_UPLINK"`: `tunnel_qos_remap_enable=true` かつ `generate_tc_to_queue_map` 定義ありの場合

## SAI ハードコード定数

```cpp
// addQosItem() L457-458 (qosorch.cpp)
qos_map_attr.id = SAI_QOS_MAP_ATTR_TYPE;
qos_map_attr.value.s32 = SAI_QOS_MAP_TYPE_TC_TO_QUEUE;  // ハードコード固定

// PORT_QOS_MAP バインド (L64)
{tc_to_queue_field_name, SAI_PORT_ATTR_QOS_TC_TO_QUEUE_MAP}
```

## フィールド名定数 (qosorch.h L19, L36)

```cpp
const string tc_to_queue_field_name          = "tc_to_queue_map";
const string encap_tc_to_queue_field_name    = "encap_tc_to_queue_map";
```

## ハンドラ登録定数 (qosorch.cpp L1332)

```cpp
m_qos_handler_map.insert(
    qos_handler_pair(CFG_TC_TO_QUEUE_MAP_TABLE_NAME, &QosOrch::handleTcToQueueTable));
// CFG_TC_TO_QUEUE_MAP_TABLE_NAME = "TC_TO_QUEUE_MAP" (swsscommon)
```

## デフォルト恒等写像 (AZURE)

```json
"TC_TO_QUEUE_MAP": {
  "AZURE": {
    "0": "0", "1": "1", "2": "2", "3": "3",
    "4": "4", "5": "5", "6": "6", "7": "7"
  }
}
```

出典: `sonic-utilities/tests/qos_config_input/config_qos.json`

## 注記

- `convertFieldValuesToAttributes()` では `stoi()` の例外は try-catch されていないため、非数値フィールドは unhandled exception になる（`handleQosMap` のラッパーで catch している）
- SAI map type は `TcToQueueMapHandler::addQosItem()` にハードコードされており、テーブル名からの動的解決ではない
