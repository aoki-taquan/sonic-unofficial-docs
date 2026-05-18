# FIXED_NEXTHOP_TABLE (set_p2p_tunnel_encap_nexthop) — Phase C 暗黙参照スキャンノート

## 調査対象

- `sonic-swss/orchagent/p4orch/next_hop_manager.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d
- `sonic-swss/orchagent/p4orch/next_hop_manager.h` @ 4305596156d70e9797e8a881b3d19b46de0bce0d

## 参照 1: FIXED_TUNNEL_TABLE (GRE Tunnel) — 必須先行依存

`validateAppDbEntry()` L124-137:

```cpp
auto gre_tunnel_or = gP4Orch->getGreTunnelManager()->getConstGreTunnelEntry(
    KeyGenerator::generateTunnelKey(next_hop_entry.gre_tunnel_id));
if (!gre_tunnel_or.ok()) {
    // SWSS_RC_NOT_FOUND → SET 失敗
}
if (!m_p4OidMapper->existsOID(SAI_OBJECT_TYPE_TUNNEL,
    KeyGenerator::generateTunnelKey(next_hop_entry.gre_tunnel_id))) {
    // SWSS_RC_NOT_FOUND → SET 失敗
}
```

`param/tunnel_id` が参照する `FIXED_TUNNEL_TABLE` エントリが GreTunnelManager に存在しない場合、
`SWSS_RC_NOT_FOUND` でエラーになる。YANG には記述なし。

## 参照 2: Router Interface (RIF) — GRE Tunnel から自動取得

`validateAppDbEntry()` L142-143:

```cpp
next_hop_entry.router_interface_id = (*gre_tunnel_or).router_interface_id;
```

`set_p2p_tunnel_encap_nexthop` アクションでは `param/router_interface_id` を直接指定しない。
GRE Tunnel エントリから `router_interface_id` を自動取得する。
コントローラは RIF を明示指定することができず (禁止フィールド)、
GRE Tunnel の作成側 (`GreTunnelManager`) が RIF を確立している必要がある。

## 参照 3: Neighbor Entry — GRE Tunnel の encap_dst_ip から自動導出

`validateAppDbEntry()` L147-168:

```cpp
next_hop_entry.neighbor_id = (*gre_tunnel_or).neighbor_id; // = encap_dst_ip
const auto neighbor_key = KeyGenerator::generateNeighborKey(
    next_hop_entry.router_interface_id, next_hop_entry.neighbor_id);
if (!m_p4OidMapper->existsOID(SAI_OBJECT_TYPE_NEIGHBOR_ENTRY, neighbor_key)) {
    // SWSS_RC_NOT_FOUND → SET 失敗
}
```

BRCM SAI 要件から、GRE tunnel の `encap_dst_ip` に対応する neighbor エントリが
nexthop 作成前に P4Orch mapper に存在している必要がある。
コントローラが `param/neighbor_id` を書く場合は `INVALID_PARAM` エラー。

## 参照 4: P4OidMapper (集中型 OID マッパー) — SAI OID 解決

`prepareSaiAttrs()` L210-221:

```cpp
m_p4OidMapper->getOID(SAI_OBJECT_TYPE_TUNNEL, tunnel_key, &tunnel_oid);
// → SAI_NEXT_HOP_ATTR_TUNNEL_ID に設定
m_p4OidMapper->getOID(SAI_OBJECT_TYPE_ROUTER_INTERFACE, rif_key, &rif_oid);
// → SAI_NEXT_HOP_ATTR_ROUTER_INTERFACE_ID (IP nexthop 時) に設定
```

`SAI_OBJECT_TYPE_TUNNEL` OID と `SAI_OBJECT_TYPE_ROUTER_INTERFACE` OID は
P4OidMapper 経由で解決される。GRE Tunnel SET が成功していれば自動的に利用可能。

## 参照 5: WCMP / Route (下流参照) — DEL 時の ref_count ガード

`validateAppDbEntry()` L181-195:

```cpp
if (!m_p4OidMapper->getRefCount(SAI_OBJECT_TYPE_NEXT_HOP, next_hop_entry.next_hop_key, &ref_count)) { ... }
if (ref_count > 0) {
    // SWSS_RC_INVALID_PARAM → DEL 失敗
}
```

WCMP や Route が nexthop を参照している間は DEL 不可。
下流の WCMP / Route を先に DEL してから nexthop DEL が必要。

## まとめ

| 参照先 | 参照方向 | 条件 | 不在時の挙動 |
|--------|---------|------|------------|
| `FIXED_TUNNEL_TABLE` (GreTunnelManager) | 先行必須 | `gre_tunnel_id` 非空 (常時) | `SWSS_RC_NOT_FOUND` → SET 失敗 |
| Router Interface | GRE Tunnel から自動取得 | `set_p2p_tunnel_encap_nexthop` 時 | GRE Tunnel 作成失敗で連鎖 |
| Neighbor Entry (`encap_dst_ip`) | P4OidMapper 照合 | `set_p2p_tunnel_encap_nexthop` 時 | `SWSS_RC_NOT_FOUND` → SET 失敗 |
| P4OidMapper (SAI OID) | OID 解決 | SAI 属性付与時 | (GRE Tunnel が正常なら問題なし) |
| WCMP / Route (下流) | DEL 時 ref_count ガード | DEL 時 | `SWSS_RC_INVALID_PARAM` → DEL 失敗 |
