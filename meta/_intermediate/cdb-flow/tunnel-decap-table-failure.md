# TUNNEL_DECAP_TABLE — Phase D 失敗挙動 証跡

<!-- evidence: sonic-net/sonic-swss orchagent/tunneldecaporch.cpp@4305596156d70e9797e8a881b3d19b46de0bce0d -->

## 不正 IP / フィールド値

| 条件 | LOG | コード行 |
|------|-----|---------|
| `tunnel_type != IPINIP` | `SWSS_LOG_ERROR("Invalid tunnel type %s")` → valid=false | L129 |
| `src_ip` 不正文字列 | `std::invalid_argument` 捕捉 → `SWSS_LOG_ERROR(e.what())` | L141-144 |
| `dscp_mode` 不正値 | `SWSS_LOG_ERROR("Invalid dscp mode %s")` | L157 |
| `ecn_mode` 不正値 | `SWSS_LOG_ERROR("Invalid ecn mode %s")` | L173 |
| `encap_ecn_mode != standard` | `SWSS_LOG_ERROR("Only standard encap ecn mode is supported currently")` | L189 |
| `ttl_mode` 不正値 | `SWSS_LOG_ERROR("Invalid ttl mode %s")` | L205 |
| 未知フィールド | `SWSS_LOG_ERROR("unknown decap tunnel table attribute '%s'")` | L277 |

## VRF 未解決 / QoS マップ未解決

| フィールド | LOG | 動作 |
|-----------|-----|-----|
| `decap_dscp_to_tc_map` OID=NULL | `SWSS_LOG_NOTICE("QoS map %s is not ready yet")` | task_need_retry (L218-221) |
| `decap_tc_to_pg_map` OID=NULL | 同上 | task_need_retry (L233-236) |
| `encap_tc_to_dscp_map` OID=NULL | 同上 | task_need_retry (L248-251) |
| `encap_tc_to_queue_map` OID=NULL | 同上 | task_need_retry (L263-266) |
| tunnel_name 未登録 (DECAP_TERM) | `SWSS_LOG_ERROR("Tunnel %s does not exist.")` | term スキップ (L904) |

## SAI tunnel 作成失敗

| SAI 呼び出し | LOG | 処理 |
|-------------|-----|-----|
| `create_tunnel()` 失敗 | `SWSS_LOG_ERROR("Failed to create tunnel")` | handleSaiCreateStatus → parseHandleSaiStatusFailure (L852-858) |
| overlay RIF `create_router_interface()` 失敗 | `SWSS_LOG_ERROR("Failed to create overlay router interface %d")` | false 返却 (L756) |
| `create_tunnel_term_table_entry()` 失敗 | `SWSS_LOG_ERROR("Failed to create tunnel decap term entry %s.")` | handleSaiCreateStatus (L982-985) |
| `remove_tunnel()` 失敗 (DEL) | `SWSS_LOG_ERROR("Failed to remove tunnel: %" PRIu64)` | handleSaiRemoveStatus (L1194) |
| `remove_router_interface()` 失敗 (DEL) | `SWSS_LOG_ERROR("Failed to remove tunnel overlay interface: %" PRIu64)` | handleSaiRemoveStatus (L1203) |
| DEL 時 decap term 残存 | `SWSS_LOG_ERROR("Failed to remove tunnel %s that has decap terms.")` | DEL 拒否 (L1184) |

## create-only 属性の変更試行

| フィールド | LOG | 動作 |
|-----------|-----|-----|
| 既存トンネルに `ecn_mode` を SET | `SWSS_LOG_WARN("Skip setting ecn_mode since ... create only")` → valid=false | L179 |
| 既存トンネルに `encap_ecn_mode` を SET | `SWSS_LOG_NOTICE("Skip setting encap_ecn_mode since ... create only")` → valid=false | L194 |
| 既存トンネルの `src_ip` を変更 | `SWSS_LOG_ERROR("cannot modify src ip for existing tunnel")` → 変更拒否 | L149 |

## まとめ

- `tunnel_type`/`dscp_mode`/`ecn_mode`/`ttl_mode` の不正値はエントリ全体スキップ（valid=false）
- QoS マップ未解決は `task_need_retry`（自動リトライ）
- SAI 呼び出し失敗は `handleSaiCreateStatus/RemoveStatus` 経由で再処理 or ドロップ
- `ecn_mode`/`encap_ecn_mode` は create-only 属性のため既存トンネルへの変更は不可（WARN/NOTICE ログ）
- `src_ip` 変更は LOG_ERROR で拒否（DEL → SET が必要）
- DEL 時に decap term が残存していると tunnel 削除を拒否
