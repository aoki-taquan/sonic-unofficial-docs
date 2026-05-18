# WATERMARK_TABLE 暗黙参照マップ (Phase C)

## 調査対象

- `sonic-swss/orchagent/watermarkorch.cpp`
- `sonic-swss/orchagent/watermarkorch.h`
- `sonic-utilities/scripts/watermarkcfg`

## 発見した参照関係

### WATERMARK_TABLE → FLEX_COUNTER_TABLE (双方向制御)

`WatermarkOrch::doTask(Consumer&)` は `CFG_WATERMARK_TABLE_NAME` と `CFG_FLEX_COUNTER_TABLE_NAME` の両方を同一 `Consumer` で購読する（`orchagent/watermarkorch.cpp:72-78`）。

```cpp
if (consumer.getTableName() == CFG_WATERMARK_TABLE_NAME)
{
    handleWmConfigUpdate(key, fvt);
}
else if (consumer.getTableName() == CFG_FLEX_COUNTER_TABLE_NAME)
{
    handleFcConfigUpdate(key, fvt);
}
```

`FLEX_COUNTER_TABLE|QUEUE_WATERMARK` または `FLEX_COUNTER_TABLE|PG_WATERMARK` の `FLEX_COUNTER_STATUS=enable` イベントを受け取らない限り、`m_wmStatus` は 0 のままでありタイマーは起動しない。`WATERMARK_TABLE` の interval 設定のみでは watermark クリアは動作しない。

### WatermarkOrch → COUNTERS_DB (書き込み先)

`WatermarkOrch` は 3 つの COUNTERS_DB テーブルに書き込む（watermarkorch.cpp:31-33）:

- `PERIODIC_WATERMARKS_TABLE` — telemetry タイマー満了ごとにリセット
- `PERSISTENT_WATERMARKS_TABLE` — `WATERMARK_CLEAR_REQUEST` ノーティフィケーション受信時
- `USER_WATERMARKS_TABLE` — `WATERMARK_CLEAR_REQUEST` ノーティフィケーション受信時

### PortsOrch (gPortsOrch) — 処理ゲート

`doTask(Consumer&)` および `doTask(NotificationConsumer&)` の先頭で `gPortsOrch->allPortsReady()` を確認する（watermarkorch.cpp:56, 148）。false の間は全処理が早期 return される。この依存は `portsorch.h` 経由でリンクされる（`extern PortsOrch *gPortsOrch`）。

### BufferOrch (gBufferOrch) — バッファプール OID 参照

`clearSingleWm()` の buffer pool 系クリアで `gBufferOrch->getBufferPoolNameOidMap()` を使用する（watermarkorch.cpp:218, 224）。`extern BufferOrch *gBufferOrch` 経由。

### APPL_DB.WATERMARK_CLEAR_REQUEST (通知チャネル)

`watermarkcfg clear` CLI が APPL_DB の `WATERMARK_CLEAR_REQUEST` チャネルに Pub/Sub 通知を送り、`WatermarkOrch::doTask(NotificationConsumer&)` がこれを受信して PERSISTENT/USER watermarks をリセットする（watermarkorch.cpp:35-38）。

## 参照マップ表

| 参照方向 | このテーブル | 相手テーブル / ページ | 条件 |
|---------|------------|---------------------|------|
| WATERMARK_TABLE → | `interval` 変更 | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | タイマーは `FLEX_COUNTER_TABLE` の `QUEUE_WATERMARK` / `PG_WATERMARK` `FLEX_COUNTER_STATUS=enable` がないと起動しない。WATERMARK_TABLE 単独では不十分 |
| WATERMARK_TABLE → | タイマー満了 | COUNTERS_DB `PERIODIC_WATERMARKS` | WatermarkOrch が指定周期で SAI 統計を 0 クリアして書き込む |
| → WATERMARK_TABLE | `FLEX_COUNTER_TABLE\|QUEUE_WATERMARK` / `PG_WATERMARK` | [`FLEX_COUNTER_TABLE`](flex-counter-table.md) | `FLEX_COUNTER_STATUS` 変化が `m_wmStatus` を更新し、タイマー起動/停止を制御する |
| → WATERMARK_TABLE | APPL_DB `WATERMARK_CLEAR_REQUEST` | `watermarkcfg clear` CLI | clear 要求通知が PERSISTENT/USER テーブルをリセット。PERIODIC は telemetry タイマーのみがリセット |
| CLI | `watermarkcfg -c <秒>` / `watermarkcfg -s` | [`watermarkcfg`](../cli/) | WATERMARK_TABLE の interval フィールドの書き込み・読み出し |
