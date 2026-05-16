# VXLAN_EVPN_NVO — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-16 (q67-f-phaseD-vxlan-evpn-nvo)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/vxlanorch.cpp`

### SET 処理 (addOperation / EvpnNvoOrch) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `source_vtep` が参照する VXLAN_TUNNEL エントリが CONFIG_DB に未登録（`getVxlanTunnel()` が nullptr） | `EvpnNvoOrch::addOperation()` | `source_vtep_ptr = nullptr` のまま `true` を返却。NVO 設定は受容されるが後続の EVPN 処理がすべて `getEVPNVtep()` で nullptr チェックに引っかかり silent-drop される | （ログなし — INFO: `"evpnnvo: %s vtep : %s"` のみ） | `vxlanorch.cpp:2779-2791` |
| EVPN VTEP が active 状態でない（`isActive()` が false）で EVPN ルートが到着 | `VxlanTunnelOrch::addTunnelUser()` | `return false` — EvpnNvoOrch がリトライキューに戻す | SWSS_LOG_WARN `"VTEP not yet active.user=%d remote_vtep=%s"` | `vxlanorch.cpp:1696` |
| EVPN VTEP 自体が nullptr（`getEVPNVtep()` 未登録）で Remote VNI 到着 | `VxlanTunnelOrch::addTunnelUser()` | `return false` — タスクキューに残留しリトライ | SWSS_LOG_WARN `"Unable to find EVPN VTEP. user=%d remote_vtep=%s"` | `vxlanorch.cpp:1689` |
| VXLAN_TUNNEL 作成時に `src_ip` と `dst_ip` のアドレスファミリが不一致 | `VxlanTunnelOrch::addOperation()` | `return true`（再試行なし）。そのトンネルエントリは作成されない | SWSS_LOG_ERROR `"Format mismatch: 'src_ip' and 'dst_ip' must be of the same family"` | `vxlanorch.cpp:1612` |
| VXLAN_TUNNEL 名が重複（既存エントリあり）で SET | `VxlanTunnelOrch::addOperation()` | `return true`（再試行なし・上書き不可） | SWSS_LOG_ERROR `"Vxlan tunnel '%s' is already exists"` | `vxlanorch.cpp:1638` |

### DEL 処理 (delOperation / EvpnNvoOrch) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| NVO DEL 到着時に `source_vtep_ptr` が NULL（先行 SET が未適用または既に null 化） | `EvpnNvoOrch::delOperation()` | `return true`（スキップ・再試行なし） | SWSS_LOG_WARN `"NVO Delete failed as VTEP Ptr is NULL"` | `vxlanorch.cpp:2799` |
| VTEP の HW 削除が未完了 (`del_tnl_hw_pending == true`) の状態で NVO DEL | `EvpnNvoOrch::delOperation()` | `return false` — タスクキューに残留してリトライ | SWSS_LOG_WARN `"NVO not deleted as hw delete is pending"` | `vxlanorch.cpp:2803-2806` |
| VXLAN_TUNNEL DEL 到着時にエントリ未存在 | `VxlanTunnelOrch::delOperation()` | `return true`（スキップ・再試行なし） | SWSS_LOG_ERROR `"Vxlan tunnel '%s' doesn't exist"` | `vxlanorch.cpp:1656` |
| VTEP に `del_tnl_hw_pending` フラグが立っている状態でトンネル DEL | `VxlanTunnelOrch::delOperation()` | `return false` — リトライ待機。DIP トンネル参照カウントが 0 になるまでブロック | SWSS_LOG_WARN `"VTEP %s not deleted as hw delete is pending"` | `vxlanorch.cpp:1663` |

### SAI API 失敗経路（VXLAN_TUNNEL 関連）

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `sai_tunnel_api->create_tunnel_map()` 失敗 | `create_tunnel_map()` | `throw std::runtime_error` → 呼び出し元で catch して SWSS_LOG_ERROR 出力 | SWSS_LOG_ERROR `"Can't create tunnel map object"` | `vxlanorch.cpp:147-155` |
| `sai_tunnel_api->create_tunnel_map_entry()` 失敗 | `create_tunnel_map_entry()` | `throw std::runtime_error` | SWSS_LOG_ERROR `"Can't create a tunnel map entry object"` | `vxlanorch.cpp:215-223` |
| `sai_tunnel_api->create_tunnel()` 失敗 | `create_tunnel()` | `throw std::runtime_error` → `VxlanTunnel::createTunnel()` の catch で SWSS_LOG_ERROR | SWSS_LOG_ERROR `"Can't create a tunnel object"` / `"Error creating tunnel %s: %s"` | `vxlanorch.cpp:403-411, 846-848` |
| `sai_tunnel_api->create_tunnel_term_table_entry()` 失敗 | `create_tunnel_termination()` | `throw std::runtime_error` | SWSS_LOG_ERROR `"Can't create a tunnel term table object"` | `vxlanorch.cpp:488-496` |
| `sai_next_hop_api->create_next_hop()` 失敗（Next Hop トンネル） | `VxlanTunnelOrch::createNextHopTunnel()` | `handleSaiCreateStatus()` で task_success でない場合 `return SAI_NULL_OBJECT_ID` | SWSS_LOG_ERROR `"NH vxlan tunnel create failed for %s, ip %s, mac %s, vni %d"` | `vxlanorch.cpp:1430-1436` |
| `sai_tunnel_api->remove_tunnel_map()` 失敗 | `remove_tunnel_map()` | `throw std::runtime_error` → catch で SWSS_LOG_ERROR | SWSS_LOG_ERROR `"Can't remove a tunnel map object"` | `vxlanorch.cpp:164-172` |
| `sai_tunnel_api->remove_tunnel()` 失敗 | `remove_tunnel()` | `throw std::runtime_error` → catch で SWSS_LOG_ERROR `"Error deleting tunnel %s"` | SWSS_LOG_ERROR `"Can't remove a tunnel object"` | `vxlanorch.cpp:422-430, 872-874` |

### retry 挙動まとめ

| シナリオ | retry 挙動 | 備考 |
|---|---|---|
| VTEP `del_tnl_hw_pending` による NVO DEL ブロック | `return false` → Orch タスクキューでリトライ（上限なし） | FDB 参照が解消されると自動的に HW 削除が進み解除 |
| EVPN VTEP 未登録・非 active 状態での Remote VNI 追加 | `return false` → リトライ | VTEP active 化後に解消 |
| VXLAN_TUNNEL 名前不一致 / SAI 失敗 の SET 失敗 | `return true` — **再試行なし**。同一フィールドの再書き込みで再トリガー必要 | |

> **補足**: `EvpnNvoOrch::addOperation()` は `source_vtep_ptr` を解決失敗しても `true` を返すため、CONFIG_DB の書き込みは受容される。後続の EVPN ルート処理（Remote VNI add）が `getEVPNVtep()` で null チェックにより `return false` し続けることで実質的なリトライが発生する。

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| EVPN_NVO 関連 SWSS_LOG_WARN/ERROR | 4 | `vxlanorch.cpp:1689, 1696, 2799, 2803` |
| VXLAN_TUNNEL SAI 失敗 SWSS_LOG_ERROR | 9 | `vxlanorch.cpp:131, 152, 169, 220, 242, 408, 427, 493, 512` |
| `del_tnl_hw_pending` リトライパス | 4 | `vxlanorch.cpp:957, 1663, 2057, 2803` |
| `return false`（リトライ）パス | 5 | `vxlanorch.cpp:1689, 1696, 1806, 2059, 2806` |

<!-- /failure -->
