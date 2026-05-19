# mux-cable-state — Phase B ordering (intermediate notes)

slug: mux-cable-state
phase: B (ordering)
source: sonic-swss/orchagent/muxorch.cpp

## 検出された順序依存

1. PEER_SWITCH 先行必須 (muxorch.cpp:2271-2275)
   - `handleMuxCfg()` が `mux_peer_switch_.isZero()` をチェック
   - ゼロの場合 return false → MuxCable 未生成 → STATE_DB 書込みなし

2. MuxCable 未生成時 HW_MUX_CABLE_TABLE ブロック (muxorch.cpp:2651-2655)
   - `MuxStateOrch::addOperation()` で `isMuxExists()` チェック
   - false → WARN → return false → state 更新なし

3. cold boot 初期 "standby" → APP_DB 上書き (muxorch.cpp:444-447, 2508-2514)
   - コンストラクタで即座に stateStandby() → "standby" 書き込み
   - APP_DB sync 完了後に実際の状態で上書き

4. warm restart "init" → 実態遷移 (muxorch.cpp:437-442)
   - warm restart 時は MUX_STATE_INIT で初期化
   - APP_DB sync 後に active/standby に遷移

5. 状態遷移中ブロック (muxorch.cpp:2673-2677)
   - `isStateChangeInProgress()` が true の間 HW state 更新ブロック
   - return false → イベントループ再キュー
