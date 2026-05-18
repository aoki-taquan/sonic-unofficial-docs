# DASH_ROUTE_RULE_TABLE — Phase C 暗黙参照テーブル スキャンノート

対象テーブル: `DASH_ROUTE_RULE_TABLE`
Consumer: `DashRouteOrch` (`sonic-swss/orchagent/dash/dashrouteorch.cpp`)
スキャン範囲: コンストラクタ (L49-58), `addInboundRouting()` (L421-477), `addInboundRoutingPost()` (L479-512), `removeInboundRouting()` (L514-548), `doTaskRouteRuleTable()` (L564-720)

---

## 検出した暗黙参照

### 1. 入力参照: DASH_ENI_TABLE — ハード必須

`addInboundRouting()` L425-428:

```cpp
if (!dash_orch_->getEni(ctxt.eni))
{
    SWSS_LOG_INFO("Retry as ENI entry %s not found", ctxt.eni.c_str());
    return false;
}
```

`dash_orch_->getEni(ctxt.eni)` は `DashOrch` が管理する ENI マップを参照する。
`DASH_ENI_TABLE` に対応するエントリが存在しない場合は `nullptr` を返し、`addInboundRouting` は `false` を返してリトライ。

`addInboundRoutingPost()` でも `dash_orch_->getEni(ctxt.eni)->eni_id` (L521) を参照し、`sai_inbound_routing_entry_t.eni_id` に代入する。

evidence: `dashrouteorch.cpp:425-428`, `dashrouteorch.cpp:521`

### 2. 入力参照: DASH_VNET_TABLE — 条件付き必須

`addInboundRouting()` L430-433:

```cpp
if (ctxt.metadata.has_vnet() && gVnetNameToId.find(ctxt.metadata.vnet()) == gVnetNameToId.end())
{
    SWSS_LOG_INFO("Retry as vnet %s not found", ctxt.metadata.vnet().c_str());
    return false;
}
```

protobuf メッセージに `vnet` フィールドが存在し、かつ `gVnetNameToId` に登録されていない場合はリトライ。
`DASH_VNET_TABLE` エントリが `DashVnetOrch` によって処理済みで `gVnetNameToId` に登録されている場合のみ SAI 反映が進む。

SAI 属性設定時 (L455-457):
```cpp
inbound_routing_attr.id = SAI_INBOUND_ROUTING_ENTRY_ATTR_SRC_VNET_ID;
inbound_routing_attr.value.oid = gVnetNameToId[ctxt.metadata.vnet()];
```

evidence: `dashrouteorch.cpp:430-433`, `dashrouteorch.cpp:455-457`

### 3. 出力参照: APPL_STATE_DB DASH_ROUTE_RULE_TABLE — 結果テーブル

コンストラクタ (L57):
```cpp
dash_route_rule_result_table_ = make_unique<Table>(app_state_db, APP_DASH_ROUTE_RULE_TABLE_NAME);
```

SET 成功後 (L644, L705):
```cpp
writeResultToDB(dash_route_rule_result_table_, key, result);
```

DEL 成功後 (L656, L712):
```cpp
removeResultFromDB(dash_route_rule_result_table_, key);
```

SAI プログラミング結果を `APPL_STATE_DB` の同名テーブルに書き戻す。これは DPU HA やコントローラ側がプログラミング完了を確認するために使用される。

evidence: `dashrouteorch.cpp:57`, `dashrouteorch.cpp:644`, `dashrouteorch.cpp:656`, `dashrouteorch.cpp:705`, `dashrouteorch.cpp:712`

### 4. 副作用: CRM リソースカウンタ

`addInboundRoutingPost()` L507:
```cpp
gCrmOrch->incCrmResUsedCounter(ctxt.sip.isV4() ? CrmResourceType::CRM_DASH_IPV4_INBOUND_ROUTING : CrmResourceType::CRM_DASH_IPV6_INBOUND_ROUTING);
```

`removeInboundRoutingPost()` L546:
```cpp
gCrmOrch->decCrmResUsedCounter(ctxt.sip.isV4() ? CrmResourceType::CRM_DASH_IPV4_INBOUND_ROUTING : CrmResourceType::CRM_DASH_IPV6_INBOUND_ROUTING);
```

エントリの SIP がIPv4 か IPv6 かによって異なる CRM カウンタを更新する。`CrmOrch` が管理するリソース上限の監視に使用される。

evidence: `dashrouteorch.cpp:507`, `dashrouteorch.cpp:546`

---

## 参照サマリ

| 方向 | テーブル / リソース | DB | 条件 | evidence |
|------|-------------------|-----|------|----------|
| 入力 | `DASH_ENI_TABLE` | APPL_DB (ZMQ) | 常時必須 | dashrouteorch.cpp:425 |
| 入力 | `DASH_VNET_TABLE` (gVnetNameToId) | APPL_DB (ZMQ) | `vnet` フィールドが存在する場合のみ | dashrouteorch.cpp:430 |
| 出力 | `APPL_STATE_DB DASH_ROUTE_RULE_TABLE` | APPL_STATE_DB | SAI 成功/失敗後に書き込み | dashrouteorch.cpp:644,705 |
| 副作用 | `CRM_DASH_IPV4/IPV6_INBOUND_ROUTING` | CrmOrch 内部 | SAI 成功後にインクリメント/デクリメント | dashrouteorch.cpp:507,546 |
