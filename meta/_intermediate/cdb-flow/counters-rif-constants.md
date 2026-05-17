# COUNTERS_DB RIF カウンタ — Phase E ハードコード定数スキャンノート

対象: `sonic-swss/orchagent/intfsorch.cpp`, `sonic-swss/orchagent/intfsorch.h`,
      `sonic-swss/orchagent/flexcounterorch.cpp`, `sonic-swss-common/common/schema.h`,
      `sonic-buildimage/dockers/docker-orchagent/enable_counters.py`

---

## 発見した定数

### intfsorch.h

| 定数名 | 値 | 行 | 用途 |
|--------|-----|-----|------|
| `RIF_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"RIF_STAT_COUNTER"` | L19 | syncd FlexCounter グループ名（通常カウンタ） |
| `RIF_RATE_COUNTER_FLEX_COUNTER_GROUP` | `"RIF_RATE_COUNTER"` | L20 | syncd FlexCounter グループ名（レートカウンタ） |
| `RIF_FLEX_STAT_COUNTER_POLL_MSECS` | `"1000"` | L21 | デフォルトポーリング間隔 (ms) |

### intfsorch.cpp

| 定数名 | 値 | 行 | 用途 |
|--------|-----|-----|------|
| `intfsorch_pri` | `35` | L43 | IntfsOrch の Orch 優先度 |
| `UPDATE_MAPS_SEC` | `1` (秒) | L45 | m_updateMapsTimer 間隔。m_rifsToAdd 処理タイマー |
| `rifStatIds[]` | 8 要素 | L49-59 | SAI カウンタ ID 静的配列 |

`rifStatIds[]` の全要素:
1. `SAI_ROUTER_INTERFACE_STAT_IN_PACKETS`
2. `SAI_ROUTER_INTERFACE_STAT_IN_OCTETS`
3. `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS`
4. `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_OCTETS`
5. `SAI_ROUTER_INTERFACE_STAT_OUT_PACKETS`
6. `SAI_ROUTER_INTERFACE_STAT_OUT_OCTETS`
7. `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS`
8. `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_OCTETS`

### flexcounterorch.cpp

| 定数名 | 値 | 行 | 用途 |
|--------|-----|-----|------|
| `FLEX_COUNTER_DELAY_SEC` | `60` (秒) | L44 | Warm-reboot 時の FlexCounter 遅延秒数 |
| `RIF_KEY` | `"RIF"` | L55 | FLEX_COUNTER_TABLE のキー識別子 |

### schema.h (sonic-swss-common)

| 定数名 | 値 | 行 | 用途 |
|--------|-----|-----|------|
| `RIF_COUNTER_ID_LIST` | `"RIF_COUNTER_ID_LIST"` | L302 | FLEX_COUNTER_DB へ SAI ID を登録するフィールド名 |
| `RIF_PLUGIN_FIELD` | `"RIF_PLUGIN_LIST"` | L330 | Lua プラグイン SHA を登録するフィールド名 |

### enable_counters.py (sonic-buildimage)

| 定数名 | 値 | 行 | 用途 |
|--------|-----|-----|------|
| `DEFAULT_SMOOTH_INTERVAL` | `"10"` (秒) | L10 | RATES:RIF の RIF_SMOOTH_INTERVAL デフォルト値 |
| `DEFAULT_ALPHA` | `"0.18"` | L11 | RATES:RIF の RIF_ALPHA デフォルト値 (= 2/(10+1)) |

---

## 変更可能性

- `RIF_FLEX_STAT_COUNTER_POLL_MSECS`: `counterpoll rif interval <msec>` で CONFIG_DB 経由で上書き可能。ただし定数はフォールバック値として使われる
- `rifStatIds[]`: コード変更なしには追加・削除不可。ASIC がサポートしない ID は syncd で N/A 扱い
- `DEFAULT_SMOOTH_INTERVAL` / `DEFAULT_ALPHA`: `config rate smoothing-interval <n> rif` で実行時変更可能
- `UPDATE_MAPS_SEC`: コード定数のみ。変更には再コンパイルが必要
- `FLEX_COUNTER_DELAY_SEC`: コード定数のみ
