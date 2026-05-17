# DASH_VNET — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/dash/dashvnetorch.cpp`
- `sonic-swss/orchagent/dash/dashvnetorch.h`
- `sonic-swss/orchagent/dash/dashorch.h`
- `sonic-swss-common/common/schema.h`
- `sonic-swss/orchagent/crmorch.h`

---

## 発見された定数一覧

### dashorch.h — 結果コード定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `DASH_RESULT_SUCCESS` | `0` | APPL_STATE_DB result table への成功コード書き込み値 | `dashorch.h:35` |
| `DASH_RESULT_FAILURE` | `1` | APPL_STATE_DB result table への失敗コード書き込み値 | `dashorch.h:36` |

### schema.h — APPL_DB テーブル名文字列定数

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `APP_DASH_VNET_TABLE_NAME` | `"DASH_VNET_TABLE"` | ZmqOrch が購読する APPL_DB テーブル名 | `schema.h:172` |
| `APP_DASH_VNET_MAPPING_TABLE_NAME` | `"DASH_VNET_MAPPING_TABLE"` | APPL_DB の VNET マッピングテーブル名 | `schema.h:188` |
| `APP_DASH_APPLIANCE_TABLE_NAME` | `"DASH_APPLIANCE_TABLE"` | appliance entry の存在確認に使われるテーブル名 | `schema.h:185` |
| `APP_DASH_ROUTING_TYPE_TABLE_NAME` | `"DASH_ROUTING_TYPE_TABLE"` | routing type actions の取得に使われるテーブル名 | `schema.h:184` |

### SAI 属性 ID 定数（dashvnetorch.cpp で使用）

| SAI 定数名 | 用途 | ソース |
|-----------|------|--------|
| `SAI_VNET_ATTR_VNI` | VNET 作成時の唯一の SAI 属性（VNI 値を渡す） | `dashvnetorch.cpp:73` |
| `SAI_PA_VALIDATION_ENTRY_ACTION_PERMIT` | PA validation エントリの action 固定値（常に PERMIT） | `dashvnetorch.cpp:475` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_UNDERLAY_DIP` | underlay_ip を SAI に渡す属性 ID | `dashvnetorch.cpp:346` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_DASH_TUNNEL_ID` | tunnel OID を SAI に渡す属性 ID（has_tunnel() 時のみ） | `dashvnetorch.cpp:362` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_METER_CLASS_OR` | metering_class_or を SAI に渡す属性 ID（has_metering_class_or() 時のみ） | `dashvnetorch.cpp:369` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_ACTION` | routing type ごとの action 値（PRIVATELINK 時に使用） | `dashvnetorch.cpp:378` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_DASH_ENCAPSULATION` | encap type（VXLAN/NVGRE）を渡す属性 ID | `dashvnetorch.cpp:382` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_OVERLAY_DIP` | PrivateLink の overlay DIP を渡す属性 ID | `dashvnetorch.cpp:386` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_OVERLAY_DIP_MASK` | PrivateLink の overlay DIP mask を渡す属性 ID | `dashvnetorch.cpp:390` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_OVERLAY_SIP` | PrivateLink の overlay SIP を渡す属性 ID | `dashvnetorch.cpp:394` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_OVERLAY_SIP_MASK` | PrivateLink の overlay SIP mask を渡す属性 ID | `dashvnetorch.cpp:398` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_TUNNEL_KEY` | routing_type_tunnel_key != 0 時に設定するトンネルキー | `dashvnetorch.cpp:404` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_OUTBOUND_PORT_MAP_ID` | PrivateLink の port_map OID を渡す属性 ID | `dashvnetorch.cpp:419` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_OVERLAY_DMAC` | non-PrivateLink の mac_address を渡す属性 ID | `dashvnetorch.cpp:429` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_USE_DST_VNET_VNI` | use_dst_vni フラグを渡す属性 ID | `dashvnetorch.cpp:436` |
| `SAI_OUTBOUND_CA_TO_PA_ENTRY_ACTION_SET_PRIVATE_LINK_MAPPING` | PRIVATELINK routing type の action 固定値 | `dashvnetorch.cpp:379` |
| `SAI_DASH_ENCAPSULATION_VXLAN` | VXLAN encap type の SAI 定数 | `dashvnetorch.cpp:329` |
| `SAI_DASH_ENCAPSULATION_NVGRE` | NVGRE encap type の SAI 定数 | `dashvnetorch.cpp:334` |
| `SAI_DASH_ENCAPSULATION_INVALID` | 不正 encap type の SAI 定数（初期値） | `dashvnetorch.cpp:322` |
| `SAI_STATUS_NOT_EXECUTED` | bulker が未実行の場合のステータス（retry 判定） | `dashvnetorch.cpp:153, 643` |
| `SAI_STATUS_OBJECT_IN_USE` | PA validation 削除時に参照カウントがある場合のステータス | `dashvnetorch.cpp:689` |
| `SAI_STATUS_ITEM_ALREADY_EXISTS` | CA to PA / PA validation の重複作成ステータス（正常扱い） | `dashvnetorch.cpp:512, 547` |
| `SAI_STATUS_ITEM_NOT_FOUND` | CA to PA 削除時に既に存在しない場合のステータス（警告のみ） | `dashvnetorch.cpp:649` |

### CRM リソースタイプ定数（crmorch.h で定義）

| 定数名 | 用途 | ソース |
|--------|------|--------|
| `CRM_DASH_VNET` | VNET 作成/削除時の CRM カウンタ増減 | `crmorch.h:38; dashvnetorch.cpp:103, 164` |
| `CRM_DASH_IPV4_OUTBOUND_CA_TO_PA` | IPv4 CA to PA エントリの CRM カウンタ | `crmorch.h:47; dashvnetorch.cpp:525, 662` |
| `CRM_DASH_IPV6_OUTBOUND_CA_TO_PA` | IPv6 CA to PA エントリの CRM カウンタ | `crmorch.h:48; dashvnetorch.cpp:525, 662` |
| `CRM_DASH_IPV4_PA_VALIDATION` | IPv4 PA validation エントリの CRM カウンタ | `crmorch.h:45; dashvnetorch.cpp:561, 706` |
| `CRM_DASH_IPV6_PA_VALIDATION` | IPv6 PA validation エントリの CRM カウンタ | `crmorch.h:46; dashvnetorch.cpp:561, 706` |

### routing_type 固定値（addOutboundCaToPa 分岐で使用）

| protobuf 定数 | 挙動 | ソース |
|--------------|------|--------|
| `dash::route_type::ROUTING_TYPE_PRIVATELINK` | PrivateLink 専用属性 (overlay DIP/SIP/DMAC 等) を設定するブランチに入る | `dashvnetorch.cpp:374` |
| `dash::route_type::RoutingType::ROUTING_TYPE_UNSPECIFIED` | 旧 action_type フィールドからの移行パスとして routing_type にコピーされる（deprecated 警告） | `dashvnetorch.cpp:771` |
| `dash::route_type::ACTION_TYPE_STATICENCAP` | STATICENCAP action の encap_type 解析 (VXLAN/NVGRE 判定) を行う | `dashvnetorch.cpp:325` |
| `dash::route_type::ENCAP_TYPE_VXLAN` | VXLAN encap を示す protobuf 定数。`SAI_DASH_ENCAPSULATION_VXLAN` に変換 | `dashvnetorch.cpp:328` |
| `dash::route_type::ENCAP_TYPE_NVGRE` | NVGRE encap を示す protobuf 定数。`SAI_DASH_ENCAPSULATION_NVGRE` に変換 | `dashvnetorch.cpp:333` |

---

## 特記事項

1. **PA validation action は常に PERMIT**: `addPaValidation()` では `SAI_PA_VALIDATION_ENTRY_ACTION_PERMIT` が固定で設定される。CONFIG_DB でユーザーが変更する手段は存在しない (`dashvnetorch.cpp:474-475`)。
2. **`DASH_RESULT_SUCCESS/FAILURE` は uint32_t**: `writeResultToDB()` に渡す result 変数は `uint32_t` として宣言される。値は 0 (SUCCESS) / 1 (FAILURE) のみ。
3. **encap_type の初期化が `SAI_DASH_ENCAPSULATION_INVALID`**: `addOutboundCaToPa()` の `encap_type` は `INVALID` で初期化され、STATICENCAP action が見つかった場合にのみ `VXLAN`/`NVGRE` に更新される。他の action type では `INVALID` のまま SAI に渡される可能性がある。
4. **bulker 変数名**: `vnet_bulker_` (ObjectBulker), `outbound_ca_to_pa_bulker_` (EntityBulker), `pa_validation_bulker_` (EntityBulker) の 3 つ。`flush()` の呼び出し順序は `pa_validation_bulker_.flush()` → `vnet_bulker_.flush()` (VNET table 処理時) / `outbound_ca_to_pa_bulker_.flush()` → `pa_validation_bulker_.flush()` (VnetMap table 処理時)。
5. **`gVnetNameToId` はグローバルマップ**: `std::unordered_map<std::string, sai_object_id_t> gVnetNameToId` が `dashvnetorch.cpp:33` でグローバル宣言される。VNET 作成時に `addVnetPost()` で追加、削除時に `removeVnetPost()` で erase される。この変数は VNET_MAPPING_TABLE のルックアップで参照されるため、VNET が存在しない状態での VNET_MAPPING_TABLE SET は `addVnetMap()` L489 で false 返却となる。

---

## 出典

- `sonic-swss/orchagent/dash/dashvnetorch.cpp`: L33, L49-50, L73-74, L103, L153, L164, L195, L253, L280, L283, L306, L322, L325, L328-329, L333-334, L346, L362, L369, L374, L378-379, L382, L386, L390, L394, L398, L404, L419, L429, L436, L442-444, L446, L474-475, L489, L512, L517-522, L525, L543-545, L547, L553-558, L561, L643, L649, L655-660, L662, L689-695, L706, L747, L823, L848, L851, L877, L881
- `sonic-swss/orchagent/dash/dashorch.h`: L35-36
- `sonic-swss/orchagent/crmorch.h`: L38, L45-48
- `sonic-swss-common/common/schema.h`: L172, L184-185, L188
