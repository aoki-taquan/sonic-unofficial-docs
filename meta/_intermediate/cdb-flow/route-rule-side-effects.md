# DASH_ROUTE_RULE_TABLE — Phase F 副次 DB 書込 調査ノート

調査対象: `sonic-swss/orchagent/dash/dashrouteorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
補助: `orchagent/saihelper.cpp`, `orchagent/saihelper.h`, `orchagent/dash/dashorch.h`

## 書き込み先まとめ

### APPL_STATE_DB / `DASH_ROUTE_RULE_TABLE` (result テーブル)

`DashRouteOrch::DashRouteOrch()` が `app_state_db` を受け取り、`APP_DASH_ROUTE_RULE_TABLE_NAME` ("DASH_ROUTE_RULE_TABLE") をキーに `dash_route_rule_result_table_` を初期化する (dashrouteorch.cpp:57)。

`writeResultToDB(dash_route_rule_result_table_, key, result)` は `saihelper.cpp:1125-1156` で実装。
書き込みフィールド: `result` = `"0"` (DASH_RESULT_SUCCESS) または `"1"` (DASH_RESULT_FAILURE)。
`version` パラメータはデフォルト `""` のため route rule 呼び出しでは `version` フィールドは書かれない。

呼び出し箇所:
- `dashrouteorch.cpp:644` — pre-op で `addInboundRouting()` が true を返したとき (SET, 依存解決済み + bulker不要ケース)
- `dashrouteorch.cpp:705` — post-op の `writeResultToDB` (SET, bulker flush 後の成功/失敗を問わず書き込み)

`removeResultFromDB(dash_route_rule_result_table_, key)` (saihelper.cpp:1157):
- `dashrouteorch.cpp:656` — pre-op DEL 成功時
- `dashrouteorch.cpp:712` — post-op DEL 成功時 (`removeInboundRoutingPost` が true を返したとき)

### CRM (CrmOrch) カウンタ

`gCrmOrch->incCrmResUsedCounter()` / `decCrmResUsedCounter()` は orchagent 内部の `CrmOrch` が保持するリソース使用量カウンタ。DB への直接書き込みではなく orchestrator メモリ上のカウンタ更新。CRM は定期的にカウンタを COUNTERS_DB へフラッシュする。

| 操作 | 条件 | カウンタ | evidence |
|------|------|---------|---------|
| inc | `addInboundRoutingPost()` 成功 かつ `ctxt.sip.isV4() == true` | `CRM_DASH_IPV4_INBOUND_ROUTING` | dashrouteorch.cpp:507 |
| inc | `addInboundRoutingPost()` 成功 かつ `ctxt.sip.isV4() == false` | `CRM_DASH_IPV6_INBOUND_ROUTING` | dashrouteorch.cpp:507 |
| dec | `removeInboundRoutingPost()` 成功 かつ `ctxt.sip.isV4() == true` | `CRM_DASH_IPV4_INBOUND_ROUTING` | dashrouteorch.cpp:546 |
| dec | `removeInboundRoutingPost()` 成功 かつ `ctxt.sip.isV4() == false` | `CRM_DASH_IPV6_INBOUND_ROUTING` | dashrouteorch.cpp:546 |

## 副次書込なし

- STATE_DB: 書き込みなし
- CONFIG_DB: 書き込みなし
- FLEX_COUNTER_DB: 書き込みなし
- COUNTERS_DB (直接): CrmOrch 経由の定期フラッシュのみ (直接書込なし)
- ASIC_DB: SAI → syncd 経由 (orchagent の直接書込なし)
