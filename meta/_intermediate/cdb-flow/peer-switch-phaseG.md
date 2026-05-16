# PEER_SWITCH — Phase G (通信メカニズム) 中間ファイル

生成日: 2026-05-16
ソース: sonic-swss/orchagent/muxorch.cpp, orchdaemon.cpp

<!-- pubsub -->
## Phase G: CONFIG_DB Subscribe 経路

### Consumer 登録 (orchdaemon.cpp)

```cpp
// orchdaemon.cpp:467-471
vector<string> mux_tables = {
    CFG_MUX_CABLE_TABLE_NAME,
    CFG_PEER_SWITCH_TABLE_NAME
};
gMuxOrch = new MuxOrch(m_configDb, mux_tables, gTunneldecapOrch, gNeighOrch, gFdbOrch);
```

- `MuxOrch` が `CONFIG_DB` の `CFG_PEER_SWITCH_TABLE_NAME` (`PEER_SWITCH`) テーブルを
  `Orch2` (swss フレームワーク) 経由で購読。
- 同一インスタンスが `CFG_MUX_CABLE_TABLE_NAME` も購読しており、両テーブルの変更が
  同一ディスパッチループで処理される。

### Handler 登録 (muxorch.cpp)

```cpp
// muxorch.cpp:2189-2190
handler_map_.insert(handler_pair(CFG_MUX_CABLE_TABLE_NAME, &MuxOrch::handleMuxCfg));
handler_map_.insert(handler_pair(CFG_PEER_SWITCH_TABLE_NAME, &MuxOrch::handlePeerSwitch));
```

- `PEER_SWITCH` テーブル変更は `MuxOrch::handlePeerSwitch()` に dispatch される。

### SAI Tunnel 経路 (SET 時)

```
CONFIG_DB PEER_SWITCH SET
  └─ MuxOrch::handlePeerSwitch()       [muxorch.cpp:2340-2391]
       ├─ decap_orch_->getDstIpAddresses(MUX_TUNNEL)
       │    → TUNNEL テーブル未設定なら return false (retry)
       ├─ decap_orch_->getDscpMode(MUX_TUNNEL)
       ├─ decap_orch_->getQosMapId(MUX_TUNNEL, ...)
       └─ create_tunnel(&peer_ip, &dst_ip, ...)  [muxorch.cpp:2380]
            ├─ sai_router_intfs_api->create_router_interface(...)
            │    SAI_ROUTER_INTERFACE_TYPE_LOOPBACK (overlay IF)
            └─ sai_tunnel_api->create_tunnel(...)  [muxorch.cpp:325]
                 属性:
                 - SAI_TUNNEL_ATTR_TYPE = SAI_TUNNEL_TYPE_IPINIP
                 - SAI_TUNNEL_ATTR_PEER_MODE = SAI_TUNNEL_PEER_MODE_P2P
                 - SAI_TUNNEL_ATTR_ENCAP_SRC_IP = peer_ip (PEER_SWITCH.address_ipv4)
                 - SAI_TUNNEL_ATTR_ENCAP_DST_IP = dst_ip (TUNNEL.src_ip)
                 - SAI_TUNNEL_ATTR_ENCAP_TTL_MODE = SAI_TUNNEL_TTL_MODE_PIPE_MODEL
                 - SAI_TUNNEL_ATTR_DECAP_TTL_MODE = SAI_TUNNEL_TTL_MODE_PIPE_MODEL
                 - SAI_TUNNEL_ATTR_LOOPBACK_PACKET_ACTION = SAI_PACKET_ACTION_DROP
```

### DEL 時

```
CONFIG_DB PEER_SWITCH DEL
  └─ MuxOrch::handlePeerSwitch() DEL パス  [muxorch.cpp:2387]
       → SWSS_LOG_NOTICE "Not Implemented" のみ
       → SAI tunnel 削除なし、mux_peer_switch_ リセットなし
```

### linkmgrd サブスクライブ (別経路)

- `linkmgrd` は `ConfigDBConnector` (Python) で `PEER_SWITCH` を独立して購読。
- orchagent 経由ではなく直接 CONFIG_DB から `address_ipv4` を読み込み、
  peer への ICMPv4/ICMPv6 プローブ送信先として使用する。
- linkmgrd は起動時 1 回のみ読み込み、実行中の変更は反映されない。

<!-- /pubsub -->
