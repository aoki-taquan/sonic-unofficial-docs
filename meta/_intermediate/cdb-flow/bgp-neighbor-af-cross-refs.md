# BGP_NEIGHBOR_AF — 暗黙参照 (Phase C) 証跡

対象ページ: `docs/reference/config-db/bgp-neighbor-af.md`
作業日: 2026-05-15
タスク: Task F Phase C (暗黙参照マップ)

## 走査対象

- `.cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-neighbor.yang`
- `.cache/sonic-sources/sonic-buildimage/src/sonic-yang-models/yang-models/sonic-bgp-common.yang`
- `.cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`
- `.cache/sonic-sources/sonic-buildimage/dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2`

## YANG leafref で強制される構造参照

### `vrf_name` → `BGP_GLOBALS`

```
sonic-bgp-neighbor.yang:116-120

leaf vrf_name {
    type leafref {
        path "/bgpg:sonic-bgp-global/bgpg:BGP_GLOBALS/bgpg:BGP_GLOBALS_LIST/bgpg:vrf_name";
    }
}
```

### `neighbor` → `BGP_NEIGHBOR` (同一 VRF 限定)

```
sonic-bgp-neighbor.yang:123-128

leaf neighbor {
    type leafref {
        path "../../../BGP_NEIGHBOR/BGP_NEIGHBOR_LIST[vrf_name=current()/../vrf_name]/neighbor";
    }
}
```

## frrcfgd.py で生成される FRR コマンドと暗黙参照

`nbr_af_key_map` (L1895-1920) は CONFIG_DB の各フィールド値を FRR コマンドに展開する。
ここで参照されるオブジェクト名は YANG では強制されず、FRR 側の名前空間で解決される。

### route-map 系 (L1899-1906)

```
('send_default_route', '+default_rmap')  → neighbor X default-originate route-map {}
('default_rmap',                         → neighbor X default-originate route-map {}
('route_map_in',                         → neighbor X route-map {} in
('route_map_out',                        → neighbor X route-map {} out
('unsuppress_map_name',                  → neighbor X unsuppress-map {}
```

参照解決: CONFIG_DB `ROUTE_MAP` テーブル → frrcfgd 経由で FRR `route-map` 定義として注入。
未定義名を指定すると bgpd の running-config 上で dangling reference となる。

### prefix-list 系 (L1918-1919)

```
('prefix_list_in',                       → neighbor X prefix-list {} in
('prefix_list_out',                      → neighbor X prefix-list {} out
```

参照解決: FRR `ip prefix-list` (vtysh から投入)。SONiC CONFIG_DB に正式な `PREFIX_LIST` テーブルは存在せず、FRR 側オブジェクトに直接依存。

### filter-list 系 (L1914-1915)

```
('filter_list_in',                       → neighbor X filter-list {} in
('filter_list_out',                      → neighbor X filter-list {} out
```

参照解決: FRR `bgp as-path access-list`。同様に FRR 名前空間で解決。

## ハンドラ・購読関係 (上流)

### Consumer 登録 (L91)

```python
'BGP_NEIGHBOR_AF': ['bgpd'],
```

### key_map 紐付け (L2111-2112)

```python
'BGP_NEIGHBOR_AF':                nbr_af_key_map,
'BGP_PEER_GROUP_AF':              nbr_af_key_map,
```

### ハンドラ登録 (L2306)

```python
('BGP_NEIGHBOR_AF', self.bgp_table_handler_common),
```

### running-config 同期対象 (L2137)

```python
'BGP_NEIGHBOR', 'BGP_PEER_GROUP', 'BGP_NEIGHBOR_AF', 'BGP_PEER_GROUP_AF',
```

## VRF ASN ゲート (silent skip)

`frrcfgd.py:2658-2663`:

```python
local_asn = self.__get_vrf_asn(vrf)
if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
    syslog.syslog(syslog.LOG_DEBUG,
        'ignore table {} update because local_asn for VRF {} was not configured'...)
```

→ BGP_GLOBALS の `local_asn` が未投入の VRF への BGP_NEIGHBOR_AF 更新は LOG_DEBUG 1 行だけで silent skip。
syslog レベルが INFO 以上だと運用者からは見えず、設定が「効かない」現象になる。

## bgpd テンプレートの起動時条件

`dockers/docker-fpm-frr/frr/bgpd/bgpd.main.conf.j2:94-95`:

```jinja
{% if (DEVICE_METADATA is defined) and ('localhost' in DEVICE_METADATA)
      and ('bgp_asn' in DEVICE_METADATA['localhost'])
      and (DEVICE_METADATA['localhost']['bgp_asn'].lower() != 'none')
      and (DEVICE_METADATA['localhost']['bgp_asn'].lower() != 'null') %}
router bgp {{ DEVICE_METADATA['localhost']['bgp_asn'] }}
```

→ `DEVICE_METADATA|localhost|bgp_asn` が未設定/`none`/`null` の場合は `router bgp` ブロック自体が生成されず、BGP_NEIGHBOR_AF の購読/反映も実質無効。

## 下流参照サマリ

| 対象 | 種別 | ソース |
|---|---|---|
| BGP_NEIGHBOR | YANG leafref | sonic-bgp-neighbor.yang:124-126 |
| BGP_GLOBALS | YANG leafref + runtime ゲート | sonic-bgp-neighbor.yang:117-119, frrcfgd.py:2658 |
| BGP_PEER_GROUP_AF | 設定階層上の対 (共通 key_map) | frrcfgd.py:2111-2112 |
| ROUTE_MAP | FRR 名前空間 (route_map_in/out, default_rmap, unsuppress_map_name) | frrcfgd.py:1899-1906 |
| PREFIX_LIST | FRR 名前空間 (prefix_list_in/out) | frrcfgd.py:1918-1919 |
| AS-path access-list | FRR 名前空間 (filter_list_in/out) | frrcfgd.py:1914-1915 |
| DEVICE_METADATA.bgp_asn | テンプレ起動時条件 | bgpd.main.conf.j2:94-95 |

## 上流参照サマリ

| 参照元 | 機構 | ソース |
|---|---|---|
| frrcfgd BGPConfigDaemon | 購読 + key_map 展開 | frrcfgd.py:91, 2306 |
| frr-mgmt-framework running-config 同期 | 双方向 | frrcfgd.py:2137 |
| sonic-mgmt-common gNMI/REST | OpenConfig マッピング | sonic-mgmt-common (本ページ範囲外) |

## 走査コマンド (再現)

```bash
grep -n "BGP_NEIGHBOR_AF\|nbr_af_key_map\|peer_group_name\|local_asn\|route_map_in\|route_map_out\|prefix_list_in\|prefix_list_out\|default_rmap\|unsuppress_map\|filter_list" \
  .cache/sonic-sources/sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py
```
