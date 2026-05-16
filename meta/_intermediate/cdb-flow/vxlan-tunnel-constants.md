# VXLAN_TUNNEL ハードコード定数 (Phase E)

ソース: `sonic-swss/orchagent/vxlanorch.cpp`, `sonic-swss/orchagent/vxlanorch.h`, `sonic-swss/cfgmgr/vxlanmgr.cpp`

## 抽出定数一覧

### UDP デスティネーションポート

| 定数 | 値 | 場所 |
|------|----|------|
| `dstport 4789` | 4789 | `vxlanmgr.cpp:67`, `vxlanmgr.cpp:1015` |

- IANA 標準 VXLAN ポート (RFC 7348)
- `ip link add ... type vxlan ... dstport 4789` にてハードコード
- CONFIG_DB に設定フィールドなし・変更不可

### SAI tunnel_type enum

| シンボル | 値 | 用途 |
|---------|-----|------|
| `SAI_TUNNEL_TYPE_VXLAN` | SAI enum | `create_tunnel()` で `SAI_TUNNEL_ATTR_TYPE` に設定 (`vxlanorch.cpp:304`) |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` | SAI enum | dst_ip 省略時の termination エントリ型 (`vxlanorch.cpp:451`) |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2P` | SAI enum | dst_ip 明示時の termination エントリ型 (`vxlanorch.cpp:457`) |

### SAI tunnel_attr 一覧

| SAI 属性 | 設定タイミング | 値 / 条件 |
|---------|--------------|----------|
| `SAI_TUNNEL_ATTR_TYPE` | 常時 | `SAI_TUNNEL_TYPE_VXLAN` |
| `SAI_TUNNEL_ATTR_UNDERLAY_INTERFACE` | 常時 | `gUnderlayIfId` (アンダーレイ RIF OID) |
| `SAI_TUNNEL_ATTR_DECAP_MAPPERS` | 常時 | decap mapper OID リスト |
| `SAI_TUNNEL_ATTR_ENCAP_MAPPERS` | 常時 | encap mapper OID リスト |
| `SAI_TUNNEL_ATTR_ENCAP_SRC_IP` | src_ip あり | src VTEP IP |
| `SAI_TUNNEL_ATTR_PEER_MODE` | 常時 | `SAI_TUNNEL_PEER_MODE_P2P` (dst_ip あり) / `SAI_TUNNEL_PEER_MODE_P2MP` (dst_ip なし) |
| `SAI_TUNNEL_ATTR_ENCAP_DST_IP` | dst_ip あり | dst VTEP IP |
| `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` | ttl_mode=PIPE | `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` |
| `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` | ttl_mode=UNIFORM | `SAI_TUNNEL_TTL_MODE_UNIFORM_MODEL` |
| `SAI_TUNNEL_ATTR_ENCAP_TTL_MODE` | encap_ttl != 0 | `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` (dead path) |
| `SAI_TUNNEL_ATTR_ENCAP_TTL_VAL` | encap_ttl != 0 | encap_ttl 値 (dead path) |

### TTL モード enum (VxlanTunnelTTLMode)

```cpp
// vxlanorch.h:142
enum class VxlanTunnelTTLMode {
    NOT_SET,   // デフォルト: SAI に TTL 属性を渡さない → プラットフォーム依存
    PIPE,      // ttl_mode="pipe": SAI_TUNNEL_TTL_MODE_PIPE_MODEL
    UNIFORM    // ttl_mode="uniform": SAI_TUNNEL_TTL_MODE_UNIFORM_MODEL
};
```

- `NOT_SET` がデフォルト。`SAI_TUNNEL_ATTR_DECAP_TTL_MODE` は SAI に送られない
- `ttl_mode` フィールド省略時は `NOT_SET` → プラットフォーム ASIC 実装依存

### DEFAULT_TUNNEL_ENCAP_TTL

```cpp
// vxlanorch.h:49
#define DEFAULT_TUNNEL_ENCAP_TTL 255
```

- `createTunnelHw()` のデフォルト引数値
- ただし CONFIG_DB / YANG に `encap_ttl` フィールドが存在しないため、呼び出し元は常に `encap_ttl=0` を渡す
- 結果として `SAI_TUNNEL_ATTR_ENCAP_TTL_VAL` は実際には SAI に設定されない (dead path)

### DSCP モード

- `SAI_TUNNEL_ATTR_DECAP_DSCP_MODE` / `SAI_TUNNEL_ATTR_ENCAP_DSCP_MODE` は `vxlanorch.cpp` に設定コードなし
- DSCP モードは CONFIG_DB / orchagent 未実装。プラットフォームデフォルト適用

## MAP_T → SAI_TUNNEL_MAP_TYPE 対応表

| MAP_T enum | SAI_TUNNEL_MAP_TYPE |
|-----------|---------------------|
| `VNI_TO_VLAN_ID` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_VLAN_ID` |
| `VLAN_ID_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VNI` |
| `VRID_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_VIRTUAL_ROUTER_ID_TO_VNI` |
| `VNI_TO_VRID` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_VIRTUAL_ROUTER_ID` |
| `BRIDGE_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_BRIDGE_IF_TO_VNI` |
| `VNI_TO_BRIDGE` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_BRIDGE_IF` |

ソース: `vxlanorch.cpp:40-46`
