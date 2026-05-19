# DASH_ROUTE_RULE_TABLE — Phase E ハードコード定数 調査ノート

調査日: 2026-05-19
対象ソース: sonic-net/sonic-swss orchagent/dash/dashrouteorch.cpp, dashorch.h
ref: 4305596156d70e9797e8a881b3d19b46de0bce0d

## 発見した定数

### 結果コード定数 (dashorch.h)

| 定数名 | 値 | ファイル | 行 |
|--------|-----|---------|-----|
| `DASH_RESULT_SUCCESS` | `0` | `orchagent/dash/dashorch.h` | L35 |
| `DASH_RESULT_FAILURE` | `1` | `orchagent/dash/dashorch.h` | L36 |

`doTaskRouteRuleTable()` は各ループ先頭で `result = DASH_RESULT_SUCCESS` に初期化し、`addInboundRoutingPost()` が SAI バルク create に失敗した場合のみ `result = DASH_RESULT_FAILURE` に上書きする (dashrouteorch.cpp:585, 702)。

### テーブル名定数 (schema.h)

| 定数名 | 値 | ファイル |
|--------|-----|---------|
| `APP_DASH_ROUTE_RULE_TABLE_NAME` | `"DASH_ROUTE_RULE_TABLE"` | `common/schema.h:187` |

`dash_route_rule_result_table_` は `app_state_db` 上のこのテーブル名で構築され、SAI プログラミング結果の書き戻し先として使用する (dashrouteorch.cpp:57)。

### CRM リソースタイプ定数 (crmorch.h)

| 定数名 | 値（enum） | 用途 |
|--------|------------|------|
| `CRM_DASH_IPV4_INBOUND_ROUTING` | enum 値 | IPv4 SIP を持つ inbound routing エントリ数の CRM リソースカウンタ |
| `CRM_DASH_IPV6_INBOUND_ROUTING` | enum 値 | IPv6 SIP を持つ inbound routing エントリ数の CRM リソースカウンタ |

SIP アドレスファミリ (`ctxt.sip.isV4()`) で分岐し、`gCrmOrch->incCrmResUsedCounter()` / `decCrmResUsedCounter()` に渡す (dashrouteorch.cpp:507, 546)。

### SAI inbound routing アクション定数 (SAI ヘッダ)

| 定数名 | 値 | 条件 |
|--------|-----|------|
| `SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP_PA_VALIDATE` | SAI enum | `pa_validation == true` |
| `SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP` | SAI enum | `pa_validation == false` (デフォルト) |

三項演算子で選択: `ctxt.metadata.pa_validation() ? SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP_PA_VALIDATE : SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP` (dashrouteorch.cpp:450)。

### SAI 属性 ID 定数

| 定数名 | 用途 |
|--------|------|
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_ACTION` | action（PA 検証あり/なし）を設定 |
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_SRC_VNET_ID` | vnet フィールドが存在する場合の VNET OID を設定 |
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_OR` | metering_class_or が存在する場合に設定 |
| `SAI_INBOUND_ROUTING_ENTRY_ATTR_METER_CLASS_AND` | metering_class_and が存在する場合に設定 |

いずれも SAI ヘッダで定義される SAI attribute ID。`has_*()` で protobuf フィールドの存在を確認してから push する条件付き定数。

## 備考

DASH 系 orch は SAI 呼び出し結果を bulker 経由で一括処理するため、`task_need_retry` / `task_failed` の振り分けは `handleSaiCreateStatus()` → `parseHandleSaiStatusFailure()` に委譲している。これらの関数内にも暗黙的な定数（`SAI_STATUS_ITEM_ALREADY_EXISTS` 等）が使われるが、それらは orchagent 共通処理の定数であり本テーブル固有ではない。
