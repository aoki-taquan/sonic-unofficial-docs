# tunnel-encap-orch — Phase A 中間ファイル (VxlanTunnelOrch encap フィールド調査)

## 対象ファイル

- `sonic-net/sonic-swss` `orchagent/vxlanorch.cpp` SHA: `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `sonic-net/sonic-swss` `orchagent/vxlanorch.h` SHA: `4305596156d70e9797e8a881b3d19b46de0bce0d`

## Phase A 調査結果: encap 関連フィールドのコード由来デフォルト

### 1. `DEFAULT_TUNNEL_ENCAP_TTL = 255`

`vxlanorch.h:49`:
```cpp
#define DEFAULT_TUNNEL_ENCAP_TTL 255
```

`createTunnelHw` のシグネチャ:
```cpp
// vxlanorch.h:207
bool createTunnelHw(uint8_t mapper_list, tunnel_map_use_t map_src,
                    bool with_term = true, sai_uint8_t encap_ttl=DEFAULT_TUNNEL_ENCAP_TTL);
```

実際の呼び出しパス:

- `VxlanTunnelMapOrch::addOperation` (line 2069) → `tunnel_obj->createTunnelHw(mapper_list, TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP)` — `encap_ttl` 省略 → デフォルト値 255
- `VxlanVrfMapOrch::addOperation` (line 2297) → 同上 → デフォルト値 255
- `VxlanTunnelOrch::createVxlanTunnelMap` (line 1491, 1501) → `encap_ttl` を引数から渡す

`create_tunnel()` 関数内 (line 385-393):
```cpp
if (encap_ttl != 0)
{
    attr.id = SAI_TUNNEL_ATTR_ENCAP_TTL_MODE;
    attr.value.s32 = SAI_TUNNEL_TTL_MODE_PIPE_MODEL;
    tunnel_attrs.push_back(attr);
    attr.id = SAI_TUNNEL_ATTR_ENCAP_TTL_VAL;
    attr.value.u8 = encap_ttl;
    tunnel_attrs.push_back(attr);
}
```

**結論**: `encap_ttl` デフォルト 255 のパスでは `PIPE_MODEL + TTL=255` が SAI に渡る。

### 2. `encap_ttl` は DB / YANG に未定義フィールド

CONFIG_DB の `VXLAN_TUNNEL` テーブルに `encap_ttl` フィールドは存在しない。
YANG モデル (`sonic-vxlan.yang`) にも対応フィールドなし。

### 3. `SAI_TUNNEL_ATTR_TYPE` = `SAI_TUNNEL_TYPE_VXLAN` (ハードコード)

`vxlanorch.cpp:303-305`

### 4. Peer mode: P2P vs P2MP

CLI 作成 (`TNL_CREATION_SRC_CLI`) は常に `SAI_TUNNEL_PEER_MODE_P2MP`。
EVPN DIP トンネル (`TNL_CREATION_SRC_EVPN`) は `SAI_TUNNEL_PEER_MODE_P2P`。
`vxlanorch.cpp:903-904`

### 5. `SAI_TUNNEL_ATTR_DECAP_TTL_MODE`

`ttl_mode` 省略時 (`NOT_SET`) は SAI に渡さない → プラットフォーム依存。
`uniform` → `SAI_TUNNEL_TTL_MODE_UNIFORM_MODEL`。
`pipe` → `SAI_TUNNEL_TTL_MODE_PIPE_MODEL`。

### 6. encap mapper タイプ

| `tunnel_map_type_t` | encap MAP_T |
|--------------------|-------------|
| `TUNNEL_MAP_T_VLAN` | `VLAN_ID_TO_VNI` |
| `TUNNEL_MAP_T_VIRTUAL_ROUTER` | `VRID_TO_VNI` |
| `TUNNEL_MAP_T_BRIDGE` | `BRIDGE_TO_VNI` |

### 7. SAI tunnel 生成タイミング

`VXLAN_TUNNEL` 追加 (`VxlanTunnelOrch::addOperation`) では SAI 呼び出しなし。
`VXLAN_TUNNEL_MAP` / VRF map 追加時に遅延生成。

## 引用

- `vxlanorch.h:49` `DEFAULT_TUNNEL_ENCAP_TTL 255`
- `vxlanorch.h:207` `createTunnelHw` シグネチャ
- `vxlanorch.cpp:289-414` `create_tunnel()` 関数全体
- `vxlanorch.cpp:885-950` `VxlanTunnel::createTunnelHw()`
- `vxlanorch.cpp:1591-1645` `VxlanTunnelOrch::addOperation()`
- `vxlanorch.cpp:1470-1533` `VxlanTunnelOrch::createVxlanTunnelMap()`
- `vxlanorch.cpp:2252-2297` `VxlanVrfMapOrch::addOperation()`
- `vxlanorch.cpp:2063-2070` `VxlanTunnelMapOrch::addOperation()` 抜粋
