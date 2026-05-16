# DASH Routing テーブル群 フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル:
- `DASH_ROUTING_TYPE_TABLE` (APP_DB)
- `DASH_ROUTE_TABLE` (APP_DB — Outbound LPM ルート)
- `DASH_ROUTE_RULE_TABLE` (APP_DB — Inbound ルートルール)
- `DASH_ROUTE_GROUP_TABLE` (APP_DB — ルートグループ)

---

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashrouteorch.cpp` (`DashRouteOrch::addOutboundRouting`, `addInboundRouting`, `addRouteGroup`, etc.)
- `sonic-swss/orchagent/dash/dashrouteorch.h` (`OutboundRoutingBulkContext`, `InboundRoutingBulkContext`)
- `sonic-swss/orchagent/dash/dashorch.cpp` (`DashOrch::addRoutingTypeEntry`, `doTaskRoutingTypeTable`)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dash.yang` (YANG: `DASH_ROUTING_TYPE`, `DASH_ROUTE_TABLE`, `DASH_VNET_MAPPING_TABLE`)
- `sonic-swss-common/common/schema.h` (テーブル名定数)
- `sonic-buildimage/src/sonic-yang-models/tests/yang_model_tests/tests_config/dash.json` (テスト設定例)

---

## 1. DASH_ROUTING_TYPE_TABLE

### テーブルキー

```
DASH_ROUTING_TYPE_TABLE:<routing_type_name>
```

`routing_type_name` は YANG パターン `direct|vnet|vnet_direct|vnet_encap|drop|appliance|privatelink|privatelinknsg|servicetunnel` の一つ。`dashorch.cpp` は uppercase に変換して `ROUTING_TYPE_` prefix を付けてから protobuf enum `RoutingType` に parse する。

### フィールド暗黙デフォルト

#### `action_name`

**コード由来デフォルト**: protobuf field — 未設定時空文字列

YANG では `length 1..255` だが protobuf (dash_api/route_type.pb) では optional string。`addRoutingTypeEntry()` はエントリをそのまま `routing_type_entries_[routing_type] = entry` に格納するだけで、`action_name` の存在確認はしない。SAI API 呼び出しに直接は使用されない (VNET mapping orchagent が参照する)。

#### `action_type`

**コード由来デフォルト**: proto3 enum 0 = `ACTION_TYPE_UNSPECIFIED`

`dashvnetorch.cpp` が `addOutboundCaToPaEntry()` でこの値を参照。
```cpp
// dashvnetorch.cpp
if (action.action_type() == dash::route_type::ACTION_TYPE_STATICENCAP)
{
    if (action.encap_type() == dash::route_type::ENCAP_TYPE_VXLAN)
        encap_type = SAI_DASH_ENCAPSULATION_VXLAN;
    else if (action.encap_type() == dash::route_type::ENCAP_TYPE_NVGRE)
        encap_type = SAI_DASH_ENCAPSULATION_NVGRE;
    else
        SWSS_LOG_ERROR("Invalid encap type ...");
}
```
`ACTION_TYPE_STATICENCAP` 以外の場合は `encap_type` が `SAI_DASH_ENCAPSULATION_INVALID` のままになる。

#### `encap_type`

**コード由来デフォルト**: proto3 enum 0 = `ENCAP_TYPE_INVALID`

`action_type = ACTION_TYPE_STATICENCAP` のときのみ参照される。省略時は `SAI_DASH_ENCAPSULATION_INVALID` となり、SAI 属性を push する際にエラーになる可能性がある。YANG では `vxlan|nvgre` の pattern のみ許可。

#### `vni`

**コード由来デフォルト**: proto3 uint32 デフォルト = 0

`ACTION_TYPE_STATICENCAP` 時のみ参照。`routing_type_tunnel_key` に格納され、0 でない場合のみ `SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_TUNNEL_KEY` として push される。
```cpp
// dashvnetorch.cpp
if (routing_type_tunnel_key != 0)
{
    outbound_ca_to_pa_attr.id = SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_TUNNEL_KEY;
    outbound_ca_to_pa_attr.value.u32 = routing_type_tunnel_key;
    outbound_ca_to_pa_attrs.push_back(outbound_ca_to_pa_attr);
}
```
VNI が 0 の場合は TUNNEL_KEY を SAI に設定しない。

### 要約表

| フィールド | 必須/任意 | コード由来デフォルト | fallback 源 |
|-----------|---------|-------------------|------------|
| `action_name` | 任意 | 空文字列 | proto3 string default; dashorch.cpp は存在確認せずそのまま格納 |
| `action_type` | 任意 | `ACTION_TYPE_UNSPECIFIED` (proto3 enum 0) | dashvnetorch.cpp: STATICENCAP 以外は encap_type 未設定 |
| `encap_type` | 条件付き必須 | `ENCAP_TYPE_INVALID` (proto3 enum 0) | action_type=STATICENCAP 時のみ参照; 不正値は SWSS_LOG_ERROR |
| `vni` | 任意 | 0 | vni==0 時は TUNNEL_KEY を SAI に push しない — dashvnetorch.cpp |

---

## 2. DASH_ROUTE_TABLE (Outbound LPM Route)

### テーブルキー

```
DASH_ROUTE_TABLE:<route_group>:<ip_prefix>
```

`DashRouteOrch::doTaskRouteTable()` が `route_group` と `ip_prefix` をコロン区切りで解析。メッセージは protobuf `dash::route::Route` 形式。

### フィールド暗黙デフォルト

#### `routing_type` (旧: `action_type`)

**コード由来デフォルト**: `ROUTING_TYPE_UNSPECIFIED` (proto3 enum 0)

`ROUTING_TYPE_UNSPECIFIED` の場合、deprecated な `action_type` フィールドからコピーする backward-compat コードがある:
```cpp
// dashrouteorch.cpp:326-334
if (ctxt.metadata.routing_type() == dash::route_type::RoutingType::ROUTING_TYPE_UNSPECIFIED)
{
    ctxt.metadata.set_routing_type(ctxt.metadata.action_type());
}
```
`action_type` も `UNSPECIFIED` の場合、後続の `sOutboundAction.find()` で miss → `SWSS_LOG_WARN` + return false (エントリはリトライキューに戻る)。

有効なマッピング (`sOutboundAction` 静的テーブル):
- `ROUTING_TYPE_VNET` → `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET`
- `ROUTING_TYPE_VNET_DIRECT` → `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET_DIRECT`
- `ROUTING_TYPE_DIRECT` → `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_DIRECT`
- `ROUTING_TYPE_DROP` → `SAI_OUTBOUND_ROUTING_ENTRY_ACTION_DROP`

#### `vnet` (for ROUTING_TYPE_VNET)

**コード由来デフォルト**: 必須 (ROUTING_TYPE_VNET 時)

```cpp
// dashrouteorch.cpp:118-125
else if (ctxt.metadata.routing_type() == dash::route_type::RoutingType::ROUTING_TYPE_VNET
    && ctxt.metadata.has_vnet()
    && !ctxt.metadata.vnet().empty())
{
    outbound_routing_attr.id = SAI_OUTBOUND_ROUTING_ENTRY_ATTR_DST_VNET_ID;
    outbound_routing_attr.value.oid = gVnetNameToId[ctxt.metadata.vnet()];
}
```
`has_vnet()` が false または vnet が空の場合、上記 else-if に入らず else ブランチに落ち `SWSS_LOG_WARN` + return false。

#### `vnet_direct.vnet` / `vnet_direct.overlay_ip` (for ROUTING_TYPE_VNET_DIRECT)

**コード由来デフォルト**: 両方必須 (ROUTING_TYPE_VNET_DIRECT 時)

```cpp
// dashrouteorch.cpp:126-141
else if (ctxt.metadata.routing_type() == dash::route_type::RoutingType::ROUTING_TYPE_VNET_DIRECT
    && ctxt.metadata.has_vnet_direct()
    && !ctxt.metadata.vnet_direct().vnet().empty()
    && (ctxt.metadata.vnet_direct().overlay_ip().has_ipv4() || ctxt.metadata.vnet_direct().overlay_ip().has_ipv6()))
{
    // ...SAI属性をpush
}
```
`vnet_direct` が未設定、vnet が空、または overlay_ip が未設定の場合は else に落ち return false。

#### `underlay_sip`

**コード由来デフォルト**: なし (SAI 未設定) — 任意フィールド

```cpp
// dashrouteorch.cpp:149-157
if (ctxt.metadata.has_underlay_sip() && ctxt.metadata.underlay_sip().has_ipv4())
{
    outbound_routing_attr.id = SAI_OUTBOUND_ROUTING_ENTRY_ATTR_UNDERLAY_SIP;
    to_sai(...);
    outbound_routing_attrs.push_back(outbound_routing_attr);
}
```
`has_underlay_sip()` が false または IPv4 でない場合は SAI 属性を push しない。

#### `metering_class_or` / `metering_class_and`

**コード由来デフォルト**: なし (SAI 未設定) — 任意フィールド

```cpp
// dashrouteorch.cpp:159-169
if (ctxt.metadata.has_metering_class_or()) {
    outbound_routing_attr.id = SAI_OUTBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_OR;
    outbound_routing_attr.value.u32 = ctxt.metadata.metering_class_or();
    outbound_routing_attrs.push_back(outbound_routing_attr);
}
if (ctxt.metadata.has_metering_class_and()) {
    outbound_routing_attr.id = SAI_OUTBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_AND;
    outbound_routing_attr.value.u32 = ctxt.metadata.metering_class_and();
    outbound_routing_attrs.push_back(outbound_routing_attr);
}
```
`has_*()` false の場合は SAI 属性を push しない。SAI デフォルトに依存。

#### `tunnel`

**コード由来デフォルト**: なし (SAI 未設定) — 任意フィールド

```cpp
// dashrouteorch.cpp:171-183
if (ctxt.metadata.has_tunnel())
{
    sai_object_id_t tunnel_oid = dash_tunnel_orch->getTunnelOid(ctxt.metadata.tunnel());
    if (tunnel_oid == SAI_NULL_OBJECT_ID)
    {
        SWSS_LOG_INFO("Retry as tunnel %s not found", ...);
        return false;
    }
    outbound_routing_attr.id = SAI_OUTBOUND_ROUTING_ENTRY_ATTR_DASH_TUNNEL_ID;
}
```
`tunnel` が設定されている場合は `DashTunnelOrch` から OID を取得。未登録の場合はリトライ。省略時は SAI に tunnel 属性を設定しない。

### 要約表

| フィールド | 必須/任意 | コード由来デフォルト | fallback 源 |
|-----------|---------|-------------------|------------|
| `routing_type` | 必須 | `ROUTING_TYPE_UNSPECIFIED` (proto3 enum 0) → return false | sOutboundAction miss → SWSS_LOG_WARN; UNSPECIFIED 時は action_type からコピー試行 |
| `vnet` | 条件付き必須 | なし | ROUTING_TYPE_VNET 時: has_vnet() false → else ブランチで return false |
| `vnet_direct.vnet` / `overlay_ip` | 条件付き必須 | なし | ROUTING_TYPE_VNET_DIRECT 時: 欠けると return false |
| `underlay_sip` | 任意 | なし (SAI 未設定) | has_underlay_sip() && has_ipv4() false → スキップ — dashrouteorch.cpp:149 |
| `metering_class_or` | 任意 | なし (SAI 未設定) | has_metering_class_or() false → スキップ — dashrouteorch.cpp:159 |
| `metering_class_and` | 任意 | なし (SAI 未設定) | has_metering_class_and() false → スキップ — dashrouteorch.cpp:165 |
| `tunnel` | 任意 | なし (SAI 未設定) | has_tunnel() false → スキップ; 未登録 OID → リトライ — dashrouteorch.cpp:171 |

---

## 3. DASH_ROUTE_RULE_TABLE (Inbound Route Rule)

### テーブルキー

```
DASH_ROUTE_RULE_TABLE:<eni>:<vni>:<ip_prefix>:<priority>
```

`priority` フィールドはキーの末尾に追加された。旧キー形式 (`priority` なし) は backward-compat として `priority = 0` にデフォルト:
```cpp
// dashrouteorch.cpp:605-623
priority = 0;
// ...
string maybe_priority = prefix_and_optional_priority.substr(last_colon + 1);
bool is_priority = !maybe_priority.empty() && all_of(...isdigit...);
if (is_priority)
{
    priority = to_uint<uint32_t>(maybe_priority);
}
```

メッセージは protobuf `dash::route_rule::RouteRule` 形式。

### フィールド暗黙デフォルト

#### `pa_validation`

**コード由来デフォルト**: `false` (proto3 bool デフォルト)

```cpp
// dashrouteorch.cpp:450
inbound_routing_attr.id = SAI_INBOUND_ROUTING_ENTRY_ATTR_ACTION;
inbound_routing_attr.value.u32 = ctxt.metadata.pa_validation() ?
    SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP_PA_VALIDATE :
    SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP;
```
`pa_validation` が false (proto3 デフォルト) の場合は `TUNNEL_DECAP` が SAI action として設定される。明示的に `true` を設定しないと PA validation は行われない。

#### `vnet`

**コード由来デフォルト**: なし (SAI 未設定) — 任意フィールド

```cpp
// dashrouteorch.cpp:453-458
if (ctxt.metadata.has_vnet())
{
    inbound_routing_attr.id = SAI_INBOUND_ROUTING_ENTRY_ATTR_SRC_VNET_ID;
    inbound_routing_attr.value.oid = gVnetNameToId[ctxt.metadata.vnet()];
}
```
`has_vnet()` が false の場合は `SRC_VNET_ID` を SAI に設定しない。

#### `metering_class_or` / `metering_class_and`

**コード由来デフォルト**: なし (SAI 未設定) — 任意フィールド

Outbound routing と同じパターン:
```cpp
// dashrouteorch.cpp:460-470
if (ctxt.metadata.has_metering_class_or()) { ... }
if (ctxt.metadata.has_metering_class_and()) { ... }
```

#### `priority` (キー部分)

**コード由来デフォルト**: 0 (旧キー形式との backward-compat)

旧キー形式 (`<eni>:<vni>:<prefix>` の 3 部構成) を使用する場合、`priority` は 0 として解釈される。

### 要約表

| フィールド | 必須/任意 | コード由来デフォルト | fallback 源 |
|-----------|---------|-------------------|------------|
| `pa_validation` | 任意 | `false` (proto3 bool 0) | false の場合 SAI action = TUNNEL_DECAP — dashrouteorch.cpp:450 |
| `vnet` | 任意 | なし (SAI 未設定) | has_vnet() false → SRC_VNET_ID をスキップ — dashrouteorch.cpp:453 |
| `metering_class_or` | 任意 | なし (SAI 未設定) | has_metering_class_or() false → スキップ — dashrouteorch.cpp:460 |
| `metering_class_and` | 任意 | なし (SAI 未設定) | has_metering_class_and() false → スキップ — dashrouteorch.cpp:465 |
| `priority` (key) | 任意 | 0 (旧キー形式の場合) | 旧 3 部構成キーとの backward-compat — dashrouteorch.cpp:605 |

---

## 4. DASH_ROUTE_GROUP_TABLE

### テーブルキー

```
DASH_ROUTE_GROUP_TABLE:<route_group_name>
```

### フィールド暗黙デフォルト

`addRouteGroup()` は protobuf `dash::route_group::RouteGroup` を受け取るが、SAI 呼び出し時に属性を一切設定しない:
```cpp
// dashrouteorch.cpp:734
sai_status_t status = sai_dash_outbound_routing_api->create_outbound_routing_group(
    &route_group_oid, gSwitchId, 0, NULL);  // 属性数=0, 属性ポインタ=NULL
```

つまりルートグループはキー名のみで作成される。`RouteGroup` protobuf に含まれる `version` フィールドは結果 DB への書き込みのみに使用される:
```cpp
// dashrouteorch.cpp:874
writeResultToDB(dash_route_group_result_table_, route_group, result, entry.version());
```

### バインド制約

- ルートグループが ENI にバインドされている場合 (`isRouteGroupBound()` が true)、ルートの追加・削除・グループ削除は拒否される
- バインドカウントは `DashEniFwdOrch` 経由で `bindRouteGroup()` / `unbindRouteGroup()` によって管理

### 要約表

| フィールド | 必須/任意 | コード由来デフォルト | fallback 源 |
|-----------|---------|-------------------|------------|
| `version` | 任意 | なし (SAI 未使用) | 結果 DB への書き込みのみ使用 — dashrouteorch.cpp:874 |
| (その他全属性) | — | SAI なし (0 属性でグループ作成) | create_outbound_routing_group() は属性なしで呼ばれる — dashrouteorch.cpp:734 |

---

## discrepancy 記録

| テーブル | フィールド | 状況 |
|---------|-----------|------|
| `DASH_ROUTE_TABLE` | `routing_type` = `ROUTING_TYPE_UNSPECIFIED` | `action_type` deprecated フィールドからのコピー処理あり。新実装では `routing_type` を使用すべき (backward-compat のみ) |
| `DASH_ROUTING_TYPE_TABLE` | `encap_type` が INVALID | `action_type=staticencap` 時に `encap_type` 省略するとエラーログのみで SAI 属性が不正になる可能性 |
| `DASH_ROUTE_TABLE` | `underlay_sip` の IPv6 非対応 | `has_underlay_sip() && has_ipv4()` の条件: IPv6 の underlay_sip は処理されない (dashrouteorch.cpp:149) |

---

## 証拠リンク

- `sonic-swss/orchagent/dash/dashrouteorch.cpp:61-189` — `addOutboundRouting()`
- `sonic-swss/orchagent/dash/dashrouteorch.cpp:421-476` — `addInboundRouting()`
- `sonic-swss/orchagent/dash/dashrouteorch.cpp:564-720` — `doTaskRouteRuleTable()`
- `sonic-swss/orchagent/dash/dashrouteorch.cpp:723-748` — `addRouteGroup()`
- `sonic-swss/orchagent/dash/dashorch.cpp:441-537` — `addRoutingTypeEntry()` / `doTaskRoutingTypeTable()`
- `sonic-swss/orchagent/dash/dashvnetorch.cpp` — routing type アクション参照
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dash.yang:356-472` — YANG DASH_ROUTING_TYPE / DASH_ROUTE_TABLE
