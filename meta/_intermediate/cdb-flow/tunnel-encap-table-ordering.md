# tunnel-encap-table: Phase B 書込み順依存 調査メモ

対象: `FIXED_TUNNEL_TABLE` (APPL_DB P4RT_TABLE) / `GreTunnelManager`
調査ソース: `orchagent/p4orch/gre_tunnel_manager.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d

## 検出された順序依存

### 1. FIXED_ROUTER_INTERFACE_TABLE (RIF) が先行必須 (SET 時)

`GreTunnelManager::processAppDbUpdate()` は SET 操作時に `validateGreTunnelAppDbEntry()` を呼び、
その中で `m_p4OidMapper->getOID(SAI_OBJECT_TYPE_ROUTER_INTERFACE, router_interface_key, ...)` を確認する。
RIF が centralized mapper に存在しない場合は `SWSS_RC_NOT_FOUND` を返してエントリ追加を拒否する。
(gre_tunnel_manager.cpp:130-134)

### 2. Neighbor エントリ (encap_dst_ip) が先行必須 (SET 時)

RIF 確認の後、`m_p4OidMapper->existsOID(SAI_OBJECT_TYPE_NEIGHBOR_ENTRY, neighbor_key)` を確認する。
neighbor_key は `{router_interface_id}:{encap_dst_ip}` 形式。
Neighbor が存在しない場合も `SWSS_RC_NOT_FOUND` を返す。
(gre_tunnel_manager.cpp:139-149)

### 3. FIXED_NEXTHOP_TABLE (nexthop) が先行削除必須 (DEL 時)

DEL 操作時に `m_p4OidMapper->getRefCount(SAI_OBJECT_TYPE_TUNNEL, entry.tunnel_key, &ref_count)` を確認し、
ref_count > 0 の場合は `SWSS_RC_INVALID_PARAM` を返して削除を拒否する。
`FIXED_NEXTHOP_TABLE` のエントリが `set_p2p_tunnel_encap_nexthop` アクションでこのトンネルを参照している場合、
それらを先に削除しないとトンネルは削除できない。
(gre_tunnel_manager.cpp:155-169)

### 4. Bulk モード: SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR

`createGreTunnels()` の bulk SAI 呼び出しは `SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR` を使用する。
エラーが発生した場合、そのエントリ以降はすべて `SAI_STATUS_NOT_EXECUTED` になる。
(gre_tunnel_manager.cpp:431)

## 結論

SET 順序: neighbor エントリ → (RIF は neighbor より先) → FIXED_TUNNEL_TABLE → FIXED_NEXTHOP_TABLE
DEL 順序: FIXED_NEXTHOP_TABLE → FIXED_TUNNEL_TABLE → (neighbor / RIF は後)
