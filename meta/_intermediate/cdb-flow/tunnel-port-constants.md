# VXLAN トンネルポート (Port::TUNNEL) — Phase E: ハードコード定数調査

## 調査対象ソース

- `sonic-swss/orchagent/vxlanorch.h`
- `sonic-swss/orchagent/vxlanorch.cpp`
- `sonic-swss/orchagent/portsorch.cpp`

Evidence sha: `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## ハードコード定数一覧

VXLAN トンネルポートオブジェクト (`Port::TUNNEL`) の生成・命名・検証に関わるハードコード定数。これらは CONFIG_DB テーブルフィールドには存在せず、コードに直書きされている。

### ポート名プレフィックス

| 定数名 | 値 | 定義場所 | 用途 |
|--------|----|---------|------|
| `LOCAL_TUNNEL_PORT_PREFIX` | `"Port_SRC_VTEP_"` | `vxlanorch.h:41` | Local SRC VTEP ポート名のプレフィックス。`getTunnelPortName(vtep, local=true)` で連結して `"Port_SRC_VTEP_<vtep_ip>"` を生成 |
| `EVPN_TUNNEL_PORT_PREFIX` | `"Port_EVPN_"` | `vxlanorch.h:42` | EVPN DIP トンネルポート名のプレフィックス。`getTunnelPortName(vtep, local=false)` で連結して `"Port_EVPN_<remote_vtep_ip>"` を生成 |
| `EVPN_TUNNEL_NAME_PREFIX` | `"EVPN_"` | `vxlanorch.h:43` | EVPN DIP トンネルオブジェクトの名前プレフィックス（`VxlanTunnel` インスタンス名）。ポート名 (`Port_EVPN_*`) とは別オブジェクトに使用 |

### VNI / VLAN 検証境界値

| 定数名 | 値 | 定義場所 | 用途 |
|--------|----|---------|------|
| `MIN_VLAN_ID` | `1` | `vxlanorch.h:45` | VLAN ID の最小値。`to_uint<sai_vlan_id_t>(vlan_name.substr(4), MIN_VLAN_ID, MAX_VLAN_ID)` の下限 |
| `MAX_VLAN_ID` | `4095` | `vxlanorch.h:46` | VLAN ID の最大値。上限超過は parse 時にエラー |
| `MAX_VNI_ID` | `16777215` | `vxlanorch.h:48` | VNI の最大値 (2^24 − 1)。`vni_id >= MAX_VNI_ID` の場合 `SWSS_LOG_ERROR` を出力して `return true`（恒久エラー）。Local SRC VTEP ポート生成もブロックされる |

### encap TTL デフォルト

| 定数名 | 値 | 定義場所 | 用途 |
|--------|----|---------|------|
| `DEFAULT_TUNNEL_ENCAP_TTL` | `255` | `vxlanorch.h:49` | VXLAN encap パケットの TTL デフォルト値。YANG モデルに対応フィールドがないため CONFIG_DB 経由では変更不可 |

### FlexCounter (統計) 関連

| 定数名 | 値 | 定義場所 | 用途 |
|--------|----|---------|------|
| `TUNNEL_STAT_COUNTER_FLEX_COUNTER_GROUP` | `"TUNNEL_STAT_COUNTER"` | `vxlanorch.h:39` | FlexCounterManager に登録するカウンタグループ名。`VxlanTunnelOrch::VxlanTunnelOrch()` (vxlanorch.cpp:1291) で使用 |
| `TUNNEL_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` | `vxlanorch.h:40` | FlexCounter のポーリング間隔 (ms)。10 秒固定。CONFIG_DB から変更不可 |
| `FLEX_COUNTER_UPD_INTERVAL` | `1` | `vxlanorch.cpp:36` | FlexCounter 更新タイマーの秒数。`timespec { .tv_sec = 1, .tv_nsec = 0 }` として使用 |

### SAI 属性のハードコード値（orsorch.cpp）

これらは `PortsOrch::addTunnel()` / `PortsOrch::addBridgePort()` 内でコードに直書きされており、CONFIG_DB フィールドに対応しない。

| 属性 | 値 | 定義箇所 | 備考 |
|------|----|---------|------|
| `SAI_BRIDGE_PORT_ATTR_TYPE` | `SAI_BRIDGE_PORT_TYPE_TUNNEL` | `portsorch.cpp:7230` | TUNNEL 型ポートに固定 |
| `SAI_BRIDGE_PORT_ATTR_BRIDGE_ID` | `m_default1QBridge` | `portsorch.cpp:7238` | デフォルト 1Q ブリッジに固定 |
| `SAI_BRIDGE_PORT_ATTR_ADMIN_STATE` | `true` (UP) | `portsorch.cpp:7250` | 作成時に常に UP |
| `SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE` | `SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DISABLE` | `portsorch.cpp:8370` | `hwlearning=false` が固定で渡されるため常に DISABLE |
| `m_oper_status` 初期値 | `SAI_PORT_OPER_STATUS_DOWN` | `portsorch.cpp:8373` | トンネルポート作成直後は常に DOWN |

---

## 定数の影響と運用上の注意

### ポート名プレフィックスの固定

- `Port_SRC_VTEP_` / `Port_EVPN_` は内部識別子として `m_portList` のキーになる
- `getTunnelPort(vtep, port, local)` でポート検索時に `getTunnelPortName()` を使ってキーを組み立てる
- 外部からポート名を変更する手段はなく、命名ルールはコードに固定

### MAX_VNI_ID = 16777215 の影響

- `vni_id >= MAX_VNI_ID` (≥ 2^24) の場合、`VxlanTunnelMapOrch::addOperation()` が `return true`（完了扱い）を返すため、エラーは永続的でリトライされない
- VNI 範囲は YANG でも `range "1..16777215"` と一致している（`sonic-vxlan.yang`）

### DEFAULT_TUNNEL_ENCAP_TTL = 255 の影響

- YANG `sonic-vxlan` に encap TTL フィールドの定義はない
- CONFIG_DB の VXLAN_TUNNEL テーブルにも `encap_ttl` フィールドは存在しない
- 変更にはコードのリコンパイルが必要

### TUNNEL_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS = 10000 の影響

- トンネル統計の FlexCounter は 10 秒間隔で収集される
- `gTraditionalFlexCounter` フラグが true の場合は旧来の VID→RID テーブル参照方式、false の場合は新方式
- polling 間隔は CONFIG_DB の FlexCounter 設定テーブルからではなく、コードから直接 FlexCounterManager に渡される

---

*生成日: 2026-05-17*
