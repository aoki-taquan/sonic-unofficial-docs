# VLAN_SUB_INTERFACE — 暗黙参照調査メモ (Phase C)

対象ページ: `docs/reference/config-db/vlan-sub-interface.md`
調査日: 2026-05-16
調査ソース:
- `sonic-swss/cfgmgr/intfmgr.cpp`
- `sonic-swss/orchagent/intfsorch.cpp`

---

## 1. PORT / PORTCHANNEL への暗黙依存

### intfmgr.cpp (cfgmgr 側)

`isIntfStateOk(parentAlias)` (intfmgr.cpp:649-686) が STATE_DB を参照:

- `Vlan` プレフィックス → `m_stateVlanTable`
- `Vrf` / `mgmt` プレフィックス → `m_stateVrfTable`
- その他 → `m_statePortTable` (STATE_PORT_TABLE / STATE_LAG_TABLE)

sub-interface の場合、`parentAlias = subIf.parentIntf()` が `Ethernet0` や `PortChannel10` となり、`m_statePortTable` を参照する。親が Ready でない場合 `return false` でリトライ待ち (intfmgr.cpp:833-836)。

```cpp
// intfmgr.cpp:833
if (!isIntfStateOk(parentAlias.empty() ? alias : parentAlias))
{
    SWSS_LOG_DEBUG("Interface is not ready, skipping %s", alias.c_str());
    return false;
}
```

### intfsorch.cpp (orchagent 側)

`gPortsOrch->getPort(alias, port)` が失敗した場合、`isSubIntf` が true であれば `gPortsOrch->addSubPort(port, alias, vlan, adminUp, mtu)` を呼ぶ (intfsorch.cpp:905-914)。この関数は PortsOrch が管理する PORT / PORTCHANNEL オブジェクトを前提とする。

---

## 2. VRF への暗黙依存

### intfmgr.cpp

`vrf_name` が空でない場合、STATE_DB の `STATE_VRF_TABLE` を確認 (intfmgr.cpp:839-842):

```cpp
if (!vrf_name.empty() && !isIntfStateOk(vrf_name))
{
    SWSS_LOG_DEBUG("VRF is not ready, skipping %s", vrf_name.c_str());
    return false;
}
```

### intfsorch.cpp

`m_vrfOrch->isVRFexists(vrf_name)` で VRF オブジェクトの存在を確認 (intfsorch.cpp:826)。不在の場合は `task_need_retry`。

VRF バインドは SAI 属性 `SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID` に `m_vrfOrch->getVRFid()` で取得した OID を設定 (intfsorch.cpp:1184):

```cpp
attr.id = SAI_ROUTER_INTERFACE_ATTR_VIRTUAL_ROUTER_ID;
attr.value.oid = vrf_id;
```

---

## 3. VLAN との関係（独立経路）

VLAN_SUB_INTERFACE は bridge VLAN (VLAN テーブル) とは独立した経路で動作する:

- kernel: `ip link add <alias> link <parent> type vlan id <vid>` (intfmgr.cpp:344-378)
- SAI: `SAI_ROUTER_INTERFACE_TYPE_SUB_PORT` タイプの RIF (intfsorch.cpp:1224)

`isIntfStateOk()` において `Vlan` プレフィックスを持つ名前は `m_stateVlanTable` を参照するため、sub-interface の alias が `Vlan` で始まるケースは設計上存在しないが、注意が必要。

---

## 4. kernel sub-interface 連携フロー

```
CONFIG_DB[VLAN_SUB_INTERFACE]
  → intfmgrd::doIntfTask()
    → isIntfStateOk(parentAlias)  ← STATE_DB[PORT/LAG] 暗黙参照
    → isIntfStateOk(vrf_name)     ← STATE_DB[VRF] 暗黙参照
    → addHostSubIntf()            → ip link add <alias> link <parent> type vlan id <vid>
    → setHostSubIntfMtu()         → ip link set <alias> mtu <val>
    → setHostSubIntfAdminStatus() → ip link set <alias> up/down
  → APPL_DB[INTF_TABLE]
    → intfsorch::doTask()
      → gPortsOrch->addSubPort()  ← PORT/PORTCHANNEL オブジェクト暗黙参照
      → addRouterIntfs()
          SAI_ROUTER_INTERFACE_TYPE_SUB_PORT
          SAI_ROUTER_INTERFACE_ATTR_PORT_ID     = parent port OID
          SAI_ROUTER_INTERFACE_ATTR_OUTER_VLAN_ID = vlan_id
          SAI_ROUTER_INTERFACE_ATTR_ADMIN_V4_STATE
          SAI_ROUTER_INTERFACE_ATTR_ADMIN_V6_STATE
```

---

## 5. 発見事項サマリ

| 暗黙参照先 | 参照コード | 参照方法 | 未設定時の挙動 |
|-----------|-----------|---------|--------------|
| PORT / PORTCHANNEL | intfmgr.cpp:833, intfsorch.cpp:905-914 | STATE_DB + PortsOrch | retry 待ち |
| VRF | intfmgr.cpp:839, intfsorch.cpp:826 | STATE_DB + VRFOrch | retry 待ち |
| VLAN (bridge) | 独立経路 | 参照なし | 無関係 |
| kernel netdev | intfmgr.cpp:344-505 | ip link コマンド | runtime_error → retry |

---

出典:
- `sonic-swss/cfgmgr/intfmgr.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/cfgmgr/intfmgr.cpp>
- `sonic-swss/orchagent/intfsorch.cpp` <https://github.com/sonic-net/sonic-swss/blob/master/orchagent/intfsorch.cpp>
