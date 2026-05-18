# 調査証跡: counters-portchannel — Phase F 副次 DB 書込み

調査日: 2026-05-18
対象コード: sonic-swss/orchagent/intfsorch.cpp, orchagent/saihelper.cpp

## 副次書込み

1. COUNTERS_RIF_TYPE_MAP: addRifToFlexCounter() 内で COUNTERS_RIF_NAME_MAP と連続書き込み (intfsorch.cpp:1535-1538)
2. FLEX_COUNTER_DB: startFlexCounterPolling() が RIF_STAT_COUNTER:<rif_oid> を書き込む (saihelper.cpp:1033-1050)
3. COUNTERS:<rif_oid>: syncd FlexCounter が定期収集して書き込む
4. RATES:<rif_oid>: rif_rates.lua プラグインが差分計算して書き込む (rif_rates.lua:69-78)

## コード証跡

- intfsorch.cpp:1527-1554: addRifToFlexCounter() — RIF_NAME_MAP, RIF_TYPE_MAP, FLEX_COUNTER_DB に連続書き込み
- intfsorch.cpp:1556-1568: removeRifFromFlexCounter() — 同3テーブルから削除
- saihelper.cpp:1033-1050: startFlexCounterPolling() — FLEX_COUNTER_DB への書き込み実装
- intfsorch.cpp:61-100: コンストラクタ — rif_rates.lua を Redis に登録
