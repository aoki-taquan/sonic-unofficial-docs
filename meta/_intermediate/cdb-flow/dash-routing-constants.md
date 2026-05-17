# DASH_ROUTING_TYPE_TABLE / DASH_ROUTE_* — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/dash/dashorch.cpp`
- `sonic-swss/orchagent/dash/dashorch.h`
- `sonic-swss/orchagent/dash/dashrouteorch.cpp`
- `sonic-swss/orchagent/dash/dashrouteorch.h`
- `sonic-swss-common/common/schema.h`

---

## APP_DB テーブル名文字列定数 (`schema.h`)

| 定数名 | 値 | 行 |
|---|---|---|
| `APP_DASH_ROUTING_TYPE_TABLE_NAME` | `"DASH_ROUTING_TYPE_TABLE"` | `schema.h:184` |
| `APP_DASH_ROUTE_TABLE_NAME` | `"DASH_ROUTE_TABLE"` | `schema.h:186` |
| `APP_DASH_ROUTE_RULE_TABLE_NAME` | `"DASH_ROUTE_RULE_TABLE"` | `schema.h:187` |
| `APP_DASH_ROUTE_GROUP_TABLE_NAME` | `"DASH_ROUTE_GROUP_TABLE"` | `schema.h:190` |
| `APP_DASH_ENI_ROUTE_TABLE_NAME` | `"DASH_ENI_ROUTE_TABLE"` | `schema.h:189` |

- `APP_DASH_ROUTING_TYPE_TABLE_NAME` は `dashorch.cpp:73` のコンストラクタで APP_STATE_DB 結果テーブル作成に使用、`dashorch.cpp:1346` で `doTask()` テーブル名判定に使用。
- `APP_DASH_ROUTE_*` 定数は `dashrouteorch.cpp:56-58` コンストラクタおよび `dashrouteorch.cpp:904-912` の `doTask()` で使用。

---

## 結果コード定数 (`dashorch.h:35-36`)

| 定数名 | 値 | 意味 |
|---|---|---|
| `DASH_RESULT_SUCCESS` | `0` | SET/DEL 操作成功 |
| `DASH_RESULT_FAILURE` | `1` | SAI API 失敗 |

- `DASH_ROUTING_TYPE_TABLE` の処理で `dashorch.cpp:397`, `416`, `485`, `514` にて結果変数 `result` に代入される。
- `writeResultToDB()` で APP_STATE_DB 結果テーブルの `"result"` フィールドに文字列化して書き込まれる。

---

## キー正規化定数 (`dashorch.cpp:487-488`)

DASH_ROUTING_TYPE_TABLE のキー処理に、以下のハードコード変換が存在する:

```cpp
std::transform(routing_type_str.begin(), routing_type_str.end(),
               routing_type_str.begin(), ::toupper);   // 全大文字化
routing_type_str = "ROUTING_TYPE_" + routing_type_str; // プレフィックス付与
```

- APP_DB のキー（例: `"vnet"`, `"direct"`）を大文字化したうえで `"ROUTING_TYPE_"` プレフィックスを付与し、protobuf の `RoutingType` enum へ変換する。
- 文字列変換に失敗した場合は `SWSS_LOG_WARN` を出力してエントリを廃棄（`return true`）。

---

## `sOutboundAction` 静的マップ (`dashrouteorch.cpp:41-47`)

アウトバウンドルートの `routing_type` → SAI アクション変換テーブル:

| protobuf RoutingType enum | SAI outbound routing action |
|---|---|
| `ROUTING_TYPE_VNET` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET` |
| `ROUTING_TYPE_VNET_DIRECT` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET_DIRECT` |
| `ROUTING_TYPE_DIRECT` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_DIRECT` |
| `ROUTING_TYPE_DROP` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_DROP` |

`ROUTING_TYPE_UNSPECIFIED` (= 0) およびその他の enum 値はこのマップに含まれないため、`sOutboundAction.find()` が `end()` を返し `task_failed` となる。

---

## SAI 属性 ID 定数 — アウトバウンドルート (`dashrouteorch.cpp`)

| SAI 属性 ID | 対応フィールド | 行 |
|---|---|---|
| `SAI_OUTBOUND_ROUTING_ENTRY_ATTR_ACTION` | `routing_type` → `sOutboundAction` 変換値 | `L110` |
| `SAI_OUTBOUND_ROUTING_ENTRY_ATTR_DST_VNET_ID` | `vnet` (vnet / vnet_direct 両方) | `L122`, `L131` |
| `SAI_OUTBOUND_ROUTING_ENTRY_ATTR_OVERLAY_IP` | `overlay_ip` (vnet_direct のみ) | `L135` |
| `SAI_OUTBOUND_ROUTING_ENTRY_ATTR_UNDERLAY_SIP` | `underlay_sip` (has_underlay_sip() guard) | `L151` |
| `SAI_OUTBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_OR` | `metering_class_or` (has_ guard) | `L160` |
| `SAI_OUTBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_AND` | `metering_class_and` (has_ guard) | `L166` |
| `SAI_OUTBOUND_ROUTING_ENTRY_ATTR_DASH_TUNNEL_ID` | `tunnel` (has_tunnel() guard) | `L180` |

---

## SAI 属性 ID 定数 — インバウンドルート (`dashrouteorch.cpp`)

| SAI 属性 ID | 対応フィールド / 値 | 行 |
|---|---|---|
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_ACTION` | `pa_validation` → `TUNNEL_DECAP_PA_VALIDATE` / `TUNNEL_DECAP` | `L449-450` |
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_SRC_VNET_ID` | `vnet` (has_vnet() guard) | `L455` |
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_OR` | `metering_class_or` (has_ guard) | `L461` |
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_AND` | `metering_class_and` (has_ guard) | `L467` |

`pa_validation` による SAI アクション定数:
- `pa_validation() == true` → `SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP_PA_VALIDATE`
- `pa_validation() == false` (省略時ゼロ値) → `SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP`

---

## バルクサイズ定数 (`dashrouteorch.cpp:50-51`)

| グローバル変数 | 型 | 用途 | 定義元 |
|---|---|---|---|
| `gMaxBulkSize` | `size_t` | `outbound_routing_bulker_` / `inbound_routing_bulker_` の最大バルクサイズ | `orchdaemon.cpp` |

`dashrouteorch.cpp` 内にハードコードなし。外部グローバル変数から受け取る。

---

## `route_group_bind_count_` — バインドカウンタ (`dashrouteorch.h`)

| 変数名 | 型 | 意味 |
|---|---|---|
| `route_group_bind_count_` | `unordered_map<string, int>` | route_group_id → ENI バインド数カウンタ |

`bindRouteGroup()` でインクリメント、`unbindRouteGroup()` でデクリメント。カウントが 0 超のとき `isRouteGroupBound()` が `true` を返し SET/DEL 操作を制限する。数値ゼロとの比較は直接コーディングされており、ハードコード定数名はなし。
