# DASH_ROUTE_* テーブル 暗黙参照テーブル調査メモ (Phase C)

調査日: 2026-05-17
対象ファイル: `sonic-swss/orchagent/dash/dashrouteorch.cpp`、`dashrouteorch.h`

---

## DASH_ROUTE_TABLE (アウトバウンド LPM ルート) の参照

### → DASH_ROUTE_GROUP_TABLE（必須）

`addOutboundRouting()` がキーから取り出した `route_group` 文字列を `route_group_oid_map_` で OID 解決する。
SAI_NULL_OBJECT_ID のとき return false（自動リトライ）。

- 参照箇所: `dashrouteorch.cpp:70–74`

### → DASH_VNET_TABLE（条件付き）

- `routing_type=vnet` かつ `has_vnet()`: `gVnetNameToId.find(vnet)` が end() → return false（リトライ）— `dashrouteorch.cpp:78–84`
- `routing_type=vnet_direct` かつ `has_vnet_direct()`: `gVnetNameToId.find(vnet_direct.vnet())` が end() → return false — `dashrouteorch.cpp:86–93`

`gVnetNameToId` グローバルマップは `DashVnetOrch` が `DASH_VNET_TABLE` の SET/DEL 時に更新する（`dashvnetorch.cpp:101, 167`）。

### → DASH_TUNNEL_TABLE（条件付き）

`has_tunnel()` が true のとき `DashTunnelOrch::getTunnelOid()` で OID 解決。
SAI_NULL_OBJECT_ID なら return false（リトライ）。

- 参照箇所: `dashrouteorch.cpp:171–183`

---

## DASH_ROUTE_RULE_TABLE (インバウンドルートルール) の参照

### → DASH_ENI_TABLE（必須）

`addInboundRouting()` が `dash_orch_->getEni(eni)` を呼ぶ。nullptr なら return false（リトライ）。
`DashOrch` 内 `eni_entries_` マップは `DASH_ENI_TABLE` SET 時に登録される。

- 参照箇所: `dashrouteorch.cpp:425–428`

### → DASH_VNET_TABLE（条件付き）

`has_vnet()` が true かつ `gVnetNameToId.find(vnet)` が end() → return false（リトライ）。

- 参照箇所: `dashrouteorch.cpp:430–433`

---

## DASH_ROUTE_GROUP_TABLE の被参照関係

### ← DASH_ENI_ROUTE_TABLE（被参照）

`DashEniFwdOrch` が `DASH_ENI_ROUTE_TABLE` の SET 時に `DashRouteOrch::bindRouteGroup(group_id)` を呼び出す。
DEL 時に `unbindRouteGroup(group_id)` を呼ぶ。

- 参照箇所: `dashorch.cpp:1192, 1232, 1236, 1272–1273`
- 影響: バインドカウント (`route_group_bind_count_`) が 1 以上のとき、ルート変更・削除・グループ削除がすべて拒否される（WARN ログ + return false）。

---

## CRM リソースカウンタ

| テーブル / 操作 | カウンタ | 参照箇所 |
|---|---|---|
| `DASH_ROUTE_TABLE` 追加成功 | `CRM_DASH_IPV4/IPV6_OUTBOUND_ROUTING` inc | `dashrouteorch.cpp:220` |
| `DASH_ROUTE_TABLE` 削除成功 | `CRM_DASH_IPV4/IPV6_OUTBOUND_ROUTING` dec | `dashrouteorch.cpp:262` |
| `DASH_ROUTE_RULE_TABLE` 追加成功 | `CRM_DASH_IPV4/IPV6_INBOUND_ROUTING` inc | `dashrouteorch.cpp:507` |
| `DASH_ROUTE_RULE_TABLE` 削除成功 | `CRM_DASH_IPV4/IPV6_INBOUND_ROUTING` dec | `dashrouteorch.cpp:546` |

`DASH_ROUTE_GROUP_TABLE` は CRM 未使用。

---

## 参照テーブル一覧（要約）

| 参照先 | 参照元テーブル | 条件 | 参照方向 |
|---|---|---|---|
| `DASH_ROUTE_GROUP_TABLE` | `DASH_ROUTE_TABLE` | 常時（OID 解決） | → 前方参照 |
| `DASH_VNET_TABLE` | `DASH_ROUTE_TABLE` | `vnet` / `vnet_direct` 指定時 | → 前方参照 |
| `DASH_TUNNEL_TABLE` | `DASH_ROUTE_TABLE` | `tunnel` フィールド指定時 | → 前方参照 |
| `DASH_ENI_TABLE` | `DASH_ROUTE_RULE_TABLE` | 常時（OID 解決） | → 前方参照 |
| `DASH_VNET_TABLE` | `DASH_ROUTE_RULE_TABLE` | `vnet` フィールド指定時 | → 前方参照 |
| `DASH_ENI_ROUTE_TABLE` | `DASH_ROUTE_GROUP_TABLE` | bind/unbind 操作時 | ← 被参照 |
