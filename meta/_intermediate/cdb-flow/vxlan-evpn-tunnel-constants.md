# EVPN DIP トンネル (動的生成) — Phase E: ハードコード定数

## 対象

`sonic-swss/orchagent/vxlanorch.h`、`sonic-swss/orchagent/vxlanorch.cpp`、
`sonic-swss-common/common/schema.h` に定義されているハードコード定数。

---

## 名前プレフィックス定数 (vxlanorch.h:42-43)

```cpp
#define EVPN_TUNNEL_PORT_PREFIX  "Port_EVPN_"
#define EVPN_TUNNEL_NAME_PREFIX  "EVPN_"
```

| 定数 | 値 | 用途 |
|------|----|------|
| `EVPN_TUNNEL_NAME_PREFIX` | `"EVPN_"` | DIP トンネル名: `EVPN_<remote_vtep_ip>` |
| `EVPN_TUNNEL_PORT_PREFIX` | `"Port_EVPN_"` | DIP トンネルポート名: `Port_EVPN_<remote_vtep_ip>` |

---

## 数値境界値定数 (vxlanorch.h:45-49)

```cpp
#define MIN_VLAN_ID 1
#define MAX_VLAN_ID 4095
#define MAX_VNI_ID 16777215
#define DEFAULT_TUNNEL_ENCAP_TTL 255
```

| 定数 | 値 | 用途 |
|------|----|------|
| `MIN_VLAN_ID` | `1` | VLAN ID の下限。`to_uint<sai_vlan_id_t>()` の境界チェックに使用 (`vxlanorch.cpp:2621`, `2704`) |
| `MAX_VLAN_ID` | `4095` | VLAN ID の上限 (IEEE 802.1Q) |
| `MAX_VNI_ID` | `16777215` (`0xFFFFFF`) | VNI の上限 (24-bit)。`vni_id >= MAX_VNI_ID` をチェックし超過時は warn + return false (`vxlanorch.cpp:2037`, `2461`) |
| `DEFAULT_TUNNEL_ENCAP_TTL` | `255` | VXLAN_TUNNEL (`TNL_CREATION_SRC_CLI`) のデフォルト encap TTL。EVPN DIP トンネルは TTL 属性を SAI に渡さないため**適用されない** |

---

## tunnel_creation_src_t enum (vxlanorch.h:52-55)

```cpp
typedef enum {
    TNL_CREATION_SRC_CLI,   // 0
    TNL_CREATION_SRC_EVPN   // 1
} tunnel_creation_src_t;
```

EVPN DIP トンネルは常に `TNL_CREATION_SRC_EVPN` で生成され、この値が peer_mode 判定
(`vxlanorch.cpp:903`) や `tnl_src` STATE_DB 書き込み (`vxlanorch.cpp:1934-1939`) の分岐に使われる。

---

## tunnel_map_use_t enum (vxlanorch.h:58-63)

```cpp
typedef enum {
    TUNNEL_MAP_USE_COMMON_ENCAP_DECAP,
    TUNNEL_MAP_USE_COMMON_DECAP_DEDICATED_ENCAP,
    TUNNEL_MAP_USE_DECAP_ONLY,
    TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP
} tunnel_map_use_t;
```

EVPN DIP トンネルは `TUNNEL_MAP_USE_COMMON_ENCAP_DECAP` でハードコードされている
(`vxlanorch.cpp:1169`)。

---

## STATE_DB テーブル名 (schema.h:435)

```cpp
#define STATE_VXLAN_TUNNEL_TABLE_NAME "VXLAN_TUNNEL_TABLE"
```

EVPN DIP トンネルの生成・削除・oper status 変更はすべてこのテーブルに書き込まれる
(`vxlanorch.cpp:1247`, `vxlanorch.cpp:1910`, `vxlanorch.cpp:1928-1953`)。

---

## ハードコード文字列定数 (STATE_DB フィールド値)

| フィールド | ハードコード値 | ソース |
|-----------|--------------|--------|
| `tnl_src` (EVPN 側) | `"EVPN"` | `vxlanorch.cpp:1939` |
| `tnl_src` (CLI 側) | `"CLI"` | `vxlanorch.cpp:1934` |
| `operstatus` (初期値) | `"down"` | `vxlanorch.cpp:1942` |
| `operstatus` (up 遷移) | `"up"` | `vxlanorch.cpp:1901` |
| `operstatus` (down 遷移) | `"down"` | `vxlanorch.cpp:1905` |
| VLAN flood domain `tagging_mode` | `"untagged"` | `vxlanorch.cpp:2525`, `vxlanorch.cpp:2685` |

---

## APP_DB テーブル名 (schema.h)

```cpp
#define APP_VXLAN_REMOTE_VNI_TABLE_NAME  "VXLAN_REMOTE_VNI_TABLE"
#define APP_VXLAN_TUNNEL_TABLE_NAME      "VXLAN_TUNNEL_TABLE"
```

`EvpnRemoteVnip2pOrch` は `APP_VXLAN_REMOTE_VNI_TABLE_NAME` ("VXLAN_REMOTE_VNI_TABLE") を購読し
DIP トンネルの生成・削除を処理する (`vxlanorch.cpp:2447-2520`)。

---

## 参照コード

- `sonic-swss/orchagent/vxlanorch.h`: l.42-49 (プレフィックス定数・数値境界)、l.52-63 (enum 定義)
- `sonic-swss/orchagent/vxlanorch.cpp`: l.903, l.1169, l.1934-1942 (定数参照箇所)、l.2037, l.2461, l.2621 (VNI/VLAN 境界チェック)
- `sonic-swss-common/common/schema.h`: l.434-435 (STATE_DB テーブル名)、l.85-88 (APP_DB テーブル名)
