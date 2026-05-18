# pwm (WATERMARK_TABLE) — Phase B ordering 調査メモ

## 調査対象

`docs/reference/config-db/pwm.md` の Phase B (書込み順依存) ブロック追加のための中間メモ。

## ソースコード確認箇所

### orchdaemon.cpp:432-437 — WatermarkOrch の登録テーブル

```cpp
vector<string> wm_tables = {
    CFG_WATERMARK_TABLE_NAME,
    CFG_FLEX_COUNTER_TABLE_NAME
};
WatermarkOrch *wm_orch = new WatermarkOrch(m_configDb, wm_tables);
```

`WatermarkOrch` は `WATERMARK_TABLE` と `FLEX_COUNTER_TABLE` の両方を同時に購読する。
orchdaemon.cpp 内の `m_orchList` 順 (line 500) では `wm_orch` は `gQosOrch` の直後に配置。

### watermarkorch.cpp:52-91 — doTask(Consumer) — 振り分けロジック

```cpp
if (!gPortsOrch->allPortsReady())
    return;
// ...
if (consumer.getTableName() == CFG_WATERMARK_TABLE_NAME)
    handleWmConfigUpdate(key, fvt);
else if (consumer.getTableName() == CFG_FLEX_COUNTER_TABLE_NAME)
    handleFcConfigUpdate(key, fvt);
```

- `gPortsOrch->allPortsReady()` が false の間は両テーブルの処理が**ブロックされる**。
- FLEX_COUNTER_TABLE イベントと WATERMARK_TABLE イベントは独立して処理される。

### watermarkorch.cpp:116-141 — handleFcConfigUpdate — タイマー起動条件

```cpp
uint8_t prevStatus = m_wmStatus;
if (key == "QUEUE_WATERMARK" || key == "PG_WATERMARK")
{
    for (... i: fvt)
    {
        if (i.first == "FLEX_COUNTER_STATUS")
        {
            if (i.second == "enable")
                m_wmStatus = (uint8_t)(m_wmStatus | groupToMask.at(key));
            else if (i.second == "disable")
                m_wmStatus = (uint8_t)(m_wmStatus & ~(groupToMask.at(key)));
        }
    }
    if (!prevStatus && m_wmStatus)
        m_telemetryTimer->start();
}
```

- `FLEX_COUNTER_TABLE|QUEUE_WATERMARK` または `FLEX_COUNTER_TABLE|PG_WATERMARK` の `FLEX_COUNTER_STATUS=enable` を受信して初めてタイマーが起動する。
- WATERMARK_TABLE のインターバル設定だけではタイマーは起動しない（タイマーは `m_wmStatus != 0` が必要条件）。

### watermarkorch.cpp:94-113 — handleWmConfigUpdate — インターバル設定

```cpp
if (key == "TELEMETRY_INTERVAL")
{
    if (i.first == "interval")
    {
        auto intervT = timespec { .tv_sec = static_cast<time_t>(to_uint<uint32_t>(i.second.c_str())), .tv_nsec = 0 };
        m_telemetryTimer->setInterval(intervT);
        m_timerChanged = true;  // 次のタイマー満了時に reset()
    }
}
```

インターバル変更は即時反映されず、現タイマーが満了した次のサイクルから有効になる。

## 確認された順序依存

1. **PortsOrch allPortsReady → WatermarkOrch 処理開始** (強制先行ガード)
2. **FLEX_COUNTER_TABLE enable → telemetry タイマー起動** (前提条件。WATERMARK_TABLE 設定はタイマー起動に影響しない)
3. **WATERMARK_TABLE|TELEMETRY_INTERVAL 書込み順序は任意** (enable 前後どちらでも機能するが、enable 後のインターバル変更は次周期適用)

## 注意点

- `WATERMARK_TABLE|TELEMETRY_INTERVAL` は FLEX_COUNTER enable の前後どちらに書いても機能する。
- ただし enable より後に `interval` を変更した場合、変更が現タイマー周期内なら次の満了まで待つ必要がある。
- `FLEX_COUNTER_TABLE` の `QUEUE_WATERMARK`/`PG_WATERMARK` が両方 disable の間はタイマーが停止し、PERIODIC_WATERMARKS の自動クリアは発生しない。
