# DASH_ROUTING_* — Phase B 書込み順依存スキャンノート

対象テーブル: `DASH_ROUTING_TYPE_TABLE`, `DASH_ROUTE_GROUP_TABLE`, `DASH_ROUTE_TABLE`, `DASH_ROUTE_RULE_TABLE`
Consumer: `DashOrch` (`dashorch.cpp`), `DashRouteOrch` (`dashrouteorch.cpp`)
スキャン範囲: `addOutboundRouting()`, `addInboundRouting()`, `addRouteGroup()`, `removeRouteGroup()`, `setEniRoute()`, `isRouteGroupBound()`, `bindRouteGroup()`, `unbindRouteGroup()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. DASH_ROUTE_GROUP_TABLE → DASH_ROUTE_TABLE (先行必須)

- `DashRouteOrch::addOutboundRouting()` は `getRouteGroupOid(ctxt.route_group)` を呼び、結果が `SAI_NULL_OBJECT_ID` の場合は `SWSS_LOG_INFO("Retry as route group %s not found")` + `return false` でリトライキューに戻る。
- `DASH_ROUTE_GROUP_TABLE:<group_id>` エントリが **先に投入されていなければ** `DASH_ROUTE_TABLE` の SET メッセージは全て retry され、SAI エントリが作成されない。
- **順序依存**: `DASH_ROUTE_GROUP_TABLE` → `DASH_ROUTE_TABLE`（同一 group_id で）。
- evidence: `dashrouteorch.cpp:70-74`

### 2. DASH_ENI_TABLE → DASH_ROUTE_RULE_TABLE (先行必須)

- `DashRouteOrch::addInboundRouting()` は `dash_orch_->getEni(ctxt.eni)` を呼び、ENI が未登録なら `SWSS_LOG_INFO("Retry as ENI entry %s not found")` + `return false`。
- `DashOrch::eni_entries_` に ENI が存在しない間、対応する `DASH_ROUTE_RULE_TABLE` エントリは全てリトライされる。
- **順序依存**: `DASH_ENI_TABLE` → `DASH_ROUTE_RULE_TABLE`（同一 ENI キーで）。
- evidence: `dashrouteorch.cpp:425-428`

### 3. DASH_VNET_TABLE → DASH_ROUTE_TABLE (routing_type=vnet / vnet_direct 時)

- `addOutboundRouting()` は `routing_type=ROUTING_TYPE_VNET` かつ `has_vnet()=true` の場合に `gVnetNameToId.find(vnet)` をチェックし、未登録なら `return false`。
- `ROUTING_TYPE_VNET_DIRECT` で `has_vnet_direct()=true` の場合も同様に `gVnetNameToId.find(vnet_direct().vnet())` をチェック。
- **順序依存**: `DASH_VNET_TABLE` → `DASH_ROUTE_TABLE`（`routing_type=vnet` / `vnet_direct` のエントリのみ）。`routing_type=direct` / `drop` は VNET 参照なしで即時プログラム可能。
- evidence: `dashrouteorch.cpp:78-93`

### 4. DASH_VNET_TABLE → DASH_ROUTE_RULE_TABLE (vnet 指定時)

- `addInboundRouting()` は `ctxt.metadata.has_vnet()=true` の場合に `gVnetNameToId.find(vnet)` をチェックし、未登録なら `return false`。
- **順序依存**: `DASH_VNET_TABLE` → `DASH_ROUTE_RULE_TABLE`（`vnet` フィールドが指定されたエントリのみ）。
- evidence: `dashrouteorch.cpp:430-433`

### 5. DASH_ROUTE_GROUP_TABLE と DASH_ENI_ROUTE_TABLE の相互排他制約

- `DashOrch::setEniRoute()` は `DASH_ROUTE_GROUP_TABLE` にグループが登録済みでなければリトライする（`dashorch.cpp:1193-1197`）。
- ENI にルートグループがバインドされた後 (`bindRouteGroup()` 呼び出し後)、`isRouteGroupBound()` が `true` を返す間は以下の操作が全て **即時拒否**（`return true`/`return false`、リトライなし）される:
  - `addOutboundRouting()`: ルートグループがバインド済みの場合は `SWSS_LOG_WARN` + `return true`（追加されずに消費）— `dashrouteorch.cpp:65-68`
  - `removeOutboundRouting()`: 同様に SWSS_LOG_WARN + `return false` — `dashrouteorch.cpp:231-234`
  - `removeRouteGroup()`: SWSS_LOG_WARN + `return false` — `dashrouteorch.cpp:755-758`
- **解除順序**: `DASH_ENI_ROUTE_TABLE` DEL → `unbindRouteGroup()` が呼ばれた後 → `DASH_ROUTE_TABLE` / `DASH_ROUTE_GROUP_TABLE` DEL が実行可能になる。
- evidence: `dashorch.cpp:1232`, `dashrouteorch.cpp:65-68`, `dashrouteorch.cpp:231-234`, `dashrouteorch.cpp:755-758`

### 6. DASH_ROUTE_TABLE DEL — ルートグループ未バインド状態での実施が必須

- ルートグループが ENI にバインドされている状態では `removeOutboundRouting()` が `return false` を返し、DEL がリトライキューに残留する（消費されない）。
- バインド解除 (`DASH_ENI_ROUTE_TABLE` DEL) を先に行ってから `DASH_ROUTE_TABLE` DEL を実施すること。
- evidence: `dashrouteorch.cpp:227-234`

---

## 推奨書込み順序まとめ

### 追加時

```
1. DASH_ROUTING_TYPE_TABLE (ルーティングタイプ定義)
2. DASH_VNET_TABLE (VNET エントリ — vnet / vnet_direct ルート使用時)
3. DASH_ENI_TABLE (ENI エントリ)
4. DASH_ROUTE_GROUP_TABLE (ルートグループ)
5. DASH_ROUTE_TABLE (Outbound LPM ルート — グループへの追加)
6. DASH_ROUTE_RULE_TABLE (Inbound ルートルール)
7. DASH_ENI_ROUTE_TABLE (ENI とルートグループのバインド — 最後)
```

### 削除時（追加の逆順）

```
1. DASH_ENI_ROUTE_TABLE DEL (バインド解除を先に)
2. DASH_ROUTE_TABLE DEL
3. DASH_ROUTE_RULE_TABLE DEL
4. DASH_ROUTE_GROUP_TABLE DEL
5. DASH_ENI_TABLE DEL
6. DASH_VNET_TABLE DEL
7. DASH_ROUTING_TYPE_TABLE DEL
```
