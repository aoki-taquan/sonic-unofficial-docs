# vxlan-tunnel — Phase H Platform Differences

Source: `sonic-swss/orchagent/vxlanorch.cpp`

## 1. EVPN 対応 ASIC 差: P2MP vs P2P トンネルモード

EVPN 動作において、ASIC が P2MP (Point-to-Multipoint) トンネルをサポートするかどうかで挙動が大きく分岐する。

### 判定ロジック (VxlanTunnelOrch コンストラクタ, vxlanorch.cpp:1245-1274)

```cpp
status = sai_query_attribute_enum_values_capability(gSwitchId, SAI_OBJECT_TYPE_TUNNEL,
                                                    SAI_TUNNEL_ATTR_PEER_MODE, &values);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_WARN("Unable to get supported tunnel peer modes. Defaulting to P2P");
    is_dip_tunnel_supported = true;  // P2P (DIP tunnel) モードに fallback
}
else
{
    is_dip_tunnel_supported = false;
    for (uint32_t idx = 0; idx < values.count; idx++)
    {
        if (values.list[idx] == SAI_TUNNEL_PEER_MODE_P2P)
        {
            is_dip_tunnel_supported = true;
            break;
        }
    }
}
```

- SAI クエリが失敗した場合（ドライバが未対応など）: `is_dip_tunnel_supported = true` (P2P/DIP モード) に自動 fallback。
- P2P (`SAI_TUNNEL_PEER_MODE_P2P`) が列挙されれば DIP tunnel サポートあり。
- P2MP のみが返された場合: `is_dip_tunnel_supported = false` → P2MP モードで動作。

## 2. DIP (Destination IP) トンネル差異

### DIP サポートあり (is_dip_tunnel_supported = true)

`addTunnelUser()` (vxlanorch.cpp:1701-1724):
- リモート VTEP ごとに個別の P2P DIP トンネルを動的生成する。
- `createDynamicDIPTunnel(remote_vtep, usr)` → SAI `create_tunnel()` with `SAI_TUNNEL_PEER_MODE_P2P` + `SAI_TUNNEL_ATTR_ENCAP_DST_IP`
- トンネルポートとブリッジポートを VTEP ごとに作成。
- FDB エントリは DIP トンネルポート単位で管理。

### DIP サポートなし (is_dip_tunnel_supported = false = P2MP モード)

`addTunnelUser()` (vxlanorch.cpp:1701-1704):
- DIP トンネルを作成しない。リモート VTEP の IP 参照カウントのみ更新する。
- 単一の P2MP SIP トンネルブリッジポートを使い回す。
- FDB/MAC フラッディングは P2MP トンネルポート経由で IMET ルートの L2MC グループメンバーとして実現 (vxlanorch.cpp:1994-1996)。

`deleteTunnelPort()` (vxlanorch.cpp:1807-1822):
```cpp
/* P2MP scenario where P2MP tunnel port is used for FDB learning */
if (!isDipTunnelsSupported())
{
    if (vtep_ptr->del_tnl_hw_pending && !vtep_ptr->isTunnelReferenced())
    {
        ret = gPortsOrch->removeBridgePort(tunnelPort);
        ...
        vtep_ptr->deletePendingSIPTunnel();
    }
    return;
}
```

## 3. SIP (Source IP) トンネル遅延削除

EVPN シナリオでは SIP トンネル HW の削除が DIP トンネル参照カウントに依存する。

`deletePendingSIPTunnel()` (vxlanorch.cpp:952-965):
```cpp
bool dip_tunnels_used = tunnel_orch->isDipTunnelsSupported();
if ((!dip_tunnels_used || getDipTunnelCnt() == 0) && del_tnl_hw_pending)
{
    SWSS_LOG_INFO("Removing SIP Tunnel HW which is pending");
    ...
    del_tnl_hw_pending = false;
}
```
- DIP トンネルが残存している間は SIP トンネル HW を削除しない。
- P2MP モード (`dip_tunnels_used = false`) では DIP カウントが常に 0 のため即時削除可能。

## 4. P2P vs P2MP の SAI トンネル作成差 (create_tunnel, vxlanorch.cpp:356-370)

```cpp
if ((dst_ip != nullptr) && p2p)
{
    attr.value.s32 = SAI_TUNNEL_PEER_MODE_P2P;
    // SAI_TUNNEL_ATTR_ENCAP_DST_IP を追加
}
else
{
    attr.value.s32 = SAI_TUNNEL_PEER_MODE_P2MP;
    // DST_IP 属性なし
}
```

EVPN 動的 DIP トンネル (`TNL_CREATION_SRC_EVPN`, dst_ip が非ゼロ): `p2p = true` → P2P モードで SAI 作成。
静的トンネル (`TNL_CREATION_SRC_CLI`, dst_ip が非ゼロ): `p2p = false` → P2MP モードで SAI 作成（CLI 経由では常に P2MP）。

## 5. SmartSwitch / DPU 差異

`vxlanorch.cpp` に SmartSwitch DPU 固有の分岐コードは存在しない。DPU 側の VXLAN トンネル処理は別のオーバーレイスタックが担当する可能性があり、現在の実装では NPU 通常モードのみが対象となっている。

## まとめ表

| 差異ポイント | P2P (DIP サポートあり) | P2MP (DIP サポートなし) |
|---|---|---|
| SAI クエリ失敗時 | fallback で P2P | - |
| リモート VTEP ごとのトンネル | 動的生成 | 生成しない |
| SIP トンネル削除タイミング | DIP カウント 0 待ち | 即時可能 |
| ブリッジポート共有 | VTEP ごと個別 | SIP 共有 |
| FDB/flooding | DIP トンネルポート経由 | P2MP + L2MC グループ経由 |
| EVPN DIP トンネル SAI mode | `SAI_TUNNEL_PEER_MODE_P2P` | 使用しない |
| CLI 静的 tunnel SAI mode | `SAI_TUNNEL_PEER_MODE_P2MP` | 同左 |
| SmartSwitch DPU 差 | コード分岐なし | 同左 |
