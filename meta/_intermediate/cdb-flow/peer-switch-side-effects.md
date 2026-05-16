# PEER_SWITCH — Phase F 副次 DB 書込 中間ファイル

生成日: 2026-05-16
ソース: sonic-swss/orchagent/muxorch.cpp

## 調査対象

`handlePeerSwitch()` (muxorch.cpp:2336-2390) および `handleMuxCfg()` (muxorch.cpp:2202-2286) の
副次 DB 書込・外部テーブル連動を網羅的に調査した。

## STATE_DB 書込

### STATE_MUX_CABLE_TABLE

`MuxOrch` コンストラクタ (muxorch.cpp:2198-2199) で `STATE_DB` へのコネクションと
`STATE_MUX_CABLE_TABLE_NAME` への Table オブジェクトを生成する。

```cpp
// muxorch.cpp:2198
std::unique_ptr<DBConnector> state_db = std::make_unique<DBConnector>("STATE_DB", 0);
state_mux_cable_table_ = std::make_unique<Table>(state_db.get(), STATE_MUX_CABLE_TABLE_NAME);
```

`handleMuxCfg()` (muxorch.cpp:2285) で `MUX_CABLE` SET 時に `neighbor_mode` フィールドを
STATE_DB `MUX_CABLE_TABLE` に書き込む:

```cpp
// muxorch.cpp:2285
state_mux_cable_table_->hset(port_name, "neighbor_mode", neighbor_mode_str);
```

この書込は `handlePeerSwitch()` が `mux_peer_switch_` を確定した**後**、`MUX_CABLE` エントリ
が処理された時点で発生する。PEER_SWITCH SET → `mux_peer_switch_` 確定 → MUX_CABLE SET
→ STATE_DB 書込 という因果連鎖になる。

## SAI / TUNNEL_DECAP 連動

### create_tunnel() による P2P トンネル SAI オブジェクト生成

`handlePeerSwitch()` SET パスで `create_tunnel()` (muxorch.cpp:2380) を呼び出す:

```cpp
// muxorch.cpp:2380
mux_tunnel_id_ = create_tunnel(&peer_ip, &dst_ip, tc_to_dscp_map_id, tc_to_queue_map_id, dscp_mode_name);
mux_peer_switch_ = peer_ip;
```

`create_tunnel()` (muxorch.cpp:217-329) 内で以下の SAI API 呼び出しが発生する:

1. `sai_router_intfs_api->create_router_interface()` — overlay loopback インターフェース生成
2. `sai_tunnel_api->create_tunnel()` — IP-in-IP P2P トンネルオブジェクト生成
   - `SAI_TUNNEL_TYPE_IPINIP`
   - `SAI_TUNNEL_ATTR_PEER_MODE = SAI_TUNNEL_PEER_MODE_P2P`
   - ENCAP_SRC_IP = `TUNNEL.src_ip` (MuxTunnel0 の dst_ip から取得)
   - ENCAP_DST_IP = `address_ipv4` (PEER_SWITCH の peer IP)
   - DSCP モード: `TUNNEL.dscp_mode` から継承

### TUNNEL_DECAP (decap_orch_) 参照

`handlePeerSwitch()` は `DecapOrch` から 3 つの値を取得する (muxorch.cpp:2348-2374):

```cpp
IpAddresses dst_ips = decap_orch_->getDstIpAddresses(MUX_TUNNEL);  // muxorch.cpp:2348
string dscp_mode_name = decap_orch_->getDscpMode(MUX_TUNNEL);       // muxorch.cpp:2359
decap_orch_->getQosMapId(MUX_TUNNEL, encap_tc_to_dscp_field_name, tc_to_dscp_map_id); // muxorch.cpp:2367
decap_orch_->getQosMapId(MUX_TUNNEL, encap_tc_to_queue_field_name, tc_to_queue_map_id); // muxorch.cpp:2374
```

`TUNNEL_DECAP` (APP_DB `TUNNEL_DECAP_TABLE` → DecapOrch) が未処理の場合、
`getDstIpAddresses()` が空を返し `handlePeerSwitch()` は `return false` でリトライ待機する。
これは PEER_SWITCH の処理が TUNNEL_DECAP 処理完了に依存することを示す。

## 副次 DB 書込サマリー

| 書込先 DB | テーブル | キー | フィールド | トリガー |
|----------|---------|------|-----------|--------|
| STATE_DB | MUX_CABLE_TABLE | `<port_name>` | `neighbor_mode` | MUX_CABLE SET (PEER_SWITCH 確定後) |
| SAI (ASIC_DB 経由) | — | — | tunnel object / overlay RIF | PEER_SWITCH SET |

## DEL パスの副次効果

`handlePeerSwitch()` DEL パス (muxorch.cpp:2387) は "Not Implemented" のログのみ:

```cpp
SWSS_LOG_NOTICE("Mux peer ip '%s' delete (Not Implemented), peer name '%s'",
                 peer_ip.to_string().c_str(), peer_name.c_str());
```

DEL 時に STATE_DB `MUX_CABLE_TABLE` や SAI トンネルオブジェクトはクリーンアップされない。
orchagent 再起動まで旧状態が残存する。
