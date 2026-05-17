# tunnel-port — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-17 (q67-f-tunnel-port2-next)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/vxlanorch.cpp`, `orchagent/portsorch.cpp`

### SET 処理 (addTunnelUser / VxlanTunnelMapOrch::addOperation) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `evpn_orch->getEVPNVtep()` が NULL (`VXLAN_EVPN_NVO` 未設定) | `addTunnelUser()` | `return false` → Orch 再試行キューへ。`Port_EVPN_*` は生成されない | `SWSS_LOG_WARN("Unable to find EVPN VTEP. user=%d remote_vtep=%s")` | `vxlanorch.cpp:1689-1692` |
| `vtep_ptr->isActive()` が false (SIP トンネル HW 未作成) | `addTunnelUser()` | `return false` → Orch 再試行キューへ。`Port_EVPN_*` は生成されない | `SWSS_LOG_WARN("VTEP not yet active.user=%d remote_vtep=%s")` | `vxlanorch.cpp:1696-1699` |
| `sai_bridge_api->create_bridge_port()` が SAI_STATUS_SUCCESS 以外を返す | `PortsOrch::addBridgePort()` | `handleSaiCreateStatus(SAI_API_BRIDGE, status)` を実行。`task_success` 以外なら `parseHandleSaiStatusFailure()` が呼ばれ、最終的に `return false` | `SWSS_LOG_ERROR("Failed to add bridge port %s to default 1Q bridge, rv:%d")` | `portsorch.cpp:7261-7265` |
| `port.m_rif_id != 0` (ルータポートへのブリッジポート追加試行) | `PortsOrch::addBridgePort()` | `return false` — TUNNEL 型ポートでは発生しないが、型誤りがあれば本パスに落ちる | `SWSS_LOG_NOTICE("Cannot create bridge port, interface %s is a router port")` | `portsorch.cpp:7201-7204` |
| `port.m_type` が PHY/LAG/TUNNEL 以外の不正値 | `PortsOrch::addBridgePort()` | `return false` | `SWSS_LOG_ERROR("Failed to add bridge port %s to default 1Q bridge, invalid port type %d")` | `portsorch.cpp:7243-7245` |
| `setHostIntfsStripTag()` が false を返す (hostif VLAN タグ設定失敗) | `PortsOrch::addBridgePort()` 末尾 | `return false` — bridge_port_id は設定済みだが m_portList 更新・通知がスキップされる | `SWSS_LOG_ERROR("Failed to set %s for hostif of port %s")` | `portsorch.cpp:7272-7274` |
| VLAN ID が VLAN テーブルに存在しない (DIP 非サポート時) | `VxlanTunnelMapOrch::addOperation()` | `return false` — Local SRC VTEP ポートも生成されない | `SWSS_LOG_WARN("Vxlan tunnel map vlan id doesn't exist: %d", vlan_id)` | `vxlanorch.cpp:2032` |
| VNI ID が最大値超過 (`vni_id >= (1 << 24)`) | `VxlanTunnelMapOrch::addOperation()` | `return false` | `SWSS_LOG_ERROR("Vxlan tunnel map vni id is too big: %d", vni_id)` | `vxlanorch.cpp:2039` |
| VXLAN_TUNNEL が CONFIG_DB に存在しない | `VxlanTunnelMapOrch::addOperation()` | `return false` → Orch 再試行キューへ | `SWSS_LOG_WARN("Vxlan tunnel '%s' doesn't exist", tunnel_name.c_str())` | `vxlanorch.cpp:2049` |

### DEL 処理 (delTunnelUser / deleteTunnelPort) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `evpn_orch->getEVPNVtep()` が NULL (削除時) | `delTunnelUser()` | `return true` (操作完了扱い) — ポート削除はスキップされ SAI リソースが残留する可能性 | `SWSS_LOG_WARN("Unable to find VTEP. remote=%s vlan=%d usr=%d")` | `vxlanorch.cpp:1738-1741` |
| `m_fdb_count != 0` の状態で `removeBridgePort()` が呼ばれた場合 | `delTunnelUser()` / `deleteTunnelPort()` | `removeBridgePort()` は即時削除を試みるが FDB が残るため SAI がエラーを返す場合がある。`return true` で呼出し元は完了扱い | `SWSS_LOG_ERROR("Remove Bridge port failed for remote = %s fdbcount = %d")` | `vxlanorch.cpp:1775, 1839` |
| `sai_bridge_api->set_bridge_port_attribute(ADMIN_STATE=DOWN)` 失敗 | `PortsOrch::removeBridgePort()` | `parseHandleSaiStatusFailure()` → `return false` — 削除処理が中断し SAI bridge port が残留 | `SWSS_LOG_ERROR("Failed to set bridge port %s admin status to DOWN, rv:%d")` | `portsorch.cpp:7303-7308` |
| `sai_bridge_api->remove_bridge_port()` 失敗 | `PortsOrch::removeBridgePort()` | `parseHandleSaiStatusFailure()` → `return false` | `SWSS_LOG_ERROR("Failed to remove bridge port %s from default 1Q bridge, rv:%d")` | `portsorch.cpp:7327-7332` |
| `setHostIntfsStripTag(SAI_HOSTIF_VLAN_TAG_STRIP)` 失敗 | `PortsOrch::removeBridgePort()` | `return false` — 削除前処理が失敗 | `SWSS_LOG_ERROR("Failed to set %s for hostif of port %s")` | `portsorch.cpp:7312-7315` |
| `deleteTunnelPort()` 時に `evpn_orch->getEVPNVtep()` が NULL | `deleteTunnelPort()` | `return` — ブリッジポート・トンネルポートが削除されずに処理終了 | `SWSS_LOG_WARN("Unable to find VTEP. tunnelPort=%s")` | `vxlanorch.cpp:1803` |
| DIP サポート有り環境で `refcnt > 0` (IMR/IP ルートが残存) | `deleteTunnelPort()` | ブリッジポート削除をスキップ — 意図的なガード。ルート削除後に再呼び出しが必要 | `SWSS_LOG_INFO("Tunnel bridge port not removed. remote = %s refcnt = %d")` | `vxlanorch.cpp:1826-1829` |
| `deleteDynamicDIPTunnel()` 時に DIP トンネルが見つからない | `deleteDynamicDIPTunnel()` | `return false` (unexpected — 内部状態不整合) | `SWSS_LOG_INFO("DIP Tunnel is NULL unexpected")` | `vxlanorch.cpp:1224` |

### 失敗時の自動回復動作

| 失敗パターン | 自動回復 | 回復条件 |
|---|---|---|
| `getEVPNVtep()` NULL → `addTunnelUser()` 失敗 | あり | `VXLAN_EVPN_NVO` が CONFIG_DB に書き込まれると `EvpnNvoOrch` が `source_vtep_ptr` を設定し、次の SET イベントで成功する |
| `isActive()` false → `addTunnelUser()` 失敗 | あり | `VXLAN_TUNNEL_MAP` / `VXLAN_VRF_MAP` が処理されて `createTunnelHw()` が成功すると `active_=true` となり、次の SET で成功する |
| VLAN 未設定 → `VxlanTunnelMapOrch::addOperation()` 失敗 | あり | VLAN が作成されると Orch が再実行される |
| SAI `create_bridge_port()` 失敗 | SAI 依存 | SAI がリトライ可能ステータスを返せば `handleSaiCreateStatus` がキューに戻す。それ以外は恒久エラー |
| `m_fdb_count != 0` でブリッジポート削除ブロック | あり | FDB エントリがエージングされ `deleteTunnelPort()` が再呼び出しされると削除が進行する |

<!-- /failure -->
