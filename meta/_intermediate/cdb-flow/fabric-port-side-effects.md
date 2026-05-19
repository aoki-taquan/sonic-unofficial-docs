# FABRIC_PORT — Phase F 副次 DB 書込分析 (intermediate)

slug: fabric-port
phase: side-effects
source: fabricportsorch.cpp

## 副次書込先 DB まとめ

### STATE_DB

1. `FABRIC_PORT_TABLE|PORT<lane>` — isolate/unisolate 状態フィールド群
   - doFabricPortTask() force unisolate 時に一括リセット (9 フィールド)
   - updateFabricPortState() タイマー毎に STATUS / REMOTE_MOD / REMOTE_PORT / PORT_DOWN_COUNT 更新
   - updateFabricDebugCounters() 12秒周期で CRC/FEC エラー関連フィールド更新
   - updateFabricRate() で OLD_RX/TX_RATE_AVG / DATA / LAST_TIME 更新
   - evidence: fabricportsorch.cpp:884-959, 1031-1041, 1374-1386, 1528-1536

2. `FABRIC_CAPACITY_TABLE|FABRIC_CAPACITY_DATA`
   - updateFabricCapacity() が fabric_capacity / missing_capacity / operating_links / number_of_links / warning_threshold / last_event / last_event_time を書き込む
   - evidence: fabricportsorch.cpp:1225-1231

### COUNTERS_DB

3. `COUNTERS_FABRIC_PORT_NAME_MAP|""` — ポート名→SAI OID マッピング
   - generatePortStats() 内で m_portNamePortCounterTable->set("", portNamePortCounterMap)
   - 初期化時 1 回のみ書き込み
   - evidence: fabricportsorch.cpp:255

4. `COUNTERS_FABRIC_QUEUE_NAME_MAP|""` — キュー名→SAI OID マッピング
   - generateQueueStats() 内で m_portNameQueueCounterTable->set("", portNameQueueMap)
   - m_fabricQueueStatEnabled=true 時のみ
   - evidence: fabricportsorch.cpp:320

5. `COUNTERS_TABLE|<port_oid>` — FlexCounter ポートカウンタ登録
   - port_stat_manager.setCounterIdList() 経由で FLEX_COUNTER_DB にも登録
   - m_fabricPortStatEnabled=true 時のみ
   - evidence: fabricportsorch.cpp:248-254

6. `COUNTERS_TABLE|<queue_oid>` — FlexCounter キューカウンタ登録
   - queue_stat_manager.setCounterIdList() 経由
   - evidence: fabricportsorch.cpp:310-319

7. `COUNTERS_DEBUG_NAME_SWITCH_STAT_MAP|""` — スイッチドロップカウンタマップ
   - createSwitchDropCounters() 内 gMySwitchType == "voq" / "fabric" 時のみ
   - evidence: fabricportsorch.cpp:1620-1628
