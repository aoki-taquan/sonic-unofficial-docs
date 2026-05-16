# FLEX_COUNTER_TABLE — Phase E: ハードコード定数調査

## 対象ファイル

- `sonic-swss/orchagent/flexcounterorch.cpp` (warm-reboot 遅延秒数、グループキー文字列)
- `sonic-utilities/counterpoll/main.py` (CLI 表示用デフォルト poll_interval、status enum)

---

## 1. warm-reboot 遅延定数 (flexcounterorch.cpp L44)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `FLEX_COUNTER_DELAY_SEC` | `60` 秒 | warm-reboot 時に `SelectableTimer` をこの秒数で起動し、その間は全 SET を無視する (`m_delayTimerExpired = false`)。通常起動では使用しない | flexcounterorch.cpp L44, L127 |

---

## 2. カウンタグループキー文字列定数 (flexcounterorch.cpp L46-66)

orchagent が CONFIG_DB キーとして受け付けるグループ名のハードコード定義。

| 定数 | 値 | ソース |
|------|----|--------|
| `BUFFER_POOL_WATERMARK_KEY` | `"BUFFER_POOL_WATERMARK"` | flexcounterorch.cpp L46 |
| `PORT_KEY` | `"PORT"` | L47 |
| `PORT_PHY_ATTR_KEY` | `"PORT_PHY_ATTR"` | L48 |
| `PORT_PHY_SERDES_ATTR_KEY` | `"PORT_PHY_SERDES_ATTR"` | L49 |
| `PORT_BUFFER_DROP_KEY` | `"PORT_BUFFER_DROP"` | L50 |
| `QUEUE_KEY` | `"QUEUE"` | L51 |
| `QUEUE_WATERMARK` | `"QUEUE_WATERMARK"` | L52 |
| `PG_WATERMARK_KEY` | `"PG_WATERMARK"` | L53 |
| `PG_DROP_KEY` | `"PG_DROP"` | L54 |
| `RIF_KEY` | `"RIF"` | L55 |
| `ACL_KEY` | `"ACL"` | L56 |
| `TUNNEL_KEY` | `"TUNNEL"` | L57 |
| `FLOW_CNT_TRAP_KEY` | `"FLOW_CNT_TRAP"` | L58 |
| `FLOW_CNT_ROUTE_KEY` | `"FLOW_CNT_ROUTE"` | L59 |
| `ENI_KEY` | `"ENI"` | L60 |
| `DASH_METER_KEY` | `"DASH_METER"` | L61 |
| `WRED_QUEUE_KEY` | `"WRED_ECN_QUEUE"` | L62 |
| `WRED_PORT_KEY` | `"WRED_ECN_PORT"` | L63 |
| `SRV6_KEY` | `"SRV6"` | L64 |
| `SWITCH_KEY` | `"SWITCH"` | L65 |
| `HA_SET_KEY` | `"HA_SET"` | L66 |

> `flexCounterGroupMap`（L68-96）はこれら定数を SAI flex counter group 定数にマッピングする `unordered_map`。ここに含まれないキーは `SWSS_LOG_NOTICE("Invalid flex counter group input")` でスキップされる。

---

## 3. FLEX_COUNTER_STATUS enum 値 (flexcounterorch.cpp L225-370, counterpoll/main.py L15-16)

| 値 | 意味 | ソース |
|----|------|--------|
| `"enable"` | カウンタポーリング有効化。各グループフラグ (`m_port_counter_enabled` 等) を `true` にセットし COUNTER_ID_LIST を syncd へ投入 | flexcounterorch.cpp L235 |
| `"disable"` | カウンタポーリング停止。フラグを `false` にリセット | flexcounterorch.cpp L356, 318, 331 |

定数 `ENABLE = "enable"`, `DISABLE = "disable"` は counterpoll/main.py L15-16 でも定義。YANG 制約 (`flex_counter_status`) でも同値。

---

## 4. POLL_INTERVAL CLI ソフトデフォルト (counterpoll/main.py L18-20)

`POLL_INTERVAL` フィールドの YANG デフォルト宣言は存在しない。counterpoll CLI の `show` サブコマンドが CONFIG_DB に値がない場合に表示するソフトデフォルト:

| 定数 | 値 | 対象グループ | ソース |
|------|----|------------|--------|
| `DEFLT_1_SEC` | `"default (1000)"` ms | `PORT`, `RIF`, `WRED_ECN_PORT` | counterpoll/main.py L20 |
| `DEFLT_10_SEC` | `"default (10000)"` ms | `QUEUE`, `PG_DROP`, `ACL`, `TUNNEL`, `FLOW_CNT_TRAP`, `FLOW_CNT_ROUTE`, `WRED_ECN_QUEUE`, `SRV6`, `ENI`, `HA_SET`, `PORT_PHY_ATTR` | counterpoll/main.py L19 |
| `DEFLT_60_SEC` | `"default (60000)"` ms | `BUFFER_POOL_WATERMARK`, `QUEUE_WATERMARK`, `PG_WATERMARK`, `SWITCH`, `PORT_BUFFER_DROP` | counterpoll/main.py L18 |

> これらは**表示のみの定数**。orchagent / syncd にこれらの値はハードコードされておらず、CONFIG_DB に値がなければポーリング間隔は syncd 側 fallback（各 SAI adapter の実装依存）になる。

---

## 5. CLI 入力範囲制約 (counterpoll/main.py)

| グループ | `IntRange` 下限 | `IntRange` 上限 | ソース行 |
|---------|---------------|---------------|---------|
| `QUEUE`, `PORT`, `PG_DROP`, `ACL`, `FLOW_CNT_TRAP`, `FLOW_CNT_ROUTE`, `WRED_ECN_QUEUE`, `WRED_ECN_PORT`, `RIF`, `SRV6`, `ENI`, `HA_SET`, `PORT_PHY_ATTR` | 100〜1000 ms (グループ依存) | 30000 ms | 各 interval コマンド |
| `WATERMARK` (QUEUE_WATERMARK, PG_WATERMARK, BUFFER_POOL_WATERMARK), `SWITCH` | 1000 ms | 60000 ms | L323, L733 |
| `PORT_BUFFER_DROP` | **30000** ms | **300000** ms | L152 (CPU 負荷大のため下限 30s) |

YANG の `poll_interval` typedef は `range 100..4294967295` で全グループ統一。CLI が group ごとに異なる上限を `IntRange` で強制しており、YANG バリデーションだけでは CLI の下限・上限が守られない。
