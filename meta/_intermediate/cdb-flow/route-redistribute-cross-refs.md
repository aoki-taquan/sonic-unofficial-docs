# ROUTE_REDISTRIBUTE 暗黙参照分析 (Phase C)

対象テーブル: `ROUTE_REDISTRIBUTE`
ソース: `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`、`sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-common.yang`

## 前提

`docs/reference/config-db/route-redistribute.md` は未存在のため、`<!-- cross-refs -->` ブロックの適用は skip。
本ファイルに抽出結果を記録し、将来ページ作成時に転用する。

## 1. BGP_GLOBALS への暗黙参照

### 1-1. local_asn の暗黙依存

`frrcfgd.py` の `BGPConfigDaemon` は `ROUTE_REDISTRIBUTE` を VRF テーブルとして扱い、
キー先頭の `<vrf>` から VRF を取得した上で `__get_vrf_asn(vrf)` を呼んで `local_asn` を解決する。

`local_asn` は `BGP_GLOBALS|<vrf>` の `local_asn` フィールドから読み込まれ、`self.bgp_asn[vrf]` にキャッシュされている。
`local_asn` が未設定の場合は `ROUTE_REDISTRIBUTE` の処理をスキップし `LOG_DEBUG` を出す。

```python
# frrcfgd.py L2658-2662
local_asn = self.__get_vrf_asn(vrf)
if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
    syslog.syslog(syslog.LOG_DEBUG, 'ignore table {} update because local_asn for VRF {} was not configured'.format(table, vrf))
    continue
```

**暗黙参照経路**: `BGP_GLOBALS|<vrf>|local_asn` → `frrcfgd.__get_vrf_asn()` → `ROUTE_REDISTRIBUTE` 処理実行可否を決定

### 1-2. BGP_GLOBALS 設定変更時の ROUTE_REDISTRIBUTE 再適用

`BGP_GLOBALS|<vrf>|local_asn` が新規設定されると (`OP_DELETE` 以外)、`frrcfgd` は
`__apply_dep_vrf_table(vrf, 'ROUTE_REDISTRIBUTE')` を呼んで保留中の `ROUTE_REDISTRIBUTE` エントリを再適用する。

```python
# frrcfgd.py L2703-2704
self.bgp_asn[vrf] = dval.data
self.__apply_dep_vrf_table(vrf, 'ROUTE_REDISTRIBUTE')
```

これは `BGP_GLOBALS` が `ROUTE_REDISTRIBUTE` の前提条件であることを意味する。
`ROUTE_REDISTRIBUTE` エントリが先に到達しても、`BGP_GLOBALS.local_asn` が設定されるまで FRR への反映が保留される。

**暗黙参照経路**: `BGP_GLOBALS|<vrf>|local_asn` 設定イベント → `ROUTE_REDISTRIBUTE` 保留エントリ再適用

### 1-3. FRR コマンド生成時の BGP_GLOBALS 依存

`ROUTE_REDISTRIBUTE` 処理時に `frrcfgd` は以下のコマンドプレフィクスを構築する。

```python
# frrcfgd.py L3161-3163
cmd_prefix = ['configure terminal',
              'router bgp {} vrf {}'.format(local_asn, vrf),
              'address-family {} {}'.format(af, ip_type)]
```

`local_asn` は `BGP_GLOBALS|<vrf>|local_asn` の値であり、FRR の `router bgp <asn>` コンテキストを決定する。

## 2. ROUTE_MAP への暗黙参照

### 2-1. YANG leafref による ROUTE_MAP_SET 依存

`sonic-route-common.yang` の `route_map` フィールドは `ROUTE_MAP_SET` テーブルへの leafref として定義されている。

```yang
# sonic-route-common.yang L60-67
leaf-list route_map {
    type leafref {
        path "/rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name";
    }
    ordered-by user;
    max-elements 1;
    description "Router filter to apply while redistributing the routes from another protocol.";
}
```

`route_map` に指定された名前は `ROUTE_MAP_SET_LIST` に存在する必要がある。YANG バリデーションが leafref 整合性を保証する。

**暗黙参照経路**: `ROUTE_REDISTRIBUTE|<vrf>|<src>|<dst>|<af>|route_map` → `ROUTE_MAP_SET|<name>` (leafref)

### 2-2. frrcfgd による FRR redistribute コマンドへの展開

`frrcfgd` の `route_redist_key_map` は `route_map` フィールドを `:redist-route-map` プレースホルダに展開し、
`redistribute <proto> route-map <name>` コマンドとして FRR (bgpd) に投入する。

```python
# frrcfgd.py L1979-1980
route_redist_key_map = [(['protocol', '++metric', '+route_map'],
                         '{no:no-prefix}redistribute {} {:redist-metric} {:redist-route-map}', hdl_route_redist_set)]
```

`hdl_route_redist_set` は SET 前に `no redistribute <proto>` を先行発行し、冪等性を確保する。

### 2-3. ROUTE_MAP が bgpd デーモンにも配信

`frrcfgd` の daemon マッピングでは `ROUTE_MAP` も `ROUTE_REDISTRIBUTE` も `bgpd` を対象デーモンとして持つ。

```python
# frrcfgd.py L86,97
'ROUTE_MAP': ['zebra', 'bgpd', 'ospfd'],
'ROUTE_REDISTRIBUTE': ['bgpd'],
```

`ROUTE_MAP` テーブルの変更が bgpd に反映された後、`ROUTE_REDISTRIBUTE` の `route_map` 参照が有効になる。

## 3. VRF テーブルとしての依存関係

`ROUTE_REDISTRIBUTE` は `vrf_tables` セットに含まれており、VRF ベースの処理フローに従う。

```python
# frrcfgd.py L2136-2140
vrf_tables = {'BGP_GLOBALS', 'BGP_GLOBALS_AF',
              'BGP_NEIGHBOR', 'BGP_PEER_GROUP', 'BGP_NEIGHBOR_AF', 'BGP_PEER_GROUP_AF',
              'BGP_GLOBALS_LISTEN_PREFIX', 'ROUTE_REDISTRIBUTE',
              'BGP_GLOBALS_AF_AGGREGATE_ADDR', 'BGP_GLOBALS_AF_NETWORK',
              'BGP_GLOBALS_EVPN_RT', 'BGP_GLOBALS_EVPN_VNI', 'BGP_GLOBALS_EVPN_VNI_RT'}
```

`vrf_tables` エントリは `BGP_GLOBALS` で VRF の `local_asn` が設定されるまで処理を保留する機構を持つ。

## 4. src_protocol の ospf3 → ospf6 暗黙変換

`frrcfgd` は `ROUTE_REDISTRIBUTE` の key 処理時に `addr_family == 'ipv6'` かつ `src_protocol == 'ospf3'` の場合に
`src_protocol` を `ospf6` に変換する。これは FRR の CLI 表記との整合を取るための暗黙変換。

```python
# frrcfgd.py L3150-3152
src_proto, dst_proto, af = key.split('|')
if af == 'ipv6' and src_proto == 'ospf3':
    src_proto = 'ospf6'
```

## 5. 暗黙参照まとめ

| 参照元 | 参照先 | 種別 | 詳細 |
|--------|--------|------|------|
| `ROUTE_REDISTRIBUTE` 全エントリ | `BGP_GLOBALS|<vrf>|local_asn` | 実行前提 | local_asn 未設定時は処理スキップ（保留） |
| `ROUTE_REDISTRIBUTE` 全エントリ | `BGP_GLOBALS|<vrf>|local_asn` | 再適用トリガー | BGP_GLOBALS.local_asn 設定時に保留エントリを再投入 |
| `ROUTE_REDISTRIBUTE|…|route_map` | `ROUTE_MAP_SET|<name>` | YANG leafref | YANG バリデーション + FRR redistribute コマンドに展開 |
| `ROUTE_REDISTRIBUTE` | `bgpd` (FRR daemon) | ランタイム | `router bgp <asn> vrf <vrf>` + `address-family` コンテキストに展開 |

## 6. ソース参照

- `sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py` L97, L1979-1980, L2117, L2136-2140, L2658-2662, L2703-2704, L3149-3165
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-common.yang` L29-76
- SHA: `9ea932ec2e18f35e58268ec2e4456b1d4afd65cd` (sonic-buildimage)
