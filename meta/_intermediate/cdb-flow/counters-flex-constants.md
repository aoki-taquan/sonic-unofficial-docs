# counters-flex Phase E — ハードコード定数スキャンノート

Generated: 2026-05-17  
Target doc: docs/reference/config-db/counters-flex.md

対象テーブル: `FLEX_COUNTER_DB|FLEX_COUNTER_TABLE|<group>|<oid>` (`*_COUNTER_ID_LIST` / `*_ATTR_ID_LIST` フィールド)  
Consumer: `orchagent` — `FlexCounterOrch` / `PortsOrch`  
スキャン範囲: `flexcounterorch.cpp:44-66`、`portsorch.cpp:79-93`、`portsorch.h:29-43`、`flex_counter_manager.cpp:37-60`

---

## 検出したハードコード定数

### 1. Warm-reboot 遅延タイマー

| 定数名 | 値 | 定義箇所 | 用途 |
|------|----|---------|------|
| `FLEX_COUNTER_DELAY_SEC` | `60` (秒) | `flexcounterorch.cpp:44` | Warm-reboot 時に `doTask()` 全処理を遅延させるタイマー秒数。CONFIG_DB / YANG では設定不可 |

### 2. FlexCounter グループ初期 Polling Interval

`portsorch.cpp:87-93` でハードコード定義。`FlexCounterManager` コンストラクタに渡されるデフォルト値であり、CONFIG_DB の `POLL_INTERVAL` フィールドで後から上書き可能。

| 定数名 | 値 (ms) | 対象グループ | 定義箇所 |
|------|---------|------------|---------|
| `PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `1000` | `PORT` / `WRED_ECN_PORT` | `portsorch.cpp:87` |
| `PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS` | `60000` | `PORT_BUFFER_DROP` | `portsorch.cpp:88` |
| `PORT_PHY_ATTR_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` | `PORT_PHY_ATTR` / `PORT_PHY_SERDES_ATTR` | `portsorch.cpp:89` |
| `QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` | `QUEUE` / `WRED_ECN_QUEUE` | `portsorch.cpp:90` |
| `QUEUE_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `60000` | `QUEUE_WATERMARK` | `portsorch.cpp:91` |
| `PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `60000` | `PG_WATERMARK` | `portsorch.cpp:92` |
| `PG_DROP_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` | `PG_DROP` | `portsorch.cpp:93` |
| `PORT_RATE_FLEX_COUNTER_POLLING_INTERVAL_MS` (文字列) | `"1000"` | `PORT_RATES` / `RIF_RATES` | `portsorch.h:41` |

### 3. FLEX_COUNTER_DB グループ名文字列

`portsorch.h:29-43` の `#define` がコード中で実際に使われるグループ名文字列を定義する。CONFIG_DB の `FLEX_COUNTER_TABLE|<group>` キー名と対応する FLEX_COUNTER_DB グループ名は**別物**であることに注意。

| 定数名 | 文字列値 | 意味 |
|------|----|------|
| `PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PORT_STAT_COUNTER"` | portsorch.h:29 |
| `PORT_RATE_COUNTER_FLEX_COUNTER_GROUP` | `"PORT_RATE_COUNTER"` | portsorch.h:30 |
| `PORT_BUFFER_DROP_STAT_FLEX_COUNTER_GROUP` | `"PORT_BUFFER_DROP_STAT"` | portsorch.h:31 |
| `PORT_PHY_ATTR_FLEX_COUNTER_GROUP` | `"PORT_PHY_ATTR"` | portsorch.h:32 |
| `PORT_PHY_SERDES_ATTR_FLEX_COUNTER_GROUP` | `"PORT_PHY_SERDES_ATTR"` | portsorch.h:33 |
| `QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"QUEUE_STAT_COUNTER"` | portsorch.h:34 |
| `QUEUE_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"QUEUE_WATERMARK_STAT_COUNTER"` | portsorch.h:35 |
| `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_WATERMARK_STAT_COUNTER"` | portsorch.h:36 |
| `PG_DROP_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_DROP_STAT_COUNTER"` | portsorch.h:37 |
| `WRED_QUEUE_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"WRED_ECN_QUEUE_STAT_COUNTER"` | portsorch.h:42 |
| `WRED_PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"WRED_ECN_PORT_STAT_COUNTER"` | portsorch.h:43 |

### 4. flexcounterorch.cpp のグループキー文字列

`flexcounterorch.cpp:46-66` の `#define` が CONFIG_DB の `FLEX_COUNTER_TABLE|<group>` のキー名として使われる。

| 定数名 | 文字列値 |
|------|----|
| `BUFFER_POOL_WATERMARK_KEY` | `"BUFFER_POOL_WATERMARK"` |
| `PORT_KEY` | `"PORT"` |
| `PORT_PHY_ATTR_KEY` | `"PORT_PHY_ATTR"` |
| `PORT_PHY_SERDES_ATTR_KEY` | `"PORT_PHY_SERDES_ATTR"` |
| `PORT_BUFFER_DROP_KEY` | `"PORT_BUFFER_DROP"` |
| `QUEUE_KEY` | `"QUEUE"` |
| `QUEUE_WATERMARK` | `"QUEUE_WATERMARK"` |
| `PG_WATERMARK_KEY` | `"PG_WATERMARK"` |
| `PG_DROP_KEY` | `"PG_DROP"` |
| `RIF_KEY` | `"RIF"` |
| `ACL_KEY` | `"ACL"` |
| `TUNNEL_KEY` | `"TUNNEL"` |
| `FLOW_CNT_TRAP_KEY` | `"FLOW_CNT_TRAP"` |
| `FLOW_CNT_ROUTE_KEY` | `"FLOW_CNT_ROUTE"` |
| `ENI_KEY` | `"ENI"` |
| `DASH_METER_KEY` | `"DASH_METER"` |
| `WRED_QUEUE_KEY` | `"WRED_ECN_QUEUE"` |
| `WRED_PORT_KEY` | `"WRED_ECN_PORT"` |
| `SRV6_KEY` | `"SRV6"` |
| `SWITCH_KEY` | `"SWITCH"` |
| `HA_SET_KEY` | `"HA_SET"` |

### 5. CounterType → FLEX_COUNTER_DB フィールド名マッピング

`flex_counter_manager.cpp:37-60` の静的マップ `counter_id_field_lookup` が CounterType enum を FLEX_COUNTER_DB のフィールド名文字列へ変換する。

| CounterType enum | FLEX_COUNTER_DB フィールド名 |
|---|---|
| `PORT` | `PORT_COUNTER_ID_LIST` |
| `QUEUE` | `QUEUE_COUNTER_ID_LIST` |
| `QUEUE_ATTR` | `QUEUE_ATTR_ID_LIST` |
| `PRIORITY_GROUP` | `PG_COUNTER_ID_LIST` |
| `PORT_PHY_ATTR` | `PORT_PHY_ATTR_ID_LIST` |
| `PORT_PHY_SERDES_ATTR` | `PORT_PHY_SERDES_ATTR_ID_LIST` |
| `PORT_DEBUG` | `PORT_DEBUG_COUNTER_ID_LIST` |
| `SWITCH_DEBUG` | `SWITCH_DEBUG_COUNTER_ID_LIST` |
| `ACL_COUNTER` | `ACL_COUNTER_ATTR_ID_LIST` |
| `TUNNEL` | `TUNNEL_COUNTER_ID_LIST` |
| `HOSTIF_TRAP` | `FLOW_COUNTER_ID_LIST` |
| `ROUTE` | `FLOW_COUNTER_ID_LIST` |
| `ENI` | `ENI_COUNTER_ID_LIST` |
| `DASH_METER` | `DASH_METER_COUNTER_ID_LIST` |
| `SRV6` | `SRV6_COUNTER_ID_LIST` |
| `SWITCH` | `SWITCH_COUNTER_ID_LIST` |
| `HA_SET` | `HA_SET_COUNTER_ID_LIST` |

> HOSTIF_TRAP と ROUTE は同じフィールド名 `FLOW_COUNTER_ID_LIST` にマップされる。
> CounterType に存在しないエントリが `setCounterIdList()` から参照されると `SWSS_LOG_ERROR` でスキップ。
