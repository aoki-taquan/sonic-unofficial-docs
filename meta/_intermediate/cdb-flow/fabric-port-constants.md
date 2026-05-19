# fabric-port Phase E — ハードコード定数調査メモ

## 調査対象
- `sonic-swss/orchagent/fabricportsorch.cpp`
- `sonic-swss/orchagent/fabricportsorch.h`

## 発見した定数群

### ポーリング間隔 (fabricportsorch.cpp:21-48)
- `FABRIC_POLLING_INTERVAL_DEFAULT` = 30 秒 → m_timer (SelectableTimer, fabricportsorch.cpp:87)
- `FABRIC_DEBUG_POLLING_INTERVAL_DEFAULT` = 12 秒 → m_debugTimer (fabricportsorch.cpp:88)
- `CHECK_TIME` = 120 秒 → dnLkQueues 保持ウィンドウ

### FlexCounter 間隔
- `FABRIC_PORT_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` = 10000 ms (10秒)
- `FABRIC_QUEUE_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` = 100000 ms (100秒)
- `SWITCH_DEBUG_COUNTER_POLLING_INTERVAL_MS` = 500 ms
- `FABRIC_SWITCH_DEBUG_COUNTER_POLLING_INTERVAL_MS` = 60000 ms (60秒)

### リンク監視閾値 (上書き不可)
- `MAX_SKIP_CRCERR_ON_LNKUP_POLLS` = 20 (fabricportsorch.cpp:766)
- `MAX_SKIP_FECERR_ON_LNKUP_POLLS` = 20 (fabricportsorch.cpp:817)
- `FABRIC_LINK_RATE` = 44316 (fabricportsorch.cpp:1133,1137)

### リンク監視閾値 (FABRIC_MONITOR で上書き可能)
コメント "// the follow will be replaced with the number in config_db" (fabricportsorch.cpp:43)
- `FEC_ISOLATE_POLLS` = 2 → monPollThreshIsolation
- `FEC_UNISOLATE_POLLS` = 8 → monPollThreshRecovery
- `ISOLATION_POLLS_CFG` = 1 → monPollThreshIsolation (CRC系)
- `RECOVERY_POLLS_CFG` = 8 → monPollThreshRecovery (CRC系)
- `ERROR_RATE_CRC_CELLS_CFG` = 1 → monErrThreshCrcCells
- `ERROR_RATE_RX_CELLS_CFG` = 61035156 → monErrThreshRxCells

### STATE_DB リセットデフォルト (fabricportsorch.h:62-68)
- `m_defaultPollWithErrors` = 0 → POLL_WITH_ERRORS
- `m_defaultPollWithNoErrors` = 8 → POLL_WITH_NO_ERRORS
- `m_defaultPollWithFecErrors` = 0 → POLL_WITH_FEC_ERRORS
- `m_defaultPollWithNoFecErrors` = 8 → POLL_WITH_NOFEC_ERRORS
- `m_defaultConfigIsolated` = 0 → CONFIG_ISOLATED
- `m_defaultIsolated` = 0 → ISOLATED
- `m_defaultAutoIsolated` = 0 → AUTO_ISOLATED

## 重要な発見
- m_defaultPollWithNoErrors=8 と monPollThreshRecovery は完全独立。FABRIC_MONITOR で
  monPollThreshRecovery を変更しても force unisolate 後の STATE_DB リセット値は変わらない。
- FlexCounter グループ名もハードコード: FABRIC_PORT_STAT_COUNTER, FABRIC_QUEUE_STAT_COUNTER,
  SWITCH_DEBUG_COUNTER, FABRIC_SWITCH_DEBUG_COUNTER (後者は未定義だが FABRIC 向け専用値)
