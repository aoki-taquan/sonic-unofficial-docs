# TUNNEL_ENCAP_ACTION (P4RT FIXED_NEXTHOP_TABLE — set_p2p_tunnel_encap_nexthop) — Phase A: コード由来の暗黙デフォルト調査結果

調査日: 2026-05-14
対象ファイル:
- `sonic-swss/orchagent/p4orch/next_hop_manager.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/p4orch/next_hop_manager.h` (同上)
- `sonic-swss/orchagent/p4orch/p4orch_util.h` (同上)
- `sonic-swss-common/common/schema.h` (ref: 158de8d3463ff4b841653f6d57190bb142b80d9c)

---

## 1. テーブル名とアクション定数

- APPL_DB テーブル名: `APP_P4RT_NEXTHOP_TABLE_NAME = "FIXED_NEXTHOP_TABLE"` (schema.h:63)
- `set_p2p_tunnel_encap_nexthop` アクション定数: `kSetTunnelNexthop = "set_p2p_tunnel_encap_nexthop"` (p4orch_util.h:64)
- 許容 action 値は 4 種: `set_ip_nexthop` / `set_ip_nexthop_and_disable_rewrites` / `set_nexthop` / `set_p2p_tunnel_encap_nexthop`

---

## 2. `neighbor_id` デフォルト値 — `0.0.0.0` (parse 初期値)

`deserializeP4NextHopAppDbEntry` は `app_db_entry.neighbor_id = swss::IpAddress("0.0.0.0")` で初期化する (next_hop_manager.cpp:420)。

`set_p2p_tunnel_encap_nexthop` アクションでは `param/neighbor_id` フィールドは不要。
代わりに、GRE トンネルから `neighbor_id` を自動取得する (`(*gre_tunnel_or).neighbor_id`, next_hop_manager.cpp:147, 518)。
BRCM SAI 要件: GRE トンネルの `encap_dst_ip` と同値の neighbor が事前に存在している必要がある。

---

## 3. `router_interface_id` — GRE トンネルから自動解決

`set_p2p_tunnel_encap_nexthop` では `param/router_interface_id` は禁止フィールド (set すると `INVALID_PARAM`)。
代わりに `createNextHops` / `validateAppDbEntry` 内で GRE トンネルオブジェクトから
`(*gre_tunnel_or).router_interface_id` を取得し内部セットする (next_hop_manager.cpp:142, 514)。

---

## 4. `disable_decrement_ttl` / `disable_src_mac_rewrite` / `disable_dst_mac_rewrite` / `disable_vlan_rewrite` — デフォルト false

これら 4 フィールドは `P4NextHopEntry` 構造体のメンバーデフォルト値として `false` が定義されている (next_hop_manager.h:38-41)。
省略された場合は `prepareSaiAttrs` で SAI に `false` として渡される。
ただし、これら 4 フィールドは `set_p2p_tunnel_encap_nexthop` アクションでは SAI に送出されない (gre_tunnel_id が設定される分岐では SAI_NEXT_HOP_ATTR_DISABLE_* は設定されない、next_hop_manager.cpp:206-260)。
これらは `set_ip_nexthop` / `set_ip_nexthop_and_disable_rewrites` / `set_nexthop` アクション専用属性。

---

## 5. `SAI_NEXT_HOP_ATTR_TYPE` — `set_p2p_tunnel_encap_nexthop` では `SAI_NEXT_HOP_TYPE_TUNNEL_ENCAP` に固定

`prepareSaiAttrs` は `gre_tunnel_id` が非空の場合 `SAI_NEXT_HOP_TYPE_TUNNEL_ENCAP` をセットする (next_hop_manager.cpp:215-216)。
非 tunnel アクション時は `SAI_NEXT_HOP_TYPE_IP` (next_hop_manager.cpp:231-232)。
DB フィールドとして公開されていない暗黙設定。

---

## 6. `SAI_NEXT_HOP_ATTR_TUNNEL_ID` — GRE トンネル OID を自動解決

`prepareSaiAttrs` がセントラライズドマッパーから `gre_tunnel_id` に対応する OID を取得して SAI にセット (next_hop_manager.cpp:210-221)。
DB フィールドとしては `param/tunnel_id` (文字列 ID) を受け取るが、SAI には OID に変換後に送出。

---

## 7. 相互排他フィールド制約 (コードで強制)

| アクション | 必須フィールド | 禁止フィールド |
|-----------|--------------|--------------|
| `set_p2p_tunnel_encap_nexthop` | `param/tunnel_id` | `param/router_interface_id` |
| `set_ip_nexthop` / `set_nexthop` | `param/router_interface_id` | `param/tunnel_id` |
| `set_ip_nexthop` / `set_ip_nexthop_and_disable_rewrites` | `param/neighbor_id` | — |

violate すると `INVALID_PARAM` を返す (validateAppDbEntry, next_hop_manager.cpp:47-101)。

---

## 8. `controller_metadata` — 無視 (ホワイトリスト外スキップ)

`p4orch::kControllerMetadata` フィールドは deserialize 時に明示的にスキップ (next_hop_manager.cpp:480)。
その他の未知フィールドは `INVALID_PARAM` エラー。

---

## 9. Update (SET on existing entry) の挙動

既存エントリへの SET は NEXTHOP では変更操作として処理される。
GRE トンネル変更 (`gre_tunnel_id` の変更) は `SWSS_RC_INVALID_PARAM` エラー (next_hop_manager.cpp:776-782)。
RIF 変更 / neighbor 変更もエラー。実質的には DEL → SET による再作成が必要。

---

## 10. Bulk SAI API 使用

`create_next_hops` / `remove_next_hops` は SAI Bulk API (`sai_next_hop_api->create_next_hops(...)`) を使用 (next_hop_manager.cpp:527, 603)。
`SAI_BULK_OP_ERROR_MODE_STOP_ON_ERROR` モード。
