# tunnel-state Phase C — STATE_DB TUNNEL クロスリファレンス調査メモ

調査日: 2026-05-17
対象: `docs/reference/config-db/tunnel-state.md`

## 調査対象ソース

| ファイル | コミット |
|---------|---------|
| `orchagent/tunneldecaporch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `orchagent/vxlanorch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `orchagent/muxorch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `orchagent/routeorch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |
| `orchagent/vnetorch.cpp` | 4305596156d70e9797e8a881b3d19b46de0bce0d |

## TUNNEL_DECAP_TABLE の参照元

### MuxOrch (muxorch.cpp)

`MuxCable` オブジェクト (`muxorch.cpp:2183`) が `TunnelDecapOrch*` を保持し、以下を直接コールする:

```cpp
// muxorch.cpp L2348-2374: MuxCable::MuxCable() / updateTunnelRoute()
IpAddresses dst_ips = decap_orch_->getDstIpAddresses(MUX_TUNNEL);
string dscp_mode_name = decap_orch_->getDscpMode(MUX_TUNNEL);
decap_orch_->getQosMapId(MUX_TUNNEL, encap_tc_to_dscp_field_name, tc_to_dscp_map_id);
decap_orch_->getQosMapId(MUX_TUNNEL, encap_tc_to_queue_field_name, tc_to_queue_map_id);
```

MUX_CABLE 設定時に `TunnelDecapOrch` から宛先 IP・DSCP モード・QoS マップを読み出す。
STATE_DB への読み書きは行わないが、`TUNNEL_DECAP_TABLE` の SAI 作成が完了していない（STATE_DB エントリ未記載）状態での MUX_CABLE SET は想定外挙動となる。

### RouteOrch (routeorch.cpp)

`SubnetDecap` ルート処理で `TunnelDecapOrch::getSubnetDecapConfig()` を参照する (`routeorch.cpp:2714, 3222, 3245`)。
`SubnetDecapConfig` には decap トンネルの src_ip や有効フラグが含まれ、サブネットルートの decap 対象判定に用いる。

### VnetOrch (vnetorch.cpp)

同様に `gTunneldecapOrch->getSubnetDecapConfig()` を参照 (`vnetorch.cpp:1565, 1583`)。
VNET ルートのアドバタイズフィルタリングに利用。

## VXLAN_TUNNEL_TABLE / VXLAN_TABLE の参照元

### EvpnNvoOrch → VxlanTunnelOrch (vxlanorch.cpp)

```cpp
// vxlanorch.cpp L1678, L1733, L1795 等
EvpnNvoOrch* evpn_orch = gDirectory.get<EvpnNvoOrch*>();
```

`VxlanTunnelOrch` は EVPN 処理のたびに `gDirectory` から `EvpnNvoOrch` を引く。
STATE_DB `VXLAN_TUNNEL_TABLE` への書き込み (`addRemoveStateTableEntry()`) は、FDB MAC 経由の `addTunnelUser()` または EVPN IMR 経由の `createDynamicDIPTunnel()` から呼ばれる。

### PortsOrch (vxlanorch.cpp)

DIP トンネル作成時:
```cpp
// vxlanorch.cpp L1719-1720
gPortsOrch->addTunnel(port_tunnel_name, dip_tunnel->getTunnelId(), false);
gPortsOrch->getPort(port_tunnel_name, tunnelPort);
```

DIP トンネル削除時:
```cpp
// vxlanorch.cpp L1761, L1780, L1819, L1843
gPortsOrch->removeTunnel(tunnelPort);
```

`VXLAN_TUNNEL_TABLE` への STATE_DB 書き込みは DIP トンネルの `addTunnel()` / `removeTunnel()` と **同一フロー内**で行われる。`gPortsOrch` の呼び出しが先行し、STATE_DB 書き込みは直後。

### QosOrch / CrmOrch (tunneldecaporch.cpp)

QoS マップ解決 (`gQosOrch->resolveTunnelQosMap()`, L217-262) は SAI トンネル作成前に行われる。
CRM カウンタ更新 (`gCrmOrch->incCrmResUsedCounter()`, L1346-1350) は SAI nexthop 作成後に行われる。
どちらも STATE_DB には直接関与しない。

## 他テーブルとの参照関係サマリ

| STATE_DB テーブル | 参照元 orch | 参照目的 |
|------------------|------------|---------|
| `TUNNEL_DECAP_TABLE` (間接) | MuxOrch | MUX_TUNNEL の dst_ip / dscp_mode / QoS マップ取得 |
| `TUNNEL_DECAP_TABLE` (間接) | RouteOrch | SubnetDecap 有効フラグ / src_ip 取得 |
| `TUNNEL_DECAP_TABLE` (間接) | VnetOrch | SubnetDecap 有効フラグ取得 |
| `VXLAN_TUNNEL_TABLE` | VxlanTunnelOrch (自身) | EVPN / FDB イベントで書き込み |
| `VXLAN_TUNNEL_TABLE` (書き込み契機) | EvpnNvoOrch | addTunnelUser / createDynamicDIPTunnel 経由 |
| `VXLAN_TUNNEL_TABLE` (書き込み契機) | PortsOrch | addTunnel / addBridgePort 完了後に STATE_DB 書き込み |
| `VXLAN_TABLE` | VxlanMgr (cfgmgr) | Linux VXLAN netdev 作成成功後に書き込み |

## 注意: STATE_DB の値は読み取られない

STATE_DB `TUNNEL_DECAP_TABLE` / `VXLAN_TUNNEL_TABLE` の値は他 orch によって直接読み取られることは確認できない。
他orch が参照するのは `TunnelDecapOrch` や `VxlanTunnel` オブジェクト内のインメモリキャッシュであり、STATE_DB を経由しない。
STATE_DB はあくまで外部モニタリング（`show` コマンド等）向けの**読み取り専用ミラー**として機能する。
