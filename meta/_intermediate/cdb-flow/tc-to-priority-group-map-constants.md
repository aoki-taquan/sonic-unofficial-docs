# TC_TO_PRIORITY_GROUP_MAP — ハードコード定数調査 (Phase E)

調査対象: `sonic-swss/orchagent/qosorch.cpp`, `sonic-swss/orchagent/qosorch.h`, `sonic-swss-common/common/schema.h`

## フィールド名文字列定数 (`qosorch.h`)

| 定数名 | 値 | 用途 | 行 |
|---|---|---|---|
| `tc_to_pg_map_field_name` | `"tc_to_pg_map"` | PORT_QOS_MAP での参照フィールド名 | `qosorch.h:18` |
| `decap_tc_to_pg_field_name` | `"decap_tc_to_pg_map"` | TUNNEL_DECAP_TABLE での参照フィールド名 | `qosorch.h:35` |
| `pfc_to_pg_map_name` | `"pfc_to_pg_map"` | 隣接する PFC_TO_PG_MAP のフィールド名（参考） | `qosorch.h:14` |

## テーブル名定数

`CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME` は swsscommon の Python binding で使用される文字列定数。
CONFIG_DB テーブル名は `"TC_TO_PRIORITY_GROUP_MAP"` として固定（YANG モデルおよびコード内で一致）。

`APP_TC_TO_PRIORITY_GROUP_MAP_NAME` = `"TC_TO_PRIORITY_GROUP_MAP_TABLE"` (schema.h:213) は APPL_DB 用だが TC_TO_PRIORITY_GROUP_MAP は APPL_DB に書き込まれないため未使用。

## SAI 属性 ID 定数

| 定数名 | 値 (enum) | 用途 | ソース |
|---|---|---|---|
| `SAI_QOS_MAP_TYPE_TC_TO_PRIORITY_GROUP` | SAI enum値 | map 作成時の type 指定 | `qosorch.cpp:913` |
| `SAI_QOS_MAP_ATTR_TYPE` | SAI enum値 | map type 属性 ID | `qosorch.cpp:912` |
| `SAI_QOS_MAP_ATTR_MAP_TO_VALUE_LIST` | SAI enum値 | TC→PG エントリリスト属性 ID | `qosorch.cpp:897, 915` |
| `SAI_PORT_ATTR_QOS_TC_TO_PRIORITY_GROUP_MAP` | SAI enum値 | ポートへのマップ適用属性 ID | `qosorch.cpp:67` |
| `SAI_NULL_OBJECT_ID` | 0 (またはハードウェア依存) | DEL/未解決時のデフォルト OID | 汎用 |

## tc / pg の型制約（コード固定）

| フィールド | C++ 型 | 変換方法 | コード上の制約 |
|---|---|---|---|
| `tc`（key の第2トークン） | `uint8_t` | `stoi(fvField(*i))` キャスト | 0..255 だが YANG では `uint8 0..15`（実用 0..7） |
| `pg`（value） | `uint8_t` | `stoi(fvValue(*i))` キャスト | 0..255 だが YANG pattern `[0-7]?` |

`stoi()` の返り値は `int` で、`uint8_t` へのキャストは暗黙の型変換（値が 0..255 範囲外でも UB にはならないが、ASIC が拒否する可能性がある）。

## ビルド時デフォルト定数 (`qos_config.j2`)

AZURE 標準マッピング（sonic-buildimage `files/build_templates/qos_config.j2`）:

| TC | PG | 備考 |
|---|---|---|
| 0, 1, 2, 5, 6 | 0 | Best-effort |
| 3 | 3 | Lossless / PFC 対象 |
| 4 | 4 | Lossless / PFC 対象 |
| 7 | 7 | High-priority control |

マップ名: `"AZURE"`（固定文字列）

PORT_DPC 有効環境では追加マップ `"AZURE_DPC"` が生成される（TC7→PG7 のみ、他は PG0）。

## orchdaemon 登録

`orchdaemon.cpp:376` でテーブル名が Consumer の subscribe リストに直接渡される。登録は `QosOrch` コンストラクタ内の `m_qos_handler_map` で `CFG_TC_TO_PRIORITY_GROUP_MAP_TABLE_NAME → &QosOrch::handleTcToPgTable` として固定。

## 変更可能性

上記定数はすべてコードにハードコードされており、CONFIG_DB や環境変数で変更不可。SAI type, port/tunnel SAI 属性 ID はすべてコンパイル時定数。
