# tunnel-encap-table: Phase C 暗黙参照テーブル 調査メモ

対象: `FIXED_TUNNEL_TABLE` (APPL_DB P4RT_TABLE) / `GreTunnelManager`
調査ソース: `orchagent/p4orch/gre_tunnel_manager.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d

## 検出された暗黙参照

### 1. FIXED_ROUTER_INTERFACE_TABLE (先行必須)

SET 時に `m_p4OidMapper->getOID(SAI_OBJECT_TYPE_ROUTER_INTERFACE, router_interface_key, &entry.underlay_if_oid)` を呼び出す。
RIF が centralized mapper に未登録の場合は `SWSS_RC_NOT_FOUND`。
(gre_tunnel_manager.cpp:129-134)

### 2. Neighbor エントリ (先行必須)

SET 時に `m_p4OidMapper->existsOID(SAI_OBJECT_TYPE_NEIGHBOR_ENTRY, neighbor_key)` を確認。
neighbor_key = `{router_interface_id}:{encap_dst_ip}` (BRCM SAI 要件)。
(gre_tunnel_manager.cpp:139-149)

### 3. FIXED_NEXTHOP_TABLE (DEL ブロック)

DEL 時に `m_p4OidMapper->getRefCount(SAI_OBJECT_TYPE_TUNNEL, tunnel_key, &ref_count)` を確認。
`ref_count > 0` の場合 `SWSS_RC_INVALID_PARAM`。
(gre_tunnel_manager.cpp:162-169)

### 4. P4OidMapper ref_count (副作用)

SET 成功時:
- `increaseRefCount(ROUTER_INTERFACE, router_interface_keys[i])` (gre_tunnel_manager.cpp:445-446)
- `increaseRefCount(NEIGHBOR_ENTRY, neighbor_key)` (gre_tunnel_manager.cpp:448-452)

DEL 成功時:
- `decreaseRefCount(ROUTER_INTERFACE, ...)` (gre_tunnel_manager.cpp:505-506)
- `decreaseRefCount(NEIGHBOR_ENTRY, ...)` (gre_tunnel_manager.cpp:508-511)

### 5. CRM インクルードのみで不使用

`gCrmOrch` は extern 宣言されているが、`gre_tunnel_manager.cpp` 内で実際には呼び出されない。
CRM カウンタの更新は行われない（tunnel オブジェクトは CRM 対象外）。
