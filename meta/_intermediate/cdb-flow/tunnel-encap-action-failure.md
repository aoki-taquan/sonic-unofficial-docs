# tunnel-encap-action — failure 調査メモ (Phase D)

## 調査対象

- `orchagent/p4orch/next_hop_manager.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)

## SET 失敗経路

### 入力検証 (validateAppDbEntry)
- action が 4 値以外: SWSS_RC_INVALID_PARAM (L53)
- `set_p2p_tunnel_encap_nexthop` で `param/router_interface_id` 指定: SWSS_RC_INVALID_PARAM (L87)
- `set_p2p_tunnel_encap_nexthop` で `param/neighbor_id` 指定: SWSS_RC_INVALID_PARAM (L94)
- `param/tunnel_id` 欠如: SWSS_RC_INVALID_PARAM (L85-98)
- 未知フィールド: SWSS_RC_INVALID_PARAM (L482)

### 依存解決 (validateAppDbEntry, SET)
- GRE Tunnel 不在 (GreTunnelManager): SWSS_RC_NOT_FOUND (L127-130)
- GRE Tunnel OID 不在 (P4OidMapper): SWSS_RC_NOT_FOUND (L136)
- Neighbor 不在: SWSS_RC_NOT_FOUND (L167-168)

### SAI Bulk (createNextHops)
- SAI create 失敗: ReturnCode で包まれ、SWSS_RC_NOT_EXECUTED として publisher へ publish (L363-369)
- Bulk はすべて SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR (L529): 1 件失敗で後続キャンセル

### UPDATE 禁止
- 既存エントリへの SET: SWSS_RC_UNIMPLEMENTED (L670-671), publisher で SWSS_RC_NOT_EXECUTED

### DEL 失敗経路
- エントリ不在: SWSS_RC_NOT_FOUND (L174)
- ref_count > 0 (下流参照あり): SWSS_RC_INVALID_PARAM (L188-194)
- SAI remove 失敗: Bulk STOP_ON_ERROR (L605)

## リトライ有無
P4Orch は失敗エントリを Consumer::m_toSync に残さない（drain 後 erase）。
失敗は即時 publisher publish で P4RT gRPC response に伝達。自動リトライなし。
