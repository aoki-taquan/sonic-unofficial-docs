# srv6-counter — Phase E: ハードコード定数調査

slug: srv6-counter
phase: E
date: 2026-05-17
sources:
  - sonic-swss/orchagent/srv6orch.cpp (L26-27, L108, L138-139)
  - sonic-swss/orchagent/srv6orch.h (L30)
  - sonic-swss/orchagent/flexcounterorch.cpp (L44, L64, L96)
  - sonic-swss/orchagent/flex_counter/flow_counter_handler.cpp (L10-13)
  - sonic-swss-common/common/schema.h (L257, L313, L320, L335)

---

## 調査結果

### 1. CONFIG_DB キー / グループ名文字列

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `SRV6_KEY` | `"SRV6"` | `FLEX_COUNTER_TABLE` の SRV6 エントリキー | `flexcounterorch.cpp:64` |
| `SRV6_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"SRV6_STAT_COUNTER"` | FLEX_COUNTER_DB 上の group 名。`FlexCounterManager` 初期化時に指定 | `srv6orch.h:30` |
| `FLEX_COUNTER_STATUS_FIELD` | `"FLEX_COUNTER_STATUS"` | enable/disable を指定するフィールド名 | `schema.h:335` |
| `POLL_INTERVAL_FIELD` | `"POLL_INTERVAL"` | カウンタポーリング間隔フィールド名 | `schema.h:320` |

### 2. ポーリング間隔デフォルト (10 秒)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `SRV6_STAT_COUNTER_POLLING_INTERVAL_MS` | `10000` (ms) | `FlexCounterManager` 初期化時の `POLL_INTERVAL` 初期値 (`FLEX_COUNTER_TABLE|SRV6|POLL_INTERVAL` 未設定時に相当) | `srv6orch.cpp:27, 108` |

### 3. 非同期タイマー定数 (1 秒)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `SRV6_FLEX_COUNTER_UPDATE_TIMER` | `1` (秒) | `m_counter_update_timer` の周期。`m_pending_counters` が空になるまで 1 秒ごとに VIDTORID 確認を繰り返す | `srv6orch.cpp:26, 138` |
| `"SRV6_FLEX_COUNTER_UPDATE_TIMER"` | (タイマー名文字列) | `ExecutableTimer` の identifier | `srv6orch.cpp:139` |

### 4. COUNTERS_DB キー

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `COUNTERS_SRV6_NAME_MAP` | `"COUNTERS_SRV6_NAME_MAP"` | MySID エントリ名→カウンタ OID のマッピングテーブル (COUNTERS_DB) | `schema.h:257` |
| `SRV6_COUNTER_ID_LIST` | `"SRV6_COUNTER_ID_LIST"` | FLEX_COUNTER_DB 上の stat ID リストフィールド名 | `schema.h:313` |

### 5. SAI generic counter stat リスト (固定 2 種)

| stat | 意味 | ソース |
|------|------|--------|
| `SAI_COUNTER_STAT_PACKETS` | パケット数 | `flow_counter_handler.cpp:12` |
| `SAI_COUNTER_STAT_BYTES` | バイト数 | `flow_counter_handler.cpp:13` |

`FlowCounterHandler::getGenericCounterStatIdList()` で取得。SRV6 カウンタは trap/route カウンタと同じ generic_counter_stat_ids を共有する。ユーザによる増減は不可。

### 6. StatsMode

| 設定 | 値 | 用途 | ソース |
|------|-----|------|--------|
| `StatsMode::READ` | `"STATS_MODE_READ"` | `FlexCounterManager` 初期化時に固定指定。累積カウントのみ読取（クリアなし）| `srv6orch.cpp:108` |

### 7. FlexCounterOrch warm boot 遅延 (共通)

| 定数 | 値 | 用途 | ソース |
|------|----|------|--------|
| `FLEX_COUNTER_DELAY_SEC` | `60` (秒) | warm boot 後、`FlexCounterOrch::doTask` を no-op に保つ秒数。SRV6 の `FLEX_COUNTER_STATUS` 変更もこの遅延の影響を受ける | `flexcounterorch.cpp:44` |

## まとめ

ユーザが CONFIG_DB 経由で変更できるのは `FLEX_COUNTER_STATUS`（`enable`/`disable`）と `POLL_INTERVAL` のみ。それ以外の項目（stats_mode・stat ID リスト・group 名・タイマー周期・COUNTERS_DB キー名・warm-up 遅延）はすべてビルド時固定であり、ソースを修正してビルドし直さなければ変更できない。
