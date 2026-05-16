# SRv6 Orch — Phase E ハードコード定数 (grep 証跡)

ソース: `sonic-swss/orchagent/srv6orch.cpp`、`sonic-swss/orchagent/srv6orch.h`

---

## マクロ定義 (`#define`)

grep コマンド:
```
grep -n '^#define' sonic-swss/orchagent/srv6orch.cpp
```

ヒット (行 19–27):
```cpp
#define ADJ_DELIMITER ','
#define OVERLAY_RIF_DEFAULT_MTU 9100
#define LOCATOR_DEFAULT_BLOCK_LEN "32"
#define LOCATOR_DEFAULT_NODE_LEN "16"
#define LOCATOR_DEFAULT_FUNC_LEN "16"
#define LOCATOR_DEFAULT_ARG_LEN "0"
#define SRV6_FLEX_COUNTER_UPDATE_TIMER 1
#define SRV6_STAT_COUNTER_POLLING_INTERVAL_MS 10000
```

---

## Flex Counter グループ名

`sonic-swss/orchagent/srv6orch.h` 行 30:
```cpp
#define SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP "SRV6_STAT_COUNTER"
```

`sonic-swss-common/common/schema.h` 行 257:
```cpp
#define COUNTERS_SRV6_NAME_MAP "COUNTERS_SRV6_NAME_MAP"
```

---

## エンドポイント動作 enum マッピング (`end_behavior_map`)

`srv6orch.cpp` 行 41–61:
```cpp
const map<string, sai_my_sid_entry_endpoint_behavior_t> end_behavior_map = {
    {"end",               SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_E},
    {"end.x",             SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_X},
    {"end.t",             SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_T},
    {"end.dx6",           SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DX6},
    {"end.dx4",           SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DX4},
    {"end.dt4",           SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DT4},
    {"end.dt6",           SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DT6},
    {"end.dt46",          SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_DT46},
    {"end.b6.encaps",     SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_ENCAPS},
    {"end.b6.encaps.red", SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_ENCAPS_RED},
    {"end.b6.insert",     SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_INSERT},
    {"end.b6.insert.red", SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_B6_INSERT_RED},
    {"udx6",              SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDX6},
    {"udx4",              SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDX4},
    {"udt6",              SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDT6},
    {"udt4",              SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDT4},
    {"udt46",             SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UDT46},
    {"un",                SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UN},
    {"ua",                SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_UA}
};
```

---

## エンドポイント flavor enum マッピング (`end_flavor_map`)

`srv6orch.cpp` 行 64–70:
```cpp
const map<string, sai_my_sid_entry_endpoint_behavior_flavor_t> end_flavor_map = {
    {"end",   SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_PSP_AND_USD},
    {"end.x", SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_PSP_AND_USD},
    {"end.t", SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_PSP_AND_USD},
    {"un",    SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_NONE},
    {"ua",    SAI_MY_SID_ENTRY_ENDPOINT_BEHAVIOR_FLAVOR_PSP_AND_USD}
};
// 上記以外のアクションはデフォルト FLAVOR_NONE のまま
```

---

## SID リスト型 enum マッピング (`sidlist_type_map`)

`srv6orch.cpp` 行 73–78:
```cpp
const map<string, sai_srv6_sidlist_type_t> sidlist_type_map = {
    {"insert",     SAI_SRV6_SIDLIST_TYPE_INSERT},
    {"insert.red", SAI_SRV6_SIDLIST_TYPE_INSERT_RED},
    {"encaps",     SAI_SRV6_SIDLIST_TYPE_ENCAPS},
    {"encaps.red", SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED}
};
// type 未指定・不明時は SAI_SRV6_SIDLIST_TYPE_ENCAPS_RED にフォールバック (行 1083)
```

---

## SAI 属性一覧

### MY_SID エントリ属性
- `SAI_MY_SID_ENTRY_ATTR_ENDPOINT_BEHAVIOR` — エンドポイント動作種別
- `SAI_MY_SID_ENTRY_ATTR_ENDPOINT_BEHAVIOR_FLAVOR` — flavor (PSP/USD 等)
- `SAI_MY_SID_ENTRY_ATTR_VRF` — 関連 VRF OID
- `SAI_MY_SID_ENTRY_ATTR_NEXT_HOP_ID` — nexthop OID
- `SAI_MY_SID_ENTRY_ATTR_TUNNEL_ID` — IpInIp tunnel OID
- `SAI_MY_SID_ENTRY_ATTR_COUNTER_ID` — flex counter OID（オプション）

### SRV6 SID リスト属性
- `SAI_SRV6_SIDLIST_ATTR_TYPE` — sidlist 種別
- `SAI_SRV6_SIDLIST_ATTR_SEGMENT_LIST` — IPv6 SID の配列

### Nexthop 属性（SRv6）
- `SAI_NEXT_HOP_ATTR_TYPE` = `SAI_NEXT_HOP_TYPE_SRV6_SIDLIST`
- `SAI_NEXT_HOP_ATTR_SRV6_SIDLIST_ID`
- `SAI_NEXT_HOP_ATTR_TUNNEL_ID`

### トンネル属性（SRv6 Encap 用）
- `SAI_TUNNEL_ATTR_TYPE` = `SAI_TUNNEL_TYPE_SRV6`
- `SAI_TUNNEL_ATTR_UNDERLAY_INTERFACE`
- `SAI_TUNNEL_ATTR_ENCAP_SRC_IP`
- `SAI_TUNNEL_ATTR_PEER_MODE` = `SAI_TUNNEL_PEER_MODE_P2MP`

### トンネル属性（IpInIp Decap 用）
- `SAI_TUNNEL_ATTR_TYPE` = `SAI_TUNNEL_TYPE_IPINIP`
- `SAI_TUNNEL_ATTR_OVERLAY_INTERFACE`
- `SAI_TUNNEL_ATTR_UNDERLAY_INTERFACE`
- `SAI_TUNNEL_ATTR_PEER_MODE` = `SAI_TUNNEL_PEER_MODE_P2MP`
- `SAI_TUNNEL_ATTR_DECAP_DSCP_MODE` — UNIFORM or PIPE (DSCP mode 依存)
- `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` = `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` (固定)

### Overlay RIF 属性
- `SAI_ROUTER_INTERFACE_ATTR_TYPE` = `SAI_ROUTER_INTERFACE_TYPE_LOOPBACK`
- `SAI_ROUTER_INTERFACE_ATTR_MTU` = `OVERLAY_RIF_DEFAULT_MTU` (9100)
- `SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID`

---

## VRF 要求・nexthop 要求・tunnel 要求の分岐条件

### VRF が必要なアクション
`srv6orch.cpp` 行 1384–1393: `mySidVrfRequired()` が `true` を返す動作:
- `end.t`, `end.dt4`, `end.dt6`, `end.dt46`, `udt4`, `udt6`, `udt46`

### nexthop が必要なアクション
`srv6orch.cpp` 行 1399–1410: `mySidNextHopRequired()` が `true` を返す動作:
- `end.x`, `end.dx4`, `end.dx6`, `udx4`, `udx6`
- `end.b6.encaps`, `end.b6.encaps.red`, `end.b6.insert`, `end.b6.insert.red`, `ua`

### IpInIp tunnel が必要なアクション
`srv6orch.cpp` 行 1419–1420: `un` と `udt46` を除くすべての `u*` 系アクション。
