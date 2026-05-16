# pwm-defaults — Phase A コード由来暗黙デフォルト調査

対象: `docs/reference/config-db/pwm.md`
調査日: 2026-05-14

## 調査対象テーブル

`WATERMARK_TABLE` (CONFIG_DB)。periodic watermark の telemetry 周期を制御する。
key は `TELEMETRY_INTERVAL` のシングルトン。フィールドは `interval` (秒) のみ。

---

## フィールド列挙

| フィールド | スコープ | YANG default 宣言 |
|---|---|---|
| `interval` | `TELEMETRY_INTERVAL` | なし（YANG モデルなし） |

`WATERMARK_TABLE` は YANG モデルが存在しない（`sonic-buildimage` の yang-models/ に対応 `.yang` ファイルなし）。
スキーマ検証は orchagent 側のランタイム型変換 (`to_uint<uint32_t>`) のみ。

---

## コード由来の暗黙デフォルト

### 1. `interval` — ハードコードデフォルト `120` 秒

**ソース**: `sonic-swss/orchagent/watermarkorch.cpp:9`
```cpp
#define DEFAULT_TELEMETRY_INTERVAL 120
```

`WatermarkOrch` コンストラクタ (`watermarkorch.cpp:41`) でこのマクロを使ってタイマーを初期化:
```cpp
auto intervT = timespec { .tv_sec = DEFAULT_TELEMETRY_INTERVAL , .tv_nsec = 0 };
m_telemetryTimer = new SelectableTimer(intervT);
```

`WATERMARK_TABLE|TELEMETRY_INTERVAL` エントリが CONFIG_DB に存在しない場合、orchagent は **120 秒**を telemetry 周期として使用して PERIODIC_WATERMARKS を定期クリアする。

**テストコード確認** (`sonic-swss/tests/test_watermark.py:32`):
```python
DEFAULT_TELEMETRY_INTERVAL = 120
```
テストでも同値 120 秒を期待値として使用しており、デフォルトが 120 秒であることを間接的に確認。

**`watermarkcfg` CLI の show 表示** (`sonic-utilities/scripts/watermarkcfg`):
```python
def show_interval(self):
    wm_info = configdb.get_entry('WATERMARK_TABLE', 'TELEMETRY_INTERVAL')
    if wm_info:
        print('\nTelemetry interval: ' + wm_info['interval'] + ' second(s)\n')
    else:
        print('\nTelemetry interval 120 second(s)\n')
```
エントリが存在しない場合に `120 second(s)` を表示する実装は、デフォルトが 120 秒であることを CLI レベルでも示している。

---

### 2. タイマー起動条件 — FLEX_COUNTER 有効時のみ

`WatermarkOrch::handleFcConfigUpdate()` (`watermarkorch.cpp:125-138`):
```cpp
if (!prevStatus && m_wmStatus)
{
    m_telemetryTimer->start();
}
```

`QUEUE_WATERMARK` または `PG_WATERMARK` の `FLEX_COUNTER_STATUS` が `enable` に変わったタイミングで telemetry タイマーが起動する。
Flex counter が disable のままだとタイマーは起動せず、PERIODIC_WATERMARKS のクリアも発生しない。

初期状態: `m_wmStatus = 0`（全 watermark 無効）。タイマーは停止状態 (`doTask(timer)` 内の `!m_wmStatus` 時に `stop()` を呼ぶ）。

---

### 3. インターバル変更の反映タイミング — 次タイマー満了後

`handleWmConfigUpdate()` 内のコメント (`watermarkorch.cpp:105`):
```cpp
// reset the timer interval when current timer expires
m_timerChanged = true;
```

`doTask(SelectableTimer &timer)` 内:
```cpp
if (m_timerChanged)
{
    m_telemetryTimer->reset();
    m_timerChanged = false;
}
```

`WATERMARK_TABLE|TELEMETRY_INTERVAL` を更新しても、現在の telemetry 間隔が満了するまで新しいインターバルは適用されない（next tick 適用）。

---

## 検出サマリ

| 種別 | フィールド | 値 | ソース |
|---|---|---|---|
| ハードコードデフォルト | `interval` | `120` 秒 | `watermarkorch.cpp:9` (`#define DEFAULT_TELEMETRY_INTERVAL 120`) |
| CLI 表示デフォルト | `interval` 未設定表示 | `120 second(s)` | `watermarkcfg:show_interval()` |
| タイマー起動条件 | 自動起動 | QUEUE_WATERMARK/PG_WATERMARK enable 時のみ | `watermarkorch.cpp:133` |
| インターバル変更反映 | next-tick 適用 | 現周期満了後 | `watermarkorch.cpp:105`, `245` |
