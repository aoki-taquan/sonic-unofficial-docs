# FABRIC_MONITOR — 例外条件分析

## consumer 一覧

| consumer | 用途 | ソースパス |
|---|---|---|
| orchagent / fabricportsorch.cpp | エラー閾値などの定数設定を APPL_DB の FABRIC_MONITOR_DATA から取得 | sonic-swss/orchagent/fabricportsorch.cpp:30,113,139,447-465 |

## 例外条件

### fabricportsorch: FABRIC_MONITOR_DATA の定数取得失敗
- fabricportsorch.cpp:139 — `m_applMonitorConstTable->get("FABRIC_MONITOR_DATA", constValues)` が false を返した場合 (= エントリ不在) は `LOG_INFO: "applConstKey %s default values not set"` を出力し、**ハードコードされたデフォルト値**を使用して処理継続。
  - `ERROR_RATE_CRC_CELLS_CFG` = コンパイル時定数
  - `ERROR_RATE_RX_CELLS_CFG` = コンパイル時定数

### fabricportsorch: FABRIC_MONITOR_DATA の個別フィールド欠落
- fabricportsorch.cpp:459-465 — `monErrThreshCrcCells` / `monErrThreshRxCells` が取得できた場合のみ `errorRateCrcCellsCfg` / `errorRateRxCellsCfg` を更新。欠落フィールドはデフォルト定数のまま継続。

### fabricportsorch: リンクアップ直後のエラーカウントスキップ
- fabricportsorch.cpp:548-561, 770-772 — リンクアップ直後は `skipCrcErrorsOnLinkupCount` / `skipFecErrorsOnLinkupCount` が閾値 (`maxSkipCrcCnt` 等) に達するまでエラーカウントを無視する。これはブート時の誤検知を防ぐための特殊動作。
