# tunnel-encap-action (FIXED_NEXTHOP_TABLE set_p2p_tunnel_encap_nexthop) — Phase F 副作用スキャンノート

対象テーブル: `APPL_DB P4RT_TABLE:FIXED_NEXTHOP_TABLE` (set_p2p_tunnel_encap_nexthop アクション)
Consumer: `NextHopManager` (`orchagent/p4orch/next_hop_manager.cpp`)
スキャン範囲: createNextHops(), removeNextHops() 全行精読
参照 SHA: `4305596156d70e9797e8a881b3d19b46de0bce0d`

---

## 検出した副作用

### SET 成功時の副作用

1. **SAI_OBJECT_TYPE_TUNNEL の ref_count インクリメント** (next_hop_manager.cpp:541-545)
   - `m_p4OidMapper->increaseRefCount(SAI_OBJECT_TYPE_TUNNEL, KeyGenerator::generateTunnelKey(entries[i].gre_tunnel_id))`
   - これにより参照先 GRE トンネルは ref_count > 0 となり、DEL 操作がブロックされる

2. **SAI_OBJECT_TYPE_NEIGHBOR_ENTRY の ref_count インクリメント** (next_hop_manager.cpp:554-557)
   - `m_p4OidMapper->increaseRefCount(SAI_OBJECT_TYPE_NEIGHBOR_ENTRY, neighbor_key)`
   - neighbor_key = (router_interface_id, encap_dst_ip)

3. **CRM カウンタのインクリメント** (next_hop_manager.cpp:558-562)
   - neighbor_id が IPv4 → `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_IPV4_NEXTHOP)`
   - neighbor_id が IPv6 → `gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_IPV6_NEXTHOP)`
   - CRM (Critical Resource Monitor) が nexthop リソース使用量を追跡するため、SAI 側の nexthop 消費が即時反映される

4. **P4OidMapper への OID 登録** (next_hop_manager.cpp:568-569)
   - `m_p4OidMapper->setOID(SAI_OBJECT_TYPE_NEXT_HOP, entries[i].next_hop_key, entries[i].next_hop_oid)`
   - これにより下流 (WCMP / Route) が nexthop OID を参照できるようになる

### DEL 成功時の副作用

1. **SAI_OBJECT_TYPE_TUNNEL の ref_count デクリメント** (next_hop_manager.cpp:613-616)
   - `m_p4OidMapper->decreaseRefCount(SAI_OBJECT_TYPE_TUNNEL, ...)`
   - ref_count が 0 になると GRE トンネルの DEL が可能になる

2. **SAI_OBJECT_TYPE_NEIGHBOR_ENTRY の ref_count デクリメント** (next_hop_manager.cpp:632-635)
   - DEL 時は router_interface_id を GRE Tunnel から再解決してから decreaseRefCount を呼ぶ

3. **CRM カウンタのデクリメント** (next_hop_manager.cpp:636-640)
   - `gCrmOrch->decCrmResUsedCounter(CrmResourceType::CRM_IPV4_NEXTHOP / CRM_IPV6_NEXTHOP)`

4. **P4OidMapper からの OID 削除** (next_hop_manager.cpp:643)
   - `m_p4OidMapper->eraseOID(SAI_OBJECT_TYPE_NEXT_HOP, next_hop_keys[i])`

## 影響範囲のまとめ

- **FIXED_TUNNEL_TABLE**: nexthop 作成/削除で ref_count が増減し、トンネル DEL 可否に直接影響する
- **Neighbor エントリ**: ref_count が増減し、Neighbor DEL 可否に影響する
- **CRM モニタリング**: `show crm resources nexthop` の CRM_IPV4_NEXTHOP / CRM_IPV6_NEXTHOP カウンタが変動する
- **P4OidMapper**: nexthop OID が登録/削除され、下流の WCMP / Route エントリのOID参照可否が変わる
