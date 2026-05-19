# FABRIC_PORT — Phase H プラットフォーム差異調査

## 調査対象

- `sonic-swss/orchagent/main.cpp:995-1014`
- `sonic-swss/orchagent/orchdaemon.cpp:601-611`
- `sonic-swss/orchagent/fabricportsorch.cpp:33-34,87-100,104-111,1201-1214`

## 主要知見

### switch_type 分岐

`main.cpp:995-1014` で `gMySwitchType` により orchagent 起動クラスが分岐。
- `"voq"` → `OrchDaemon`、`FabricPortsOrch` 起動、`m_fabricEnabled=true`、fabricQueueStat=false
- `"fabric"` → `FabricOrchDaemon`、`FabricPortsOrch` 起動、fabricQueueStat=true
- その他 → `FabricPortsOrch` 起動しない（FABRIC_PORT テーブルは処理されない）

### drop counter polling interval

`fabricportsorch.cpp:104-111`:
- `"voq"`: `SWITCH_DEBUG_COUNTER_POLLING_INTERVAL_MS` = 500 ms
- `"fabric"`: `FABRIC_SWITCH_DEBUG_COUNTER_POLLING_INTERVAL_MS` = 60,000 ms

### NOTICE ログ

`updateFabricCapacity()` (`fabricportsorch.cpp:1201-1214`):
- `"voq"` のみ `SWSS_LOG_NOTICE` 出力
- `"fabric"` では STATE_DB 書き込みのみ、ログ出力なし

### lanes フィールドのプラットフォーム依存

`to_uint<uint8_t>(lanes)` による変換 (`fabricportsorch.cpp:1541`)。
プラットフォームが複数レーンをカンマ区切りで格納する場合は変換失敗の可能性あり。
