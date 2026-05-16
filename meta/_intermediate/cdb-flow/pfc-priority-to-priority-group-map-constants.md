# Phase E: Constants — PFC_PRIORITY_TO_PRIORITY_GROUP_MAP

調査対象: `sonic-swss/orchagent/qosorch.cpp`, `sonic-swss/orchagent/qosorch.h`, `sonic-swss-common/common/schema.h`

## テーブル名定数

`schema.h:214` に APPL_DB 側定数が存在する。CONFIG_DB 購読用マクロ
`CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME` はキャッシュ済みソース内に `#define` が見当たらないが、
実値は `"PFC_PRIORITY_TO_PRIORITY_GROUP_MAP"` と `orchdaemon.cpp:377` / `qosorch.cpp:90,107,1343` 利用箇所から確定できる。

| 定数名 | 値 | evidence |
|---|---|---|
| `APP_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_NAME` | `"PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE"` | `sonic-swss-common/common/schema.h:214` |
| `CFG_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP_TABLE_NAME` | `"PFC_PRIORITY_TO_PRIORITY_GROUP_MAP"` (実値) | `sonic-swss/orchagent/qosorch.cpp:90,107,1343` |

## フィールド名定数

| 定数名 | 値 | 用途 | evidence |
|---|---|---|---|
| `pfc_to_pg_map_name` | `"pfc_to_pg_map"` | `PORT_QOS_MAP` テーブル内で PFC_PRIORITY_TO_PRIORITY_GROUP_MAP 名を参照する field 名 | `sonic-swss/orchagent/qosorch.h:14` |

## SAI qos_map_type 定数

| 定数名 | 用途 | evidence |
|---|---|---|
| `SAI_QOS_MAP_TYPE_PFC_PRIORITY_TO_PRIORITY_GROUP` | `addQosItem()` で `SAI_QOS_MAP_ATTR_TYPE` に設定される SAI map type | `qosorch.cpp:966` |
| `SAI_QOS_MAP_ATTR_TYPE` | SAI attribute ID — map type を指定 | `qosorch.cpp:965` |
| `SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` | SAI attribute ID — pfc_priority→pg ペアのリストを渡す | `qosorch.cpp:950,969` |
| `SAI_PORT_ATTR_QOS_PFC_PRIORITY_TO_PRIORITY_GROUP_MAP` | PORT_QOS_MAP バインド時の SAI port attribute | `qosorch.cpp:68` |

## 値域ハードコード

- `pfc_priority` (key): 0..7（YANG `pattern "[0-7]?"` が保証）、`(uint8_t)stoi(fvField(*i))` で変換 (`qosorch.cpp:947`)
- `pg` (value): 0..7（同 YANG `pattern "[0-7]?"` が保証）、`(uint8_t)stoi(fvValue(*i))` で変換 (`qosorch.cpp:948`)
- エントリ数: CONFIG_DB に登録されたフィールド数ぶん動的に `pfc_prio_to_pg_map_list.count` に入る（上限は SAI 実装依存）

YANG バリデーションをバイパスして 8 以上を書き込んだ場合は `(uint8_t)` キャストで wrap するが SAI 側でエラーになる可能性がある。

## SAI API

| 関数 | 用途 | evidence |
|---|---|---|
| `sai_qos_map_api->create_qos_map()` | MAP 新規作成 | `qosorch.cpp:974` |
| `sai_qos_map_api->set_qos_map_attribute()` | 既存 MAP 更新 | `qosorch.cpp:153` |
| `sai_qos_map_api->remove_qos_map()` | MAP 削除 | `qosorch.cpp:190` |
