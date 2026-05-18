# pg-watermark — Phase B ordering 調査メモ

## 調査対象

`docs/reference/config-db/pg-watermark.md` の Phase B (書込み順依存) ブロック追加のための中間メモ。

## ソースコード確認箇所

### flexcounterorch.cpp:265-269 — enable ハンドラ

```cpp
else if(key == PG_WATERMARK_KEY)
{
    gPortsOrch->generatePriorityGroupMap(getPgConfigurations());
    m_pg_watermark_enabled = true;
    gPortsOrch->addPriorityGroupWatermarkFlexCounters(getPgConfigurations());
}
```

`enable` 受信時に `generatePriorityGroupMap()` → `m_pg_watermark_enabled=true` → `addPriorityGroupWatermarkFlexCounters()` の順で直列実行。

### portsorch.cpp:8904-8933 — createPortBufferPgCounters / addPortBufferPgCounters

```cpp
if (flexCounterOrch->getPgWatermarkCountersState())
{
    /* Add watermark counters to flex_counter */
    addPriorityGroupWatermarkFlexCountersPerPortPerPgIndex(port, pgIndex);
}
```

BUFFER_PG イベント時は `getPgWatermarkCountersState()` が真の場合のみ OID 登録。

### portsorch.cpp:8998-9027 — addPriorityGroupWatermarkFlexCounters

enable 時に全ポートの PG OID を一括登録するルート。既存 BUFFER_PG 設定から PG 構成を読み込んで FlexCounter に登録する。

### watermarkorch.cpp:116-140 — handleFcConfigUpdate

```cpp
uint8_t prevStatus = m_wmStatus;
// ...
if (!prevStatus && m_wmStatus)
{
    m_telemetryTimer->start();
}
```

FlexCounter enable 通知を受けて `m_wmStatus` を更新。`prevStatus==0` から `m_wmStatus!=0` になった瞬間に telemetry タイマー起動。

## 確認された順序依存

1. PG_WATERMARK enable → `m_pg_watermark_enabled` フラグ設定 (強制先行)
2. BUFFER_PG 設定 → PG OID FlexCounter 登録 (enable フラグ依存)
3. `generatePriorityGroupMap()` → `addPriorityGroupWatermarkFlexCounters()` (同一ハンドラ内直列)
4. FlexCounter enable → watermarkorch telemetry タイマー起動 (120秒後に初発火)
5. OID 登録 → syncd ポーリング開始 (最大 POLL_INTERVAL=60000ms 遅延)

## 注意点

- BUFFER_PG 先設定・PG_WATERMARK 後 enable でも機能する（ルート 1 で一括登録）
- PG_WATERMARK 先 enable・BUFFER_PG 後設定でも機能する（ルート 2 でイベント駆動）
- orchagent 再起動時は両テーブル再読み込みで順序依存解消
