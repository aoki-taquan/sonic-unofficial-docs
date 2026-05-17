# DASH_ROUTING_* — Phase B 書込み順依存スキャンノート

対象テーブル: `DASH_ROUTING_TYPE_TABLE`, `DASH_ROUTE_GROUP_TABLE`, `DASH_ROUTE_TABLE`, `DASH_ROUTE_RULE_TABLE`
Consumer: `DashOrch::doTaskRoutingTypeTable()` (`dashorch.cpp`) / `DashRouteOrch::doTaskRouteGroupTable()` / `doTaskRouteTable()` / `doTaskRouteRuleTable()` (`dashrouteorch.cpp`)
スキャン範囲: `dashrouteorch.cpp:61-920` 全行精読、`dashorch.cpp:473-537` 参照

---

## 検出した順序依存・タイミング依存

### 1. DASH_ROUTE_GROUP_TABLE が DASH_ROUTE_TABLE より先行必須

- `addOutboundRouting()` L61-191: 最初に `this->getRouteGroupOid(ctxt.route_group)` を呼び、`SAI_NULL_OBJECT_ID` が返った場合は `SWSS_LOG_INFO("Retry as route group %s not found")` + `return false` (リトライ)。
- ルートグループが `DASH_ROUTE_GROUP_TABLE` の SAI 作成完了前に `DASH_ROUTE_TABLE` エントリを投入すると、Consumer キューに残留して毎イベントループで再試行される。
- 順序依存: `DASH_ROUTE_GROUP_TABLE|<group_id>` の SAI 作成完了後に `DASH_ROUTE_TABLE|<group_id>:<prefix>` を SET すること。
- evidence: `dashrouteorch.cpp:70-74`

### 2. DASH_ENI_TABLE が DASH_ROUTE_RULE_TABLE より先行必須

- `addInboundRouting()` L421-476: `dash_orch_->getEni(ctxt.eni)` が nullptr を返すと `SWSS_LOG_INFO("Retry as ENI entry %s not found")` + `return false` (リトライ)。
- `DashOrch` の `getEni()` は ENI OID がマップに登録されていない場合に nullptr を返す。
- 順序依存: `DASH_ENI_TABLE|<eni>` の SAI 作成完了後に `DASH_ROUTE_RULE_TABLE|<eni>:<vni>:<prefix>` を SET すること。
- evidence: `dashrouteorch.cpp:425-428`

### 3. DASH_VNET_TABLE が DASH_ROUTE_TABLE (vnet/vnet_direct) より先行必須

- `addOutboundRouting()` L78-92: `routing_type=ROUTING_TYPE_VNET` または `ROUTING_TYPE_VNET_DIRECT` の場合、`gVnetNameToId.find(vnet)` が end() を返すと `return false` (リトライ)。
- `gVnetNameToId` はグローバルマップ。`DashVnetOrch` が `DASH_VNET_TABLE` 処理時に登録する。
- 順序依存: `DASH_VNET_TABLE|<vnet>` の SAI 作成完了後に `vnet` フィールドを参照する `DASH_ROUTE_TABLE` エントリを SET すること。
- evidence: `dashrouteorch.cpp:78-92`

### 4. DASH_VNET_TABLE が DASH_ROUTE_RULE_TABLE (vnet 付き) より先行必須

- `addInboundRouting()` L429-433: `ctxt.metadata.has_vnet()` が true かつ `gVnetNameToId.find(vnet)` が end() なら `SWSS_LOG_INFO("Retry as vnet %s not found")` + `return false`。
- `vnet` フィールドが設定されている ROUTE_RULE は、対応する VNET が登録済みであることが必要。
- evidence: `dashrouteorch.cpp:429-433`

### 5. DASH_TUNNEL_TABLE が DASH_ROUTE_TABLE (tunnel フィールド) より先行必須

- `addOutboundRouting()` L173-178: `has_tunnel()` が true の場合、`dash_tunnel_orch->getTunnelOid(tunnel)` が `SAI_NULL_OBJECT_ID` を返すと `SWSS_LOG_INFO("Retry as tunnel %s not found")` + `return false`。
- `DashTunnelOrch` は `DASH_TUNNEL_TABLE` からトンネル OID を管理する。
- 順序依存: `DASH_TUNNEL_TABLE|<tunnel>` の SAI 作成完了後に `tunnel` フィールドを指定した `DASH_ROUTE_TABLE` エントリを SET すること。
- evidence: `dashrouteorch.cpp:173-178`

### 6. ルートグループが ENI にバインドされている間はルート変更不可

- `addOutboundRouting()` L65-68: `isRouteGroupBound(route_group)` が true なら `SWSS_LOG_WARN("Cannot add new route to route group %s as it is already bound")` + `return false`。
- `removeOutboundRouting()` L231-236: 同様にバインド中はルート削除も不可。
- `removeRouteGroup()` L751-758: バインド中はグループ削除も不可。
- バインド管理: `DashEniFwdOrch` が `bindRouteGroup()` / `unbindRouteGroup()` を呼び、参照カウントで管理 (`route_group_bind_count_`)。
- ルートグループのルートを変更するには、ENI のルートグループバインドを解除（`DASH_ENI_ROUTE_TABLE` DEL）してから行う必要がある。
- evidence: `dashrouteorch.cpp:65-68, 231-236, 751-758, 803-831`

### 7. DASH_ROUTING_TYPE_TABLE の重複登録は上書き不可

- orchagent がルーティングタイプエントリを既存と判断した場合、`SWSS_LOG_WARN` を出力して success (true) を返し、既存エントリを保持する。変更するには DEL 後に再 SET が必要。
- evidence: `dashorch.cpp:473-537`

### 8. DEL 順序の推奨

推奨 DEL 順序（依存関係の逆順）:
```
DEL DASH_ENI_ROUTE_TABLE|<eni>                               # ENI からルートグループ解除
DEL DASH_ROUTE_TABLE|<group>:<prefix>                        # バインド解除後にルート削除
DEL DASH_ROUTE_GROUP_TABLE|<group_id>                        # ルート削除後にグループ削除
DEL DASH_ROUTE_RULE_TABLE|<eni>:<vni>:<prefix>:<priority>    # Inbound ルール削除
```

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | DASH_ROUTE_GROUP_TABLE SAI 完了 → DASH_ROUTE_TABLE SET | 必須先行 | return false で自動リトライ |
| 2 | DASH_ENI_TABLE SAI 完了 → DASH_ROUTE_RULE_TABLE SET | 必須先行 | return false で自動リトライ |
| 3 | DASH_VNET_TABLE SAI 完了 → DASH_ROUTE_TABLE (vnet/vnet_direct) SET | 必須先行 | return false で自動リトライ |
| 4 | DASH_VNET_TABLE SAI 完了 → DASH_ROUTE_RULE_TABLE (vnet 付き) SET | 必須先行 | return false で自動リトライ |
| 5 | DASH_TUNNEL_TABLE SAI 完了 → DASH_ROUTE_TABLE (tunnel 付き) SET | 必須先行 | return false で自動リトライ |
| 6 | DASH_ENI_ROUTE_TABLE DEL → ルートグループ内 ROUTE 変更 | 必須 | バインド中は SET/DEL とも WARN + return false |
| 7 | DASH_ROUTING_TYPE_TABLE: 重複 SET は上書き不可 | 必須 | 変更時は DEL → SET |
| 8 | DEL: ENI_ROUTE → ROUTE_TABLE → ROUTE_GROUP | 推奨 | バインドカウント依存 |
