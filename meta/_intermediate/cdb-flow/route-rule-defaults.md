# DASH_ROUTE_RULE_TABLE — フィールドデフォルト調査メモ (Phase A)

調査日: 2026-05-14
対象テーブル: `DASH_ROUTE_RULE_TABLE` (APPL_DB)
対応ページ: `docs/reference/config-db/route-rule.md`
担当ハンドラ: `DashRouteOrch::doTaskRouteRuleTable()` → `addInboundRouting()`
ソース: `sonic-swss/orchagent/dash/dashrouteorch.cpp`

---

## key 構造

```
DASH_ROUTE_RULE_TABLE:<eni>:<vni>:<prefix>:<priority>
```

- `<eni>` — ENI MAC 文字列 (例: `F4939FEFC47E`)
- `<vni>` — VXLAN VNI (uint32)
- `<prefix>` — SIP プレフィックス (IPv4/IPv6 CIDR、または DASH_PREFIX_TAG_TABLE のタグ名)
- `<priority>` — ルール優先度 (uint32、省略可能、旧フォーマット互換)

### priority のキーパース (dashrouteorch.cpp:605-623)

```cpp
priority = 0;  // フォールバックデフォルト

size_t last_colon = prefix_and_optional_priority.rfind(':');
if (last_colon != string::npos) {
    string maybe_priority = prefix_and_optional_priority.substr(last_colon + 1);
    bool is_priority = !maybe_priority.empty() &&
                       all_of(maybe_priority.begin(), maybe_priority.end(),
                              [](unsigned char c) { return std::isdigit(c); });
    if (is_priority) {
        priority = to_uint<uint32_t>(maybe_priority);
        ip_str = prefix_and_optional_priority.substr(0, last_colon);
    }
}
```

旧フォーマット (`<eni>:<vni>:<prefix>` — priority 省略) の互換のため、
priority フィールドが数字のみでない場合は priority=0 に fallback する。

---

## protobuf フィールド (RouteRule) とデフォルト

`dash_api/route_rule.pb.h` は未確認 (shallow clone にヘッダ未含)。
`dash-sonic-hld.md` スキーマ + `dashrouteorch.cpp` の `has_*()` パターンから導出。

| フィールド | 型 | 必須/任意 | コード由来デフォルト | 根拠 |
|-----------|----|---------|--------------------|------|
| `action_type` | routing_type enum | 任意 (deprecated) | 省略可。protobuf3 デフォルト=0 | HLD:598 "deprecated"; dashrouteorch.cpp には action_type の明示チェックなし |
| `priority` | uint32 | 任意 (key に移動) | `0` (旧フォーマット互換 fallback) | dashrouteorch.cpp:605 `priority = 0;` |
| `protocol` | uint32 | 任意 | `0` (any プロトコル) | proto3 数値デフォルト; HLD:613 "0 (any)" |
| `vnet` | string | 任意 | 未設定 (SAI 属性 push なし) | dashrouteorch.cpp:453-458 `if (ctxt.metadata.has_vnet())` |
| `pa_validation` | bool | 任意 | `false` → `TUNNEL_DECAP` (PA 検証なし) | dashrouteorch.cpp:450 三項演算子; proto3 bool デフォルト=false |
| `metering_class_or` | uint32 | 任意 | 未設定 (SAI 属性 push なし) | dashrouteorch.cpp:460-464 `if (ctxt.metadata.has_metering_class_or())` |
| `metering_class_and` | uint32 | 任意 | 未設定 (SAI 属性 push なし) | dashrouteorch.cpp:466-470 `if (ctxt.metadata.has_metering_class_and())` |
| `region` | string | 任意 | 未設定 | HLD:618 "optional region_id"; dashrouteorch.cpp に has_region() コードなし |

---

## SAI アクション決定ロジック (dashrouteorch.cpp:449-451)

```cpp
inbound_routing_attr.id = SAI_INBOUND_ROUTING_ENTRY_ATTR_ACTION;
inbound_routing_attr.value.u32 = ctxt.metadata.pa_validation()
    ? SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP_PA_VALIDATE
    : SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP;
```

`pa_validation` が設定されていない (proto3 bool デフォルト=false) 場合、
`SAI_INBOUND_ROUTING_ENTRY_ACTION_TUNNEL_DECAP` が SAI に渡される。
PA 検証なしの TUNNEL_DECAP がデフォルト動作。

---

## 依存関係

- ENI (`DASH_ENI_TABLE`) が存在しない → `addInboundRouting` が false を返しリトライ
  (`dash_orch_->getEni(ctxt.eni)` が nullptr)
- `vnet` 指定時に `DASH_VNET_TABLE` 未登録 → リトライ
  (`gVnetNameToId.find(ctxt.metadata.vnet()) == gVnetNameToId.end()`)

---

## HLD 引用 (dash-sonic-hld.md:609-618)

```
key = DASH_ROUTE_RULE_TABLE:eni:vni:prefix:priority
action_type = routing_type   ; deprecated
priority    = INT32          ; deprecated, moved to key
protocol    = INT32 value    ; 0 (any)
vnet        = vnet name      ; OPTIONAL
pa_validation = true/false   ; Default is set to true (HLD 記載)
metering_class_or = uint32   ; OPTIONAL
metering_class_and = uint32  ; OPTIONAL
region = region_id           ; OPTIONAL
```

**注意**: HLD の `pa_validation` デフォルト `true` と orchagent の proto3 boolean デフォルト
`false` (= `TUNNEL_DECAP`) に乖離あり。HLD は "Default is set to true" と記載するが、
コントローラが明示的に `true` を送らない限り、proto3 デフォルトの `false` が適用される。
discrepancy として記録する。

---

## 調査終了状態

- Phase A 完了: フィールドデフォルト特定
- `docs/reference/config-db/route-rule.md` に `<!-- defaults -->` セクション追加済み
