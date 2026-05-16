# TUNNEL テーブル — Phase D: 失敗挙動 中間ファイル

生成日: 2026-05-15 (q67-f-phaseD-tunnel)

<!-- failure -->
## Phase D: 失敗挙動マトリクス

ソース:
- `sonic-net/sonic-swss/cfgmgr/tunnelmgr.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-net/sonic-swss/orchagent/tunneldecaporch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

### tunnelmgr.cpp — SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | リトライ | evidence |
|---|---|---|---|---|
| `tunnel_type` が `IPINIP` 以外 | `doTunnelTask()` L250 | APPL_DB 未通知。キャッシュ (`m_tunnelCache`) には追加される | なし (恒久スキップ) | `tunnelmgr.cpp:250-293` |
| `m_peerIp` が空 (PEER_SWITCH 未設定) | `doTunnelTask()` L258-261 | `"Peer/Remote IP not configured"` LOG_NOTICE → Linux tunnel 未作成。APPL_DB への通知は実行される (decap term のみ有効) | **自動再処理なし**、PEER_SWITCH 設定後に TUNNEL 再 SET が必要 | `tunnelmgr.cpp:258-261` |
| `configIpTunnel()` が `false` を返す (Linux `ip tunnel add` 失敗) | `doTunnelTask()` L254-256 | `return false` → タスクがキュー (`m_toSync`) に残る、次サイクルでリトライ | **自動リトライ** (無限ループの可能性) | `tunnelmgr.cpp:254-256` |
| `cmdIpTunnelIfCreate` コマンド失敗 (ret != 0) | `configIpTunnel()` L391-396 | LOG_WARN 出力のみ。`configIpTunnel()` は `true` を返し続けるため APPL_DB 通知は実行される (kernel IF なし状態で APPL_DB だけ設定) | なし | `tunnelmgr.cpp:391-416` |
| `cmdIpTunnelIfUp` コマンド失敗 (ret != 0) | `configIpTunnel()` L398-403 | LOG_WARN 出力のみ。処理継続 | なし | `tunnelmgr.cpp:398-403` |
| Loopback3 の IP アドレス付与失敗 (cmdIpTunnelIfAddress ret != 0) | `configIpTunnel()` L408-413 | LOG_WARN 出力のみ。処理継続 | なし | `tunnelmgr.cpp:408-413` |
| 不明な operation type (`op` が SET/DEL 以外) | `doTask()` L201-203 | `SWSS_LOG_ERROR("Unknown operation: '%s'")` → タスク消費 (erase) | なし (恒久スキップ) | `tunnelmgr.cpp:201-203` |

### tunnelmgr.cpp — DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | リトライ | evidence |
|---|---|---|---|---|
| DEL 対象が `m_tunnelCache` に存在しない | `doTunnelTask()` L299-302 | `SWSS_LOG_ERROR("Tunnel %s not found")` → `return true` (タスク消費) | なし (恒久スキップ) | `tunnelmgr.cpp:299-302` |
| キャッシュにあるが `tunnel_type` が IPINIP 以外の DEL | `doTunnelTask()` L312-314 | `SWSS_LOG_WARN("Tunnel %s type %s is not handled")` → キャッシュ削除のみ、APPL_DB DEL は送られない | なし | `tunnelmgr.cpp:312-314` |

### tunneldecaporch.cpp — SET 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | リトライ | evidence |
|---|---|---|---|---|
| `tunnel_type` が `IPINIP` 以外 | `doDecapTunnelTask()` L127-131 | `SWSS_LOG_ERROR("Invalid tunnel type")` → `valid=false` → `addDecapTunnel()` 呼び出しスキップ。タスク消費 | なし (恒久スキップ) | `tunneldecaporch.cpp:127-131` |
| `src_ip` が不正な IP 文字列 (IpAddress 例外) | `doDecapTunnelTask()` L141-146 | `SWSS_LOG_ERROR` → `valid=false` → タスク消費 | なし | `tunneldecaporch.cpp:141-146` |
| `dscp_mode` が `uniform`/`pipe` 以外 | `doDecapTunnelTask()` L155-160 | `SWSS_LOG_ERROR("Invalid dscp mode")` → `valid=false` → タスク消費 | なし | `tunneldecaporch.cpp:155-160` |
| `ecn_mode` が `copy_from_outer`/`standard` 以外 | `doDecapTunnelTask()` L170-175 | `SWSS_LOG_ERROR("Invalid ecn mode")` → `valid=false` → タスク消費 | なし | `tunneldecaporch.cpp:170-175` |
| 既存トンネルへの `ecn_mode` 変更 (SAI create-only) | `doDecapTunnelTask()` L177-182 | `SWSS_LOG_WARN("Skip setting ecn_mode since the SAI attribute SAI_TUNNEL_ATTR_DECAP_ECN_MODE is create only")` → `valid=false` → **SET 全体が無効化**される (他フィールドの更新も含む) | なし。DEL → 再 SET が必要 | `tunneldecaporch.cpp:177-182` |
| `encap_ecn_mode` が `standard` 以外 | `doDecapTunnelTask()` L187-191 | `SWSS_LOG_ERROR("Only standard encap ecn mode is supported")` → `valid=false` → タスク消費 | なし | `tunneldecaporch.cpp:187-191` |
| 既存トンネルへの `encap_ecn_mode` 変更 (SAI create-only) | `doDecapTunnelTask()` L193-198 | `SWSS_LOG_NOTICE("Skip setting encap_ecn_mode since create only")` → `valid=false` → **SET 全体が無効化** | なし。DEL → 再 SET が必要 | `tunneldecaporch.cpp:193-198` |
| `ttl_mode` が `uniform`/`pipe` 以外 | `doDecapTunnelTask()` L202-207 | `SWSS_LOG_ERROR("Invalid ttl mode")` → `valid=false` → タスク消費 | なし | `tunneldecaporch.cpp:202-207` |
| 未知のフィールド名 | `doDecapTunnelTask()` L277-279 | `SWSS_LOG_ERROR("unknown decap tunnel table attribute")` → `valid=false` → タスク消費 | なし | `tunneldecaporch.cpp:277-279` |
| QoS map (`decap_dscp_to_tc_map` 等) が未作成 | `doDecapTunnelTask()` L217-222 | `SWSS_LOG_NOTICE("QoS map not ready yet")` → `task_need_retry` → `it++` でタスクをキューに残す | **自動リトライ** (QoS map 作成後に再処理) | `tunneldecaporch.cpp:217-236` |
| `addDecapTunnel()` 失敗 (SAI create_tunnel 失敗) | `doDecapTunnelTask()` L313 | `SWSS_LOG_ERROR("Failed to add tunnel to ASIC_DB")` → タスク消費 (erase)。SAI エラー詳細は syncd ログで確認 | なし | `tunneldecaporch.cpp:311-314` |

### tunneldecaporch.cpp — DEL 処理における失敗経路

| 失敗条件 | 検出箇所 | 結果 | リトライ | evidence |
|---|---|---|---|---|
| DEL 対象トンネルが存在しない | `doDecapTunnelTask()` L325-327 | `SWSS_LOG_ERROR("Tunnel %s cannot be removed since it doesn't exist")` → タスク消費 | なし (冪等扱いだがエラーログ出力) | `tunneldecaporch.cpp:325-327` |
| 不明な operation type | `doDecapTunnelTask()` L331 | `SWSS_LOG_ERROR("Unknown operation type")` → タスク消費 | なし | `tunneldecaporch.cpp:331` |

---

### 重要な設計上の注意点

1. **`configIpTunnel()` は常に `true` を返す**: Linux kernel コマンド (`ip tunnel add`, `ip link set up`, `ip addr add`) が失敗しても LOG_WARN を出力するだけで `true` を返す。したがって kernel IF なし状態で APPL_DB だけ設定される可能性がある。

2. **create-only 属性の罠**: `ecn_mode` / `encap_ecn_mode` は SAI の create-only 属性。既存トンネルへの SET で `valid=false` となり **同一 SET 内の他フィールド更新も全て無効化**される。変更には必ず DEL → 再 SET が必要。

3. **PEER_SWITCH 先行設定は必須**: `m_peerIp` が空の場合、Linux tunnel IF は作成されない。PEER_SWITCH を後から設定しても `tunnelmgrd` の自動再処理は発生しないため、TUNNEL テーブルの再 SET が必要。

4. **QoS map 未作成によるスタック**: `decap_dscp_to_tc_map` / `decap_tc_to_pg_map` / `encap_tc_to_dscp_map` / `encap_tc_to_queue_map` に指定した QoS map が未作成の場合、`task_need_retry` でタスクがキューに残り続け、map 作成まで処理がスタックする。

---

### 回復シナリオまとめ

| 失敗ケース | 回復方法 | 自動か手動か |
|-----------|---------|------------|
| `tunnel_type` 不正 / 未知フィールド | 正しい値を再投入 | 手動 |
| `m_peerIp` 空 (PEER_SWITCH 未設定) | PEER_SWITCH 設定後に TUNNEL 再 SET | 手動 |
| `ip tunnel add` 失敗 (kernel エラー) | `tunnelmgrd` が次サイクルで自動リトライ (無限ループ注意) | 自動リトライ (根本原因解決が必要) |
| `ecn_mode` / `encap_ecn_mode` 変更 | `TUNNEL` DEL → 再 SET | 手動 |
| QoS map 未作成 | QoS map テーブル SET → orchagent が自動再処理 | 自動 |
| SAI `create_tunnel` 失敗 | syncd ログを確認し SAI エラーを特定、再 SET | 手動 |
| DEL 対象不存在 | 操作なし (既に削除済み) | 確認のみ |

<!-- /failure -->
