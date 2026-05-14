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

しかし、実際の呼び出しパスを追うと:

- `VxlanTunnelMapOrch::addOperation` (line 2069) → `tunnel_obj->createTunnelHw(mapper_list, TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP)` — `encap_ttl` 省略 → デフォルト値 255 が使われる
- `VxlanVrfMapOrch::addOperation` (line 2297) → `tunnel_obj->createTunnelHw(mapper_list, TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP)` — `encap_ttl` 省略 → デフォルト値 255 が使われる
- `VxlanTunnelOrch::createVxlanTunnelMap` (line 1491, 1501) → `encap_ttl` を引数から渡す (呼び出し元依存)

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

**結論**: `encap_ttl=0` のときのみ SAI に `ENCAP_TTL_MODE` / `ENCAP_TTL_VAL` が渡されない。
`encap_ttl` のデフォルト引数は `DEFAULT_TUNNEL_ENCAP_TTL = 255` なので、
`createTunnelHw` を引数省略で呼ぶと SAI に `PIPE_MODEL + TTL=255` が渡る。

しかし `VxlanTunnelOrch::addOperation` (VXLAN_TUNNEL 作成) では `createTunnelHw` を直接呼ばない。
TUNNEL 作成は VTEP 登録のみで、実際の SAI tunnel creation は TUNNEL_MAP / VRF_MAP 追加時に遅延される。

### 2. `encap_ttl` が DB に存在しないフィールド

CONFIG_DB の `VXLAN_TUNNEL` テーブルに `encap_ttl` フィールドは存在しない。
YANG モデル (`sonic-vxlan.yang`) にも該当フィールドはない。
呼び出しパス上でデフォルト引数 255 が暗黙的に使われる。

### 3. `SAI_TUNNEL_ATTR_ENCAP_TTL_MODE` = `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` (条件付き)

`encap_ttl != 0` の場合のみ `SAI_TUNNEL_ATTR_ENCAP_TTL_MODE = SAI_TUNNEL_TTL_MODE_PIPE_MODEL` が設定される。
`encap_ttl == 0` の場合は ENCAP_TTL_MODE を設定しない → SAI プラットフォーム依存デフォルト。

### 4. `SAI_TUNNEL_ATTR_TYPE` = `SAI_TUNNEL_TYPE_VXLAN` (ハードコード)

`vxlanorch.cpp:303-305`:
```cpp
attr.id = SAI_TUNNEL_ATTR_TYPE;
attr.value.s32 = SAI_TUNNEL_TYPE_VXLAN;
tunnel_attrs.push_back(attr);
```

### 5. Peer mode: P2P vs P2MP (dst_ip 依存)

`vxlanorch.cpp:355-370`:
```cpp
if ((dst_ip != nullptr) && p2p)
{
    attr.id = SAI_TUNNEL_ATTR_PEER_MODE;
    attr.value.s32 = SAI_TUNNEL_PEER_MODE_P2P;
    ...
}
else
{
    attr.id = SAI_TUNNEL_ATTR_PEER_MODE;
    attr.value.s32 = SAI_TUNNEL_PEER_MODE_P2MP;
    ...
}
```

`p2p` フラグは `(src_creation_ == TNL_CREATION_SRC_EVPN)? true:false` により、
EVPN 作成時のみ P2P。CLI 作成 (`TNL_CREATION_SRC_CLI`) は常に P2MP (line 903-904)。

### 6. `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` は `ttl_mode` フィールド依存

`ttl_mode` が省略された場合 (`VxlanTunnelTTLMode::NOT_SET`) は `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` を SAI に渡さない。
これはプラットフォーム依存のデフォルトに委ねられる。

### 7. `tunnel_map_use_t` モード (encap mapper 共有/専用)

- `TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP`: encap/decap ともに専用 mapper を作成 (L3VNI/Bridge 用)
- `TUNNEL_MAP_USE_COMMON_ENCAP_DECAP`: EVPN DIP tunnel。src VTEP の encap/decap mapper を共有
- `TUNNEL_MAP_USE_COMMON_DECAP_DEDICATED_ENCAP`: decap は共有、encap は専用
- `TUNNEL_MAP_USE_DECAP_ONLY`: decap のみ (特殊)

### 8. encap mapper タイプ

| `tunnel_map_type_t` | encap MAP_T |
|--------------------|-------------|
| `TUNNEL_MAP_T_VLAN` | `VLAN_ID_TO_VNI` |
| `TUNNEL_MAP_T_VIRTUAL_ROUTER` | `VRID_TO_VNI` |
| `TUNNEL_MAP_T_BRIDGE` | `BRIDGE_TO_VNI` |

`vxlanorch.cpp:96-107`:
```cpp
static inline MAP_T tunnel_map_type (tunnel_map_type_t type, bool isencap)
{
    if (isencap) {
        switch(type) {
            case TUNNEL_MAP_T_VLAN : return MAP_T::VLAN_ID_TO_VNI;
            case TUNNEL_MAP_T_VIRTUAL_ROUTER: return MAP_T::VRID_TO_VNI;
            case TUNNEL_MAP_T_BRIDGE: return MAP_T::BRIDGE_TO_VNI;
        }
    }
    ...
}
```

## 引用

- `vxlanorch.h:49` `DEFAULT_TUNNEL_ENCAP_TTL 255`
- `vxlanorch.h:207` `createTunnelHw` シグネチャ
- `vxlanorch.cpp:289-414` `create_tunnel()` 関数全体
- `vxlanorch.cpp:885-950` `VxlanTunnel::createTunnelHw()`
- `vxlanorch.cpp:1591-1645` `VxlanTunnelOrch::addOperation()`
- `vxlanorch.cpp:1470-1533` `VxlanTunnelOrch::createVxlanTunnelMap()`
- `vxlanorch.cpp:2252-2297` `VxlanVrfMapOrch::addOperation()`
- `vxlanorch.cpp:2063-2070` `VxlanTunnelMapOrch::addOperation()` 抜粋
