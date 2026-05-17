# DASH_ROUTING_TYPE — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/dash/dashorch.h`
- `sonic-swss/orchagent/dash/dashorch.cpp`
- `sonic-swss/orchagent/dash/dashvnetorch.cpp`
- `sonic-swss/orchagent/dash/dashrouteorch.cpp`
- `sonic-swss/orchagent/dash/dashtunnelorch.cpp`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dash.yang`

---

## 発見された定数一覧

### dashorch.h — 結果コード定数

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `DASH_RESULT_SUCCESS` | `0` | SET/DEL 成功時に `APP_DASH_ROUTING_TYPE_TABLE_NAME` の `result` フィールドに書き込む値 |
| `DASH_RESULT_FAILURE` | `1` | SET 失敗時（`addRoutingTypeEntry()` が `false` 返却）に result フィールドに書き込む値 |

ソース: `sonic-swss/orchagent/dash/dashorch.h:35-36`

### dashorch.h — FlexCounter 定数（ENI / Meter カウンタ、routing type 間接影響）

| 定数名 | 値 | 用途 |
|--------|-----|------|
| `ENI_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"ENI_STAT_COUNTER"` | ENI stat FlexCounter グループ名 |
| `ENI_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` ms | ENI stat counter ポーリング間隔（10 秒） |
| `METER_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"METER_STAT_COUNTER"` | Meter stat FlexCounter グループ名 |
| `METER_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` ms | Meter stat counter ポーリング間隔（10 秒） |

ソース: `sonic-swss/orchagent/dash/dashorch.h:29-33`

### dashorch.cpp — routing type キー変換定数（ハードコード文字列プレフィックス）

| 変換ルール | 値 | 用途 |
|-----------|-----|------|
| protobuf enum prefix | `"ROUTING_TYPE_"` | APPL_DB キー（小文字）を protobuf enum 名に変換する際に付加するプレフィックス。例: `"vnet_encap"` → `"ROUTING_TYPE_VNET_ENCAP"` |
| 大文字変換 | `std::toupper` による全文字大文字化 | protobuf `RoutingType_Parse()` 前処理 |

ソース: `sonic-swss/orchagent/dash/dashorch.cpp:487-488`

### dashrouteorch.cpp — ROUTING_TYPE → SAI アクション変換マップ（sOutboundAction）

| RoutingType enum 値 | 対応 SAI アクション |
|--------------------|---------------------|
| `ROUTING_TYPE_VNET` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET` |
| `ROUTING_TYPE_VNET_DIRECT` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET_DIRECT` |
| `ROUTING_TYPE_DIRECT` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_DIRECT` |
| `ROUTING_TYPE_DROP` | `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_DROP` |

ソース: `sonic-swss/orchagent/dash/dashrouteorch.cpp:41-47`

### dashvnetorch.cpp / dashtunnelorch.cpp — ENCAP_TYPE 変換定数

| encap_type enum 値 | 対応 SAI 属性 |
|--------------------|---------------|
| `ENCAP_TYPE_VXLAN` | `SAI_DASH_ENCAPSULATION_VXLAN` |
| `ENCAP_TYPE_NVGRE` | `SAI_DASH_ENCAPSULATION_NVGRE` |

ソース: `sonic-swss/orchagent/dash/dashvnetorch.cpp:327-333`, `dashtunnelorch.cpp:289-292`

### YANG — 許容値（pattern constraint）

| フィールド | 許容値一覧 | ソース |
|-----------|-----------|--------|
| `name` (routing type) | `direct`, `vnet`, `vnet_direct`, `vnet_encap`, `drop`, `appliance`, `privatelink`, `privatelinknsg`, `servicetunnel` | `sonic-dash.yang:365` |
| `action_type` | `none`, `maprouting`, `direct`, `staticencap`, `appliance`, `4to6`, `mapdecap`, `decap`, `drop` | `sonic-dash.yang:379` |
| `encap_type` | `vxlan`, `nvgre` | `sonic-dash.yang:385` |
| `vni` | `1..16777215`（24bit VNI 範囲） | `sonic-dash.yang:392` |

### 未マップ routing type（sOutboundAction に含まれない）

以下の routing type は YANG で有効だが `dashrouteorch.cpp:41-47` の `sOutboundAction` マップに含まれない。`DashRouteOrch::addOutboundRouting()` で `sOutboundAction.find()` が失敗し、ルートエントリの SAI プログラミングがスキップされる（または別経路で処理）:

- `ROUTING_TYPE_APPLIANCE`
- `ROUTING_TYPE_PRIVATELINK`
- `ROUTING_TYPE_PRIVATELINKNSG`
- `ROUTING_TYPE_SERVICETUNNEL`

`ROUTING_TYPE_PRIVATELINK` は `dashvnetorch.cpp:374` で専用処理ブランチあり。

---

## 特記事項

1. **routing type はメモリ管理のみ・SAI なし**: `addRoutingTypeEntry()` は SAI API を呼ばず、`routing_type_entries_` マップに格納するだけ。定数は主に参照側 orch（dashvnetorch, dashrouteorch, dashtunnelorch）が使用する。
2. **vni 範囲 YANG constraint**: `1..16777215` は 24bit VNI の全有効範囲（RFC 7348）。`0` は予約（UNSPECIFIED）で拒否される。
3. **ROUTING_TYPE_ プレフィックス変換**: APPL_DB キーと protobuf enum 名の変換は `dashorch.cpp:487-488` でハードコード。キーが `ROUTING_TYPE_` プレフィックスで始まると parse 失敗する（二重付加になる）ため、外部コントローラはプレフィックスなしの小文字名を書き込む必要がある。

---

## 出典

- `sonic-swss/orchagent/dash/dashorch.h` lines 29-36
- `sonic-swss/orchagent/dash/dashorch.cpp` lines 45-46, 73, 487-488
- `sonic-swss/orchagent/dash/dashvnetorch.cpp` lines 322-343, 374
- `sonic-swss/orchagent/dash/dashrouteorch.cpp` lines 41-47
- `sonic-swss/orchagent/dash/dashtunnelorch.cpp` lines 289-292
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dash.yang` lines 356-398
