# tunnel-encap-action: Phase H プラットフォーム / SAI Capability 差異 調査メモ

対象: `FIXED_NEXTHOP_TABLE` (APPL_DB P4RT_TABLE) / `NextHopManager` (`set_p2p_tunnel_encap_nexthop` アクション)
調査ソース: `orchagent/p4orch/next_hop_manager.cpp` @ 4305596156d70e9797e8a881b3d19b46de0bce0d

## 概要

`next_hop_manager.cpp` にはプラットフォーム分岐コード (`getenv("platform")` / `MLNX_PLATFORM_SUBSTRING` 等) は存在しない。
差異は SAI 実装レベルで生じる。

## BRCM SAI 固有要件 — neighbor 事前生成

```cpp
// next_hop_manager.cpp:144
// BRCM requires neighbor object to be created before GRE tunnel,
// referring to the one in GRE tunnel object when creating
// next_hop_entry_with setTunnelAction
```

`set_p2p_tunnel_encap_nexthop` 時、NextHopManager は GreTunnelManager から `neighbor_id`（= `encap_dst_ip`）を取得し、
centralized mapper で neighbor エントリの存在を確認してから SAI nexthop を作成する。
この順序制約は BRCM SAI 要件としてコードに明記されている (next_hop_manager.cpp:144, 515)。

## CRM カウンタ更新 (プラットフォーム非依存)

SET 成功時に `gCrmOrch->incCrmResUsedCounter()` が呼ばれる:
- IPv4 neighbor: `CRM_IPV4_NEXTHOP` (next_hop_manager.cpp:558-559)
- IPv6 neighbor: `CRM_IPV6_NEXTHOP` (next_hop_manager.cpp:560-561)

GreTunnelManager (`gre_tunnel_manager.cpp`) は CRM カウンタを更新しない点と対照的。

## SAI Bulk モード

`create_next_hops` / `remove_next_hops` は `SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR` 固定
(next_hop_manager.cpp:527-530)。

## 結論

| プラットフォーム | 状況 |
|----------------|------|
| Broadcom (BRCM SAI) | 対応。neighbor 事前生成が必須要件 |
| VS / VPP (libsaivs / libsaivpp) | SAI nexthop 作成は成功するがハードウェア転送なし (CI/テスト専用) |
| その他 ASIC | SAI 実装次第。P4RT gRPC サービスを持つプラットフォームでのみ機能する |
