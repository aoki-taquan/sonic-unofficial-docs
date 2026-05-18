# fabric-port — Phase B ordering (intermediate)

slug: fabric-port
phase: ordering
source: fabricportsorch.cpp

## 検出された順序依存

1. SAI `getFabricPortList()` 完了が `updateFabricPortState()` / `updateFabricDebugCounters()` の前提条件
   - `m_getFabricPortListDone` フラグで制御、失敗時はポーリングタイマー毎に再試行
   - evidence: fabricportsorch.cpp:1562-1576, 1594-1598

2. `APPL_DB FABRIC_MONITOR_DATA.monState == "enable"` が `doFabricPortTask()` の実行前提
   - `checkFabricPortMonState()` が false の場合 early return、CONFIG_DB 変更は SAI に未反映
   - evidence: fabricportsorch.cpp:1394-1399

3. `STATE_DB FABRIC_PORT_TABLE|PORT<lane>` エントリ存在が `forceUnisolateStatus` 差分比較に影響
   - 不在時は FORCE_UN_ISOLATE=0 扱い、evidence: fabricportsorch.cpp:1499-1516

4. `alias` + `lanes` + `isolateStatus` の 3 フィールド全揃いが isolate 処理実行の前提
   - partial update は APPL_DB hget で補完、それでも欠落なら silent drop
   - evidence: fabricportsorch.cpp:1436-1484

5. CONFIG_DB → fabricmgrd → APPL_DB → doFabricPortTask() の非同期パイプライン遅延
