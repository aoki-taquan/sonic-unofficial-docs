# ROUTE_REDISTRIBUTE — Phase C 暗黙参照スキャンノート

対象テーブル: `ROUTE_REDISTRIBUTE`
Consumer: `frrcfgd.BGPConfigDaemon` (`sonic-buildimage/src/sonic-frr-mgmt-framework/frrcfgd/frrcfgd.py`)
YANG: `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-route-common.yang`
スキャン範囲: sonic-route-common.yang 全行、frrcfgd.py L2136-2145 (vrf_tables), L2518-2520 (__vrf_based_table), L2530-2545 (__apply_dep_vrf_table), L2658-2661 (local_asn gate), L2703-2704 (BGP_GLOBALS re-apply), L3149-3180 (ROUTE_REDISTRIBUTE handler)

---

## 検出した参照関係

### 1. VRF — YANG leafref（vrf_name が non-default の場合）

`sonic-route-common.yang` L38-41:

```yang
type leafref {
    path "/vrf:sonic-vrf/vrf:VRF/vrf:VRF_LIST/vrf:name";
}
```

`vrf_name` フィールドの union 型の一方に VRF テーブルへの leafref が定義されている。`"default"` は別パターンで許容されるが、それ以外の VRF 名は `VRF` テーブルに対応するエントリが存在していなければ config-load 時に YANG バリデーションで reject される。

### 2. ROUTE_MAP_SET — YANG leafref（route_map フィールド）

`sonic-route-common.yang` L61-62:

```yang
type leafref {
    path "/rmap:sonic-route-map/rmap:ROUTE_MAP_SET/rmap:ROUTE_MAP_SET_LIST/rmap:name";
}
```

`route_map` leaf-list の型が ROUTE_MAP_SET への leafref として定義されている。存在しない ROUTE_MAP 名を指定すると config-load で reject される。なお `frrcfgd` はランタイム処理時に ROUTE_MAP の存在を再チェックしないため（`+route_map` プレフィクスは単純に absent 時スキップ）、leafref バリデーションのみが保護機構。

### 3. BGP_GLOBALS — runtime gate（local_asn ゲート）

`frrcfgd.py` L2658-2661:

```python
local_asn = self.__get_vrf_asn(vrf)
if local_asn is None and (table != 'BGP_GLOBALS' or 'local_asn' not in data):
    syslog.syslog(LOG_DEBUG, 'ignore table {} update...')
    continue
```

ROUTE_REDISTRIBUTE は `vrf_tables`（L2136-2140）に含まれるため、全イベント処理の先頭で VRF の `local_asn` 解決が実行される。YANG leafref としての定義はなく純粋なランタイム依存。

### 4. frrcfgd — 購読元（上流参照）

`frrcfgd.py` L2316: `('ROUTE_REDISTRIBUTE', self.bgp_table_handler_common)` として subscribe 登録。
`frrcfgd.py` L2703-2704: `BGP_GLOBALS.local_asn` SET 後に `__apply_dep_vrf_table(vrf, 'ROUTE_REDISTRIBUTE')` で自動再適用。

---

## 参照関係サマリ

| 方向 | 参照元 | 参照先 | 機構 | 違反時の挙動 |
|---|---|---|---|---|
| outgoing | `ROUTE_REDISTRIBUTE.vrf_name` | `VRF.name` | YANG leafref | config-load reject |
| outgoing | `ROUTE_REDISTRIBUTE.route_map` | `ROUTE_MAP_SET.name` | YANG leafref | config-load reject |
| outgoing (runtime) | `ROUTE_REDISTRIBUTE` 処理 | `BGP_GLOBALS.local_asn` | frrcfgd runtime gate | silent drop |
| incoming | `frrcfgd BGPConfigDaemon` | `ROUTE_REDISTRIBUTE` | subscribe | vtysh コマンドへ変換 |
| incoming (auto) | `frrcfgd __apply_dep_vrf_table` | `ROUTE_REDISTRIBUTE` | BGP_GLOBALS 後の再適用 | 自動 FRR 反映 |
