# state-flex-counter — Phase E: ハードコード定数スキャンノート

Generated: 2026-05-18
Target doc: docs/reference/config-db/state-flex-counter.md

対象テーブル: `FLEX_COUNTER_DB|FLEX_COUNTER_GROUP_TABLE|<group>`
スキャン範囲: `flexcounterorch.cpp`, `portsorch.h`, `sonic-swss-common/common/schema.h`

---

## FLEX_COUNTER_GROUP_TABLE フィールド名定数 (schema.h:318-336)

```cpp
#define BULK_CHUNK_SIZE_FIELD               "BULK_CHUNK_SIZE"       // schema.h:318
#define BULK_CHUNK_SIZE_PER_PREFIX_FIELD    "BULK_CHUNK_SIZE_PER_PREFIX" // schema.h:319
#define POLL_INTERVAL_FIELD                 "POLL_INTERVAL"         // schema.h:320
#define STATS_MODE_FIELD                    "STATS_MODE"            // schema.h:322
#define STATS_MODE_READ                     "STATS_MODE_READ"       // schema.h:323
#define STATS_MODE_READ_AND_CLEAR           "STATS_MODE_READ_AND_CLEAR" // schema.h:324
#define FLEX_COUNTER_STATUS_FIELD           "FLEX_COUNTER_STATUS"   // schema.h:335
#define FLEX_COUNTER_GROUP_TABLE            "FLEX_COUNTER_GROUP_TABLE" // schema.h:336
```

## CONFIG_DB キー名定数 (flexcounterorch.cpp:46-66)

```cpp
#define FLEX_COUNTER_DELAY_SEC 60  // flexcounterorch.cpp:44

#define BUFFER_POOL_WATERMARK_KEY   "BUFFER_POOL_WATERMARK"
#define PORT_KEY                    "PORT"
#define PORT_PHY_ATTR_KEY           "PORT_PHY_ATTR"
#define PORT_PHY_SERDES_ATTR_KEY    "PORT_PHY_SERDES_ATTR"
#define PORT_BUFFER_DROP_KEY        "PORT_BUFFER_DROP"
#define QUEUE_KEY                   "QUEUE"
#define QUEUE_WATERMARK             "QUEUE_WATERMARK"
#define PG_WATERMARK_KEY            "PG_WATERMARK"
#define PG_DROP_KEY                 "PG_DROP"
#define RIF_KEY                     "RIF"
#define ACL_KEY                     "ACL"
#define TUNNEL_KEY                  "TUNNEL"
#define FLOW_CNT_TRAP_KEY           "FLOW_CNT_TRAP"
#define FLOW_CNT_ROUTE_KEY          "FLOW_CNT_ROUTE"
#define ENI_KEY                     "ENI"
#define DASH_METER_KEY              "DASH_METER"
#define WRED_QUEUE_KEY              "WRED_ECN_QUEUE"
#define WRED_PORT_KEY               "WRED_ECN_PORT"
#define SRV6_KEY                    "SRV6"
#define SWITCH_KEY                  "SWITCH"
#define HA_SET_KEY                  "HA_SET"
```

## FLEX_COUNTER グループ名定数 (portsorch.h:29-43)

```cpp
#define PORT_STAT_COUNTER_FLEX_COUNTER_GROUP "PORT_STAT_COUNTER"
#define PORT_RATE_COUNTER_FLEX_COUNTER_GROUP "PORT_RATE_COUNTER"
#define PORT_BUFFER_DROP_STAT_FLEX_COUNTER_GROUP "PORT_BUFFER_DROP_STAT"
#define PORT_PHY_ATTR_FLEX_COUNTER_GROUP "PORT_PHY_ATTR"
#define PORT_PHY_SERDES_ATTR_FLEX_COUNTER_GROUP "PORT_PHY_SERDES_ATTR"
#define QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP "QUEUE_STAT_COUNTER"
#define QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP "QUEUE_WATERMARK_STAT_COUNTER"
#define PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP "PG_WATERMARK_STAT_COUNTER"
#define PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP "PG_DROP_STAT_COUNTER"
#define WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP "WRED_ECN_QUEUE_STAT_COUNTER"
#define WRED_PORT_STAT_COUNTER_FLEX_COUNTER_GROUP "WRED_ECN_PORT_STAT_COUNTER"
```

## ポーリング間隔定数 (portsorch.cpp:87-93)

```cpp
#define PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS     1000
#define PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS      60000
#define PORT_PHY_ATTR_FLEX_COUNTER_POLLING_INTERVAL_MS 10000
#define QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS    10000
#define QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS  60000
#define PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS     60000
#define PG_DROP_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS  10000
```

## flexCounterGroupMap (flexcounterorch.cpp:68-83)

CONFIG_DB キーから FLEX_COUNTER_DB グループ名へのマッピング定数テーブル:

```cpp
unordered_map<string, string> flexCounterGroupMap =
{
    {"PORT", PORT_STAT_COUNTER_FLEX_COUNTER_GROUP},
    {"PORT_BUFFER_DROP", PORT_BUFFER_DROP_STAT_FLEX_COUNTER_GROUP},
    {"QUEUE", QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP},
    ...
};
```

## YANG との乖離

YANG の `poll_interval` typedef は `range 100..4294967295`。portsorch のハードコード定数は YANG バリデーション外。CONFIG_DB 未設定でも orchagent 起動時にこれらの値が FLEX_COUNTER_DB に書き込まれる。

## warm-reboot 遅延定数

`FLEX_COUNTER_DELAY_SEC = 60` (flexcounterorch.cpp:44)。warm-reboot 時に FlexCounterOrch が FLEX_COUNTER_DB への書き込みを 60 秒遅延。コード変更以外では変更不可。
