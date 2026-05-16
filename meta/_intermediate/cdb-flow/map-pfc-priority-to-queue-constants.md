# map-pfc-priority-to-queue — Phase E ハードコード定数

ソース: `sonic-swss/orchagent/qosorch.cpp` / `qosorch.h` / `sonic-swss-common/common/schema.h`

## テーブル名定数

| 定数名 | 値 | ソース |
|---|---|---|
| `CFG_PFC_PRIORITY_TO_QUEUE_MAP_TABLE_NAME` | `"MAP_PFC_PRIORITY_TO_QUEUE"` | `sonic-swss-common/common/schema.h:363` |

## フィールド名定数 (PORT_QOS_MAP 側バインドキー)

| 定数名 | 値 | 用途 |
|---|---|---|
| `pfc_to_queue_map_name` | `"pfc_to_queue_map"` | `PORT_QOS_MAP` の field 名、MAP_PFC_PRIORITY_TO_QUEUE マップ名を参照する | 

ソース: `sonic-swss/orchagent/qosorch.h:15`

## SAI qos_map_type 定数

| 定数名 | 用途 | ソース |
|---|---|---|
| `SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_QUEUE` | `addQosItem()` で `SAI_QOS_MAP_ATTR_TYPE` に設定される SAI map type | `qosorch.cpp:1021` |
| `SAI_QOS_MAP_ATTR_TYPE` | SAI attribute ID (map type 指定) | `qosorch.cpp:1020` |
| `SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` | SAI attribute ID (map list 指定) | `qosorch.cpp:1004,1024` |
| `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_QUEUE_MAP` | PORT_QOS_MAP バインド時の SAI port attribute | `qosorch.cpp:69` |

## 値域ハードコード

| 対象フィールド | 範囲 | 型変換 | ソース |
|---|---|---|---|
| `pfc_priority` (key フィールド) | 0..7 (YANG `pattern "[0-7]?"`) | `(uint8_t)stoi(fvField(*i))` | `qosorch.cpp:1001` |
| `qindex` (value フィールド) | 0..7 (YANG `pattern "[0-7]?"`) | `(uint8_t)stoi(fvValue(*i))` | `qosorch.cpp:1002` |
| SAI `key.prio` | uint8_t (0..255) — YANG が 0..7 を保証 | キャスト後 SAI へ | `qosorch.cpp:1001` |
| SAI `value.queue_index` | uint8_t (0..255) — YANG が 0..7 を保証 | キャスト後 SAI へ | `qosorch.cpp:1002` |

## SAI API

| 関数 | 用途 | ソース |
|---|---|---|
| `sai_qos_map_api->create_qos_map()` | MAP 作成 (`addQosItem`) | `qosorch.cpp:1029` |
| `sai_qos_map_api->set_qos_map_attribute()` | MAP 更新 (既存 SET) | `qosorch.cpp:207` |
| `sai_qos_map_api->remove_qos_map()` | MAP 削除 (DEL) | `qosorch.cpp:220` |

## 補足: 暗黙キャストの注意

`stoi()` 結果を `(uint8_t)` に無検証キャストするため、YANG バリデーションをバイパスして 8 以上の値を書き込んだ場合は値が 0..255 の範囲で切り捨てのみ（mod 256 ではなくビットマスク）。通常は YANG が 0..7 に制限するため問題ない。
