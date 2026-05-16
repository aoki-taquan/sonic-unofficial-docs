# Phase F 中間ファイル: VXLAN_EVPN_NVO 副次 DB 書込

ソース: `sonic-swss/orchagent/vxlanorch.cpp`

## 調査対象

`EvpnNvoOrch::addOperation()` (vxlanorch.cpp:2776-2793) は CONFIG_DB `VXLAN_EVPN_NVO` エントリを受け取り、参照する `VXLAN_TUNNEL`（VTEP）ポインタを `source_vtep_ptr` に格納する。直接的な DB 書込は行わないが、後続の VNI マッピング登録時に以下の副次書込が発生する。

## SAI tunnel_map 書込（SAI 経由）

`VxlanTunnel::createTunnelHw()` (vxlanorch.cpp:885-950) が呼ばれると、以下の SAI オブジェクトが作成される。

### 1. SAI `create_tunnel_map`

- **呼び出し箇所**: `vxlanorch.cpp:124-157` (`create_tunnel_map` 関数)
- **SAI API**: `sai_tunnel_api->create_tunnel_map()`
- **作成されるマップ型**:
  - `SAI_TUNNEL_MAP_TYPE_VNI_TO_VLAN_ID` (decap, VLAN モード)
  - `SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VNI` (encap, VLAN モード)
  - `SAI_TUNNEL_MAP_TYPE_VNI_TO_VIRTUAL_ROUTER_ID` (decap, VRF モード)
  - `SAI_TUNNEL_MAP_TYPE_VIRTUAL_ROUTER_ID_TO_VNI` (encap, VRF モード)
  - `SAI_TUNNEL_MAP_TYPE_VNI_TO_BRIDGE_IF` (decap, Bridge モード)
  - `SAI_TUNNEL_MAP_TYPE_BRIDGE_IF_TO_VNI` (encap, Bridge モード)
- **格納先**: `ids_.tunnel_decap_id[]` / `ids_.tunnel_encap_id[]` (VxlanTunnel 内部)

### 2. SAI `create_tunnel`

- **呼び出し箇所**: `vxlanorch.cpp:291-422` (`create_tunnel` 関数)
- **SAI API**: `sai_tunnel_api->create_tunnel()`
- **設定属性**:
  - `SAI_TUNNEL_ATTR_TYPE = SAI_TUNNEL_TYPE_VXLAN`
  - `SAI_TUNNEL_ATTR_DECAP_MAPPERS`: 上記 decap map OID 一覧
  - `SAI_TUNNEL_ATTR_ENCAP_MAPPERS`: 上記 encap map OID 一覧
  - `SAI_TUNNEL_ATTR_ENCAP_SRC_IP`: VTEP の src_ip
  - `SAI_TUNNEL_ATTR_PEER_MODE`: EVPN 動的トンネルは `SAI_TUNNEL_PEER_MODE_P2P`、VTEP は `SAI_TUNNEL_PEER_MODE_P2MP`
  - TTL モード属性 (PIPE / UNIFORM)
- **格納先**: `ids_.tunnel_id` (VxlanTunnel 内部)

### 3. SAI `create_tunnel_map_entry`

- **呼び出し箇所**: `vxlanorch.cpp:174-225` (`create_tunnel_map_entry` 関数)
- **SAI API**: `sai_tunnel_api->create_tunnel_map_entry()`
- VNI ↔ VLAN / VRF / Bridge のマッピングエントリ 1 件ごとに呼ばれる

## STATE_DB 書込

### STATE_DB: `VXLAN_TUNNEL_TABLE`

EVPN 動的トンネル（`TNL_CREATION_SRC_EVPN`）作成時に `VxlanTunnel` コンストラクタ (vxlanorch.cpp:524-547) から `addRemoveStateTableEntry()` が呼ばれる。

- **テーブル名**: `STATE_VXLAN_TUNNEL_TABLE_NAME = "VXLAN_TUNNEL_TABLE"` (schema.h:435)
- **キー形式**: `<tunnel_name>`（EVPN 動的トンネル名）
- **書込フィールド**:
  - `src_ip`: VTEP の source IP アドレス
  - `dst_ip`: リモート VTEP の destination IP
  - `tnl_src`: `"EVPN"`（EVPN 由来の場合）
  - `operstatus`: `"down"`（作成直後の初期値）
- **コード箇所**: `vxlanorch.cpp:1913-1954`

注意: `VXLAN_EVPN_NVO` 自体の `addOperation` は `source_vtep_ptr` の格納のみで STATE_DB への直接書込は行わない。STATE_DB 書込は EVPN ルートに基づいてリモート VTEP トンネルが作成される際に発生する。

## VXLAN_EVPN_NVO addOperation の直接副作用なし確認

`EvpnNvoOrch::addOperation()` (vxlanorch.cpp:2776-2793) のコードは以下のみ:
1. `nvo_name` / `vtep_name` の取得
2. `tunnel_orch->getVxlanTunnel(vtep_name)` で VTEP ポインタ取得
3. `source_vtep_ptr` への格納
4. `return true`

DB 書込なし。SAI API 呼び出しなし。副作用はポインタ格納のみ。後続の EVPN MAC/IP ルート受信時に上記 SAI 書込が連鎖的に発生する。
