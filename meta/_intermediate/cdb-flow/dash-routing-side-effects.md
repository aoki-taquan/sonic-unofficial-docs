# dash-routing — Phase F: 副作用 (side-effects) 調査ノート

調査対象: `sonic-net/sonic-swss orchagent/dash/dashrouteorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 1. APP_STATE_DB 結果テーブルへの書き戻し

`DashRouteOrch` は constructor 内で APP_STATE_DB に接続した 3 つの `Table` を初期化する:

| メンバー変数 | バックエンドテーブル名 | 対象テーブル |
|---|---|---|
| `dash_route_result_table_` | `APP_DASH_ROUTE_TABLE_NAME` (`"DASH_ROUTE_TABLE"`) | DASH_ROUTE_TABLE |
| `dash_route_rule_result_table_` | `APP_DASH_ROUTE_RULE_TABLE_NAME` (`"DASH_ROUTE_RULE_TABLE"`) | DASH_ROUTE_RULE_TABLE |
| `dash_route_group_result_table_` | `APP_DASH_ROUTE_GROUP_TABLE_NAME` (`"DASH_ROUTE_GROUP_TABLE"`) | DASH_ROUTE_GROUP_TABLE |

各ハンドラの処理完了時に `writeResultToDB()` / `removeResultFromDB()` を呼ぶ。

### DASH_ROUTE_TABLE への書き戻し

- SET 成功 (pre-op erase): `result=DASH_RESULT_SUCCESS(0)` → 結果テーブルに `result=0` 書き込み (dashrouteorch.cpp:342)
- SET 成功 (post-op erase): `result=DASH_RESULT_SUCCESS(0)` → 結果テーブルに `result=0` 書き込み (L403)
- SET 失敗 (post-op 継続): `result=DASH_RESULT_FAILURE(1)` → 結果テーブルに `result=1` 書き込み (L401-403)
- DEL 成功 (post-op erase): `removeResultFromDB()` でエントリ削除 (L410)

### DASH_ROUTE_RULE_TABLE への書き戻し

- SET 成功 (pre-op): result=SUCCESS → write (L644)
- SET 成功 (post-op): result=SUCCESS → write (L705)
- SET 失敗 (post-op): result=FAILURE → write (L702-705)
- DEL 成功: removeResultFromDB (L712)

### DASH_ROUTE_GROUP_TABLE への書き戻し

`writeResultToDB` 第 4 引数として `entry.version()` を渡すため、`version` フィールドも同時に書き込まれる。

- SET 成功: result=SUCCESS + version 書き込み (L874)
- SET 失敗: result=FAILURE + version 書き込み (L871, L874)
- DEL 成功: removeResultFromDB (L881)

`DASH_ROUTING_TYPE_TABLE` は `DashOrch::doTaskRoutingTypeTable()` が管理し、同様のパターンで `dash_routing_type_result_table_` (APP_STATE_DB) に書き戻す。

---

## 2. CRM カウンタ更新

`gCrmOrch->incCrmResUsedCounter()` / `decCrmResUsedCounter()` を SAI API 成功後に呼ぶ。

### incCrmResUsedCounter (追加成功時)

| 関数 | カウンタ | コード行 |
|---|---|---|
| `addOutboundRoutingPost()` 成功 | `CRM_DASH_IPV4_OUTBOUND_ROUTING` または `CRM_DASH_IPV6_OUTBOUND_ROUTING` | L220 |
| `addInboundRoutingPost()` 成功 | `CRM_DASH_IPV4_INBOUND_ROUTING` または `CRM_DASH_IPV6_INBOUND_ROUTING` | L507 |

### decCrmResUsedCounter (削除成功時)

| 関数 | カウンタ | コード行 |
|---|---|---|
| `removeOutboundRoutingPost()` 成功 | `CRM_DASH_IPV4_OUTBOUND_ROUTING` または `CRM_DASH_IPV6_OUTBOUND_ROUTING` | L262 |
| `removeInboundRoutingPost()` 成功 | `CRM_DASH_IPV4_INBOUND_ROUTING` または `CRM_DASH_IPV6_INBOUND_ROUTING` | L546 |

IP アドレス族の判定: アウトバウンドは `ctxt.destination.isV4()`、インバウンドは `ctxt.sip.isV4()`。

`DASH_ROUTE_GROUP_TABLE` は CRM カウンタを更新しない。

---

## 3. in-memory マップ更新

### `route_group_oid_map_` (DashRouteOrch メンバ)

- `addRouteGroup()` 成功時: `route_group_oid_map_[route_group] = route_group_oid` → 挿入 (L745)
- `removeRouteGroup()` 成功時: `route_group_oid_map_.erase(route_group)` → 削除 (L784)
- `getRouteGroupOid()` は参照のみ（更新しない）

### `route_group_bind_count_` (DashRouteOrch メンバ)

- `bindRouteGroup()` 呼び出し時: カウントインクリメント (L809)
- `unbindRouteGroup()` 呼び出し時: デクリメント、0 になればエントリ削除 (L824-829)
- 呼び出し元は `DashEniFwdOrch` のみ。`doTaskRouteTable()` / `doTaskRouteGroupTable()` からは更新しない

---

## 4. SAI API 呼び出し (副作用の最終宛先)

| 操作 | SAI API | 方式 | コード行 |
|---|---|---|---|
| ルートグループ作成 | `sai_dash_outbound_routing_api->create_outbound_routing_group()` | 即時 | L734 |
| ルートグループ削除 | `sai_dash_outbound_routing_api->remove_outbound_routing_group()` | 即時 | L768 |
| アウトバウンドルート作成 | `outbound_routing_bulker_.create_entry()` → `flush()` | バルク | L186, L368 |
| アウトバウンドルート削除 | `outbound_routing_bulker_.remove_entry()` → `flush()` | バルク | L243, L368 |
| インバウンドルート作成 | `inbound_routing_bulker_.create_entry()` → `flush()` | バルク | L473, L670 |
| インバウンドルート削除 | `inbound_routing_bulker_.remove_entry()` → `flush()` | バルク | L527, L670 |

ルートグループ操作はバルクを使わず即時 SAI 呼び出し。ルートエントリは `EntityBulker` で蓄積し `flush()` で一括コミット。

---

## 5. 副作用が発生しないケース

| 条件 | 副作用なし理由 |
|---|---|
| バインド中グループへの SET | `addOutboundRouting()` が `return true` で早期終了（SAI・CRM 呼び出しなし）。結果テーブルには `DASH_RESULT_SUCCESS(0)` が書かれる |
| protobuf パース失敗 | consumer から消費するが SAI / CRM / 結果テーブルへの書き込みなし |
| リトライ中 (`return false`) | SAI 未呼び出し、CRM 未更新。SET の post-op 失敗時のみ結果テーブルに `DASH_RESULT_FAILURE` が書かれる |
