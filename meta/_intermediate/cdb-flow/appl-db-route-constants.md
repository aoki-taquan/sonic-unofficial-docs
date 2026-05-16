# appl-db-route — Phase E hardcoded constants scan

`docs/reference/config-db/appl-db-route.md` の `<!-- constants -->` ブロック向け
grep 証跡。`sonic-swss` SHA `4305596156d70e9797e8a881b3d19b46de0bce0d` を対象。

## 1. ECMP / NHG 上限関連 (`orchagent/routeorch.cpp`)

```
$ grep -nE '^#define' sonic-swss/orchagent/routeorch.cpp
37:#define DEFAULT_NUMBER_OF_ECMP_GROUPS   128
38:#define DEFAULT_MAX_ECMP_GROUP_SIZE     32
```

- `DEFAULT_NUMBER_OF_ECMP_GROUPS = 128` … SAI が `SAI_SWITCH_ATTR_NUMBER_OF_ECMP_GROUPS`
  を取得できなかった場合のフォールバック上限値（L74-L82）。
- `DEFAULT_MAX_ECMP_GROUP_SIZE = 32` … Mellanox 補正で `m_maxNextHopGroupCount` を
  この値で除算する（L84-L88）。

## 2. プラットフォーム判定文字列 (`orchagent/orch.h`)

```
$ grep -n 'PLATFORM_SUBSTRING' sonic-swss/orchagent/orch.h
42:#define MLNX_PLATFORM_SUBSTRING "mellanox"
46:#define VS_PLATFORM_SUBSTRING   "vs"
49:#define XS_PLATFORM_SUBSTRING   "xsight"
```

`routeorch.cpp` L84 で `getenv("platform")` を `MLNX_PLATFORM_SUBSTRING`
(="mellanox") に対して `strstr()` 部分一致。

## 3. VOQ chassis 強制値 (`orchagent/routeorch.cpp` L109-L122)

```
109:        if (gMySwitchType == "voq" && maxEcmpGroupSize >= 128)
110:        {
111:            maxEcmpGroupSize = 128;
112:            attr.id = SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT;
112:            attr.value.s32 = maxEcmpGroupSize;
```

- リテラル `"voq"` … `DEVICE_METADATA|localhost:switch_type` の値。
- リテラル `128` … `SAI_SWITCH_ATTR_ECMP_MEMBER_COUNT` に書き戻す ECMP メンバ数上限。
  `#define` 化はされておらず、inline magic number。

## 4. CRM 関連 (`orchagent/crmorch.cpp`)

```
$ grep -nE '^#define' sonic-swss/orchagent/crmorch.cpp
9:#define CRM_POLLING_INTERVAL "polling_interval"
10:#define CRM_COUNTERS_TABLE_KEY "STATS"
12:#define CRM_POLLING_INTERVAL_DEFAULT (5 * 60)
13:#define CRM_THRESHOLD_TYPE_DEFAULT CrmThresholdType::CRM_PERCENTAGE
14:#define CRM_THRESHOLD_LOW_DEFAULT 70
15:#define CRM_THRESHOLD_HIGH_DEFAULT 85
16:#define CRM_EXCEEDED_MSG_MAX 10
17:#define CRM_ACL_RESOURCE_COUNT 256
```

- `CRM_EXCEEDED_MSG_MAX = 10` … `THRESHOLD_EXCEEDED` syslog のスパム抑止上限
  （`checkCrmThresholds()` L1168）。
- `CRM_POLLING_INTERVAL_DEFAULT = 300 秒` … 既定ポーリング間隔。
- `CRM_THRESHOLD_LOW_DEFAULT = 70` / `CRM_THRESHOLD_HIGH_DEFAULT = 85` …
  使用率パーセントの既定下限・上限閾値。
- `CRM_THRESHOLD_TYPE_DEFAULT = CRM_PERCENTAGE` … 既定の閾値判定タイプ。

CRM リソース ↔ SAI 属性マッピング（`crmorch.cpp` L74-L94 抜粋）:

```
76: { CRM_IPV4_ROUTE,           SAI_SWITCH_ATTR_AVAILABLE_IPV4_ROUTE_ENTRY },
77: { CRM_IPV6_ROUTE,           SAI_SWITCH_ATTR_AVAILABLE_IPV6_ROUTE_ENTRY },
82: { CRM_NEXTHOP_GROUP_MEMBER, SAI_SWITCH_ATTR_AVAILABLE_NEXT_HOP_GROUP_MEMBER_ENTRY },
83: { CRM_NEXTHOP_GROUP,        SAI_SWITCH_ATTR_AVAILABLE_NEXT_HOP_GROUP_ENTRY },
```

CRM リソース名文字列定数（L30-L37 抜粋）:

```
30: { CRM_IPV4_ROUTE, "IPV4_ROUTE" },
31: { CRM_IPV6_ROUTE, "IPV6_ROUTE" },
36: { CRM_NEXTHOP_GROUP_MEMBER, "NEXTHOP_GROUP_MEMBER" },
37: { CRM_NEXTHOP_GROUP,        "NEXTHOP_GROUP" },
```

これらの文字列は STATE_DB `CRM:STATS` の counter キー名
`crm_stats_ipv4_route_used` / `... _available` 等の生成に使われる。

## 5. STATE_DB capability キー (`routeorch.cpp` L89-L91)

```
89: fvTuple.emplace_back("MAX_NEXTHOP_GROUP_COUNT", to_string(m_maxNextHopGroupCount));
90: m_switchOrch->set_switch_capability(fvTuple);
```

STATE_DB `SWITCH_CAPABILITY|switch` テーブルに `MAX_NEXTHOP_GROUP_COUNT` フィールド
として補正後の値が publish される。ROUTE_TABLE 側の `nexthop_group` 上限管理は
このキーを参照する。
