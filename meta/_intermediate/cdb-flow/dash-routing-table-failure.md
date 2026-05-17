# DASH_ROUTE_* テーブル — Phase D 失敗挙動スキャンノート

対象テーブル: `DASH_ROUTE_GROUP_TABLE` / `DASH_ROUTE_TABLE` / `DASH_ROUTE_RULE_TABLE`
Consumer: `DashRouteOrch` (`sonic-swss/orchagent/dash/dashrouteorch.cpp`)
スキャン範囲: 全ハンドラ関数の失敗分岐・SAI エラーハンドリング・WARN/ERROR ログ箇所

---

## DASH_ROUTE_TABLE（アウトバウンドルート）失敗パターン

### SET 操作

| 失敗ケース | 発生箇所 | 挙動 | retry |
|---|---|---|---|
| protobuf パース失敗 | `doTaskRouteTable()` L320-324 | `erase(it)` してスキップ（永続消費）| なし |
| ルートグループ未登録（`getRouteGroupOid()` = NULL） | `addOutboundRouting()` L70-74 | `return false` → `it++` → 次イベントループ再試行 | グループ作成まで無制限 |
| ルートグループがバインド中（`isRouteGroupBound()` = true） | `addOutboundRouting()` L65-69 | `return true`（成功扱いで erase）→ WARN ログ。ルートは**SAI に登録されない** | なし（静かに無視） |
| VNET 未登録（`gVnetNameToId` miss, routing_type=vnet） | `addOutboundRouting()` L78-84 | `return false` → `it++` → 次イベントループ再試行 | VNET 登録まで無制限 |
| VNET 未登録（`gVnetNameToId` miss, routing_type=vnet_direct） | `addOutboundRouting()` L86-93 | `return false` → `it++` → 次イベントループ再試行 | VNET 登録まで無制限 |
| routing_type が sOutboundAction マップ外 | `addOutboundRouting()` L103-108 | `return false` → `it++` → WARN ログ。ループで永続残留 | 事実上無制限だが SAI 成功しないため解消不可 |
| routing_type=vnet/vnet_direct で必須属性欠落（vnet 空 / overlay_ip 欠落） | `addOutboundRouting()` L142-147 | `return false` → WARN ログ → 永続残留 | 解消不可（データ不整合） |
| tunnel 未登録（`getTunnelOid()` = NULL） | `addOutboundRouting()` L171-178 | `return false` → `it++` → 次イベントループ再試行 | トンネル作成まで無制限 |
| `to_sai()` IP 変換失敗（underlay_sip / overlay_ip） | `addOutboundRouting()` L136-139, L152-156 | `return false` → 永続残留 | 解消不可 |
| SAI `create_outbound_routing_entry` 失敗（`ITEM_ALREADY_EXISTS`） | `addOutboundRoutingPost()` L206-209 | `return false` → `it++` → 次イベントループ再試行（bulker 再実行） | 無制限 |
| SAI `create_outbound_routing_entry` 失敗（その他） | `addOutboundRoutingPost()` L212-217 | `SWSS_LOG_ERROR` + `handleSaiCreateStatus()` → `parseHandleSaiStatusFailure()` | SAI API 依存 |
| `DASH_RESULT_FAILURE` 書き込み | `doTaskRouteTable()` L401-403 | `writeResultToDB()` で result DB に FAILURE を書き込み | - |

### DEL 操作

| 失敗ケース | 発生箇所 | 挙動 | retry |
|---|---|---|---|
| ルートグループがバインド中 | `removeOutboundRouting()` L231-235 | `return false` → WARN ログ → 永続再試行ループ | ENI バインド解除まで無制限 |
| SAI `remove_outbound_routing_entry` 失敗（`NOT_EXECUTED`） | `removeOutboundRoutingPost()` L266-269 | `return false` → 次イベントループ再試行 | 無制限 |
| SAI `remove_outbound_routing_entry` 失敗（その他） | `removeOutboundRoutingPost()` L271-276 | `SWSS_LOG_ERROR` + `handleSaiRemoveStatus()` | SAI API 依存 |

---

## DASH_ROUTE_RULE_TABLE（インバウンドルール）失敗パターン

### SET 操作

| 失敗ケース | 発生箇所 | 挙動 | retry |
|---|---|---|---|
| protobuf パース失敗 | `doTaskRouteRuleTable()` L631-635 | `erase(it)` してスキップ（永続消費）| なし |
| ENI 未登録（`getEni()` = nullptr） | `addInboundRouting()` L425-429 | `return false` → `it++` → 次イベントループ再試行 | ENI 作成まで無制限 |
| VNET 未登録（`gVnetNameToId` miss） | `addInboundRouting()` L430-434 | `return false` → `it++` → 次イベントループ再試行 | VNET 登録まで無制限 |
| SAI `create_inbound_routing_entry` 失敗（`ITEM_ALREADY_EXISTS`） | `addInboundRoutingPost()` L493-496 | `return false` → `it++` → 次イベントループ再試行（bulker 再実行） | 無制限 |
| SAI `create_inbound_routing_entry` 失敗（その他） | `addInboundRoutingPost()` L499-504 | `SWSS_LOG_ERROR` + `handleSaiCreateStatus()` | SAI API 依存 |

### DEL 操作

| 失敗ケース | 発生箇所 | 挙動 | retry |
|---|---|---|---|
| SAI `remove_inbound_routing_entry` 失敗（`NOT_EXECUTED`） | `removeInboundRoutingPost()` L550-553 | `return false` → 次イベントループ再試行 | 無制限 |
| SAI `remove_inbound_routing_entry` 失敗（その他） | `removeInboundRoutingPost()` L555-559 | `SWSS_LOG_ERROR` + `handleSaiRemoveStatus()` | SAI API 依存 |

---

## DASH_ROUTE_GROUP_TABLE（ルートグループ）失敗パターン

### SET 操作

| 失敗ケース | 発生箇所 | 挙動 | retry |
|---|---|---|---|
| protobuf パース失敗 | `doTaskRouteGroupTable()` L858-862 | `erase(it)` してスキップ | なし |
| グループ既存（`getRouteGroupOid()` != NULL） | `addRouteGroup()` L727-731 | `return true` + WARN ログ（idempotent 処理、再作成しない）| なし |
| SAI `create_outbound_routing_group` 失敗 | `addRouteGroup()` L735-742 | `SWSS_LOG_ERROR` + `handleSaiCreateStatus()` → result=FAILURE を DB 書き込み | SAI API 依存 |

### DEL 操作

| 失敗ケース | 発生箇所 | 挙動 | retry |
|---|---|---|---|
| バインド中のグループ削除 | `removeRouteGroup()` L755-758 | `return false` + WARN ログ → `it++` 再試行ループ | ENI バインド解除まで無制限 |
| `getRouteGroupOid()` = NULL（既に削除済み） | `removeRouteGroup()` L762-766 | `return true`（idempotent）| なし |
| SAI `remove_outbound_routing_group` 失敗（`OBJECT_IN_USE`） | `removeRouteGroup()` L772-774 | `return false` → `it++` 再試行ループ | SAI 側の in-use が解消されるまで無制限 |
| SAI `remove_outbound_routing_group` 失敗（その他） | `removeRouteGroup()` L776-780 | `SWSS_LOG_ERROR` + `handleSaiRemoveStatus()` | SAI API 依存 |

---

## 重要な挙動の非対称性

### SET 時の「バインド中ルートグループへの追加」は静かに無視される

`addOutboundRouting()` L65-69:
```cpp
if (isRouteGroupBound(ctxt.route_group))
{
    SWSS_LOG_WARN("Cannot add new route to route group %s as it is already bound", ...);
    return true;  // 成功扱い → erase → 結果 DB に SUCCESS を書く
}
```

- エラー扱いではなく **成功扱い** で Consumer キューから消費される。
- `writeResultToDB()` に `DASH_RESULT_SUCCESS` が渡される（L342）。
- ルートは **SAI に登録されない**。STATE_DB / result DB は成功だが実態は未設定という非対称が生じる。

### DEL 時の「バインド中ルートグループからの削除」は永続ループする

`removeOutboundRouting()` L231-235:
```cpp
if (isRouteGroupBound(ctxt.route_group))
{
    SWSS_LOG_WARN("Cannot remove route from route group %s as it is already bound", ...);
    return false;  // 失敗扱い → it++ → 次イベントループ再試行
}
```

- ENI バインドを解除しない限り、ループが永続化し orchagent の CPU 負荷に繋がる可能性がある。
