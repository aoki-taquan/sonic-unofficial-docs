# dash-routing-table — Phase F: 副作用 (side-effects) 調査ノート

調査対象: `sonic-net/sonic-swss orchagent/dash/dashrouteorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 1. APP_DB 結果テーブルへの書き戻し

### DASH_ROUTE_TABLE (アウトバウンド)

`doTaskRouteTable()` は操作の完了・失敗を問わず `writeResultToDB(dash_route_result_table_, key, result)` を呼ぶ。
`dash_route_result_table_` の背後は `APP_DASH_ROUTE_TABLE_NAME` (`"DASH_ROUTE_TABLE"`) をバックエンドとする `Table`（APP_STATE_DB に接続）。

- **SET 成功** (pre-op erase): `result = DASH_RESULT_SUCCESS` → 結果テーブルに `result=0` 書き込み (L342)
- **SET 成功** (post-op erase): `result = DASH_RESULT_SUCCESS` → 結果テーブルに `result=0` 書き込み (L403)
- **SET 失敗** (post-op 継続): `result = DASH_RESULT_FAILURE` → 結果テーブルに `result=1` 書き込み (L401-403)
- **DEL 成功** (post-op erase): `removeResultFromDB(dash_route_result_table_, key)` でエントリ削除 (L410)

### DASH_ROUTE_RULE_TABLE (インバウンド)

同パターンで `dash_route_rule_result_table_` (`APP_DASH_ROUTE_RULE_TABLE_NAME`) に書き戻す。

- **SET 成功** (pre-op): result=SUCCESS → write (L644)
- **SET 成功** (post-op): result=SUCCESS → write (L705)
- **SET 失敗** (post-op): result=FAILURE → write (L702-705)
- **DEL 成功**: removeResultFromDB (L712)

### DASH_ROUTE_GROUP_TABLE (ルートグループ)

`dash_route_group_result_table_` (`APP_DASH_ROUTE_GROUP_TABLE_NAME`) に書き戻す。
追加として `version` フィールドも書き込まれる（`writeResultToDB` の第 4 引数 `entry.version()`）。

- **SET 成功**: result=SUCCESS + version 書き込み (L874)
- **SET 失敗**: result=FAILURE + version 書き込み (L871, L874)
- **DEL 成功**: removeResultFromDB (L881)

---

## 2. CRM カウンタ更新

### `gCrmOrch->incCrmResUsedCounter()`

| タイミング | カウンタ | コード行 |
|---|---|---|
| `addOutboundRoutingPost()` 成功 (SAI_STATUS_SUCCESS) | `CRM_DASH_IPV4_OUTBOUND_ROUTING` または `CRM_DASH_IPV6_OUTBOUND_ROUTING` | L220 |
| `addInboundRoutingPost()` 成功 | `CRM_DASH_IPV4_INBOUND_ROUTING` または `CRM_DASH_IPV6_INBOUND_ROUTING` | L507 |

### `gCrmOrch->decCrmResUsedCounter()`

| タイミング | カウンタ | コード行 |
|---|---|---|
| `removeOutboundRoutingPost()` 成功 | `CRM_DASH_IPV4_OUTBOUND_ROUTING` または `CRM_DASH_IPV6_OUTBOUND_ROUTING` | L262 |
| `removeInboundRoutingPost()` 成功 | `CRM_DASH_IPV4_INBOUND_ROUTING` または `CRM_DASH_IPV6_INBOUND_ROUTING` | L546 |

`DASH_ROUTE_GROUP_TABLE` は CRM カウンタを更新しない。

IP アドレス族の判定は `ctxt.destination.isV4()` (Outbound) / `ctxt.sip.isV4()` (Inbound) で行われる。

---

## 3. in-memory マップ更新

### `route_group_oid_map_`

- `addRouteGroup()` 成功時: `route_group_oid_map_[route_group] = route_group_oid` (L745) → 挿入
- `removeRouteGroup()` 成功時: `route_group_oid_map_.erase(route_group)` (L784) → 削除
- `getRouteGroupOid()` は参照のみ（更新しない）

### `route_group_bind_count_`

`bindRouteGroup()` / `unbindRouteGroup()` によって更新される（呼び出し元は `DashEniFwdOrch`）。
`DashRouteOrch` 自身は `isRouteGroupBound()` で参照するのみで、`doTaskRouteTable()` / `doTaskRouteGroupTable()` 内からは更新しない。

---

## 4. SAI API 呼び出し (副作用の最終宛先)

| 操作 | SAI API | コード行 |
|---|---|---|
| ルートグループ作成 | `sai_dash_outbound_routing_api->create_outbound_routing_group()` | L734 |
| ルートグループ削除 | `sai_dash_outbound_routing_api->remove_outbound_routing_group()` | L768 |
| アウトバウンドルート作成 (bulk) | `outbound_routing_bulker_.create_entry()` → flush() | L186, L368 |
| アウトバウンドルート削除 (bulk) | `outbound_routing_bulker_.remove_entry()` → flush() | L243, L368 |
| インバウンドルート作成 (bulk) | `inbound_routing_bulker_.create_entry()` → flush() | L473, L670 |
| インバウンドルート削除 (bulk) | `inbound_routing_bulker_.remove_entry()` → flush() | L527, L670 |

ルートグループ操作はバルクを使わず即時 SAI 呼び出し。ルートエントリは `EntityBulker` で蓄積し `flush()` で一括コミット。

---

## 5. 副作用が発生しないケース

| 条件 | 副作用なし理由 |
|---|---|
| バインド中グループへの SET | `addOutboundRouting()` が `return true` で早期終了（SAI 呼び出しなし）。ただし結果テーブルには `DASH_RESULT_SUCCESS` が書かれる |
| protobuf パース失敗 | `it = consumer.m_toSync.erase(it)` で消費するが、SAI / CRM / 結果テーブルへの書き込みなし |
| リトライ中 (`return false`) | SAI 未呼び出し、CRM 未更新、結果テーブルへの書き込みは発生する場合あり（SET の post-op 失敗時） |
