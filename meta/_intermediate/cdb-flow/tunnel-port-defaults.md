# VXLAN トンネルポート (Port::TUNNEL) — Phase A: コード由来の暗黙デフォルト調査

## 調査対象ソース

- `sonic-swss/orchagent/vxlanorch.cpp` (VxlanTunnelOrch)
- `sonic-swss/orchagent/vxlanorch.h`
- `sonic-swss/orchagent/portsorch.cpp` (PortsOrch::addTunnel / addBridgePort)
- `sonic-swss/orchagent/port.h` (Port 構造体)

---

## 概要

VXLAN トンネルポートは CONFIG_DB テーブルではなく、`orchagent` 内の `PortsOrch` が
`m_portList` に保持するランタイムオブジェクト。`Port::TUNNEL` 型の Port 構造体として
管理される。CONFIG_DB の `VXLAN_TUNNEL` / `VXLAN_TUNNEL_MAP` の処理結果として動的生成
される。

---

## トンネルポートの種別と命名

| 種別 | 命名規則 | 定数 | 生成元 |
|------|---------|------|-------|
| Local SRC VTEP ポート | `Port_SRC_VTEP_<src_ip>` | `LOCAL_TUNNEL_PORT_PREFIX` (vxlanorch.h:41) | `VxlanTunnelMapOrch::addOperation` |
| EVPN DIP トンネルポート | `Port_EVPN_<remote_vtep_ip>` | `EVPN_TUNNEL_PORT_PREFIX` (vxlanorch.h:42) | `VxlanTunnelOrch::addTunnelUser` |

---

## フィールド別コード由来デフォルト

### `m_type`

- 常に `Port::TUNNEL` ハードコード
- `PortsOrch::addTunnel()` L8362: `Port tunnel(tunnel_alias, Port::TUNNEL)`
- CONFIG_DB から変更不可

### `m_learn_mode` (FDB 学習モード)

- `PortsOrch::addTunnel(tunnel_alias, tunnel_id, hwlearning)` の `hwlearning` 引数で決定
- **EVPN DIP トンネルポート**: `hwlearning=false` → `SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DISABLE`
  - 根拠: `vxlanorch.cpp:1719` — `gPortsOrch->addTunnel(port_tunnel_name, dip_tunnel->getTunnelId(), false)`
- **Local SRC VTEP ポート** (DIP トンネル非サポート時): `hwlearning=false` → `SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DISABLE`
  - 根拠: `vxlanorch.cpp:2082` — `gPortsOrch->addTunnel(port_tunnel_name, tunnel_obj->getTunnelId(), false)`
- **結論**: 現在の実装ではすべてのトンネルポートで FDB ハードウェア学習は **常に無効** (DISABLE)
- CONFIG_DB に対応フィールドなし → 変更不可

### `m_oper_status` (初期運用状態)

- `PortsOrch::addTunnel()` L8372: `tunnel.m_oper_status = SAI_PORT_OPER_STATUS_DOWN`
- 初期値は常に `DOWN`
- その後 `updateDbTunnelOperStatus()` (vxlanorch.cpp:1893) による STATE_DB 通知で更新
- CONFIG_DB から制御不可（ランタイム状態のみ）

### `m_bridge_port_id` (ブリッジポート)

- `addTunnel()` 直後は `SAI_NULL_OBJECT_ID`
- `PortsOrch::addBridgePort()` (L7189) により SAI ブリッジポートとして登録される
- ブリッジポート生成時の SAI 属性:
  - `SAI_BRIDGE_PORT_ATTR_TYPE` → `SAI_BRIDGE_PORT_TYPE_TUNNEL` (L7230)
  - `SAI_BRIDGE_PORT_ATTR_TUNNEL_ID` → トンネル OID (L7234)
  - `SAI_BRIDGE_PORT_ATTR_BRIDGE_ID` → `m_default1QBridge` (デフォルト 1Q ブリッジ固定) (L7238)
  - `SAI_BRIDGE_PORT_ATTR_ADMIN_STATE` → `true` (UP) (L7250)
  - `SAI_BRIDGE_PORT_ATTR_FDB_LEARNING_MODE` → `port.m_learn_mode` (DISABLE) (L7255)

### `m_fdb_count` (FDB エントリ数)

- `port.h:234`: `uint32_t m_fdb_count = 0`
- デフォルト 0。FDB エントリが追加されると incrementされる
- 削除ガード: `m_fdb_count != 0` の場合 `removeBridgePort` をスキップ (vxlanorch.cpp:1770-1776, 1836-1840)

### `m_tunnel_id` (SAI トンネル OID)

- `PortsOrch::addTunnel()` 引数 `tunnel_id` から設定
- CONFIG_DB から直接指定不可 (orchagent が SAI から取得した OID を渡す)

---

## ハードコード定数

| 定数 | 値 | 場所 | 用途 |
|------|----|------|------|
| `LOCAL_TUNNEL_PORT_PREFIX` | `"Port_SRC_VTEP_"` | `vxlanorch.h:41` | Local VTEP ポート名プレフィックス |
| `EVPN_TUNNEL_PORT_PREFIX` | `"Port_EVPN_"` | `vxlanorch.h:42` | EVPN DIP トンネルポート名プレフィックス |
| `DEFAULT_TUNNEL_ENCAP_TTL` | `255` | `vxlanorch.h:49` | encap TTL のデフォルト値 (YANG 未定義) |
| `TUNNEL_STAT_FLEX_COUNTER_POLLING_INTERVAL_MS` | `10000` | `vxlanorch.h:40` | フレックスカウンター polling 間隔 (ms) |
| FDB learning mode | `DISABLE` | `portsorch.cpp:8370` | 全トンネルポートで HW 学習無効 |
| Bridge | `m_default1QBridge` | `portsorch.cpp:7238` | デフォルト 1Q ブリッジに常に接続 |
| Admin state | `true` (UP) | `portsorch.cpp:7250` | ブリッジポート作成時の admin 状態 |
| 初期 oper_status | `SAI_PORT_OPER_STATUS_DOWN` | `portsorch.cpp:8372` | 初期運用状態は常に DOWN |

---

## 生成フロー

### EVPN DIP トンネルポート生成 (DIP トンネルサポート有り)

```
addTunnelUser(remote_vtep, vni_id, ...) [vxlanorch.cpp:1674]
  → createDynamicDIPTunnel(remote_vtep, ...) [vxlanorch.cpp:1707]
  → getTunnelPort(remote_vtep, ...) が false の場合
  → getTunnelPortName(remote_vtep) = "Port_EVPN_<remote_vtep>"
  → gPortsOrch->addTunnel(port_tunnel_name, dip_tunnel->getTunnelId(), false)
     [hwlearning=false → m_learn_mode=DISABLE, m_oper_status=DOWN]
  → gPortsOrch->addBridgePort(tunnelPort)
     [SAI_BRIDGE_PORT_TYPE_TUNNEL, DISABLE, default 1Q bridge]
```

### Local SRC VTEP ポート生成 (DIP トンネル非サポート時)

```
VxlanTunnelMapOrch::addOperation [vxlanorch.cpp:2079]
  → getTunnelPort(src_vtep, tunPort, local=true) が false の場合
  → getTunnelPortName(src_vtep, true) = "Port_SRC_VTEP_<src_vtep>"
  → gPortsOrch->addTunnel(port_tunnel_name, tunnel_obj->getTunnelId(), false)
     [hwlearning=false → m_learn_mode=DISABLE]
  → gPortsOrch->addBridgePort(tunPort)
```

---

## 削除ガード条件

| 条件 | 動作 | 根拠 |
|------|------|------|
| `m_fdb_count != 0` | `removeBridgePort` をスキップ。`SWSS_LOG_ERROR` を記録 | `vxlanorch.cpp:1770-1776`, `vxlanorch.cpp:1836-1840` |
| ポートが存在しない | `getTunnelPort()` が `false` → `SWSS_LOG_WARN("Unable to find VTEP")` | `vxlanorch.cpp:1803` |

---

## 検出サマリ

| 種別 | フィールド | 内容 |
|------|----------|------|
| ハードコード初期値 | `m_oper_status` | 常に `SAI_PORT_OPER_STATUS_DOWN` で生成 |
| ハードコード | FDB learning | 全トンネルポートで `SAI_BRIDGE_PORT_FDB_LEARNING_MODE_DISABLE` 固定 |
| ハードコード | admin state | ブリッジポート作成時に常に `true` (UP) |
| ハードコード | bridge | デフォルト 1Q ブリッジ (`m_default1QBridge`) 固定 |
| CONFIG_DB 非連動 | 全フィールド | CONFIG_DB テーブルなし。VXLAN_TUNNEL_MAP 処理結果として動的生成 |
| YANG 未定義 | 全フィールド | sonic-yang-models に TUNNEL_PORT テーブル定義なし |
