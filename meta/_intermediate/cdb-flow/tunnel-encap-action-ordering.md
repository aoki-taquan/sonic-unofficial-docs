# tunnel-encap-action — ordering 調査メモ (Phase B)

## 調査対象

- `orchagent/p4orch/next_hop_manager.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/p4orch/gre_tunnel_manager.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## SET 時の依存チェーン（コードエビデンス）

### 1. FIXED_TUNNEL_TABLE エントリ先行必須

`next_hop_manager.cpp:122-140`:
```cpp
if (!next_hop_entry.gre_tunnel_id.empty()) {
  auto gre_tunnel_or = gP4Orch->getGreTunnelManager()->getConstGreTunnelEntry(
      KeyGenerator::generateTunnelKey(next_hop_entry.gre_tunnel_id));
  if (!gre_tunnel_or.ok()) {
    LOG_ERROR_AND_RETURN(ReturnCode(StatusCode::SWSS_RC_NOT_FOUND) ...);
  }
  if (!m_p4OidMapper->existsOID(SAI_OBJECT_TYPE_TUNNEL, ...)) {
    LOG_ERROR_AND_RETURN(ReturnCode(StatusCode::SWSS_RC_NOT_FOUND) ...);
  }
```

→ param/tunnel_id が参照する FIXED_TUNNEL_TABLE エントリは NextHopManager 処理前に存在していなければ SWSS_RC_NOT_FOUND でエラー。

### 2. Neighbor エントリ先行必須（BRCM SAI 要件）

`next_hop_manager.cpp:144-170`:
```
BRCM requires neighbor object to be created before GRE tunnel,
referring to the one in GRE tunnel object when creating next_hop_entry
```

→ GRE トンネルの encap_dst_ip に対応する neighbor エントリが存在しないと SWSS_RC_NOT_FOUND。

### 3. DEL 時は参照カウント確認

`next_hop_manager.cpp:179-187`: ref_count > 0 の場合は削除不可。

## 結論

SET 順: FIXED_ROUTER_INTERFACE_TABLE → FIXED_NEIGHBOR_TABLE → FIXED_TUNNEL_TABLE → FIXED_NEXTHOP_TABLE
DEL 順: 逆順。nexthop を参照する上位エントリを先に削除。
