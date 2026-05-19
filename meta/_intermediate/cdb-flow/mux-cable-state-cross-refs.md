# mux-cable-state Phase C — 暗黙参照テーブル 調査ノート

## 調査日時
2026-05-19

## 調査対象ソース
- `sonic-swss/orchagent/muxorch.cpp` (MuxOrch / MuxStateOrch / MuxCable)
- `sonic-linkmgrd/src/DbInterface.cpp`
- `sonic-platform-daemons/sonic-ycabled/ycable/ycable_utilities/y_cable_helper.py`
- `sonic-swss-common/common/schema.h`

## 検出した暗黙参照

### MUX_CABLE_TABLE (STATE_DB) の書き込みトリガ元

1. **CONFIG_DB.MUX_CABLE** (`CFG_MUX_CABLE_TABLE_NAME`)
   - `MuxOrch::handleMuxCfg()` が CONFIG_DB の `MUX_CABLE|<ifname>` を購読 (muxorch.cpp:2189)
   - `server_ipv4` / `server_ipv6` / `soc_ipv4` / `cable_type` / `neighbor_mode` フィールドを読み取る
   - `neighbor_mode` の値 → `STATE_DB MUX_CABLE_TABLE.<neighbor_mode>` 書き込み (muxorch.cpp:2283-2285)

2. **CONFIG_DB.PEER_SWITCH** (`CFG_PEER_SWITCH_TABLE_NAME`)
   - `MuxOrch::handlePeerSwitch()` が処理し `mux_peer_switch_` を設定
   - `PEER_SWITCH` が未処理の間は `MuxCable` オブジェクト生成がブロックされる (muxorch.cpp:2271-2275)
   - つまり STATE_DB `MUX_CABLE_TABLE` への最初の書き込みも遅延される

3. **APP_DB.HW_MUX_CABLE_TABLE** (`APP_HW_MUX_CABLE_TABLE_NAME`)
   - `MuxStateOrch` が APPL_DB の `HW_MUX_CABLE_TABLE` を購読 (muxorch.cpp:2505)
   - ycabled → APPL_DB → MuxStateOrch → STATE_DB MUX_CABLE_TABLE.state 更新
   - `isMuxExists(port_name)` チェック (muxorch.cpp:2651-2655) で MuxCable 未生成なら更新スキップ

4. **NeighOrch (gNeighOrch)** — neighbor entry
   - `MuxCable::nbrHandler()` 内で `gNeighOrch->enableNeighbor()` / `disableNeighbor()` を呼ぶ
   - neighbor の有効/無効切替で MUX 側の route 変更が起きるが、STATE_DB への直接書き込みではなくSAI 操作が主

5. **FdbOrch (fdbOrch)** — FDB エントリ
   - `MuxOrch` が `FdbOrch` を `attach(this)` して `SUBJECT_TYPE_FDB_CHANGE` を受信 (muxorch.cpp:2196, 2161)
   - FDB update 契機で neighbor → MUX neighbor 変換が起こる (muxorch.cpp:1885-1894)
   - STATE_DB への直接書き込みではないが MuxCable 状態変化のトリガになる

6. **MuxTunnel0 (TunnelDecapOrch / decap_orch_)**
   - `handlePeerSwitch()` で `decap_orch_->getDstIpAddresses(MUX_TUNNEL)` 参照 (muxorch.cpp:2348)
   - tunnel が存在しない場合 P2P tunnel 作成に失敗し、STATE_DB の状態遷移に影響

7. **Loopback3 インターフェース (CONFIG_DB.LOOPBACK_INTERFACE)**
   - linkmgrd の `DbInterface` が Loopback3 の IPv4 アドレスを参照して `read_side` 判定に使用
   - y_cable_helper.py:633-651 の Loopback3 参照

### HW_MUX_CABLE_TABLE (STATE_DB) の書き込みトリガ元

1. **gRPC チャネル (soc_ipv4)**
   - ycabled の `put_init_values_for_grpc_states()` が gRPC 経由でハードウェアの forwarding state を取得
   - `soc_ipv4` が CONFIG_DB の `MUX_CABLE|<ifname>` になければ gRPC チャネル未確立 → `"unknown"` 書き込み

2. **CONFIG_DB.MUX_CABLE** (soc_ipv4, cable_type)
   - ycabled がポートごとの `soc_ipv4` を参照して gRPC エンドポイントを決定 (y_cable_helper.py:672)

### MUX_LINKMGR_TABLE (STATE_DB) の書き込みトリガ元

1. **linkmgrd (sonic-linkmgrd)**
   - `DbInterface` が `STATE_MUX_LINKMGR_TABLE_NAME` にリンク監視ステータスを書き込む (DbInterface.cpp:332-340)
   - これは `mux-cable-state.md` の主テーブルには含まれないが関連テーブルとして参照

## 参照方向の整理

| 参照先 | 参照元コンポーネント | 参照の用途 | 参照フィールド |
|-------|-----------------|---------|--------------|
| CONFIG_DB.MUX_CABLE | MuxOrch | MuxCable 生成トリガ・neighbor_mode 取得 | server_ipv4/v6, neighbor_mode, cable_type, soc_ipv4 |
| CONFIG_DB.PEER_SWITCH | MuxOrch | peer switch IP → MuxCable 生成可否判定 | address_ipv4 |
| APPL_DB.HW_MUX_CABLE_TABLE | MuxStateOrch | hw_state → MUX_CABLE_TABLE.state 更新 | state |
| CONFIG_DB.LOOPBACK_INTERFACE (Loopback3) | linkmgrd/ycabled | read_side 判定 | IP prefix |
| gRPC (soc_ipv4 エンドポイント) | ycabled | HW forwarding state 取得 | — |
| TunnelDecapOrch (MuxTunnel0) | MuxOrch | peer switch tunnel 作成 | dscp_mode, tc_to_dscp_map_id |
| NeighOrch | MuxCable | neighbor enable/disable | — |
| FdbOrch | MuxOrch | FDB 変化 → neighbor MUX 変換 | port_name, mac |
