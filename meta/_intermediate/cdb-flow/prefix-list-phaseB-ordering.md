# PREFIX_LIST — Phase B: 順序依存性 中間ファイル

生成日: 2026-05-16 (Task F Phase B)

## 調査対象ソース

- `sonic-buildimage/src/sonic-bgpcfgd/bgpcfgd/managers_prefix_list.py`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/radian/add_radian.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/radian/del_radian.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/suppress_prefix/add_suppress_prefix.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/suppress_prefix/del_suppress_prefix.conf.j2`
- `sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2`
- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`

## 1. PREFIX_LIST エントリ順序

CONFIG_DB キー構造: `PREFIX_LIST|<prefix_type>|<ip-prefix>`

シーケンス番号フィールドなし。YANG モデル `sonic-bgp-prefix-list.yang` にも seq フィールドなし。

FRR コマンド生成 (add_suppress_prefix.conf.j2):
```
{{ data.ipv }} prefix-list {{ data.prefix_list_name }} permit {{ data.prefix }}
```
→ seq 指定なし。FRR が内部で自動採番する。

FRR コマンド生成 (add_radian.conf.j2):
```
{{ data.ipv }} prefix-list ANCHOR_CONTRIBUTING_ROUTES permit {{ data.prefix }} ge {{ data.prefixlen + 1 }}
router bgp {{ data.bgp_asn }}
 address-family ipv4/ipv6 unicast
  aggregate-address {{ data.prefix }} route-map TAG_ANCHOR_COMMUNITY
 exit
exit
```
→ prefix-list と aggregate-address (route-map 参照) が同一ブロックに含まれる。

## 2. ROUTE_MAP からの参照順序

`bgpd.main.conf.j2` 生成順 (L14-75):
1. `ip prefix-list PL_LoopbackV4 permit <lo>/32` (L14)
2. `ipv6 prefix-list PL_LoopbackV6 permit ...` (L34/L36)
3. `ip prefix-list LOCAL_VLAN_IPV4_PREFIX seq N permit ...` (L45, VLAN_INTERFACE ループ)
4. `ipv6 prefix-list LOCAL_VLAN_IPV6_PREFIX seq N permit ...` (L51)
5. `ip prefix-list V4_P2P_IP permit 0.0.0.0/0 ge 31 le 31` (L64)
6. `ipv6 prefix-list V6_P2P_IP permit ::/0 ge 126 le 126` (L66)
7. `route-map V4_CONNECTED_ROUTES permit 10` → `match ip address prefix-list V4_P2P_IP` (L68-70)
8. `route-map V6_CONNECTED_ROUTES permit 10` → `match ipv6 address prefix-list V6_P2P_IP` (L72-74)

**結論**: prefix-list は常に route-map より先に宣言される (テンプレート上の静的順序保証)。

## 3. frrcfgd table_handler_list 登録順

`frrcfgd.py` L2293-2338:
```python
self.table_handler_list = [
    ('VRF', self.vrf_handler),
    ('DEVICE_METADATA', self.metadata_handler),
    ('BGP_GLOBALS', self.bgp_global_handler),
    ('BGP_GLOBALS_AF', self.bgp_af_handler),
    ('PREFIX_SET', self.bgp_table_handler_common),  # ← prefix-list 先行
    ('PREFIX', self.bgp_table_handler_common),       # ← prefix-list 先行
    ('COMMUNITY_SET', self.comm_set_handler),
    ('EXTENDED_COMMUNITY_SET', self.comm_set_handler),
    ('ROUTE_MAP', self.bgp_table_handler_common),    # ← route-map は後
    ...
]
```

PREFIX_SET/PREFIX が ROUTE_MAP より前に処理されることが保証される。

## 4. bgpcfgd PrefixListMgr 依存関係

`PrefixListMgr.__init__` の `deps`:
```python
[
    ("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/type"),
    ("CONFIG_DB", CFG_DEVICE_METADATA_TABLE_NAME, "localhost/bgp_asn"),
]
```

DEVICE_METADATA の `type` と `bgp_asn` が揃うまで set_handler はリトライ待ち。PREFIX_LIST エントリ間の順序依存はなし（各エントリ独立処理）。

## 結論

- PREFIX_LIST エントリ自体にシーケンス番号なし（FRR が自動採番）
- ROUTE_MAP → prefix-list 参照: テンプレート/handler 登録順で prefix-list が先行適用
- ANCHOR_PREFIX は prefix-list + aggregate-address (route-map 参照) を同一 push で原子適用
- SUPPRESS_PREFIX は prefix-list のみ。route-map 参照なし
