# PREFIX_LIST — Phase C 暗黙参照 (cross-refs) 調査メモ

**対象ページ**: `docs/reference/config-db/prefix-list.md`
**ソース**: bgpcfgd (`sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/`)
**調査日**: 2026-05-16

## 調査方針

ROUTE_MAP および BGP_NEIGHBOR テーブルから PREFIX_LIST への被参照を抽出する。
YANG レベルでの leafref 制約は存在しないため、FRR テンプレート・Python manager コードを走査。

## ROUTE_MAP → PREFIX_LIST 参照

bgpcfgd が PREFIX_LIST エントリを FRR `ip prefix-list` / `ipv6 prefix-list` コマンドに変換し、
その名前が各 route-map テンプレートの `match ip address prefix-list` 句で参照される。

### templates/general/policies.conf.j2

- L124: `match ipv6 address prefix-list ANCHOR_CONTRIBUTING_ROUTES`
  → `TO_BGP_PEER_V6 permit 50` 内。PREFIX_LIST `ANCHOR_PREFIX` から派生。
- L133: `match ip address prefix-list ANCHOR_CONTRIBUTING_ROUTES`
  → `TO_BGP_PEER_V4 permit 50` 内。同上。
- L45: `match ip address prefix-list DEFAULT_IPV4`
  → `FROM_BGP_PEER_V4 permit 12` 内。
- L68: `match ipv6 address prefix-list DEFAULT_IPV6`
  → `FROM_BGP_PEER_V6 permit 12` 内。

### idf_isolate/idf_isolate.conf.j2

- L2: `match ip address prefix-list PL_LoopbackV4`
- L5: `match ipv6 address prefix-list PL_LoopbackV6`

### tsa/bgpd.tsa.isolate.conf.j2

- L7: `match {{ ip_protocol }} address prefix-list PL_Loopback{{ ip_version }}`

### templates/voq_chassis/policies.conf.j2

- L32: `match ip address prefix-list PL_LoopbackV4`
- L67: `match ipv6 address prefix-list PL_LoopbackV6`

### bgpd.main.conf.j2

- L69: `match ip address prefix-list V4_P2P_IP` (route-map V4_CONNECTED_ROUTES)
- L73: `match ipv6 address prefix-list V6_P2P_IP` (route-map V6_CONNECTED_ROUTES)

## BGP_NEIGHBOR / BGP_PEER_GROUP → PREFIX_LIST 参照

直接 YANG leafref なし。間接参照のみ:

- `bgpd.main.conf.j2` L200: `redistribute connected route-map V4_CONNECTED_ROUTES`
- `bgpd.main.conf.j2` L203: `redistribute connected route-map V6_CONNECTED_ROUTES`
  → これらの route-map が `prefix-list V4_P2P_IP` / `V6_P2P_IP` に依存
- `PrefixListMgr.generate_prefix_list_config()` が ANCHOR_CONTRIBUTING_ROUTES を生成し、
  `TO_BGP_PEER_V4/V6` route-map 経由で全 BGP ピアへの広報フィルタに影響

## 結論

- YANG 外部キー制約: なし
- FRR テンプレート経由のシンボル依存: ROUTE_MAP → PREFIX_LIST (複数テンプレート)
- BGP_NEIGHBOR への影響: route-map チェーン経由で間接的に存在
- cross-refs ブロックを `docs/reference/config-db/prefix-list.md` に追加済み
