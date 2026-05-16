# TUNNEL_DECAP_TABLE — Phase E: ハードコード定数調査

## 調査対象ソース

- `sonic-swss/orchagent/tunneldecaporch.cpp` (tunneldecaporch)
- `sonic-swss/orchagent/tunneldecaporch.h`

---

## ハードコード SAI 定数一覧

| 定数名 | 値 | 定義場所 | 用途 |
|--------|----|---------|------|
| `OVERLAY_RIF_DEFAULT_MTU` | `9100` | `tunneldecaporch.cpp` L14 | Overlay loopback ルータインターフェースの MTU。`SAI_ROUTER_INTERFACE_ATTR_MTU` として SAI に渡す。フィールドで上書き不可 |
| `SAI_TUNNEL_TYPE_IPINIP` | SAI enum | `tunneldecaporch.cpp` L768 | `tunnel_type == "IPINIP"` のとき `SAI_TUNNEL_ATTR_TYPE` に設定される固定値 |
| `SAI_ROUTER_INTERFACE_TYPE_LOOPBACK` | SAI enum | `tunneldecaporch.cpp` L746 | Overlay RIF は常に LOOPBACK タイプ。変更不可 |
| `SAI_TUNNEL_TTL_MODE_UNIFORM_MODEL` | SAI enum | `tunneldecaporch.cpp` L811 | `ttl_mode == "uniform"` のとき `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` に設定 |
| `SAI_TUNNEL_TTL_MODE_PIPE_MODEL` | SAI enum | `tunneldecaporch.cpp` L815 | `ttl_mode == "pipe"` のとき同属性に設定 |
| `SAI_TUNNEL_DSCP_MODE_UNIFORM_MODEL` | SAI enum | `tunneldecaporch.cpp` L823 | `dscp_mode == "uniform"` のとき `SAI_TUNNEL_ATTR_DECAP_DSCP_MODE` に設定 |
| `SAI_TUNNEL_DSCP_MODE_PIPE_MODEL` | SAI enum | `tunneldecaporch.cpp` L827 | `dscp_mode == "pipe"` のとき同属性に設定 |
| `SAI_TUNNEL_DECAP_ECN_MODE_COPY_FROM_OUTER` | SAI enum | `tunneldecaporch.cpp` L789 | `ecn_mode == "copy_from_outer"` のとき `SAI_TUNNEL_ATTR_DECAP_ECN_MODE` に設定 |
| `SAI_TUNNEL_DECAP_ECN_MODE_STANDARD` | SAI enum | `tunneldecaporch.cpp` L793 | `ecn_mode == "standard"` のとき同属性に設定 |
| `SAI_TUNNEL_ENCAP_ECN_MODE_STANDARD` | SAI enum | `tunneldecaporch.cpp` L802 | `encap_ecn_mode == "standard"` のとき `SAI_TUNNEL_ATTR_ENCAP_ECN_MODE` に設定 |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2P` | SAI enum | `tunneldecaporch.cpp` L928 | `term_type == P2P` のとき `SAI_TUNNEL_TERM_TABLE_ENTRY_ATTR_TYPE` に設定 |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_P2MP` | SAI enum | `tunneldecaporch.cpp` L932 | `term_type == P2MP` のとき同属性に設定 |
| `SAI_TUNNEL_TERM_TABLE_ENTRY_TYPE_MP2MP` | SAI enum | `tunneldecaporch.cpp` L936 | `term_type == MP2MP` のとき同属性に設定 |
| `MUX_TUNNEL` | `"MuxTunnel0"` | `tunneldecaporch.h` L21 | MuxOrch が固定参照する Dual-ToR トンネル名 |
| `SubnetDecapConfig.tunnel` | `"IPINIP_SUBNET"` | `tunneldecaporch.h` L101 | サブネット decap 用 IPv4 トンネル内部識別子 |
| `SubnetDecapConfig.tunnel_v6` | `"IPINIP_SUBNET_V6"` | `tunneldecaporch.h` L102 | サブネット decap 用 IPv6 トンネル内部識別子 |

---

## TTL / DSCP デフォルト値

フィールドに `ttl_mode` / `dscp_mode` を省略した場合、`addDecapTunnel()` では空文字列が渡され、SAI の `uniform` / `pipe` 分岐のいずれにも入らず、SAI デフォルト値が使われる（実装ではデフォルト固定値の定義なし）。

---

## Overlay RIF の固定パラメータ

| SAI 属性 | 値 | 備考 |
|----------|-----|------|
| `SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID` | `gVirtualRouterId` (デフォルト VRF) | ハードコード。VRF 分離不可 |
| `SAI_ROUTER_INTERFACE_ATTR_TYPE` | `SAI_ROUTER_INTERFACE_TYPE_LOOPBACK` | 固定 LOOPBACK タイプ |
| `SAI_ROUTER_INTERFACE_ATTR_MTU` | `9100` | `OVERLAY_RIF_DEFAULT_MTU` |

---

## 証跡

- `tunneldecaporch.cpp` L14: `#define OVERLAY_RIF_DEFAULT_MTU 9100`
- `tunneldecaporch.cpp` L741-750: Overlay RIF 属性設定（VR_ID, TYPE=LOOPBACK, MTU=9100）
- `tunneldecaporch.cpp` L767-827: `addDecapTunnel()` 内 SAI 定数割り当て
- `tunneldecaporch.cpp` L921-936: tunnel term entry type 分岐
- `tunneldecaporch.h` L21: `#define MUX_TUNNEL "MuxTunnel0"`
- `tunneldecaporch.h` L97-102: `SubnetDecapConfig` デフォルト値
