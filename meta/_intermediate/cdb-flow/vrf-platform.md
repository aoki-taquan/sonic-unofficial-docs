# VRF テーブル — プラットフォーム差 (Phase H)

調査日: 2026-05-15
調査対象:
- sonic-swss/cfgmgr/vrfmgr.cpp
- sonic-swss/cfgmgr/vrfmgrd.cpp
- sonic-swss/orchagent/vrforch.cpp
- sonic-swss/orchagent/vrforch.h
- sonic-swss/orchagent/main.cpp
- sonic-sairedis/vslib/vpp/SwitchVpp.cpp, SwitchVppRif.cpp, IpVrfInfo.h
- sonic-sairedis/vslib/SwitchStateBase.cpp
- sonic-host-services/scripts/hostcfgd

---

## 検出したプラットフォーム差

### 1. mgmt VRF — プラットフォーム/デプロイメント形態依存の初期化分岐

**検出箇所**: `vrfmgr.cpp:176-183`

```cpp
if (vrfName == MGMT_VRF)
{
    // Mgmt VRF is initialised as part of hostcfgd,
    // just return the reserved table_id for mgmt VRF from here.
    uint32_t table_id = MGMT_VRF_TABLE_ID;
    m_vrfTableMap.emplace(vrfName, table_id);
    return true;
}
```

- `mgmt` VRF は通常の `ip link add <name> type vrf table <id>` を実行しない
- `hostcfgd` が `systemctl restart interfaces-config` 経由で Linux の管理 VRF を先に初期化している前提
- 固定テーブル ID `6000` を使用（通常プール 1001–5096 外）
- **hostcfgd の管理 VRF 初期化はプラットフォームに依存しない**が、管理インタフェース (`eth0`) が存在するかどうかはハードウェア形態（1U スイッチ vs SmartSwitch DPU 等）に依存する

### 2. Linux ルーティングテーブル ID プール — カーネルバージョン・設定依存

**検出箇所**: `vrfmgr.cpp:12-15`

```cpp
#define VRF_TABLE_START 1001
#define VRF_TABLE_END   5097
#define TABLE_LOCAL_PREF 1001
#define MGMT_VRF_TABLE_ID 6000
```

- ルーティングテーブル ID はカーネル VRF のリソースであり、ハードウェア ASIC とは無関係
- ただし一部の組み込み Linux カーネル（Barefoot / Intel Tofino 等）では `/proc/net/rt_tables` の最大エントリ数がデフォルトから削減されていることがある
- **VS (virtual switch) プラットフォーム**: ASIC 不在のため SAI VR 作成は常に成功するが、Linux ルーティングテーブル ID の取得は同じコードパスを経由する

### 3. SAI Virtual Router 属性サポート — ASIC ベンダー依存

**検出箇所**: `vrforch.cpp:38-84`, `vrforch.h:26-36`

vrforch が APP_DB 経由で設定可能な SAI 属性は以下のとおりだが、CONFIG_DB の `VRF` テーブルフィールドには存在せず、通常は VNET テーブル経由でのみ使用される内部フィールド:

| SAI 属性 | YANG/CONFIG_DB | 利用可能性 |
|---------|---------------|-----------|
| `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V4_STATE` | なし（`v4` フィールド、VNET 経由） | ほぼ全 ASIC |
| `SAI_VIRTUAL_ROUTER_ATTR_ADMIN_V6_STATE` | なし（`v6` フィールド、VNET 経由） | ほぼ全 ASIC |
| `SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS` | なし（`src_mac` フィールド、VNET 経由） | Broadcom/Mellanox でサポート。Barefoot (Tofino) など一部 ASIC では未サポートの場合あり |
| `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION` | なし（`ttl_action`、VNET 経由） | ベンダー依存。Mellanox はサポート |
| `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION` | なし（`ip_opt_action`、VNET 経由） | ベンダー依存 |
| `SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION` | なし（`l3_mc_action`、VNET 経由） | ベンダー依存 |

- `fallback` フィールドは YANG に存在するが orchagent に処理ハンドラが実装されておらず、**全 ASIC で silent drop** される（`vrforch.cpp:80-82`）
- SAI capability query（`sai_query_attribute_capability`）は VRF 属性について実施されていない。unsupported 属性を set した場合の挙動はベンダー SAI の実装に依存

### 4. VS (Virtual Switch) / VPP SAI — Linux VRF との二重管理

**検出箇所**: `sonic-sairedis/vslib/vpp/SwitchVpp.cpp:1183-1195`, `SwitchVppRif.cpp:1390-1460`, `IpVrfInfo.h`

VPP（Vector Packet Processing）SAI バックエンドを使う VS プラットフォームでは、SAI VR の create/remove が VPP API (`ip_vrf_add` / `ip_vrf_del`) を呼ぶ追加処理が行われる:

```cpp
// SwitchVppRif.cpp:1403-1414
if (!vrf_id || ip_vrf_add(vrf_id, vrf_name.c_str(), false) == 0) {
    SWSS_LOG_NOTICE("VRF(%s) with id %u created in VS", ...);
    vrf_objMap[objectId] = std::make_shared<IpVrfInfo>(objectId, vrf_id, vrf_name, false);
    // ECMP hash 設定も実施
    int ret = vpp_ip_flow_hash_set(vrf_id, hash_mask, AF_INET);
}
```

- 通常 SAI では VR 作成は純粋な ASIC 操作だが、VS/VPP では Linux + VPP の両方で VRF を作成する
- `vpp_get_vrf_id()` は `ip link show dev <linux_ifname>` から Linux ルーティングテーブル ID を取得する (`SwitchVppRif.cpp:1455` コメント)
- `vrf_id = 0` の場合（デフォルト VRF）は `ip_vrf_add` を呼ばずスキップ

**標準 VS (SwitchStateBase)** では VR 作成は SAI OID 管理のみで、Linux へのフォールスルーなし:
- `SwitchStateBase.cpp:1533`: `create(SAI_OBJECT_TYPE_VIRTUAL_ROUTER, ...)` → OID 割り当てのみ

### 5. EVPN L3 VNI — VTEP 設定の有無による動作差

**検出箇所**: `vrforch.cpp:225-238`

```cpp
auto evpn_vtep_ptr = evpn_orch->getEVPNVtep();
if(!evpn_vtep_ptr)
{
    SWSS_LOG_NOTICE("updateVrfVNIMap unable to find EVPN VTEP");
    return false;
}
```

- `VRF.vni` 設定時、EVPN NVO（VTEP）が設定されていない環境では VNI マッピングが常に失敗して CONFIG_DB エントリが破棄される
- EVPN をサポートするプラットフォーム（Broadcom TD3/TH2, Mellanox SN2700 以降等）と非サポートプラットフォーム（一部 Barefoot, Marvell Prestera 等）では `VRF.vni` の有効性が異なる
- **実質的に VXLAN EVPN が設定・動作している環境以外では `vni` フィールドは無効**

---

## 結論

| 差の性質 | 影響範囲 | 実装 ASIC |
|---------|---------|----------|
| mgmt VRF 初期化経路 (hostcfgd 前提) | デプロイメント形態依存 | 管理 IF 有無によらず共通コード |
| Linux ルーティングテーブル ID プール上限 (4096) | Linux カーネル設定依存 | 全プラットフォーム共通定数 |
| VNET 経由 SAI VR 属性 (`src_mac`, `ttl_action` 等) | ASIC ベンダー依存 | Broadcom/Mellanox で主にサポート |
| `fallback` フィールド — 全 ASIC で silent drop | 全プラットフォーム共通 | orchagent にハンドラなし |
| VS/VPP SAI — VPP API で Linux+VPP 二重管理 | VS (VPP) プラットフォームのみ | `SwitchVpp.cpp` 経由 |
| EVPN L3 VNI — VTEP 未設定環境では `vni` 無効 | EVPN 非サポート環境 | EVPN VTEP 設定必須 |
