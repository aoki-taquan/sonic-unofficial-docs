# PEER_SWITCH テーブル 暗黙参照スキャン (Phase C)

`docs/reference/config-db/peer-switch.md` の Phase C (暗黙参照) ブロック裏付け資料。

ソース: `sonic-net/sonic-swss/orchagent/muxorch.cpp`

`PEER_SWITCH` エントリ処理時に `MuxOrch::handlePeerSwitch()` が暗黙的に読み出す関連テーブル・SAI オブジェクトを列挙する。

## スキャン手順

```
grep -n "decap_orch_\|MUX_TUNNEL\|MUX_CABLE\|mux_peer_switch_\|mux_cable_tb_\|mux_tunnel_id_\|create_tunnel\|TunnelDecap" \
    .cache/sonic-sources/sonic-swss/orchagent/muxorch.cpp
```

## 検出された暗黙参照テーブル・オブジェクト

### TUNNEL_DECAP 経由の暗黙参照 (handlePeerSwitch — muxorch.cpp:2348-2380)

`handlePeerSwitch()` は SET 受信時に `decap_orch_->getDstIpAddresses(MUX_TUNNEL)` を呼び出し、`TUNNEL` テーブルから登録されたトンネルデカップエントリの dst_ip を取得する。未登録であれば `return false` でリトライ待機となる。

| 暗黙参照対象 | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `TUNNEL` (MuxTunnel0) — decap dst_ip | PEER_SWITCH SET 時 | `decap_orch_->getDstIpAddresses(MUX_TUNNEL)` でデカップ先 IP を取得し `create_tunnel()` の引数に渡す。未設定なら `return false` | `muxorch.cpp:2348-2353` |
| `TUNNEL` (MuxTunnel0) — dscp_mode | PEER_SWITCH SET 時 | `decap_orch_->getDscpMode(MUX_TUNNEL)` で DSCP モードを取得し encap トンネルに適用 | `muxorch.cpp:2359` |
| `TUNNEL` (MuxTunnel0) — tc_to_dscp_map_id | PEER_SWITCH SET 時 | `decap_orch_->getQosMapId(MUX_TUNNEL, encap_tc_to_dscp_field_name, ...)` | `muxorch.cpp:2367` |
| `TUNNEL` (MuxTunnel0) — tc_to_queue_map_id | PEER_SWITCH SET 時 | `decap_orch_->getQosMapId(MUX_TUNNEL, encap_tc_to_queue_field_name, ...)` | `muxorch.cpp:2374` |

> `decap_orch_` は `TunnelDecapOrch` のインスタンス。`TunnelDecapOrch` は `TUNNEL_DECAP` テーブルを購読して decap エントリを管理する。`handlePeerSwitch()` は `decap_orch_` を介して間接的に `TUNNEL` (MuxTunnel0) の登録済み情報を読み出す。

### MUX_CABLE への暗黙連鎖 (handleMuxCfg — muxorch.cpp:2271-2280)

`PEER_SWITCH` SET によって `mux_peer_switch_` が確定した後、`handleMuxCfg()` (MUX_CABLE 処理ハンドラ) が `mux_peer_switch_` を参照して `MuxCable` オブジェクトを生成する。すなわち `PEER_SWITCH` の存在が `MUX_CABLE` 処理の前提条件となる。

| 暗黙参照対象 | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `mux_peer_switch_` (内部変数) | MUX_CABLE SET 時 (handleMuxCfg) | `mux_peer_switch_.isZero()` が真なら MUX_CABLE エントリを `return false` でスキップ | `muxorch.cpp:2271-2274` |
| `mux_peer_switch_` (内部変数) | MUX_CABLE SET 時 (handleMuxCfg) | `MuxCable(port_name, srv_ip, srv_ip6, mux_peer_switch_, ...)` コンストラクタ引数として渡す | `muxorch.cpp:2280` |

### キャッシュ済み隣接更新での参照 (updateCachedNeighbors — muxorch.cpp:2483)

`mux_peer_switch_` 未設定時にキャッシュ済み Neighbor 更新がスキップされる。

| 暗黙参照対象 | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `mux_peer_switch_` (内部変数) | `updateCachedNeighbors()` 呼び出し時 | isZero() なら `SWSS_LOG_NOTICE("Skip ... no peer switch addr")` で即 return | `muxorch.cpp:2483-2486` |

### ネクストホップトンネル経由の参照 (muxorch.cpp:1651, 2445)

`MuxOrch` 内で `getNextHopTunnelId(MUX_TUNNEL, mux_peer_switch_)` を呼び出す箇所が複数あり、トンネル NextHop が未生成の場合は tunnel route 生成をスキップする。

| 暗黙参照対象 | 参照タイミング | 用途 | evidence |
|---|---|---|---|
| `MUX_TUNNEL` nexthop (SAI) | neighbor 更新時 | `getNextHopTunnelId(MUX_TUNNEL, mux_peer_switch_)` が SAI_NULL_OBJECT_ID なら tunnel route 作成スキップ | `muxorch.cpp:2445-2447` |
| `mux_tunnel_nh_` マップ (内部) | `createNextHopTunnel` / `getNextHopTunnelId` | `mux_tunnel_id_` (create_tunnel() の戻り値) を用いて nexthop を生成・キャッシュ | `muxorch.cpp:1519,1531` |

## まとめ — `peer-switch.md` Phase C 記載対象

| カテゴリ | 参照対象 |
|---|---|
| TUNNEL (MuxTunnel0) decap 情報 | dst_ip / dscp_mode / tc_to_dscp_map_id / tc_to_queue_map_id |
| MUX_CABLE 処理前提 | PEER_SWITCH 未設定時に MUX_CABLE エントリが pending |
| キャッシュ隣接更新 | PEER_SWITCH 未設定時に updateCachedNeighbors がスキップ |
| SAI トンネル NextHop | mux_peer_switch_ の IP で nexthop を生成・参照 |

## 検証コマンド

```bash
grep -n "decap_orch_\|getDstIpAddresses\|getDscpMode\|getQosMapId\|mux_peer_switch_\|mux_tunnel_id_\|create_tunnel" \
    .cache/sonic-sources/sonic-swss/orchagent/muxorch.cpp

grep -n "MUX_TUNNEL\|TunnelDecapOrch\|decapOrch" \
    .cache/sonic-sources/sonic-swss/orchagent/muxorch.cpp
```

このスキャン結果から派生して `docs/reference/config-db/peer-switch.md` の `<!-- cross-refs -->` ブロックを生成する。
