# route-orch constants — 調査メモ (Phase E)

## 調査対象ファイル

- `orchagent/flex_counter/flowcounterrouteorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/flex_counter/flowcounterrouteorch.h` (同 SHA)
- `orchagent/routeorch.cpp` (同 SHA)
- `orchagent/routeorch.h` (同 SHA)

## 発見した定数一覧

### flowcounterrouteorch.cpp (L21-26)

```cpp
#define FLEX_COUNTER_UPD_INTERVAL                   1
#define FLOW_COUNTER_ROUTE_KEY                      "route"
#define FLOW_COUNTER_SUPPORT_FIELD                  "support"
#define ROUTE_PATTERN_MAX_MATCH_COUNT_FIELD         "max_match_count"
#define ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT       30
#define ROUTE_FLOW_COUNTER_POLLING_INTERVAL_MS      10000
```

### flowcounterrouteorch.h (L13)

```cpp
#define ROUTE_FLOW_COUNTER_FLEX_COUNTER_GROUP "ROUTE_FLOW_COUNTER"
```

### routeorch.cpp (L37-38)

```cpp
#define DEFAULT_NUMBER_OF_ECMP_GROUPS   128
#define DEFAULT_MAX_ECMP_GROUP_SIZE     32
```

### routeorch.h (L24-29)

```cpp
#define NHGRP_MAX_SIZE 128
#define EUI64_INTF_ID_LEN 8
#define LOOPBACK_PREFIX     "Loopback"
#define VLAN_PREFIX         "Vlan"
```

## CONFIG_DB 変更可否の整理

| 定数 | 値 | CONFIG_DB から変更可 |
|------|-----|---------------------|
| `ROUTE_PATTERN_DEFAULT_MAX_MATCH_COUNT` | 30 | × (ハードコード; ただし `max_match_count` フィールドで上書き可能) |
| `ROUTE_FLOW_COUNTER_POLLING_INTERVAL_MS` | 10000 ms | × |
| `FLEX_COUNTER_UPD_INTERVAL` | 1 秒 | × |
| `ROUTE_FLOW_COUNTER_FLEX_COUNTER_GROUP` | "ROUTE_FLOW_COUNTER" | × |
| `DEFAULT_NUMBER_OF_ECMP_GROUPS` | 128 | △ (SAI capability で上書き) |
| `DEFAULT_MAX_ECMP_GROUP_SIZE` | 32 | △ (SAI capability で上書き) |
| `NHGRP_MAX_SIZE` | 128 | × |
