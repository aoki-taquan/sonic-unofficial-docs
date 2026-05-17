# DASH Routing テーブル群 暗黙参照テーブル調査メモ (Phase C)

調査日: 2026-05-17
対象テーブル:
- `DASH_ROUTING_TYPE_TABLE` (APP_DB)
- `DASH_ROUTE_TABLE` (APP_DB — Outbound LPM ルート)
- `DASH_ROUTE_RULE_TABLE` (APP_DB — Inbound ルートルール)
- `DASH_ROUTE_GROUP_TABLE` (APP_DB — ルートグループ)

---

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashrouteorch.cpp` (`addOutboundRouting`, `addInboundRouting`, `addRouteGroup`, `bindRouteGroup`, `isRouteGroupBound`)
- `sonic-swss/orchagent/dash/dashrouteorch.h` (`DashRouteOrch`, `OutboundRoutingBulkContext`, `InboundRoutingBulkContext`)
- `sonic-swss/orchagent/dash/dashorch.cpp` (`DashOrch::addRoutingTypeEntry`, `doTaskRoutingTypeTable`)
- `sonic-swss/orchagent/dash/dashorch.h` (`DashOrch` — `getEni()` 提供)

---

## 参照関係の整理

### DASH_ROUTE_TABLE (Outbound LPM Route) の暗黙参照

#### → DASH_ROUTE_GROUP_TABLE (必須参照)

- `addOutboundRouting()` (`dashrouteorch.cpp:70-74`): `this->getRouteGroupOid(ctxt.route_group)` を呼び、ルートグループ OID を取得。`SAI_NULL_OBJECT_ID` の場合 return false (リトライ)。
- `route_group_oid_map_` (in-memory マップ) に `DASH_ROUTE_GROUP_TABLE` 追加時に登録される。
- 参照の性質: **先行必須・OID 解決**

#### → DASH_VNET_TABLE (条件付き必須)

- `addOutboundRouting()` (`dashrouteorch.cpp:78-92`):
  - `routing_type=ROUTING_TYPE_VNET`: `gVnetNameToId.find(vnet) == end()` → return false
  - `routing_type=ROUTING_TYPE_VNET_DIRECT`: `gVnetNameToId.find(vnet_direct.vnet()) == end()` → return false
- `gVnetNameToId` グローバルマップは `DashVnetOrch` (`dashvnetorch.cpp`) が `DASH_VNET_TABLE` 処理時に登録・削除する。
- `routing_type=ROUTING_TYPE_DIRECT` / `ROUTING_TYPE_DROP` では VNET 参照なし。
- 参照の性質: **OID 解決（`vnet`/`vnet_direct` 指定時のみ）**

#### → DASH_TUNNEL_TABLE (条件付き必須)

- `addOutboundRouting()` (`dashrouteorch.cpp:171-183`): `has_tunnel()` が true の場合、`gDirectory.get<DashTunnelOrch*>()->getTunnelOid(tunnel)` を呼ぶ。OID が `SAI_NULL_OBJECT_ID` なら return false (リトライ)。
- 参照の性質: **OID 解決（`tunnel` フィールド指定時のみ）**

---

### DASH_ROUTE_RULE_TABLE (Inbound Route Rule) の暗黙参照

#### → DASH_ENI_TABLE (必須参照)

- `addInboundRouting()` (`dashrouteorch.cpp:425-428`): `dash_orch_->getEni(ctxt.eni)` が `nullptr` なら return false (リトライ)。
- `DashOrch` の ENI マップ (`eni_entries_`) に `DASH_ENI_TABLE` SET 時に登録される。
- 参照の性質: **先行必須・OID 解決**

#### → DASH_VNET_TABLE (条件付き必須)

- `addInboundRouting()` (`dashrouteorch.cpp:430-433`): `has_vnet()` かつ `gVnetNameToId.find(vnet) == end()` → return false (リトライ)。
- `vnet` フィールド省略時は参照なし。
- 参照の性質: **OID 解決（`vnet` フィールド指定時のみ）**

---

### DASH_ROUTE_GROUP_TABLE の暗黙参照

#### → (なし、直接 SAI に書き込み)

- `addRouteGroup()` (`dashrouteorch.cpp:723-748`): 外部テーブルへの参照なし。`create_outbound_routing_group()` を属性なしで呼ぶ。
- `route_group_oid_map_` に登録し、後続の DASH_ROUTE_TABLE から参照される（逆方向）。

#### ← DASH_ENI_ROUTE_TABLE からの参照 (被参照)

- `DashEniFwdOrch` (`dashenifwdorch.cpp`) が `DASH_ENI_ROUTE_TABLE` 処理時に `DashRouteOrch::bindRouteGroup()` / `unbindRouteGroup()` を呼ぶ。
- `route_group_bind_count_` (in-memory) でバインドカウントを管理。バインド中はルート追加・削除・グループ削除を拒否。
- 参照の性質: **バインドカウント管理（双方向影響）**

---

### DASH_ROUTING_TYPE_TABLE の暗黙参照

#### → (なし、他テーブルから参照される)

- `DashOrch::addRoutingTypeEntry()` (`dashorch.cpp:441-497`): `routing_type_entries_` in-memory マップに格納するのみ。外部テーブル参照なし。
- `DashVnetOrch` (`dashvnetorch.cpp`) がこのマップを `getRoutingTypeEntry()` 経由で参照する（逆方向）。

---

## SAI リソース管理 (CRM)

### DASH_ROUTE_TABLE (Outbound)

- 追加成功時 (`addOutboundRoutingPost()`): `gCrmOrch->incCrmResUsedCounter(CRM_DASH_IPV4_OUTBOUND_ROUTING / CRM_DASH_IPV6_OUTBOUND_ROUTING)` — `dashrouteorch.cpp:220`
- 削除成功時 (`removeOutboundRoutingPost()`): `gCrmOrch->decCrmResUsedCounter(...)` — `dashrouteorch.cpp:262`

### DASH_ROUTE_RULE_TABLE (Inbound)

- 追加成功時 (`addInboundRoutingPost()`): `gCrmOrch->incCrmResUsedCounter(CRM_DASH_IPV4_INBOUND_ROUTING / CRM_DASH_IPV6_INBOUND_ROUTING)` — `dashrouteorch.cpp:507`
- 削除成功時 (`removeInboundRoutingPost()`): `gCrmOrch->decCrmResUsedCounter(...)` — `dashrouteorch.cpp:546`

CRM カウンタ参照なし: `DASH_ROUTE_GROUP_TABLE` / `DASH_ROUTING_TYPE_TABLE`

---

## 参照テーブル一覧 (要約)

| 参照先テーブル / リソース | 参照方向 | 条件 | 参照元 evidence |
|--------------------------|---------|------|----------------|
| `DASH_ROUTE_GROUP_TABLE` | OID 解決（必須） | `DASH_ROUTE_TABLE` SET 時常時 | `dashrouteorch.cpp:70-74` (`getRouteGroupOid()`) |
| `DASH_ENI_TABLE` | OID 解決（必須） | `DASH_ROUTE_RULE_TABLE` SET 時常時 | `dashrouteorch.cpp:425-428` (`getEni()`) |
| `DASH_VNET_TABLE` | OID 解決（条件付き） | `DASH_ROUTE_TABLE` の `routing_type=vnet/vnet_direct` 時 | `dashrouteorch.cpp:78-92` (`gVnetNameToId`) |
| `DASH_VNET_TABLE` | OID 解決（条件付き） | `DASH_ROUTE_RULE_TABLE` の `vnet` フィールド指定時 | `dashrouteorch.cpp:430-433` (`gVnetNameToId`) |
| `DASH_TUNNEL_TABLE` | OID 解決（条件付き） | `DASH_ROUTE_TABLE` の `tunnel` フィールド指定時 | `dashrouteorch.cpp:171-183` (`getTunnelOid()`) |
| `DASH_ENI_ROUTE_TABLE` (被参照) | バインドカウント管理 | `DashEniFwdOrch` から `bindRouteGroup()` 呼び出し時 | `dashenifwdorch.cpp` → `dashrouteorch.cpp:803-841` |
| CrmOrch (`gCrmOrch`) | リソースカウンタ | Outbound/Inbound ルート SAI 追加・削除成功時 | `dashrouteorch.cpp:220, 262, 507, 546` |

---

## 証拠リンク

- `sonic-swss/orchagent/dash/dashrouteorch.cpp:61-191` — `addOutboundRouting()`
- `sonic-swss/orchagent/dash/dashrouteorch.cpp:421-476` — `addInboundRouting()`
- `sonic-swss/orchagent/dash/dashrouteorch.cpp:723-748` — `addRouteGroup()`
- `sonic-swss/orchagent/dash/dashrouteorch.cpp:803-841` — `bindRouteGroup()` / `unbindRouteGroup()` / `isRouteGroupBound()`
- `sonic-swss/orchagent/dash/dashorch.cpp:441-497` — `addRoutingTypeEntry()`
