# FLEX_COUNTER_TABLE|PG_WATERMARK — Phase E ハードコード定数スキャンノート

対象エントリ: `CONFIG_DB FLEX_COUNTER_TABLE|PG_WATERMARK`
Consumer: `FlexCounterOrch::doTask()`, `PortsOrch` PG watermark manager, `WatermarkOrch::doTask()`
スキャン範囲: `orchagent/portsorch.h:35-41`, `orchagent/portsorch.cpp:88-93,736,872-876`, `orchagent/flexcounterorch.cpp:44,79,127`, `orchagent/watermarkorch.cpp:9-17,41`

---

## 検出したハードコード定数

### ポーリング間隔 (POLL_INTERVAL)

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `60000` ms | `pg_watermark_manager` コンストラクタ引数 (`StatsMode::READ_AND_CLEAR`) — syncd に渡すデフォルトポーリング間隔 | `portsorch.cpp:92,736` |
| `PG_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS` | `"60000"` | `setFlexCounterGroupParameter()` で `FLEX_COUNTER_GROUP_TABLE|PG_WATERMARK_STAT_COUNTER` に書き込む文字列定数 | `portsorch.h:39`, `portsorch.cpp:872-876` |

どちらも同一の 60000 ms を異なる型（int / const char*）で保持し、orchagent init 時に syncd へ書き込む。CONFIG_DB の `POLL_INTERVAL` フィールドが設定されると上書きされる。

### FlexCounter グループ名

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_WATERMARK_STAT_COUNTER"` | FLEX_COUNTER_DB のグループキー。`pg_watermark_manager` および `setFlexCounterGroupParameter()` で使用 | `portsorch.h:36` |

このグループ名は CONFIG_DB / YANG で変更不可。FlexCounter インフラが内部的に `FLEX_COUNTER_GROUP_TABLE|PG_WATERMARK_STAT_COUNTER` キーで管理する。

### FlexCounter 遅延タイマー

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `FLEX_COUNTER_DELAY_SEC` | `60` 秒 | warm-reboot 時に `FlexCounterOrch::doTask()` 全体をブロックする遅延タイマー。cold boot では即座に満了 (`m_delayTimerExpired = true`) | `flexcounterorch.cpp:44,127,136` |

### watermarkorch telemetry タイマー

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `DEFAULT_TELEMETRY_INTERVAL` | `120` 秒 | `WatermarkOrch` が `PERIODIC_WATERMARKS` テーブルを周期クリアするタイマーのデフォルト間隔。`WATERMARK_TABLE|TELEMETRY_INTERVAL` で上書き可能 | `watermarkorch.cpp:9,41` |

### watermarkorch クリアリクエスト文字列

| 定数名 | 値 | 用途 | ソース |
|--------|-----|------|--------|
| `CLEAR_PG_HEADROOM_REQUEST` | `"PG_HEADROOM"` | `APPL_DB WATERMARK_CLEAR_REQUEST` 通知の op 文字列 — PG headroom watermark クリア | `watermarkorch.cpp:11` |
| `CLEAR_PG_SHARED_REQUEST` | `"PG_SHARED"` | 同上 — PG shared watermark クリア | `watermarkorch.cpp:12` |

この 2 つは `counterpoll watermark` / `watermarkcfg clear` CLI が使用する op 名。CONFIG_DB とは無関係で APPL_DB 通知経路のみに関係する。

### SAI カウンタ ID（収集対象）

`portsorch.cpp:410-414` の静的配列（CONFIG_DB / YANG から変更不可）:

```cpp
static const vector<sai_ingress_priority_group_stat_t> ingressPriorityGroupWatermarkStatIds =
{
    SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES,
    SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES,
};
```

これらの SAI stat ID は文字列定数ではなく enum 値であり、`pg_watermark_manager.setCounterIdList()` が FLEX_COUNTER_DB の `PG_WATERMARK_STAT_ID_LIST` フィールドとして書き込む。ユーザーが収集対象を追加・変更する手段はない。

---

## 定数サマリ

| 定数 | 値 | 変更可否 |
|------|----|---------|
| `PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | 60000 ms | CONFIG_DB `POLL_INTERVAL` で上書き可 |
| `PG_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS` | `"60000"` | 同上（init 時のみ使用） |
| `PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"PG_WATERMARK_STAT_COUNTER"` | 変更不可 |
| `FLEX_COUNTER_DELAY_SEC` | 60 秒 | 変更不可（warm-reboot 専用） |
| `DEFAULT_TELEMETRY_INTERVAL` | 120 秒 | `WATERMARK_TABLE\|TELEMETRY_INTERVAL` で上書き可 |
| `CLEAR_PG_HEADROOM_REQUEST` | `"PG_HEADROOM"` | 変更不可（APPL_DB 通知プロトコル） |
| `CLEAR_PG_SHARED_REQUEST` | `"PG_SHARED"` | 変更不可（同上） |
| SAI stat IDs (2 件) | XOFF_ROOM / SHARED WATERMARK_BYTES | 変更不可 |
