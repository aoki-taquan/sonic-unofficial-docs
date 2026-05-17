# TUNNEL STATE_DB — Phase D: 失敗挙動スキャンノート

生成日: 2026-05-17 (q67-f-tunnel-state-phaseD)
ソース: `sonic-net/sonic-swss` orchagent/tunneldecaporch.cpp, orchagent/vxlanorch.cpp, cfgmgr/vxlanmgr.cpp

---

## TUNNEL_DECAP_TABLE / TUNNEL_DECAP_TERM_TABLE (tunneldecaporch)

### SET 処理における失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ出力 | evidence |
|---|---|---|---|---|
| `tunnel_type` が `IPINIP` 以外 | `doDecapTunnelTask()` L129 | `valid=false` → SAI 呼び出しなし → STATE_DB 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:127-131` |
| `src_ip` が無効な IP アドレス文字列 | `doDecapTunnelTask()` L143 | `valid=false` → STATE_DB 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:142-145` |
| `src_ip` を既存トンネルに対して変更しようとした場合 | `doDecapTunnelTask()` L149 | エラーログのみ・既存 STATE_DB エントリは変化なし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:148-150` |
| `dscp_mode` が `uniform`/`pipe` 以外 | `doDecapTunnelTask()` L157 | `valid=false` → 新規作成時は STATE_DB 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:155-159` |
| `ecn_mode` が `copy_from_outer`/`standard` 以外 | `doDecapTunnelTask()` L173 | `valid=false` → STATE_DB 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:171-175` |
| `ecn_mode` を既存トンネルに SET（create-only SAI 属性のため） | `doDecapTunnelTask()` L179 | WARN ログのみ・SAI 変更なし・STATE_DB 書き込みは実施（キャッシュは変化するが SAI 不一致） | SWSS_LOG_WARN | `tunneldecaporch.cpp:178-182` |
| `encap_ecn_mode` が `standard` 以外 | `doDecapTunnelTask()` L189 | `valid=false` → STATE_DB 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:188-192` |
| `ttl_mode` が `uniform`/`pipe` 以外 | `doDecapTunnelTask()` L205 | `valid=false` → STATE_DB 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:203-207` |
| QoS マップ (`decap_dscp_to_tc_map` 等) がまだ準備できていない | `doDecapTunnelTask()` L221,236 | `task_need_retry` → エントリを `m_toSync` に留保・STATE_DB 書き込みなし（後で再試行） | SWSS_LOG_NOTICE | `tunneldecaporch.cpp:218-237` |
| SAI `create_router_interface` 失敗 | `addDecapTunnel()` L754-760 | トンネル作成中断 → STATE_DB に書き込まれない | SWSS_LOG_ERROR | `tunneldecaporch.cpp:754-761` |
| SAI `create_tunnel` 失敗 | `addDecapTunnel()` L850-856 | トンネル作成中断 → STATE_DB に書き込まれない | SWSS_LOG_ERROR | `tunneldecaporch.cpp:850-857` |
| SAI `create_tunnel_term_table_entry` 失敗 | `addDecapTunnelTermEntry()` L980-986 | decap term エントリが STATE_DB に書かれない（`setDecapTunnelTermStatus` 未呼び出し） | SWSS_LOG_ERROR | `tunneldecaporch.cpp:980-987` |
| 不明フィールドが SET に含まれる | `doDecapTunnelTask()` L277 | `valid=false` → STATE_DB 書き込みなし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:275-279` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ出力 | evidence |
|---|---|---|---|---|
| DEL 対象トンネルが `tunnelTable` に存在しない | `doDecapTunnelTask()` L326 | エラーログのみ・STATE_DB 変化なし | SWSS_LOG_ERROR | `tunneldecaporch.cpp:325-327` |
| DEL 時に tunnel_term が残存（`removeDecapTunnel()` 内チェック） | `removeDecapTunnel()` L1182-1185 | `removeDecapTunnelStatus()` 未呼び出し → STATE_DB エントリが残存 | SWSS_LOG_ERROR | `tunneldecaporch.cpp:1182-1186` |
| ref_count > 0 の状態での DEL 要求 | `RemoveTunnelIfNotReferenced()` L1569-1575 | `removeDecapTunnel()` がスキップされる → STATE_DB エントリは残存 | （ログなし、カウントが 0 になるまで保留） | `tunneldecaporch.cpp:1569-1575` |
| SAI `remove_tunnel` 失敗 | `removeDecapTunnel()` L1190-1196 | `removeDecapTunnelStatus()` 未呼び出し → STATE_DB エントリが残存 | SWSS_LOG_ERROR | `tunneldecaporch.cpp:1188-1196` |

## VXLAN_TUNNEL_TABLE (vxlanorch)

### SET/作成処理における失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ出力 | evidence |
|---|---|---|---|---|
| `gPortsOrch->allPortsReady()` が false（起動時全ポート未 ready） | `TunnelDecapOrch::doTask()` L55 | タスク全体がスキップ → STATE_DB 書き込みなし（次サイクルで再試行） | （ログなし） | `tunneldecaporch.cpp:55-58` |
| SAI `create_tunnel` 失敗（vxlanorch） | `VxlanTunnel::createTunnel()` L403-408 | 例外がキャッチされ `SWSS_LOG_ERROR` → `addRemoveStateTableEntry()` が呼ばれない → STATE_DB 書き込みなし | SWSS_LOG_ERROR | `vxlanorch.cpp:848` |
| SAI `create_tunnel_term_table_entry` 失敗（vxlanorch） | `VxlanTunnel::createTunnel()` L488-493 | 例外キャッチ後に STATE_DB に書き込まれない | SWSS_LOG_ERROR | `vxlanorch.cpp:944` |
| P2P トンネルで `dst_ip` が 0（VTEP 用） | `VxlanTunnel` コンストラクタ | `addRemoveStateTableEntry()` が呼ばれない → `VXLAN_TUNNEL_TABLE` に書き込まれない | （ログなし） | `vxlanorch.cpp:529-532` |

### DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ出力 | evidence |
|---|---|---|---|---|
| SAI `remove_tunnel` 失敗（vxlanorch） | `VxlanTunnel::deleteTunnel()` L424-427 | 例外キャッチ → `~VxlanTunnel()` が完了せず STATE_DB `del()` が呼ばれない → エントリ残存 | SWSS_LOG_ERROR | `vxlanorch.cpp:874` |

## VXLAN_TABLE (vxlanmgr)

### SET/作成処理における失敗経路

| 失敗条件 | 検出箇所 | STATE_DB への影響 | ログ出力 | evidence |
|---|---|---|---|---|
| `vxlanTunnelCache` にトンネルが未登録（トンネル未作成） | `doVxlanCreateTask()` L319-324 | タスクを m_toSync に保留・STATE_DB 書き込みなし（トンネル作成後に自動再試行） | SWSS_LOG_DEBUG | `vxlanmgr.cpp:319-325` |
| VRF (`isVrfStateOk()`) が未 ready | `doVxlanCreateTask()` L328-333 | 保留・STATE_DB 書き込みなし | SWSS_LOG_DEBUG | `vxlanmgr.cpp:328-333` |
| MAC アドレス未設定 (`getVxlanRouterMacAddress()`) | `doVxlanCreateTask()` L336-342 | 保留・STATE_DB 書き込みなし | SWSS_LOG_DEBUG | `vxlanmgr.cpp:336-342` |
| `createVxlan()` 失敗（netdevice 作成エラー） | `doVxlanCreateTask()` L366-369 | `m_stateVxlanTable.set()` 未呼び出し → `VXLAN_TABLE` に `state=ok` が書き込まれない | SWSS_LOG_ERROR | `vxlanmgr.cpp:366-370` |

## 補足: PortsOrch 待機による全体ゲート

- `TunnelDecapOrch::doTask()` は `gPortsOrch->allPortsReady()` チェックを毎回実施する。ポートが全 ready になるまで SET/DEL を含む全イベントがスキップされる。この間は TUNNEL_DECAP_TABLE も TUNNEL_DECAP_TERM_TABLE も STATE_DB に書かれない。
- 起動シーケンス上、PortsOrch が allPortsReady を返すまでの遅延が長い場合（大規模プラットフォーム等）、CONFIG_DB から APPL_DB にトンネル設定が届いても STATE_DB エントリが現れない期間が生じる。
