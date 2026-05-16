# DASH_ROUTING_TYPE フィールド暗黙デフォルト調査メモ

調査日: 2026-05-14
対象テーブル: APPL_DB `DASH_ROUTING_TYPE_TABLE` (YANG: CONFIG_DB `DASH_ROUTING_TYPE`)

## 調査対象ファイル

- `sonic-swss/orchagent/dash/dashorch.cpp` — `doTaskRoutingTypeTable()` (L473-537), `addRoutingTypeEntry()` (L441-455)
- `sonic-swss/orchagent/dash/dashvnetorch.cpp` — `addOutboundCaToPa()` (L300-410)
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-dash.yang` — `DASH_ROUTING_TYPE` container (L356-398)
- `sonic-buildimage/src/sonic-yang-models/tests/yang_model_tests/tests_config/dash.json` — テスト設定例

---

## フィールド別 暗黙デフォルト

### `action_name` (string 1–255)

**YANG default**: なし
**コード由来デフォルト**: protobuf zero value (`""`)

`action_name` は `dash::route_type::RouteTypeItem` protobuf フィールドとして格納されるが、orchagent は SAI 変換時に参照しない。完全にラベル目的のみ。

```yang
# sonic-dash.yang:369-374
leaf action_name {
    description "Name of the forwarding action.";
    type string {
        length 1..255;
    }
}
```

---

### `action_type` (enum string)

**YANG default**: なし
**コード由来デフォルト**: protobuf zero value (`ACTION_TYPE_UNSPECIFIED` = 0)

`dashvnetorch.cpp:325` で `action.action_type() == dash::route_type::ACTION_TYPE_STATICENCAP` を判定。
`staticencap` 以外は encap_type/vni 変換の分岐に入らない（`maprouting`, `drop` 等は別経路）。

```cpp
// dashvnetorch.cpp:325-326
if (action.action_type() == dash::route_type::ACTION_TYPE_STATICENCAP)
{
```

許容値: `none | maprouting | direct | staticencap | appliance | 4to6 | mapdecap | decap | drop`

---

### `encap_type` (enum string: vxlan | nvgre)

**YANG default**: なし
**実態**: `action_type=staticencap` のとき**実質必須**

```cpp
// dashvnetorch.cpp:322, 327-339
sai_dash_encapsulation_t encap_type = SAI_DASH_ENCAPSULATION_INVALID;
if (action.action_type() == dash::route_type::ACTION_TYPE_STATICENCAP)
{
    if (action.encap_type() == dash::route_type::ENCAP_TYPE_VXLAN)
    {
        encap_type = SAI_DASH_ENCAPSULATION_VXLAN;
    }
    else if (action.encap_type() == dash::route_type::ENCAP_TYPE_NVGRE)
    {
        encap_type = SAI_DASH_ENCAPSULATION_NVGRE;
    }
    else
    {
        SWSS_LOG_ERROR("Invalid encap type %d for %s", action.encap_type(), key.c_str());
        return true;  // consumer から削除、エラー扱い
    }
```

省略した場合 `ENCAP_TYPE_UNSPECIFIED` (0) となり `else` 分岐でエラー終了。

---

### `vni` (uint32: 1–16777215)

**YANG default**: なし (range 1–16777215、0 は無効)
**コード由来デフォルト**: protobuf フィールド未設定時は `routing_type_tunnel_key = 0`

```cpp
// dashvnetorch.cpp:321, 341-343
uint32_t routing_type_tunnel_key = 0;
...
if (action.has_vni())
{
    routing_type_tunnel_key = action.vni();
}
```

`routing_type_tunnel_key = 0` の場合 `dashvnetorch.cpp:402-404`:

```cpp
if (routing_type_tunnel_key != 0)
{
    // SAI_OUTBOUND_CA_TO_PA_ENTRY_ATTR_TUNNEL_KEY を設定
```

→ `vni` 省略時は tunnel key SAI 属性が設定されない。ASIC の実装依存デフォルトが適用される。

---

## key 名正規化ロジック

```cpp
// dashorch.cpp:487-490
std::transform(routing_type_str.begin(), routing_type_str.end(), routing_type_str.begin(), ::toupper);
routing_type_str = "ROUTING_TYPE_" + routing_type_str;

if (!dash::route_type::RoutingType_Parse(routing_type_str, &routing_type))
{
    SWSS_LOG_WARN("Invalid routing type %s", routing_type_str.c_str());
```

例: `"vnet_encap"` → `"VNET_ENCAP"` → `"ROUTING_TYPE_VNET_ENCAP"` → enum parse

YANG pattern 許容値: `direct | vnet | vnet_direct | vnet_encap | drop | appliance | privatelink | privatelinknsg | servicetunnel`

---

## 再登録保護

```cpp
// dashorch.cpp:445-449
if (routing_type_entries_.find(routing_type) != routing_type_entries_.end())
{
    SWSS_LOG_WARN("Routing type entry already exists for %s", dash::route_type::RoutingType_Name(routing_type).c_str());
    return true;  // 既存エントリは上書きされない
}
```

更新には DEL → SET の順序が必要。

---

## テスト設定例 (YANG tests_config/dash.json)

```json
"DASH_ROUTING_TYPE_LIST": [
  {
    "name": "vnet_direct",
    "action_name": "act_name",
    "action_type": "maprouting"
  },
  {
    "name": "vnet_encap",
    "action_name": "act_name1",
    "action_type": "staticencap",
    "encap_type": "vxlan"
  }
]
```

`vnet_encap` では `vni` が省略されており、コード上 `routing_type_tunnel_key = 0` (VNI 属性なし) となる。

---

## Phase A 判定

全フィールドを YANG (`sonic-dash.yang:356-398`) と orchagent コード (`dashorch.cpp:441-537`, `dashvnetorch.cpp:300-410`) の全行精読で調査完了。YANG に明示デフォルトなし、コードレベルで上記の挙動が実装されている。
