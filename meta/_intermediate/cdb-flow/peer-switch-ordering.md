# PEER_SWITCH — Phase B 書込み順依存スキャンノート

対象テーブル: `PEER_SWITCH`
Consumer: `MuxOrch` (`sonic-swss/orchagent/muxorch.cpp`)
スキャン範囲: `handlePeerSwitch()`、`handleMuxCfg()`、`createStandaloneTunnelRoute()`

---

## 検出した順序依存・タイミング依存

### 1. TUNNEL (MuxTunnel0) が PEER_SWITCH より先行必須

- `MuxOrch::handlePeerSwitch()` (muxorch.cpp:2336-2353):
  ```cpp
  IpAddresses dst_ips = decap_orch_->getDstIpAddresses(MUX_TUNNEL);
  if (!dst_ips.getSize())
  {
      SWSS_LOG_INFO("Mux tunnel not yet created for '%s' peer ip '%s'",
                     MUX_TUNNEL, peer_ip.to_string().c_str());
      return false;
  }
  ```
  MuxTunnel0 の decap dst IP が decap_orch に登録されていない場合、PEER_SWITCH の SET 処理が
  `return false` でリトライ待機に入る。
- PEER_SWITCH は TUNNEL (MuxTunnel0) の登録後でなければ確定しない。

### 2. PEER_SWITCH が MUX_CABLE より先行必須

- `MuxOrch::handleMuxCfg()` (muxorch.cpp:2271-2275):
  ```cpp
  if (mux_peer_switch_.isZero())
  {
      SWSS_LOG_INFO("Mux Peer switch addr not yet configured, port '%s'", port_name.c_str());
      return false;
  }
  ```
  `mux_peer_switch_` は `handlePeerSwitch()` が PEER_SWITCH テーブルを処理した後に設定される。
  PEER_SWITCH が先に処理されていないと MUX_CABLE エントリが `return false` でリトライ待機に入る。
- MuxOrch の retry ループで自動回復するが、PEER_SWITCH 処理完了まで MUX_CABLE は pending。

### 3. tunnel nexthop も先行必須（standalone tunnel route 生成時）

- `MuxOrch::createStandaloneTunnelRoute()` (muxorch.cpp:2445-2447):
  ```cpp
  sai_object_id_t tunnel_nexthop = getNextHopTunnelId(MUX_TUNNEL, mux_peer_switch_);
  if (tunnel_nexthop == SAI_NULL_OBJECT_ID) {
      SWSS_LOG_NOTICE("... nexthop not created yet, ignoring tunnel route creation ...");
      return;
  }
  ```
  Tunnel NH が存在しない場合は tunnel route 生成が silent skip される。
  Tunnel NH は `handlePeerSwitch()` 内の `create_tunnel()` (muxorch.cpp:2380) で SAI 生成される。

### 4. PEER_SWITCH DELETE 未実装

- `handlePeerSwitch()` の DEL パス (muxorch.cpp:2387-2390):
  ```
  "Mux peer ip '%s' delete (Not Implemented), peer name '%s'"
  ```
  DEL が来ても `mux_peer_switch_` はリセットされない。orchagent は旧 peer IP を保持し続ける。
- **回避策**: orchagent 再起動が必要。

### 5. PEER_SWITCH max-elements 1 制約

- YANG `sonic-peer-switch.yang` の `max-elements 1` により 2 件目の SET は YANG バリデーションで reject。
- 変更手順: 既存エントリ DEL → orchagent 再起動 → 新規 SET。

### 6. MUX_LINKMGR との orchagent 非依存関係

- MUX_LINKMGR は linkmgrd が直接 CONFIG_DB から購読するため orchagent レベルでの PEER_SWITCH
  との順序依存はない。ただし linkmgrd は起動時に CONFIG_DB を読み込む順序として
  `getPortCableType()` / `getServerIpAddress()` / `getSoCIpAddress()` を実行した後
  event loop に入る（DbInterface.cpp:1850-1852）。PEER_SWITCH は linkmgrd のこれらの
  初期化関数の処理対象外であり、event loop 内で通知を受け取る。

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | TUNNEL (MuxTunnel0 decap dst IP) → PEER_SWITCH SET | 必須（return false でリトライ待機） | orchagent retry ループで自動回復 |
| 2 | PEER_SWITCH SET → MUX_CABLE SET | 必須（mux_peer_switch_ が 0.0.0.0 のまま MUX_CABLE が pending） | orchagent retry ループで自動回復 |
| 3 | TUNNEL NH 存在 → standalone tunnel route 生成 | 必須（NH 未存在時 silent skip） | create_tunnel() 完了後に自動生成 |
| 4 | PEER_SWITCH DEL → orchagent が旧 IP 保持 | 未実装（実質不可逆） | orchagent 再起動 |
| 5 | PEER_SWITCH 変更（DEL + SET） | YANG max-elements 1 + DEL 未実装のため orchagent 再起動必須 | — |
