# VXLAN トンネルポート (Port::TUNNEL) — Phase C: 暗黙参照テーブル調査

## 調査対象ソース

- `sonic-swss/orchagent/vxlanorch.cpp` (VxlanTunnelOrch, VxlanTunnelMapOrch)
- `sonic-swss/orchagent/portsorch.cpp` (PortsOrch::addTunnel, addBridgePort)
- `sonic-swss/orchagent/port.h`

---

## 概要

VXLAN トンネルポートは CONFIG_DB テーブルではないため、直接的なテーブル購読はない。
しかし、生成・削除・状態更新の各フェーズで以下のオブジェクト・テーブルを暗黙的に参照する。

---

## 参照テーブル一覧

### 1. VXLAN_EVPN_NVO (CONFIG_DB) — addTunnelUser の前提

- `addTunnelUser()` (vxlanorch.cpp:1678) は `gDirectory.get<EvpnNvoOrch*>()` で `EvpnNvoOrch` を取得。
- `evpn_orch->getEVPNVtep()` が NULL の場合: `SWSS_LOG_WARN("Unable to find EVPN VTEP")` → `return false`。
- `VXLAN_EVPN_NVO` が CONFIG_DB に書かれ `EvpnNvoOrch::addOperation` が処理されることで `source_vtep_ptr` が設定される。
- **参照方向**: 読み取り (必須前提条件)
- evidence: `vxlanorch.cpp:1678`, `vxlanorch.cpp:1685-1692`

### 2. VXLAN_TUNNEL (CONFIG_DB) — SAI トンネル OID 依存

- `addTunnel(port_tunnel_name, dip_tunnel->getTunnelId(), false)` の第2引数は SAI トンネル OID。
- SIP トンネルの SAI OID は `VxlanTunnel::getTunnelId()` で取得。これは `createTunnelHw()` の成功後に有効。
- `isActive()` チェック (vxlanorch.cpp:1694) で `active_=false` なら `Port_EVPN_*` 生成がブロック。
- **参照方向**: 読み取り (SAI OID 取得)
- evidence: `vxlanorch.cpp:1694-1699`, `vxlanorch.cpp:1707`, `vxlanorch.cpp:1719`

### 3. VXLAN_TUNNEL_MAP (CONFIG_DB) — 生成トリガー（DIP 非サポート時）

- DIP 非サポート (`isDipTunnelsSupported() == false`) の場合、`Port_SRC_VTEP_*` は `VxlanTunnelMapOrch::addOperation` (vxlanorch.cpp:2079) でのみ生成される。
- `VXLAN_TUNNEL_MAP` エントリが存在しない場合は生成トリガーがなく、ポートは作られない。
- **参照方向**: 生成トリガー依存
- evidence: `vxlanorch.cpp:2076-2088`

### 4. STATE_DB:VXLAN_TUNNEL_TABLE — operstatus 書き込み

- `updateDbTunnelOperStatus(tunnel_portname, status)` (vxlanorch.cpp:1893) が `m_stateVxlanTable.set()` で STATE_DB に `operstatus` を書き込む。
- `m_stateVxlanTable` は `VxlanTunnelOrch` コンストラクタ (vxlanorch.cpp:1247) で `statedb, STATE_VXLAN_TUNNEL_TABLE_NAME` として初期化。
- 書き込みフィールド: `operstatus` = `"up"` / `"down"`。
- **参照方向**: 書き込み (一方向)
- evidence: `vxlanorch.cpp:1893-1912`, `vxlanorch.cpp:1247`

### 5. PortsOrch::m_portList (内部) — ポートオブジェクト管理

- `PortsOrch::addTunnel(alias, tunnel_id, hwlearning)` (portsorch.cpp:8362) が `Port` 構造体を作成し `m_portList[alias]` に登録。
- `getTunnelPort(vtep, tunnelPort, local)` (vxlanorch.cpp:1957) が `getTunnelPortName` で名前を生成し `gPortsOrch->getPort(name, port)` で存在確認。
- 重複防止: `getTunnelPort` が `true` を返した場合は `addTunnel` をスキップ。
- **参照方向**: 読み取り / 書き込み (双方向)
- evidence: `portsorch.cpp:8362`, `vxlanorch.cpp:1715`, `vxlanorch.cpp:1957-1966`

### 6. PortsOrch::m_default1QBridge (内部) — ブリッジ固定参照

- `PortsOrch::addBridgePort(port)` (portsorch.cpp:7189) が `SAI_BRIDGE_PORT_ATTR_BRIDGE_ID` に `m_default1QBridge` を使用。
- ハードコードで常にデフォルト 1Q ブリッジに接続される。変更不可。
- **参照方向**: 読み取り (ハードコード)
- evidence: `portsorch.cpp:7238`

### 7. FdbOrch (間接参照) — FDB カウント管理

- `tunnelPort.m_fdb_count` (port.h:234) が 0 になるまでブリッジポート削除がブロックされる。
- FDB エントリの追加・削除は `FdbOrch` が管理し、`m_fdb_count` をインクリメント / デクリメント。
- トンネルポートの削除タイミングが FDB エージングに依存する。
- **参照方向**: 間接参照 (削除ガード)
- evidence: `vxlanorch.cpp:1770-1776`, `port.h:234`

---

## 参照方向まとめ

| 参照先 | 参照方向 | 必須 / 任意 | 自動回復 |
|--------|---------|------------|---------|
| `VXLAN_EVPN_NVO` | 読み取り (前提) | 必須 (EVPN DIP 生成時) | あり (再試行) |
| `VXLAN_TUNNEL` SAI OID | 読み取り | 必須 | あり (再試行) |
| `VXLAN_TUNNEL_MAP` | 生成トリガー | 必須 (DIP 非サポート時) | なし (手動) |
| `STATE_DB:VXLAN_TUNNEL_TABLE` | 書き込み | 自動 (operstatus) | N/A |
| `PortsOrch::m_portList` | 双方向 | 内部管理 | N/A |
| `PortsOrch::m_default1QBridge` | 読み取り | ハードコード | N/A |
| `FdbOrch::m_fdb_count` | 間接 | 削除ガード | FDB エージング後 |
