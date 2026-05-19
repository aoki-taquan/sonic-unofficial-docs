# SUBNET_DECAP — Phase E ハードコード定数調査メモ

調査日: 2026-05-19
調査対象:
- `sonic-swss/orchagent/tunneldecaporch.h`
- `sonic-swss/orchagent/tunneldecaporch.cpp`
- `sonic-buildimage/dockers/docker-orchagent/ipinip.json.j2`

## 定数一覧

### tunneldecaporch.h — subnetDecapConfig 初期化定数

`SubnetDecapConfig` 構造体はヘッダファイルのメンバ初期化子でデフォルト値が固定される。

```cpp
SubnetDecapConfig subnetDecapConfig = {
    false,         // enable
    "",            // src_ip
    "",            // src_ip_v6
    "IPINIP_SUBNET",     // tunnel (IPv4)
    "IPINIP_SUBNET_V6"   // tunnel_v6 (IPv6)
};
```
(tunneldecaporch.h:97-103)

### tunneldecaporch.cpp — OVERLAY_RIF_DEFAULT_MTU

```cpp
#define OVERLAY_RIF_DEFAULT_MTU 9100
```
(tunneldecaporch.cpp:14)

Overlay RIF 作成時の `SAI_ROUTER_INTERFACE_ATTR_MTU` に使用される。CONFIG_DB からは設定不可。

### tunneldecaporch.cpp — トンネルタイプ固定値

`addDecapTunnel()` 内 (`tunneldecaporch.cpp:768`):
```cpp
attr.value.s32 = SAI_TUNNEL_TYPE_IPINIP;
```
tunnel_type は常に IPINIP 固定で CONFIG_DB の設定を参照しない。

### ipinip.json.j2 — ecn_mode / ttl_mode ハードコード

```json
"ecn_mode": "copy_from_outer",
"ttl_mode": "pipe"
```
これらは `ipinip.json.j2` 全テンプレートを通じて変更条件なしに固定。

### ipinip.json.j2 — dscp_mode プラットフォーム分岐

| 条件 | dscp_mode 値 |
|------|-------------|
| Broadcom T1 (is_broadcom_t1) | `"pipe"` |
| Broadcom 非T1 (is_broadcom) | `"uniform"` |
| その他 (非Broadcom) | `"pipe"` |

`is_broadcom_t1`: `ASIC_VENDOR` に "broadcom" が含まれ、かつ `DEVICE_METADATA.localhost.type` に "LeafRouter" が含まれる場合。

### ipinip.json.j2 — decap_dscp_to_tc_map 条件付き挿入

```jinja
{% if DSCP_TO_TC_MAP is defined and DSCP_TO_TC_MAP.AZURE is defined %}
    "decap_dscp_to_tc_map": "AZURE",
{% endif %}
```
`DSCP_TO_TC_MAP.AZURE` が存在する場合のみ付加。キー文字列 `"AZURE"` はハードコード。

### ipinip.json.j2 — term_type / subnet_type ハードコード

vlan decap term:
```json
"term_type": "MP2MP",
"subnet_type": "vlan"
```
vip decap term (routeorch/vnetorch 経由):
- `subnet_type: "vip"` は `routeorch.cpp` / `vnetorch.cpp` に直接リテラルで埋め込まれ。

### ipinip.json.j2 — loopback インタフェース名定数

```jinja
{% if ... sub_role == 'FrontEnd' or sub_role == 'BackEnd' %}
    {% set loopback_intf_names = ['Loopback0', 'Loopback4096'] %}
{% else %}
    {% set loopback_intf_names = ['Loopback0', 'Loopback2', 'Loopback3'] %}
{% endif %}
```
対象 loopback 名は FrontEnd/BackEnd の場合 `Loopback0`, `Loopback4096`、それ以外は `Loopback0`, `Loopback2`, `Loopback3` に固定。
