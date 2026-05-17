# COUNTERS_DB PORT カウンタ — Phase E ハードコード定数スキャンノート

対象テーブル: `COUNTERS_PORT_NAME_MAP` / `COUNTERS:<oid>` / flex counter グループ制御  
ソース: `sonic-swss/orchagent/portsorch.cpp`, `sonic-swss/orchagent/portsorch.h`, `sonic-swss/orchagent/flexcounterorch.cpp`  
スキャン範囲: `#define` 全行, `const vector<>` 宣言, `FlexCounterManager` コンストラクタ引数 全行精読

---

## 検出したハードコード定数

### ポーリング間隔定数

| 定数名 | 値 | 対象グループ | ソース |
|--------|----|------------|--------|
| `PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | **1000** ms | `PORT_STAT_COUNTER` / `WRED_ECN_PORT_STAT_COUNTER` | portsorch.cpp:87 |
| `PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS` | **60000** ms | `PORT_BUFFER_DROP_STAT` | portsorch.cpp:88 |
| `PORT_PHY_ATTR_FLEX_COUNTER_POLLING_INTERVAL_MS` | **10000** ms | `PORT_PHY_ATTR` | portsorch.cpp:89 |
| `PORT_RATE_FLEX_COUNTER_POLLING_INTERVAL_MS` | **"1000"** ms (文字列) | `PORT_RATE_COUNTER` | portsorch.h:41 |

これらは `FlexCounterManager` コンストラクタへの初期値として渡され、`FLEX_COUNTER_TABLE|<group>|POLL_INTERVAL` が CONFIG_DB で指定されない場合に syncd へ投入されるデフォルト値となる。`counterpoll show` で表示される「default」値とは別に、コード側からも同じ値がハードコードされている。

### flex counter グループ名定数

| 定数名 | 値（FLEX_COUNTER_DB キー prefix） | 用途 | ソース |
|--------|----------------------------------|------|--------|
| `PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PORT_STAT_COUNTER"` | 通常ポートカウンタグループ名 | portsorch.h:29 |
| `PORT_RATE_COUNTER_FLEX_COUNTER_GROUP` | `"PORT_RATE_COUNTER"` | ポートレートカウンタグループ名 | portsorch.h:30 |
| `PORT_BUFFER_DROP_STAT_FLEX_COUNTER_GROUP` | `"PORT_BUFFER_DROP_STAT"` | バッファドロップカウンタグループ名 | portsorch.h:31 |
| `PORT_PHY_ATTR_FLEX_COUNTER_GROUP` | `"PORT_PHY_ATTR"` | PHY 属性カウンタグループ名 | portsorch.h:32 |
| `PORT_PHY_SERDES_ATTR_FLEX_COUNTER_GROUP` | `"PORT_PHY_SERDES_ATTR"` | PHY SerDes 属性カウンタグループ名 | portsorch.h:33 |
| `WRED_PORT_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"WRED_ECN_PORT_STAT_COUNTER"` | WRED ポートカウンタグループ名 | portsorch.h:43 |

### flex counter テーブルキー定数（FlexCounterOrch 用）

| 定数名 | 値（FLEX_COUNTER_TABLE のキー） | ソース |
|--------|-------------------------------|--------|
| `PORT_KEY` | `"PORT"` | flexcounterorch.cpp:47 |
| `PORT_PHY_ATTR_KEY` | `"PORT_PHY_ATTR"` | flexcounterorch.cpp:48 |
| `PORT_PHY_SERDES_ATTR_KEY` | `"PORT_PHY_SERDES_ATTR"` | flexcounterorch.cpp:49 |
| `PORT_BUFFER_DROP_KEY` | `"PORT_BUFFER_DROP"` | flexcounterorch.cpp:50 |
| `WRED_PORT_KEY` | `"WRED_ECN_PORT"` | flexcounterorch.cpp:63 |

### warm-reboot 遅延定数

| 定数名 | 値 | 用途 | ソース |
|--------|----|------|--------|
| `FLEX_COUNTER_DELAY_SEC` | **60** 秒 | warm-reboot 時に FlexCounter 処理を遅延させるタイマー値。この間 PORT / QUEUE 等全グループの処理がブロックされる | flexcounterorch.cpp:44 |

### その他ポート関連定数

| 定数名 | 値 | 用途 | ソース |
|--------|----|------|--------|
| `PORT_STATE_POLLING_SEC` | **5** 秒 | ポートオペ状態ポーリング間隔（カウンタ収集とは独立） | portsorch.cpp:86 |
| `DEFAULT_SYSTEM_PORT_MTU` | **9100** バイト | システムポートのデフォルト MTU | portsorch.cpp:79 |

---

## 注意事項

- `PORT_BUFFER_DROP_STAT_POLLING_INTERVAL_MS = 60000` は `counterpoll` CLI 許容下限（30000 ms）より大きいため、CLI 経由での変更は 30000 ms 以上であれば受け付けられる。
- `PORT_RATE_FLEX_COUNTER_POLLING_INTERVAL_MS` は文字列 `"1000"` として定義されており（portsorch.h:41）、syncd への SetTable 呼び出しに直接渡される。
- `FLEX_COUNTER_DELAY_SEC = 60` は warm-reboot 固有であり、cold boot では即 `m_delayTimerExpired = true` となるためこの値は使用されない。
