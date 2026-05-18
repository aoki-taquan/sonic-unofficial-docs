# tunnel-encap-table — Phase D: 失敗挙動スキャン

## 対象ファイル
- `orchagent/p4orch/gre_tunnel_manager.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## SET 失敗マトリクス

### デシリアライズ段階 (`deserializeP4GreTunnelAppDbEntry`)
| 失敗条件 | エラーコード | evidence |
|---------|-------------|----------|
| JSON キー (`match/tunnel_id`) のパース失敗 | `SWSS_RC_INVALID_PARAM` | `gre_tunnel_manager.cpp:336` |
| `param/encap_src_ip` が不正な IP アドレス | `SWSS_RC_INVALID_PARAM` | `gre_tunnel_manager.cpp:355-358` |
| `param/encap_dst_ip` が不正な IP アドレス | `SWSS_RC_INVALID_PARAM` | `gre_tunnel_manager.cpp:366-369` |
| 未知フィールド (`controller_metadata` を除く) | `SWSS_RC_INVALID_PARAM` | `gre_tunnel_manager.cpp:377-379` |

### バリデーション段階 (`validateGreTunnelAppDbEntry` SET)
| 失敗条件 | エラーコード | evidence |
|---------|-------------|----------|
| `action` が `mark_for_p2p_tunnel_encap` 以外 | `SWSS_RC_INVALID_PARAM` | `gre_tunnel_manager.cpp:83-87` |
| `param/router_interface_id` 欠如 | `SWSS_RC_INVALID_PARAM` | `gre_tunnel_manager.cpp:88-92` |
| `param/encap_src_ip` がゼロ IP (0.0.0.0 / ::) | `SWSS_RC_INVALID_PARAM` | `gre_tunnel_manager.cpp:93-97` |
| `param/encap_dst_ip` がゼロ IP | `SWSS_RC_INVALID_PARAM` | `gre_tunnel_manager.cpp:98-102` |
| 参照 RIF (`router_interface_id`) が P4OidMapper に未登録 | `SWSS_RC_NOT_FOUND` | `gre_tunnel_manager.cpp:129-135` |
| Neighbor (`router_interface_id` + `encap_dst_ip`) が P4OidMapper に未登録 | `SWSS_RC_NOT_FOUND` | `gre_tunnel_manager.cpp:139-149` |

### drain ループ段階
| 失敗条件 | エラーコード | evidence |
|---------|-------------|----------|
| 既存エントリへの SET (UPDATE) — SAI 非対応 | `SWSS_RC_UNIMPLEMENTED` | `gre_tunnel_manager.cpp:279-281` |
| バッチ内先行エントリ失敗による後続キャンセル | `SWSS_RC_NOT_EXECUTED` | `gre_tunnel_manager.cpp:269-275` |

### SAI Bulk 作成段階 (`createGreTunnels`)
| 失敗条件 | エラーコード | evidence |
|---------|-------------|----------|
| `sai_tunnel_api->create_tunnels()` 失敗 (1 件) | SAI status をラップした ReturnCode | `gre_tunnel_manager.cpp:461-465` |
| Bulk 内の前エントリ失敗による後続キャンセル | `SWSS_RC_NOT_EXECUTED` 相当 | `SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR` |

## DEL 失敗マトリクス

### バリデーション段階 (`validateGreTunnelAppDbEntry` DEL)
| 失敗条件 | エラーコード | evidence |
|---------|-------------|----------|
| 対象トンネルが GreTunnelManager に未登録 | `SWSS_RC_NOT_FOUND` | `gre_tunnel_manager.cpp:153-158` |
| `ref_count > 0`（nexthop 等が参照中） | `SWSS_RC_INVALID_PARAM` | `gre_tunnel_manager.cpp:168-172` |

### SAI Bulk 削除段階 (`removeGreTunnels`)
| 失敗条件 | エラーコード | evidence |
|---------|-------------|----------|
| `sai_tunnel_api->remove_tunnels()` 失敗 | SAI status をラップした ReturnCode | `gre_tunnel_manager.cpp:518-522` |

## エラー伝達経路

`m_publisher->publish(APP_P4RT_TABLE_NAME, key, fields, status, replace=true)` で P4RT gRPC レスポンスに即時返却される。
失敗エントリは `Consumer::m_toSync` に残留しない（自動リトライなし）。
