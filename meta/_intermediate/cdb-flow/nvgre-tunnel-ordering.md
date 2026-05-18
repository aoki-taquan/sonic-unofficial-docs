# nvgre-tunnel 書込み順依存エビデンス (Phase B)

## 調査ソース

- `sonic-swss/orchagent/nvgreorch.cpp`
- `sonic-swss/orchagent/orchdaemon.cpp`

## 主な発見

### allPortsReady ガード

`NvgreTunnelOrch::addOperation()` (L350) および `NvgreTunnelMapOrch::addOperation()` (L464) のいずれにも `gPortsOrch->allPortsReady()` チェックは存在しない。orchdaemon 起動後すぐに処理可能。

### NVGRE_TUNNEL → NVGRE_TUNNEL_MAP 先行必須

`NvgreTunnelMapOrch::addOperation()` L471:
```cpp
if (!tunnel_orch->isTunnelExists(tunnel_name))
{
    SWSS_LOG_WARN("NVGRE tunnel '%s' doesn't exist", tunnel_name.c_str());
    return true;  // エントリ破棄、retry なし
}
```
`return true` は Orch2 フレームワークで「正常完了」扱いになるため、MAP エントリは **retry キューに戻らず永続的に破棄**される。

### VLAN 先行必須（MAP 登録時）

`addOperation()` L489:
```cpp
if (!gPortsOrch->getVlanByVlanId(vlan_id, port))
{
    SWSS_LOG_WARN("VLAN ID doesn't exist: %d", vlan_id);
    return true;  // エントリ破棄、retry なし
}
```

### orchdaemon 登録順 (orchdaemon.cpp:361-364)

```cpp
NvgreTunnelOrch *nvgre_tunnel_orch = new NvgreTunnelOrch(...);
gDirectory.set(nvgre_tunnel_orch);
NvgreTunnelMapOrch *nvgre_tunnel_map_orch = new NvgreTunnelMapOrch(...);
gDirectory.set(nvgre_tunnel_map_orch);
```
NvgreTunnelOrch が先に初期化される。起動直後から `gDirectory.get<NvgreTunnelOrch*>()` で参照可能。

## 結論

- `NVGRE_TUNNEL` SET → `NVGRE_TUNNEL_MAP` SET の順序は**必須**（逆順だと MAP 永続破棄）
- `VLAN` 登録完了 → `NVGRE_TUNNEL_MAP` SET の順序も**必須**（逆順だと MAP 永続破棄）
- DEL は MAP → TUNNEL の順を**推奨**（逆順でも orchagent は継続するが SAI 孤立リスク）
