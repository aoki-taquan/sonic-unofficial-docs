# counters-rif Phase A — defaults 調査メモ

対象ページ: `docs/reference/config-db/counters-rif.md`
調査日: 2026-05-15
調査者: Claude (batch agent)

## 調査対象ソース

| ファイル | 用途 |
|---------|------|
| `sonic-swss/orchagent/intfsorch.cpp` | RIF カウンタ ID 列挙・flex counter 登録 |
| `sonic-swss/orchagent/intfsorch.h` | ポーリング間隔定数 (`RIF_FLEX_STAT_COUNTER_POLL_MSECS = "1000"`) |
| `sonic-swss/orchagent/rif_rates.lua` | EMA レート計算 Lua プラグイン |
| `sonic-swss-common/common/schema.h` | `COUNTERS_RIF_NAME_MAP`, `COUNTERS_RIF_TYPE_MAP`, `RIF_COUNTER_ID_LIST`, `RIF_PLUGIN_FIELD` 定義 |
| `sonic-utilities/scripts/intfstat` | カウンタ読み取り・表示ロジック |
| `sonic-utilities/counterpoll/main.py` | counterpoll rif サブコマンド・`DEFLT_1_SEC` フォールバック |
| `sonic-buildimage/dockers/docker-orchagent/enable_counters.py` | 起動時 `RATES:RIF` デフォルト書き込み |

## 発見事項

### 1. ポーリング間隔 (RIF_FLEX_STAT_COUNTER_POLL_MSECS)

- `intfsorch.h:21`: `#define RIF_FLEX_STAT_COUNTER_POLL_MSECS "1000"`
- `intfsorch.cpp:96-100`: `setFlexCounterGroupParameter(RIF_STAT_COUNTER_FLEX_COUNTER_GROUP, RIF_FLEX_STAT_COUNTER_POLL_MSECS, ...)` で syncd に 1000ms が投入される
- `counterpoll/main.py:20`: `DEFLT_1_SEC = "default (1000)"` → `counterpoll show` のフォールバック表示値も 1000ms

### 2. SAI カウンタ ID セット (rifStatIds)

`intfsorch.cpp:49-59` に 8 フィールド定義:
- `SAI_ROUTER_INTERFACE_STAT_IN_PACKETS`
- `SAI_ROUTER_INTERFACE_STAT_IN_OCTETS`
- `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_PACKETS`
- `SAI_ROUTER_INTERFACE_STAT_IN_ERROR_OCTETS`
- `SAI_ROUTER_INTERFACE_STAT_OUT_PACKETS`
- `SAI_ROUTER_INTERFACE_STAT_OUT_OCTETS`
- `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_PACKETS`
- `SAI_ROUTER_INTERFACE_STAT_OUT_ERROR_OCTETS`

### 3. RATES テーブル (rif_rates.lua)

`rif_rates.lua` は `RATES:RIF` から設定を読んで EMA でレートを計算:
- 入力: `SAI_ROUTER_INTERFACE_STAT_IN/OUT_OCTETS/PACKETS` の差分
- 出力: `RATES:<oid>` の `RX_BPS`, `RX_PPS`, `TX_BPS`, `TX_PPS`
- 初回: `INIT_DONE = "COUNTERS_LAST"` にセットしてカウンタ値のスナップショットを保存
- 2回目以降: 差分計算 → `"DONE"` になったら EMA 適用

### 4. EMA パラメータのデフォルト (enable_counters.py)

`enable_counters.py:10-11`:
- `DEFAULT_SMOOTH_INTERVAL = '10'`（ウィンドウ 10 秒）
- `DEFAULT_ALPHA = '0.18'`（= 2/(10+1) ≈ 0.1818...）

`RATES:RIF` に書き込まれるキー:
- `RIF_SMOOTH_INTERVAL`: 10
- `RIF_ALPHA`: 0.18

RIF_ALPHA 未定義の場合、Lua スクリプトは早期 return → レート計算ゼロ。

### 5. 起動遅延

`enable_counters.py:57-64`:
- uptime < 300s → sleep(180) 後に書き込み
- uptime >= 300s → sleep(60) 後に書き込み

### 6. counterpoll CLI デフォルト状態

`counterpoll/main.py:814-815`:
```python
if rif_info:
    data.append(["RIF_STAT", rif_info.get("POLL_INTERVAL", DEFLT_1_SEC), rif_info.get("FLEX_COUNTER_STATUS", DISABLE)])
```
- POLL_INTERVAL 未設定 → `"default (1000)"` 表示
- FLEX_COUNTER_STATUS 未設定 → `"disable"` 表示

## 結論

`<!-- defaults -->` セクションに記載すべき主要事項:
1. ポーリング間隔ハードコード: 1000ms (`RIF_FLEX_STAT_COUNTER_POLL_MSECS`)
2. FLEX_COUNTER_STATUS 未設定時はカウンタ収集なし
3. EMA デフォルト: smooth_interval=10, alpha=0.18
4. RIF_ALPHA 未定義時の early return (Lua)
5. 起動遅延: 180s or 60s
