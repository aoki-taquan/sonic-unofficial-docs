# DASH_ROUTE_* テーブル — Phase A デフォルト調査メモ

## 対象ファイル

- `sonic-swss/orchagent/dash/dashrouteorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/dash/dashrouteorch.h`
- `SONiC/doc/dash/dash-sonic-hld.md` (ref: 49bab5b5ff0e924f1ea52b3d9db0dfa4191a7c06)

## DASH_ROUTE_TABLE (アウトバウンド)

### routing_type SAI マッピング (dashrouteorch.cpp:41-47)

```cpp
static std::unordered_map<dash::route_type::RoutingType, sai_outbound_routing_entry_action_t> sOutboundAction = {
    { ROUTING_TYPE_VNET,        SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET },
    { ROUTING_TYPE_VNET_DIRECT, SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_VNET_DIRECT },
    { ROUTING_TYPE_DIRECT,      SAI_OUTBOUND_ROUTING_ENTRY_ACTION_ROUTE_DIRECT },
    { ROUTING_TYPE_DROP,        SAI_OUTBOUND_ROUTING_ENTRY_ACTION_DROP }
};
```

- `servicetunnel`, `privatelink`, `appliance` は **マップ外** → `task_failed`
- HLD 記載の `routing_type` と実装の乖離あり (discrepancy)

### action_type 後方互換 (dashrouteorch.cpp:326-333)

```cpp
if (ctxt.metadata.routing_type() == ROUTING_TYPE_UNSPECIFIED) {
    ctxt.metadata.set_routing_type(ctxt.metadata.action_type());
}
```

### 条件付き SAI 属性 (省略時 = SAI 属性なし)

| フィールド | has_ guard | 行 |
|-----------|-----------|-----|
| `underlay_sip` | `has_underlay_sip() && underlay_sip().has_ipv4()` | 149 |
| `metering_class_or` | `has_metering_class_or()` | 159 |
| `metering_class_and` | `has_metering_class_and()` | 165 |
| `tunnel` | `has_tunnel()` | 171 |

### routing_type=vnet 必須チェック (dashrouteorch.cpp:78-93)

```cpp
if (routing_type == VNET && !vnet().empty() && gVnetNameToId.find(vnet()) == end) → retry
if (routing_type == VNET_DIRECT && !vnet_direct().vnet().empty() && ...) → retry
```

## DASH_ROUTE_RULE_TABLE (インバウンド)

### pa_validation デフォルト (dashrouteorch.cpp:449-451)

```cpp
inbound_routing_attr.value.u32 =
    ctxt.metadata.pa_validation()
        ? SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP_PA_VALIDATE
        : SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP;
```

proto3 bool のゼロ値 = `false` → PA 検証なし

### priority フォールバック (dashrouteorch.cpp:605-622)

```cpp
priority = 0;  // デフォルト
// ... キーから数字部分を抽出し、見つかれば上書き
if (is_priority) { priority = to_uint<uint32_t>(maybe_priority); }
```

旧キー形式（priority なし）では `priority=0` が使われる。コード内コメントに明記。

### 条件付き SAI 属性 (インバウンド)

| フィールド | has_ guard | 行 |
|-----------|-----------|-----|
| `vnet` (src_vnet_id) | `has_vnet()` | 453 |
| `metering_class_or` | `has_metering_class_or()` | 460 |
| `metering_class_and` | `has_metering_class_and()` | 466 |

## DASH_ROUTE_GROUP_TABLE

### SAI 属性ゼロ個 (dashrouteorch.cpp:734)

```cpp
sai_dash_outbound_routing_api->create_outbound_routing_group(&oid, gSwitchId, 0, NULL);
```

`version` フィールドは `writeResultToDB` の第 3 引数にのみ渡され、SAI には一切渡されない。

## 結論

- `routing_type` は実質必須（UNSPECIFIED のままだと SAI エラー）
- `pa_validation` 省略 = `false` = PA 検証なし（proto3 ゼロ値）
- `metering_class_or/and` は has_ guard で省略可（SAI 属性なし）
- `priority` の省略（旧キー形式）= 0 フォールバック
- `servicetunnel` / `privatelink` 等の routing_type は現行実装で未サポート（HLD との乖離）
