# VNET / VNET_ROUTE ハードコード定数 — スキャン証跡 (Phase E)

調査日: 2026-05-18

## スキャン対象ファイル

- `sonic-swss/orchagent/vnetorch.h`
- `sonic-swss/orchagent/vnetorch.cpp`
- `sonic-swss-common/common/schema.h`
- `sonic-buildimage/src/sonic-yang-models/yang-templates/sonic-types.yang.j2`
- `sonic-buildimage/src/sonic-yang-models/yang-models/sonic-vnet.yang`

## 発見した定数

### vnetorch.h マクロ (#define)

```
#define VNET_BITMAP_SIZE 32             // L20
#define VNET_TUNNEL_SIZE 40960          // L21
#define VNET_ROUTE_FULL_MASK_OFFSET_MAX 3000  // L22
#define VNET_NEIGHBOR_MAX 0xffff        // L23
#define VXLAN_ENCAP_TTL 128             // L24
#define VNET_BITMAP_RIF_MTU 9100        // L25
#define VNET_MONITORING_TYPE_CUSTOM "custom"      // L27
#define VNET_MONITORING_TYPE_CUSTOM_BFD "custom_bfd" // L28
```

### VXLAN_ENCAP_TTL 使用箇所

`vnetorch.cpp:513`:
```cpp
vrf_obj->getEncapMapId(), vrf_obj->getDecapMapId(), VXLAN_ENCAP_TTL)
```
VNET 作成時の `VxlanTunnelOrch::addTnlIntf()` 呼び出し引数として TTL=128 を渡す。CONFIG_DB フィールドでは変更不可。

### VNET_MONITORING_TYPE_* 使用箇所

`vnetorch.cpp:786`: monitoring が `custom` / `custom_bfd` でない場合、BFD 状態チェックをスキップして endpoint を常時 UP 扱いにする。

### vnid_type YANG 型 (sonic-types.yang.j2:321-328)

```yang
typedef vnid_type {
    type uint32 {
         range "1..16777215";
    }
    description "VXLAN Network Identifier";
}
```

VNI の有効範囲は 1〜16777215（24bit max）。0 は orchagent 内で "VNI 未設定" を意味するデフォルト値として扱われる。

### scope YANG pattern (sonic-vnet.yang:81-89)

```yang
leaf scope {
    type string {
        pattern "default" {
            error-message "Invalid VRF name";
        }
    }
}
```

`"default"` の 1 値のみ YANG バリデーターが許可する。

### schema.h テーブル名定数

APPL_DB/STATE_DB 側のテーブル名は schema.h で定義され、ConfigDB フィールドでは変更できない。

| 定数 | 値 |
|------|----|
| APP_VNET_TABLE_NAME | "VNET_TABLE" |
| APP_VNET_RT_TABLE_NAME | "VNET_ROUTE_TABLE" |
| APP_VNET_RT_TUNNEL_TABLE_NAME | "VNET_ROUTE_TUNNEL_TABLE" |
| APP_VNET_MONITOR_TABLE_NAME | "VNET_MONITOR_TABLE" |
| STATE_VNET_RT_TUNNEL_TABLE_NAME | "VNET_ROUTE_TUNNEL_TABLE" |
| STATE_VNET_MONITOR_TABLE_NAME | "VNET_MONITOR_TABLE" |
| CFG_VNET_RT_TABLE_NAME | "VNET_ROUTE" |

## 注記

- `VNET_BITMAP_SIZE`, `VNET_TUNNEL_SIZE`, `VNET_ROUTE_FULL_MASK_OFFSET_MAX`, `VNET_NEIGHBOR_MAX`, `VNET_BITMAP_RIF_MTU` は VRF モード (`VNET_EXEC_VRF`) では使用されず、bitmap モード (`VNET_EXEC_BRIDGE`) 専用。community master での bitmap モード使用は限定的。
- `VXLAN_ENCAP_TTL=128` は変更不可。TTL 調整が必要な場合は SAI 側の設定を使うしかない。
