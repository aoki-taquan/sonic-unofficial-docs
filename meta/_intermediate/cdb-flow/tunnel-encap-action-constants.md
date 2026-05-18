# tunnel-encap-action — Phase E ハードコード定数 スキャンノート

調査日: 2026-05-18
対象ソース: `orchagent/p4orch/p4orch_util.h`, `orchagent/p4orch/next_hop_manager.h`, `common/schema.h`

## 文字列定数 (p4orch_util.h)

`FIXED_NEXTHOP_TABLE` の `set_p2p_tunnel_encap_nexthop` アクションに直接関係する定数:

| 定数名 | 値 | 用途 |
|--------|----|------|
| `kSetTunnelNexthop` | `"set_p2p_tunnel_encap_nexthop"` | アクション名 (validateAppDbEntry で比較) |
| `kSetIpNexthop` | `"set_ip_nexthop"` | 許容アクション1 |
| `kSetIpNexthopAndDisableRewrites` | `"set_ip_nexthop_and_disable_rewrites"` | 許容アクション2 |
| `kSetNexthop` | `"set_nexthop"` | 許容アクション3 |
| `kNexthopId` | `"nexthop_id"` | match フィールド名 |
| `kTunnelId` | `"tunnel_id"` | param フィールド名 |
| `kRouterInterfaceId` | `"router_interface_id"` | param フィールド名 (禁止フィールド) |
| `kNeighborId` | `"neighbor_id"` | param フィールド名 (禁止フィールド) |
| `kControllerMetadata` | `"controller_metadata"` | 無視されるホワイトリスト外フィールド |
| `kMatchPrefix` | `"match"` | match フィールドプレフィックス |
| `kActionParamPrefix` | `"param"` | action param フィールドプレフィックス |
| `kFieldDelimiter` | `'/'` | match/param フィールド名のデリミタ |

## SAI 定数 (next_hop_manager.cpp / next_hop_manager.h)

| 定数 / 属性 | 値 | 用途 |
|------------|-----|------|
| `SAI_NEXT_HOP_TYPE_TUNNEL_ENCAP` | SAI enum | set_p2p_tunnel_encap_nexthop 時に使用 |
| `SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR` | SAI enum | createNextHops/removeNextHops のバルクモード |
| P4NextHopEntry::disable_decrement_ttl | `false` | 構造体デフォルト (set_p2p_tunnel_encap_nexthop では SAI に送出されない) |
| P4NextHopEntry::disable_src_mac_rewrite | `false` | 同上 |
| P4NextHopEntry::disable_dst_mac_rewrite | `false` | 同上 |
| P4NextHopEntry::disable_vlan_rewrite | `false` | 同上 |

## テーブル名定数 (schema.h)

| 定数名 | 値 | 用途 |
|--------|----|------|
| `APP_P4RT_TABLE_NAME` | `"P4RT_TABLE"` | APPL_DB テーブルプレフィックス |
| `APP_P4RT_NEXTHOP_TABLE_NAME` | `"FIXED_NEXTHOP_TABLE"` | nexthop テーブル名 |

## 許容アクション一覧

`validateAppDbEntry()` (next_hop_manager.cpp:49-55) で受け入れるアクション値:

1. `"set_p2p_tunnel_encap_nexthop"` (kSetTunnelNexthop)
2. `"set_ip_nexthop"` (kSetIpNexthop)
3. `"set_ip_nexthop_and_disable_rewrites"` (kSetIpNexthopAndDisableRewrites)
4. `"set_nexthop"` (kSetNexthop)

上記以外は即座に `SWSS_RC_INVALID_PARAM` を返す。

## フィールドパースのホワイトリスト

`deserializeP4NextHopAppDbEntry()` は以下のフィールドのみ処理し、不明フィールドは
`SWSS_RC_INVALID_PARAM` を返す (controller_metadata は例外的に無視される):

- `match/nexthop_id`
- `action`
- `param/router_interface_id`
- `param/neighbor_id`
- `param/tunnel_id`
- `controller_metadata` (無視)
