# VXLAN_TUNNEL_MAP — Phase E: ハードコード定数調査

対象テーブル: `VXLAN_TUNNEL_MAP`
Consumer: `orchagent` / `VxlanTunnelMapOrch`
スキャン範囲: `sonic-swss/orchagent/vxlanorch.h`, `sonic-swss/orchagent/vxlanorch.cpp`

---

## 発見された定数一覧

### vxlanorch.h — 数値マクロ

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `MAX_VNI_ID` | `16777215` (= 2^24 - 1) | VNI 上限チェック。`vni_id >= MAX_VNI_ID` の場合 `SWSS_LOG_ERROR` + 永続破棄 (return true) | `vxlanorch.h:48` |
| `MIN_VLAN_ID` | `1` | `to_uint<sai_vlan_id_t>(vlan_name.substr(4), MIN_VLAN_ID, MAX_VLAN_ID)` の下限クランプ | `vxlanorch.h:45` |
| `MAX_VLAN_ID` | `4095` | 同上、上限クランプ。VLAN 名の数字部分が 1–4095 範囲外なら例外 | `vxlanorch.h:46` |
| `DEFAULT_TUNNEL_ENCAP_TTL` | `255` | `create_tunnel()` の `encap_ttl` 引数省略時に使用される TTL 初期値 | `vxlanorch.h:49` |
| `TUNNEL_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` ms | トンネル統計 flex counter ポーリング間隔（10 秒） | `vxlanorch.h:40` |

### vxlanorch.h — 文字列マクロ（ポート名プレフィクス）

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `TUNNEL_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"TUNNEL_STAT_COUNTER"` | flex_counter_manager へ渡すグループ名 | `vxlanorch.h:39` |
| `LOCAL_TUNNEL_PORT_PREFIX` | `"Port_SRC_VTEP_"` | 自ノード VTEP 発トンネルポート名のプレフィクス | `vxlanorch.h:41` |
| `EVPN_TUNNEL_PORT_PREFIX` | `"Port_EVPN_"` | EVPN remote VTEP トンネルポート名のプレフィクス | `vxlanorch.h:42` |
| `EVPN_TUNNEL_NAME_PREFIX` | `"EVPN_"` | EVPN 動的 DIP トンネル名のプレフィクス | `vxlanorch.h:43` |

### vxlanorch.h — 列挙型定数（MAP_T）

`MAP_T` enum は `vxlanTunnelMap` テーブルと `vxlanTunnelMapKeyVal` テーブルで SAI 定数に対応付けられる。

| MAP_T 値 | SAI マップ種別 | SAI エントリ key attr | SAI エントリ value attr | evidence |
|---------|-------------|---------------------|----------------------|---------|
| `VNI_TO_VLAN_ID` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_VLAN_ID` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VLAN_ID_VALUE` | `vxlanorch.cpp:40,51` |
| `VLAN_ID_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_VLAN_ID_TO_VNI` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VLAN_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_VALUE` | `vxlanorch.cpp:41,54` |
| `VRID_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_VIRTUAL_ROUTER_ID_TO_VNI` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VIRTUAL_ROUTER_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_VALUE` | `vxlanorch.cpp:42,57` |
| `VNI_TO_VRID` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_VIRTUAL_ROUTER_ID` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VIRTUAL_ROUTER_ID_VALUE` | `vxlanorch.cpp:43,60` |
| `BRIDGE_TO_VNI` | `SAI_TUNNEL_MAP_TYPE_BRIDGE_IF_TO_VNI` | `SAI_TUNNEL_MAP_ENTRY_ATTR_BRIDGE_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_VALUE` | `vxlanorch.cpp:44,63` |
| `VNI_TO_BRIDGE` | `SAI_TUNNEL_MAP_TYPE_VNI_TO_BRIDGE_IF` | `SAI_TUNNEL_MAP_ENTRY_ATTR_VNI_ID_KEY` | `SAI_TUNNEL_MAP_ENTRY_ATTR_BRIDGE_ID_VALUE` | `vxlanorch.cpp:45,66` |

### vxlanorch.h — 列挙型定数（tunnel_map_use_t）

TUNNEL_MAP の encap/decap マッパー共有モードを制御する。`VXLAN_TUNNEL_MAP` の初回追加時は常に `TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP` が使用される。

| 列挙値 | 意味 |
|--------|------|
| `TUNNEL_MAP_USE_COMMON_ENCAP_DECAP` | DIP トンネルが VTEP の encap/decap マッパーを共有（EVPN remote DIP トンネル用） |
| `TUNNEL_MAP_USE_COMMON_DECAP_DEDICATED_ENCAP` | decap は共有、encap は専用 |
| `TUNNEL_MAP_USE_DECAP_ONLY` | decap のみ |
| `TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP` | encap/decap ともに専用（CLI / EVPN NVO VTEP 用、**VXLAN_TUNNEL_MAP 追加時に使用**） |

### vxlanorch.cpp — flex counter / その他数値定数

| 定数 | 値 | 用途 | evidence |
|-----|-----|------|---------|
| `FLEX_COUNTER_UPD_INTERVAL` | `1` | flex counter 更新間隔マクロ（内部使用） | `vxlanorch.cpp:36` |

---

## VXLAN_TUNNEL_MAP に直接関係する定数の運用意味

1. **`MAX_VNI_ID = 16777215`**: RFC 7348 の VNI 上限（24bit）。`vni_id >= MAX_VNI_ID` は厳密等価含む不等号（`>=`）のため、VNI=16777215 も reject される。実質有効範囲は `1–16777214`。
2. **`MIN_VLAN_ID / MAX_VLAN_ID = 1 / 4095`**: `vlan` 文字列の `Vlan` プレフィクス以降を数値化する際のクランプ範囲。範囲外の場合は `to_uint` が例外を送出する（catch → SWSS_LOG_WARN + return false）。
3. **`TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP`**: `VXLAN_TUNNEL_MAP` の初回 SET で呼ばれる `createTunnelHw()` に渡されるモード。このモードでは encap 用 VLAN→VNI マッパーと decap 用 VNI→VLAN マッパーが独立して SAI に生成される（`vxlanorch.cpp:755-780`）。

---

## スキャン証跡

- `vxlanorch.h` L39-49 (マクロ定義全件), L12-63 (enum 定義全件) を読了。
- `vxlanorch.cpp` L36-70 (グローバル定数テーブル), L2037-2040 (MAX_VNI_ID チェック) を読了。
- 数値マクロ 5 件、文字列マクロ 4 件、enum 10 件、運用意味 3 件を抽出。

source: `sonic-swss/orchagent/vxlanorch.h`, `sonic-swss/orchagent/vxlanorch.cpp`
