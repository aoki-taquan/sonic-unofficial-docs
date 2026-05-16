# MIRROR_SESSION — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-mirror-session)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース: `sonic-net/sonic-swss/orchagent/mirrororch.cpp`

### SET 処理 (createEntry) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| セッション名が既に存在 | `createEntry()` L389-393 | `task_duplicated` (処理なし) | NOTICE "Failed to create session %s: object already exists" | `mirrororch.cpp:391-392` |
| `queue` 値が `m_maxNumTC` 以上 | `createEntry()` L426-430 | `task_invalid_entry` | ERROR "Failed to get valid queue %s" | `mirrororch.cpp:428-429` |
| `policer` 名指定かつ `policerExists()` が false | `createEntry()` L434-438 | `task_need_retry` (policer 作成後に自動再試行) | ERROR "Failed to get policer %s" | `mirrororch.cpp:436-438` |
| `src_port` にポートが存在しない / PHY・LAG 以外 | `validateSrcPortList()` L317-325 | `task_invalid_entry` (retry なし) | ERROR "Failed to locate Port/LAG %s" / "Not supported port %s" | `mirrororch.cpp:318-319, 324-325` |
| `src_port` にメンバーポートと LAG が同時に指定 | `validateSrcPortList()` L336-340 | `task_invalid_entry` | ERROR "Port %s in LAG %s is also part of src_port config %s" | `mirrororch.cpp:338-340` |
| `src_port` の LAG が空 (メンバーなし) | `validateSrcPortList()` L344-348 | `task_invalid_entry` | ERROR "Source LAG %s is empty. set mirror session to inactive" | `mirrororch.cpp:346-348` |
| `dst_port` が PortsOrch に存在しない | `validateDstPort()` L277-281 | `task_invalid_entry` | ERROR "Not supported port %s type %d" | `mirrororch.cpp:279-280` |
| `dst_port` が PHY 以外 (VLAN / LAG 等) | `validateDstPort()` L282-286 | `task_invalid_entry` | ERROR "Not supported port %s" | `mirrororch.cpp:284-285` |
| `direction` が `RX`/`TX`/`BOTH` 以外の文字列 | `createEntry()` L464-469 | `task_invalid_entry` | ERROR "Failed to get valid direction %s" | `mirrororch.cpp:467-468` |
| 不明フィールドが含まれる | `createEntry()` L476-480 | `task_invalid_entry` | ERROR "Failed to parse session %s configuration. Unknown attribute %s" | `mirrororch.cpp:478-479` |
| フィールド値の数値変換で `exception` | `createEntry()` catch L482-486 | `task_invalid_entry` | ERROR "Failed to parse session %s attribute %s error: %s." | `mirrororch.cpp:484-485` |
| フィールド値の数値変換で不明例外 (`...`) | `createEntry()` catch L487-491 | `task_failed` | ERROR "Failed to parse session %s attribute %s. Unknown error has been occurred" | `mirrororch.cpp:489-490` |
| `src_ip` と `dst_ip` のアドレスファミリ不一致 | `createEntry()` L493-498 | `task_invalid_entry` | ERROR "Address family of source and destination IPs is different" | `mirrororch.cpp:496-497` |
| `isHwResourcesAvailable()` が false (SAI リソース枯渇) | `createEntry()` L500-504 | `task_failed` | ERROR "Failed to create session %s: HW resources are not available" | `mirrororch.cpp:502-503` |

### activateSession における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| SPAN: `dst_port` が PortsOrch に存在しない | `activateSession()` L943-947 | `false` 返却 → INACTIVE のまま | ERROR "Failed to locate Port/LAG %s" | `mirrororch.cpp:945-946` |
| VoQ スイッチで recirc ポート取得失敗 | `activateSession()` L964-968 | `false` 返却 | ERROR "Failed to get recirc port" | `mirrororch.cpp:966-967` |
| `policer` の OID 取得失敗 | `activateSession()` L1055-1059 | `false` 返却 | ERROR "Failed to get policer %s" | `mirrororch.cpp:1057-1058` |
| `sai_mirror_api->create_mirror_session()` がエラー | `activateSession()` L1068-1078 | `session.status = false` → INACTIVE / `parseHandleSaiStatusFailure` | ERROR "Failed to activate mirroring session %s" | `mirrororch.cpp:1070-1077` |
| `configurePortMirrorSession()` (src_port 設定) が false | `activateSession()` L1084-1090 | `session.status = false`、`false` 返却 | ERROR "Failed to activate port mirror session %s" | `mirrororch.cpp:1087-1089` |
| ASIC が ingress mirror 非対応 | `setUnsetPortMirror()` L817-821 | `false` 返却 | ERROR "Port ingress mirror is not supported by the ASIC" | `mirrororch.cpp:819-820` |
| ASIC が egress mirror 非対応 | `setUnsetPortMirror()` L822-826 | `false` 返却 | ERROR "Port egress mirror is not supported by the ASIC" | `mirrororch.cpp:824-825` |
| LAG メンバーポートが PHY 以外 | `setUnsetPortMirror()` L848-852 | `false` 返却 | ERROR "Failed to locate port %s" | `mirrororch.cpp:850-851` |
| `sai_port_api->set_port_attribute()` がエラー (LAG) | `setUnsetPortMirror()` L854-863 | `parseHandleSaiStatusFailure` | ERROR "Failed to configure %s session on port %s: %s, status %d, sessionId %lx" | `mirrororch.cpp:856-863` |
| `sai_port_api->set_port_attribute()` がエラー (PHY) | `setUnsetPortMirror()` L869-878 | `parseHandleSaiStatusFailure` | ERROR "Failed to configure %s session on port %s, status %d, sessionId %lx" | `mirrororch.cpp:872-877` |

### DEL 処理 (deleteEntry) における失敗経路

| 失敗条件 | 検出箇所 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| 存在しないセッション名を DEL | `deleteEntry()` L530-535 | `task_invalid_entry` | ERROR "Failed to remove non-existent mirror session %s" | `mirrororch.cpp:532-534` |
| `refCount > 0` (ACL_RULE 等から参照中) | `deleteEntry()` L539-544 | `task_need_retry` (参照解除後に自動再試行) | WARN "Failed to remove still referenced mirror session %s, retry..." | `mirrororch.cpp:541-543` |
| `deactivateSession()` が false (SAI remove 失敗) | `deleteEntry()` L546-553 | `task_failed` | ERROR "Failed to remove mirror session %s" | `mirrororch.cpp:550-551` |
| `sai_mirror_api->remove_mirror_session()` がエラー | `deactivateSession()` L1123-1133 | `parseHandleSaiStatusFailure` | ERROR "Failed to deactivate mirroring session %s" | `mirrororch.cpp:1127-1131` |

### SAI 属性更新時の失敗経路

| 操作 | 失敗条件 | 結果 | ログ出力 | evidence |
|---|---|---|---|---|
| `updateSessionDstMac()` | `set_mirror_session_attribute()` がエラー | `parseHandleSaiStatusFailure` | ERROR "Failed to update mirror session %s destination MAC to %s, rv:%d" | `mirrororch.cpp:1164-1169` |
| `updateSessionDstPort()` (VoQ) | recirc ポート取得失敗 | `false` 返却 | ERROR "Failed to get recirc port for mirror session %s" | `mirrororch.cpp:1197-1198` |
| `updateSessionDstPort()` | `set_mirror_session_attribute()` がエラー | `parseHandleSaiStatusFailure` | ERROR "Failed to update mirror session %s monitor port to %s, rv:%d" | `mirrororch.cpp:1211-1216` |

### allPortsReady guard (doTask 早期リターン)

`doTask()` L1571-1574: `gPortsOrch->allPortsReady()` が false の間は全エントリを処理せず早期 return。ポート初期化完了前に CONFIG_DB に MIRROR_SESSION を書き込んでも orchagent は一切処理しない。エラーログは出ず silent 待機となる。

### 失敗パターン分類

| 分類 | 挙動 | 自動回復 |
|---|---|---|
| `task_duplicated` | 処理なし・キューに残す | - |
| `task_invalid_entry` | キューから破棄 (永続的失敗) | なし |
| `task_need_retry` | キューに残し再試行 | 依存リソース追加後に自動回復 |
| `task_failed` | キューから破棄 / SAI エラー次第 | なし (HW リソース増加は不可) |
| `false` (activateSession) | INACTIVE 状態維持。次回 updateSession 呼出しで再評価 | RouteOrch/NeighOrch 等の変化で非同期回復 |

### grep カバレッジ

| 項目 | hit 数 | 証跡 |
|---|---|---|
| `task_invalid_entry` | 9 | `mirrororch.cpp:429, 449, 458, 468, 479, 485, 497, 534, ...` |
| `task_need_retry` | 2 | `mirrororch.cpp:438, 543` |
| `task_failed` | 3 | `mirrororch.cpp:490, 503, 551` |
| `task_duplicated` | 1 | `mirrororch.cpp:392` |
| `SWSS_LOG_ERROR` | 25+ | `mirrororch.cpp` 全体 |
| `SWSS_LOG_WARN` | 2 | `mirrororch.cpp:102, 541` |
| `return false` (activateSession 系) | 8+ | 各 activate/configure 関数 |

<!-- /failure -->
