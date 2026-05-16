# FIXED_NEXTHOP_TABLE (set_p2p_tunnel_encap_nexthop) — ordering 調査メモ

## 調査対象ファイル

- `sonic-swss/orchagent/p4orch/next_hop_manager.cpp`
- `sonic-swss/orchagent/p4orch/p4orch.cpp`

## P4Orch 内での処理順序 (ADD)

`p4orch.cpp` の `m_p4ManagerAddPrecedence` で定義される処理優先順:

1. TablesDefnManager (TABLE_DEFINITION)
2. RouterInterfaceManager (ROUTER_INTERFACE) ← GRE tunnel が依存
3. NeighborManager (NEIGHBOR) ← GRE tunnel が依存
4. GreTunnelManager (FIXED_TUNNEL_TABLE) ← nexthop が依存
5. **NextHopManager (FIXED_NEXTHOP_TABLE)** ← 本テーブル (5番目)
6. WcmpManager (WCMP_GROUP) ← nexthop を参照
7. RouteManager など下流

→ P4RT controller がこの順に書けばバッチ内での依存エラーを回避できる。

## SET における依存前提条件

`validateAppDbEntry()` (next_hop_manager.cpp:104-200) が SET 時に以下を必須チェック:

1. `param/tunnel_id` が参照する GRE トンネルエントリが `GreTunnelManager` キャッシュに存在すること
   (`getConstGreTunnelEntry()` — not ok → `SWSS_RC_NOT_FOUND`)
2. 同 GRE トンネルの OID が `P4OidMapper` (`SAI_OBJECT_TYPE_TUNNEL`) に存在すること
   (mapper 確認 — 不在 → `SWSS_RC_NOT_FOUND`)
3. GRE トンネルから取得した `(router_interface_id, neighbor_id)` ペアの neighbor が
   `P4OidMapper` (`SAI_OBJECT_TYPE_NEIGHBOR_ENTRY`) に存在すること
   (BRCM SAI 要件: neighbor は nexthop より先に存在する必要がある — next_hop_manager.cpp:144-158)

→ `FIXED_TUNNEL_TABLE` エントリ（GRE トンネル本体）と、その配下の RIF・neighbor が
   先に作成されていないと `SWSS_RC_NOT_FOUND` で失敗する。

## DEL における依存チェック

`validateAppDbEntry()` (DEL パス) が ref_count を確認:
- `m_p4OidMapper->getRefCount(SAI_OBJECT_TYPE_NEXT_HOP, ...)` で参照カウントを確認
- `ref_count > 0` の場合は `SWSS_RC_INVALID_PARAM` エラー
→ nexthop を参照している WCMP グループ / ルートエントリを先に削除しないと消せない (next_hop_manager.cpp:179-191)。

## Bulk SAI 呼び出し順序

`createNextHops()` / bulk パス (next_hop_manager.cpp:490-550):
- SET バッチは `validateAppDbEntry()` → `prepareSaiAttrs()` を全エントリ分ループした後に
  `sai_next_hop_api->create_next_hops()` を `SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR` で一括呼び出し
- 1 件でも失敗するとバッチ内の後続エントリはすべてキャンセル
- ref_count インクリメント (tunnel OID / RIF OID) はバッチ成功後にまとめて実行 (next_hop_manager.cpp:541-548)

## 結論

FIXED_NEXTHOP_TABLE (set_p2p_tunnel_encap_nexthop) エントリは以下の順序制約を持つ:

```
ADD:  RIF → Neighbor → GRE Tunnel (FIXED_TUNNEL_TABLE) → NextHop (FIXED_NEXTHOP_TABLE) → WCMP / Route
DEL:  Route / WCMP → NextHop (FIXED_NEXTHOP_TABLE) → GRE Tunnel → Neighbor / RIF
```

GRE Tunnel ID を変更する UPDATE は禁止。変更には DEL → SET の順が必要 (next_hop_manager.cpp:104-112)。
