# tunnel-encap-table: Phase F 副作用・他オブジェクトへの波及 調査メモ

対象: `FIXED_TUNNEL_TABLE` (APPL_DB P4RT_TABLE) / `GreTunnelManager`
調査ソース: `orchagent/p4orch/gre_tunnel_manager.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d

## 検出された副作用

### SET 成功時 (`createGreTunnels()`)

1. **P4OidMapper — ROUTER_INTERFACE ref_count インクリメント**
   - `m_p4OidMapper->increaseRefCount(SAI_OBJECT_TYPE_ROUTER_INTERFACE, router_interface_keys[i])`
   - gre_tunnel_manager.cpp:445-447
   - 結果: RIF の ref_count が増加し、RIF DEL が INVALID_PARAM でブロックされる

2. **P4OidMapper — NEIGHBOR_ENTRY ref_count インクリメント**
   - `m_p4OidMapper->increaseRefCount(SAI_OBJECT_TYPE_NEIGHBOR_ENTRY, neighbor_key)`
   - neighbor_key = `{router_interface_id}:{encap_dst_ip}` 形式
   - gre_tunnel_manager.cpp:449-452
   - 結果: Neighbor の ref_count が増加し、Neighbor DEL がブロックされる

3. **P4OidMapper — SAI_OBJECT_TYPE_TUNNEL OID 登録**
   - `m_p4OidMapper->setOID(SAI_OBJECT_TYPE_TUNNEL, entries[i].tunnel_key, entries[i].tunnel_oid)`
   - gre_tunnel_manager.cpp:458-459
   - 結果: 下流の NextHopManager が `getOID(TUNNEL, ...)` でこのトンネル OID を参照できるようになる

4. **内部テーブル `m_greTunnelTable` への登録**
   - `m_greTunnelTable.emplace(entries[i].tunnel_key, entries[i])`
   - gre_tunnel_manager.cpp:456
   - 結果: NextHopManager の `getConstGreTunnelEntry()` によるトンネル情報参照が可能になる

### DEL 成功時 (`removeGreTunnels()`)

1. **P4OidMapper — ROUTER_INTERFACE ref_count デクリメント**
   - `m_p4OidMapper->decreaseRefCount(SAI_OBJECT_TYPE_ROUTER_INTERFACE, ...)`
   - gre_tunnel_manager.cpp:504-506
   - 結果: RIF の ref_count が減少。0 になれば RIF DEL が可能になる

2. **P4OidMapper — NEIGHBOR_ENTRY ref_count デクリメント**
   - `m_p4OidMapper->decreaseRefCount(SAI_OBJECT_TYPE_NEIGHBOR_ENTRY, neighbor_key)`
   - gre_tunnel_manager.cpp:508-511
   - 結果: Neighbor の ref_count が減少。0 になれば Neighbor DEL が可能になる

3. **P4OidMapper — SAI_OBJECT_TYPE_TUNNEL OID 削除**
   - `m_p4OidMapper->eraseOID(SAI_OBJECT_TYPE_TUNNEL, entries[i]->tunnel_key)`
   - gre_tunnel_manager.cpp:514
   - 結果: 下流の NextHopManager から OID 参照が不可能になる（DEL 前に nexthop が削除されていなければ ref_count ガードで到達不能）

4. **内部テーブル `m_greTunnelTable` からの削除**
   - `m_greTunnelTable.erase(entries[i]->tunnel_key)`
   - gre_tunnel_manager.cpp:517
   - 結果: NextHopManager の `getConstGreTunnelEntry()` が nullptr を返すようになる

### CRM について

`gre_tunnel_manager.cpp` は `crmorch.h` をインクルードし `extern CrmOrch *gCrmOrch` を宣言しているが、
実際には `gCrmOrch->incCrmResUsedCounter()` / `decCrmResUsedCounter()` を呼び出していない。
GRE tunnel オブジェクトは CRM カウンタの対象外。

### 結論

`GreTunnelManager` の副作用は P4OidMapper の ref_count 操作と OID 登録/削除のみ。
COUNTERS_DB / FLEX_COUNTER_DB / STATE_DB への書込みは一切ない。
下流への波及は NextHop → WCMP → Route と連鎖するが、それらは各 Manager の責務。
