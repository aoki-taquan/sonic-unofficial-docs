# DASH_ROUTE_* テーブル — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/dash/dashrouteorch.cpp`
- `sonic-swss/orchagent/dash/dashrouteorch.h`
- `sonic-swss/orchagent/dash/dashorch.h`
- `sonic-swss/orchagent/saihelper.cpp`
- `sonic-swss-common/common/schema.h`

---

## APP_DB テーブル名文字列定数 (`schema.h`)

| 定数名 | 値 | 行 |
|---|---|---|
| `APP_DASH_ROUTE_TABLE_NAME` | `"DASH_ROUTE_TABLE"` | `schema.h:186` |
| `APP_DASH_ROUTE_RULE_TABLE_NAME` | `"DASH_ROUTE_RULE_TABLE"` | `schema.h:187` |
| `APP_DASH_ROUTE_GROUP_TABLE_NAME` | `"DASH_ROUTE_GROUP_TABLE"` | `schema.h:190` |
| `APP_DASH_ENI_ROUTE_TABLE_NAME` | `"DASH_ENI_ROUTE_TABLE"` | `schema.h:189` |

これらは `dashrouteorch.cpp:56-58` のコンストラクタおよび `doTask()` (L904-915) でテーブル名判定に使用される。

---

## 結果コード定数 (`dashorch.h:35-36`)

| 定数名 | 値 | 意味 |
|---|---|---|
| `DASH_RESULT_SUCCESS` | `0` | SET/DEL 操作成功 |
| `DASH_RESULT_FAILURE` | `1` | SAI API 失敗 |

これらは `writeResultToDB()` に `uint32_t res` として渡され、APP_DB 結果テーブルの `"result"` フィールドに文字列化して書き込まれる（`saihelper.cpp:1138`）。

---

## 結果テーブルへの書き込みフィールド (`saihelper.cpp:1138-1143`)

`writeResultToDB()` が結果テーブルに設定するフィールド:

| フィールド名 | 型 | 値 | 条件 |
|---|---|---|---|
| `"result"` | string (数値) | `"0"` (SUCCESS) / `"1"` (FAILURE) | 常時 |
| `"version"` | string | エントリの `version` フィールド値 | `version` が非空の場合のみ（`DASH_ROUTE_GROUP_TABLE` のみ） |

---

## `sOutboundAction` 静的マップ (`dashrouteorch.cpp:41-47`)

アウトバウンドルートの `routing_type` → SAI アクション変換テーブル:

| protobuf RoutingType enum | SAI outbound routing action | 行 |
|---|---|---|
| `ROUTING_TYPE_VNET` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET` | `L43` |
| `ROUTING_TYPE_VNET_DIRECT` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET_DIRECT` | `L44` |
| `ROUTING_TYPE_DIRECT` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_DIRECT` | `L45` |
| `ROUTING_TYPE_DROP` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_DROP` | `L46` |

`ROUTING_TYPE_UNSPECIFIED` (= 0) ・ `servicetunnel` ・ `privatelink` ・ `appliance` 等はこのマップに含まれない → `sOutboundAction.find()` が `end()` を返し `task_failed`。

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

`pa_validation` による アクション定数:
- `pa_validation() == true` → `SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP_PA_VALIDATE`
- `pa_validation() == false` (省略時ゼロ値) → `SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP`

---

## SAI ステータス定数 (`dashrouteorch.cpp`)

| SAI ステータス | 使用箇所 | 挙動 |
|---|---|---|
| `SAI_STATUS_ITEM_ALREADY_EXISTS` | `addOutboundRoutingPost()` L206, `addInboundRoutingPost()` L493 | bulker 再実行 (return false) |
| `SAI_STATUS_NOT_EXECUTED` | `removeOutboundRoutingPost()` L266, `removeInboundRoutingPost()` L550 | bulker 再実行 (return false) |
| `SAI_STATUS_OBJECT_IN_USE` | `removeRouteGroup()` L772 | グループ削除拒否 (return false) |

---

## bulker サイズ定数 (`dashrouteorch.cpp:50-51`)

| グローバル変数 | 型 | 用途 | 定義元 |
|---|---|---|---|
| `gMaxBulkSize` | `size_t` | `outbound_routing_bulker_` / `inbound_routing_bulker_` の最大バルクサイズ | `orchdaemon.cpp` |

バルクサイズは外部グローバルから受け取るため、`dashrouteorch.cpp` 内にハードコードなし。

---

## `route_group_bind_count_` — バインドカウンタ (`dashrouteorch.h:72`)

| 変数名 | 型 | 意味 |
|---|---|---|
| `route_group_bind_count_` | `unordered_map<string, int>` | route_group_id → ENI バインド数カウンタ |

`bindRouteGroup()` でインクリメント、`unbindRouteGroup()` でデクリメント。カウントが 0 超のときは `isRouteGroupBound()` が `true` を返し、SET/DEL 操作を制限する。数値ゼロに相当するハードコード定数はなく、`0` との比較が直接コーディングされている。
