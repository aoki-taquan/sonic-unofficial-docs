# IPINIP Tunnel (tunneldecaporch) — Phase E: ハードコード定数調査

## 調査対象ソース

- `sonic-swss/orchagent/tunneldecaporch.cpp`
- `sonic-swss/orchagent/tunneldecaporch.h`

## 対象ドキュメント

`docs/reference/config-db/ipinip-tunnel.md` は存在しない。  
近似 slug `docs/reference/config-db/tunnel.md` は既に `<!-- constants -->` ブロック実装済み（`tunnel-constants.md` 参照）。  
本ファイルは `tunneldecaporch.cpp` 起点の Phase E 調査記録として独立して保存する。

---

## ハードコード定数一覧 (tunneldecaporch.cpp 起点)

| 定数名 | 値 | 定義場所 | 用途 |
|--------|----|---------|------|
| `OVERLAY_RIF_DEFAULT_MTU` | `9100` | `tunneldecaporch.cpp` L14 | Overlay loopback RIF の MTU。`SAI_ROUTER_INTERFACE_ATTR_MTU` として SAI に渡す。CONFIG_DB から読まない |
| `SAI_TUNNEL_TYPE_IPINIP` (SAI enum) | — | `tunneldecaporch.cpp` L768 | トンネル種別。`tunnel_type == "IPINIP"` の場合のみ到達するため、事実上 IPinIP 固定 |
| `SAI_TUNNEL_TTL_MODE_UNIFORM_MODEL` | — | `tunneldecaporch.cpp` L811 | `ttl_mode == "uniform"` 時に `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` に設定する SAI enum 値 |
| `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` | — | `tunneldecaporch.cpp` L815 | `ttl_mode == "pipe"` 時に設定する SAI enum 値 |
| `SAI_TUNNEL_DSCP_MODE_UNIFORM_MODEL` | — | `tunneldecaporch.cpp` L823 | `dscp_mode == "uniform"` 時に `SAI_TUNNEL_ATTR_DECAP_DSCP_MODE` に設定する SAI enum 値 |
| `SAI_TUNNEL_DSCP_MODE_PIPE_MODEL` | — | `tunneldecaporch.cpp` L827 | `dscp_mode == "pipe"` 時に設定する SAI enum 値 |
| `SAI_TUNNEL_DECAP_ECN_MODE_COPY_FROM_OUTER` | — | `tunneldecaporch.cpp` L789 | `ecn_mode == "copy_from_outer"` 時に `SAI_TUNNEL_ATTR_DECAP_ECN_MODE` に設定 |
| `SAI_TUNNEL_DECAP_ECN_MODE_STANDARD` | — | `tunneldecaporch.cpp` L793 | `ecn_mode == "standard"` 時に設定 |
| `MUX_TUNNEL` | `"MuxTunnel0"` | `tunneldecaporch.h` L21 | MuxOrch が固定参照する Dual-ToR トンネル名 |
| `SubnetDecapConfig.tunnel` | `"IPINIP_SUBNET"` | `tunneldecaporch.h` L101 | サブネット decap 用 IPv4 トンネル識別子（内部用） |
| `SubnetDecapConfig.tunnel_v6` | `"IPINIP_SUBNET_V6"` | `tunneldecaporch.h` L102 | サブネット decap 用 IPv6 トンネル識別子（内部用） |

---

## デフォルト値の有無

### TTL デフォルト

`ttl_mode` に対するハードコードデフォルトは存在しない。`tunneldecaporch.cpp` は `ttl_mode == "uniform"` / `"pipe"` の分岐しか持たず、どちらでもない場合は SAI attrs への push が行われないまま `create_tunnel()` が呼ばれる（SAI 実装依存）。  
CONFIG_DB エントリで `ttl_mode` を省略した場合の挙動は SAI ドライバに依存。

### dscp_mode デフォルト

同様に `dscp_mode` のハードコードデフォルトは存在しない。`dscp_mode == "uniform"` / `"pipe"` 以外は SAI に `DECAP_DSCP_MODE` が push されない。

### tunnel_type

`tunnel_type != "IPINIP"` はエラーとして `valid=false` になる（`tunneldecaporch.cpp` L127-131）。実質的に `IPINIP` がハードコード固定値。

---

## SAI tunnel 属性の付与順序 (addDecapTunnel)

```
SAI_TUNNEL_ATTR_TYPE                    = SAI_TUNNEL_TYPE_IPINIP  (固定)
SAI_TUNNEL_ATTR_OVERLAY_INTERFACE       = overlayIfId
SAI_TUNNEL_ATTR_UNDERLAY_INTERFACE      = gUnderlayIfId
SAI_TUNNEL_ATTR_ENCAP_SRC_IP            = src_ip (設定時のみ)
SAI_TUNNEL_ATTR_DECAP_ECN_MODE          = copy_from_outer | standard
SAI_TUNNEL_ATTR_ENCAP_ECN_MODE          = standard (encap_ecn_mode 設定時のみ)
SAI_TUNNEL_ATTR_DECAP_TTL_MODE          = UNIFORM_MODEL | PIPE_MODEL
SAI_TUNNEL_ATTR_DECAP_DSCP_MODE         = UNIFORM_MODEL | PIPE_MODEL
SAI_TUNNEL_ATTR_DECAP_QOS_DSCP_TO_TC_MAP    (dscp_to_tc_map_id 設定時のみ)
SAI_TUNNEL_ATTR_DECAP_QOS_TC_TO_PRIORITY_GROUP_MAP  (tc_to_pg_map_id 設定時のみ)
```

Overlay RIF 作成時:
```
SAI_ROUTER_INTERFACE_ATTR_MTU = 9100  (OVERLAY_RIF_DEFAULT_MTU 固定)
```

---

## 証跡

- `tunneldecaporch.cpp` L14: `#define OVERLAY_RIF_DEFAULT_MTU 9100`
- `tunneldecaporch.cpp` L127: `if (tunnel_type != "IPINIP")` → valid=false
- `tunneldecaporch.cpp` L766-768: `// tunnel type (only ipinip for now)` + `SAI_TUNNEL_TYPE_IPINIP`
- `tunneldecaporch.cpp` L808-827: TTL / DSCP mode SAI enum マッピング
- `tunneldecaporch.cpp` L749-750: `overlay_intf_attr.value.u32 = OVERLAY_RIF_DEFAULT_MTU`
- `tunneldecaporch.h` L21: `#define MUX_TUNNEL "MuxTunnel0"`
- `tunneldecaporch.h` L97-102: `SubnetDecapConfig subnetDecapConfig = {"IPINIP_SUBNET", "IPINIP_SUBNET_V6"}`
