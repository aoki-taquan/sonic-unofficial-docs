# FLEX_COUNTER_TABLE|PG_WATERMARK — フィールド暗黙デフォルト調査メモ (Phase A)

調査日: 2026-05-15
対象テーブル: CONFIG_DB `FLEX_COUNTER_TABLE|PG_WATERMARK`

---

## 調査対象ファイル

| ファイル | リポ | 役割 |
|---------|------|------|
| `orchagent/portsorch.cpp` | sonic-swss | FlexCounterGroup 登録・PG カウンタ追加ロジック |
| `orchagent/portsorch.h` | sonic-swss | 定数定義（グループ名・ポーリング間隔） |
| `orchagent/flexcounterorch.cpp` | sonic-swss | FLEX_COUNTER_TABLE 購読・enable/disable ハンドラ |
| `orchagent/watermarkorch.cpp` | sonic-swss | telemetry タイマー・watermark clear ハンドラ |
| `counterpoll/main.py` | sonic-utilities | CLI `counterpoll watermark` |
| `yang-models/sonic-flex_counter.yang` | sonic-buildimage | YANG スキーマ |
| `minigraph.py` | sonic-buildimage | 管理デバイスでの disable 設定 |

---

## フィールド別 コード由来デフォルト

### `FLEX_COUNTER_STATUS`

**コード由来デフォルト**: `"disable"`（エントリ未設定時）

証跡 — `counterpoll/main.py:819`:
```python
data.append(["PG_WATERMARK_STAT", pg_wm_info.get("POLL_INTERVAL", DEFLT_60_SEC),
             pg_wm_info.get("FLEX_COUNTER_STATUS", DISABLE)])
```
`DISABLE = "disable"` (main.py:16) が fallback として使われる。
- orchagent (`flexcounterorch.cpp:265-268`): `FLEX_COUNTER_TABLE|PG_WATERMARK` が来たとき `i.second == "enable"` のときのみ `m_pg_watermark_enabled = true` にセット。
- **管理デバイス例外**: `minigraph.py:58/2740` で `PG_WATERMARK` を含む `mgmt_disabled_counters` が `FLEX_COUNTER_STATUS = "disable"` に明示設定される。

---

### `POLL_INTERVAL`

**コード由来デフォルト**: `60000`（ms）

証跡:
- `portsorch.h:39`: `#define PG_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS "60000"`
- `portsorch.cpp:92`: `#define PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS 60000`
- `portsorch.cpp:736`: `pg_watermark_manager(PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP, StatsMode::READ_AND_CLEAR, PG_WATERMARK_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS, false)`
- `portsorch.cpp:872-876`: `setFlexCounterGroupParameter(PG_WATERMARK_STAT_COUNTER_FLEX_COUNTER_GROUP, PG_WATERMARK_FLEX_STAT_COUNTER_POLL_MSECS, STATS_MODE_READ_AND_CLEAR, PG_PLUGIN_FIELD, pgWmSha)`
- `counterpoll/main.py:18`: `DEFLT_60_SEC = "default (60000)"` — `pg_wm_info.get("POLL_INTERVAL", DEFLT_60_SEC)` が CLI 表示 fallback

`counterpoll watermark interval <ms>` で上書き可能（POLL_INTERVAL フィールドを書き込む）。

---

### `STATS_MODE` (内部値)

ユーザーが CONFIG_DB で設定するフィールドではない。orchagent が `setFlexCounterGroupParameter()` 呼び出し時に `STATS_MODE_READ_AND_CLEAR` を渡す (`portsorch.cpp:874`)。syncd FlexCounter がポーリングのたびに SAI カウンタをリセットする副作用がある。

---

### `FLEX_COUNTER_DELAY_STATUS`

**コード由来デフォルト**: 設定なし（`false` 相当）

YANG では `flex_delay_status` 型で定義されるが、fast-reboot 等特殊フローでのみ明示設定される。通常運用では FLEX_COUNTER_TABLE|PG_WATERMARK エントリにこのフィールドは存在しない。

---

### `BULK_CHUNK_SIZE` / `BULK_CHUNK_SIZE_PER_PREFIX`

**コード由来デフォルト**: 設定なし（syncd 側デフォルト使用）

YANG で定義されるがコード上の初期値は syncd FlexCounter 実装依存。通常 CONFIG_DB には書かれない。

---

## FlexCounter グループ登録フロー

1. portsorch コンストラクタ (`portsorch.cpp:736`) で `pg_watermark_manager` を `StatsMode::READ_AND_CLEAR` / 60000 ms で初期化。
2. portsorch init 時 (`portsorch.cpp:872-876`) に `setFlexCounterGroupParameter()` → syncd の `FLEX_COUNTER_GROUP_TABLE|PG_WATERMARK_STAT_COUNTER` にポーリング設定を書き込み。
3. `flexcounterorch.cpp:265-270`: FLEX_COUNTER_TABLE|PG_WATERMARK の `FLEX_COUNTER_STATUS=enable` を受けて `m_pg_watermark_enabled = true` をセット。
4. `portsorch.cpp:9048-9051`: `addPriorityGroupWatermarkFlexCountersPerPortPerPgIndex()` が `pg_watermark_manager.setCounterIdList()` を呼び SAI OID を FlexCounter DB に登録。

**先行条件**: `FLEX_COUNTER_TABLE|PG_WATERMARK` が `enable` でない状態で BUFFER_PG を設定しても SAI カウンタは登録されない（`getPgWatermarkCountersState()` チェック）。後から enable した場合は `addPriorityGroupWatermarkFlexCounters()` 再実行で追加される。

---

## 収集する SAI カウンタ

`portsorch.cpp:410-414` の静的配列 `ingressPriorityGroupWatermarkStatIds`:

```cpp
static const vector<sai_ingress_priority_group_stat_t> ingressPriorityGroupWatermarkStatIds =
{
    SAI_INGRESS_PRIORITY_GROUP_STAT_XOFF_ROOM_WATERMARK_BYTES,
    SAI_INGRESS_PRIORITY_GROUP_STAT_SHARED_WATERMARK_BYTES,
};
```

YANG / CONFIG_DB からは変更不可。ハードコード。

---

## watermarkorch との連携

`watermarkorch.cpp:41-44` で DEFAULT_TELEMETRY_INTERVAL = 120 秒の telemetry タイマーを初期化。`handleFcConfigUpdate()` (watermarkorch.cpp:116-141) が `PG_WATERMARK` と `QUEUE_WATERMARK` を同時監視し、どちらかが enable になると `m_telemetryTimer->start()` を呼んで周期型ウォーターマーク (PERIODIC_WATERMARKS) のリセットをスケジュール。
