# VXLAN_EVPN_TUNNEL (動的生成) — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-19 (q67-f-phaseD-vxlan-evpn-tunnel)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/vxlanorch.cpp`

### SET 処理 (addTunnelUser → createDynamicDIPTunnel) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `getEVPNVtep()` が nullptr（VXLAN_EVPN_NVO 未設定） | `VxlanTunnelOrch::addTunnelUser()` | `return false` — orchagent タスクキューに残留してリトライ | SWSS_LOG_WARN `"Unable to find EVPN VTEP. user=%d remote_vtep=%s"` | `vxlanorch.cpp:1689` |
| VTEP が存在するが `isActive()` が false | `VxlanTunnelOrch::addTunnelUser()` | `return false` — タスクキューに残留してリトライ | SWSS_LOG_WARN `"VTEP not yet active.user=%d remote_vtep=%s"` | `vxlanorch.cpp:1696` |
| `isDipTunnelsSupported()` が false（プラットフォーム非対応） | `VxlanTunnelOrch::addTunnelUser()` | DIP トンネル作成をスキップし `return true`。`updateRemoteEndPointIpRef()` で IP 参照カウントのみ更新（縮退動作） | （ログなし — NOTICE で diprefcnt のみ） | `vxlanorch.cpp:1701-1704` |
| VLAN が PortsOrch 未登録（`getVlanByVlanId()` 失敗） | `EvpnRemoteVniOrch::addOperation()` (p2p) | `return false` — タスクキューに残留してリトライ | SWSS_LOG_WARN `"Vxlan tunnel map vlan id doesn't exist: %d"` | `vxlanorch.cpp:2483-2487` |
| VNI-VLAN マップ未存在（`isVniVlanMapExists()` 失敗） | `EvpnRemoteVniOrch::addOperation()` (p2p) | `return false` — タスクキューに残留してリトライ | SWSS_LOG_WARN `"Vxlan tunnel map is not created for vni:%d"` | `vxlanorch.cpp:2491-2494` |
| L3 VNI として登録済みの VNI に対する Remote VNI add | `EvpnRemoteVniOrch::addOperation()` (p2p) | `return false`（再試行なし扱い） | SWSS_LOG_WARN `"Ignoring remote VNI add for L3 VNI:%d, remote:%s"` | `vxlanorch.cpp:2499` |
| `getTunnelPort()` 失敗（addTunnelUser 後にポート未生成） | `EvpnRemoteVniOrch::addOperation()` (p2p) | `return false` — タスクキューに残留してリトライ | SWSS_LOG_WARN `"Vxlan tunnelPort doesn't exist: %s"` | `vxlanorch.cpp:2520` |
| トンネルポートがすでに VLAN メンバ（重複 add） | `EvpnRemoteVniOrch::addOperation()` (p2p) | `return true`（スキップ）。`increment_spurious_imr_add()` でカウンタ更新のみ | SWSS_LOG_WARN `"tunnelPort %s already member of vid %d"` | `vxlanorch.cpp:2513` |

### DEL 処理 (deleteDynamicDIPTunnel / RemoteVniDel) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `del_tnl_hw_pending` — 参照カウント > 0 の DIP が残存する間の削除要求 | `VxlanTunnel::deleteDynamicDIPTunnel()` | `return true`（削除スキップ・HW ペンディング維持）。FDB 参照カウントが 0 になるまでポートを保持 | SWSS_LOG_NOTICE `"DIP = %s Not deleting tunnel from HW as tunnelPort is not yet deleted. fdbcount = %d"` | `vxlanorch.cpp:1213` |
| DIP トンネルオブジェクトが nullptr（`getVxlanTunnel()` 失敗） | `VxlanTunnel::deleteDynamicDIPTunnel()` | `return false`（異常扱い） | SWSS_LOG_INFO `"DIP Tunnel is NULL unexpected"` | `vxlanorch.cpp:1222` |
| `tnl_users_` マップに対象 DIP エントリが存在しない | `VxlanTunnel::deleteDynamicDIPTunnel()` | WARN ログを出力して `return true`（no-op） | SWSS_LOG_WARN `"Unable to find dynamic tunnel for deletion"` | `vxlanorch.cpp:1235` |
| Remote VNI DEL 時に対象 VLAN が PortsOrch 未登録 | `EvpnRemoteVniOrch::delOperation()` (p2p) | `return true`（スキップ・再試行なし） | SWSS_LOG_WARN `"Vxlan tunnel map vlan id doesn't exist: %d"` | `vxlanorch.cpp:2559` |
| Remote VNI DEL 時に `getTunnelPort()` 失敗 | `EvpnRemoteVniOrch::delOperation()` (p2p) | `return true`（スキップ・再試行なし） | SWSS_LOG_WARN `"RemoteVniDel getTunnelPort Fails: %s"` | `vxlanorch.cpp:2567` |
| Remote VNI DEL 時に `getEVPNVtep()` が nullptr | `EvpnRemoteVniOrch::delOperation()` (p2p) | `return true`（スキップ・再試行なし） | SWSS_LOG_WARN `"Remote VNI del: VTEP not found. remote=%s vid=%d"` | `vxlanorch.cpp:2575` |
| トンネルポートが VLAN の非メンバ状態での DEL（spurious del） | `EvpnRemoteVniOrch::delOperation()` (p2p) | `return true`（スキップ）。`increment_spurious_imr_del()` でカウンタ更新のみ | SWSS_LOG_WARN `"marking it as spurious tunnelPort %s not a member of vid %d"` | `vxlanorch.cpp:2582` |
| `removeVlanMember()` 失敗 | `EvpnRemoteVniOrch::delOperation()` (p2p) | `return true`（スキップ・再試行なし） | SWSS_LOG_WARN `"RemoteVniDel remove vlan member fails: %s"` | `vxlanorch.cpp:2593` |
| IP 参照カウントのデクリメント対象エントリが未存在 | `VxlanTunnel::updateRemoteEndPointIpRef()` | `return`（no-op、カウンタ不整合の可能性） | SWSS_LOG_ERROR `"Cannot decrement ref. End point not referenced %s"` | `vxlanorch.cpp:1133` |

### retry 挙動まとめ

| シナリオ | return 値 | retry 挙動 |
|---|---|---|
| EVPN VTEP 未登録 / 非 active での DIP トンネル生成要求 | `false` | orchagent タスクキューで自動リトライ（上限なし、VTEP active 化で解消） |
| VLAN 未存在 / VNI-VLAN マップ未存在での Remote VNI add | `false` | orchagent タスクキューで自動リトライ（VLAN / TUNNEL_MAP 設定後に解消） |
| tunnelPort 生成待ち (addTunnelUser 後の getPort 失敗) | `false` | タスクキューでリトライ |
| DIP トンネル参照カウント > 0 での HW 削除スキップ | `true` | **リトライなし**。FDB カウント解消後に再 DEL イベントが必要 |
| getTunnelPort / VLAN 未存在 での DEL スキップ | `true` | **リトライなし**（エントリが残存しないため実害は少ない） |
| isDipTunnelsSupported() = false | `true` | リトライなし — 縮退動作として設計上許容 |

> **補足**: SET 失敗の大半は `return false` によりタスクキューに残留して自動リトライされる。
> DEL 失敗の大半は `return true` で即座に確定し再試行されない。特に `del_tnl_hw_pending`
> 状態では HW 削除が遅延するが、ログ (`"Not deleting tunnel from HW as tunnelPort is not yet deleted"`)
> により状況は可視化される。

<!-- /failure -->
