# DASH_ROUTE_* テーブル — Phase B 書込み順依存スキャンノート

調査日: 2026-05-17
ソース: sonic-swss orchagent/dash/dashrouteorch.cpp, dashorch.cpp, orchdaemon.cpp

---

## 検出した順序依存・タイミング依存

### 1. DASH_ROUTE_GROUP_TABLE が DASH_ROUTE_TABLE より先行必須

`addOutboundRouting()` (dashrouteorch.cpp:70-74) の冒頭で `this->getRouteGroupOid(ctxt.route_group)` を呼び出し、`SAI_NULL_OBJECT_ID` が返った場合は `SWSS_LOG_INFO("Retry as route group %s not found")` + `return false` でリトライキューに戻す。`DASH_ROUTE_GROUP_TABLE|<group_id>` の SAI 作成が完了する前に `DASH_ROUTE_TABLE` エントリを投入すると、Consumer キューに残留して毎イベントループで再試行される。

### 2. DASH_ENI_TABLE が DASH_ROUTE_RULE_TABLE より先行必須

`addInboundRouting()` (dashrouteorch.cpp:425-428) で `dash_orch_->getEni(ctxt.eni)` が nullptr を返すと `SWSS_LOG_INFO("Retry as ENI entry %s not found")` + `return false`。`DashOrch::getEni()` は ENI OID がマップに登録されていない場合に nullptr を返すため、`DASH_ENI_TABLE|<eni>` の SAI 作成完了後に `DASH_ROUTE_RULE_TABLE` エントリを投入すること。

### 3. DASH_VNET_TABLE が DASH_ROUTE_TABLE (routing_type=vnet/vnet_direct) より先行必須

`addOutboundRouting()` (dashrouteorch.cpp:78-92): `routing_type=ROUTING_TYPE_VNET` または `ROUTING_TYPE_VNET_DIRECT` の場合、`gVnetNameToId.find(vnet)` が end() を返すと `SWSS_LOG_INFO("Retry as vnet %s not found")` + `return false`。グローバルマップ `gVnetNameToId` は `DashVnetOrch` が `DASH_VNET_TABLE` 処理時に登録する。

### 4. DASH_VNET_TABLE が DASH_ROUTE_RULE_TABLE (vnet フィールド付き) より先行必須

`addInboundRouting()` (dashrouteorch.cpp:429-433): `ctxt.metadata.has_vnet()` が true かつ `gVnetNameToId.find(vnet)` が end() なら `SWSS_LOG_INFO("Retry as vnet %s not found")` + `return false`。インバウンドルールで VNET デカプセルを指定する場合も同様に先行登録が必要。

### 5. DASH_TUNNEL_TABLE が DASH_ROUTE_TABLE (tunnel フィールド付き) より先行必須

`addOutboundRouting()` (dashrouteorch.cpp:173-178): `has_tunnel()` が true の場合、`dash_tunnel_orch->getTunnelOid(tunnel)` が `SAI_NULL_OBJECT_ID` を返すと `SWSS_LOG_INFO("Retry as tunnel %s not found")` + `return false`。`routing_type=direct` でトンネル転送を使う場合は `DASH_TUNNEL_TABLE` への登録が先行必要。

### 6. ルートグループが ENI にバインド中はルート変更・削除・グループ削除が全て不可

- `addOutboundRouting()` (dashrouteorch.cpp:65-68): `isRouteGroupBound(route_group)` が true なら `SWSS_LOG_WARN("Cannot add new route to route group %s as it is already bound")` + `return false`（リトライなし）。
- `removeOutboundRouting()` (dashrouteorch.cpp:231-236): バインド中はルート削除も `return false`。
- `removeRouteGroup()` (dashrouteorch.cpp:751-758): バインド中はグループ削除も `return false`。
- バインド管理は `DashEniFwdOrch` または `DashOrch` の `bindRouteGroup()` / `unbindRouteGroup()` が `route_group_bind_count_` 参照カウントで追跡する。
- ルートを変更するには `DASH_ENI_ROUTE_TABLE` DEL でバインドを解除してから行うこと。

### 7. orchdaemon addOrchList 登録順序

`orchdaemon.cpp:1409-1412` の `addOrchList` 登録順:

```
DashAclOrch → DashVnetOrch → DashRouteOrch → DashOrch → ...
```

各 Orch の `doTask()` はこの順で実行される。`DashVnetOrch` が先行するため VNET マップが `DashRouteOrch` の処理前に埋まる設計になっている。

### 8. 推奨 SET 順序

```
SET DASH_ROUTE_GROUP_TABLE|<group_id>           # グループ作成
SET DASH_ROUTE_TABLE|<group_id>:<prefix>        # アウトバウンドルート追加（VNET 登録後）
SET DASH_ROUTE_RULE_TABLE|<eni>:<vni>:<pfx>:<prio>  # インバウンドルール（ENI / VNET 登録後）
# バインドは DASH_ENI_ROUTE_TABLE 経由
```

### 9. 推奨 DEL 順序（依存関係の逆順）

```
DEL DASH_ENI_ROUTE_TABLE|<eni>                               # ENI からルートグループ解除
DEL DASH_ROUTE_TABLE|<group>:<prefix>                        # バインド解除後にルート削除
DEL DASH_ROUTE_GROUP_TABLE|<group_id>                        # ルート削除後にグループ削除
DEL DASH_ROUTE_RULE_TABLE|<eni>:<vni>:<prefix>:<priority>    # インバウンドルール削除
```

---

## 順序依存サマリ

| # | 先行テーブル / 操作 | 後続テーブル / 操作 | 緩和策 |
|---|-------------------|-------------------|--------|
| 1 | `DASH_ROUTE_GROUP_TABLE` SAI 完了 | `DASH_ROUTE_TABLE` SET | `SAI_NULL_OBJECT_ID` → `return false` でリトライ |
| 2 | `DASH_ENI_TABLE` SAI 完了 | `DASH_ROUTE_RULE_TABLE` SET | `getEni()` nullptr → `return false` でリトライ |
| 3 | `DASH_VNET_TABLE` SAI 完了 | `DASH_ROUTE_TABLE` (vnet/vnet_direct) SET | `gVnetNameToId` miss → `return false` でリトライ |
| 4 | `DASH_VNET_TABLE` SAI 完了 | `DASH_ROUTE_RULE_TABLE` (vnet 付き) SET | `gVnetNameToId` miss → `return false` でリトライ |
| 5 | `DASH_TUNNEL_TABLE` SAI 完了 | `DASH_ROUTE_TABLE` (tunnel 付き) SET | `getTunnelOid()` null → `return false` でリトライ |
| 6 | `DASH_ENI_ROUTE_TABLE` DEL | ルートグループ内 ROUTE 変更/削除 | バインド中は WARN + `return false`（自動リトライなし） |
| 7 | `DASH_ROUTE_TABLE/RULE_TABLE` 全 DEL | `DASH_ROUTE_GROUP_TABLE` DEL | バインド中 → `return false`、ROUTE 削除後に自動解消 |
