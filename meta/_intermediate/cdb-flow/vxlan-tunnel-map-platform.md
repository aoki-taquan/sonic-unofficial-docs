# vxlan-tunnel-map — Phase H プラットフォーム差

Source: `sonic-swss/orchagent/vxlanorch.cpp`, `sonic-swss/orchagent/vxlanorch.h`

## 1. ASIC 差: P2MP vs P2P トンネルモード (SAI ケーパビリティクエリ)

`VXLAN_TUNNEL_MAP` の `addOperation()` / `delOperation()` における SAI オブジェクト生成・削除パスは、`VxlanTunnelOrch` 初期化時に実行される SAI ケーパビリティクエリ結果に依存する。

### 判定ロジック (vxlanorch.cpp:1256-1274)

```cpp
status = sai_query_attribute_enum_values_capability(gSwitchId, SAI_OBJECT_TYPE_TUNNEL,
                                                    SAI_TUNNEL_ATTR_PEER_MODE, &values);
if (status != SAI_STATUS_SUCCESS)
{
    SWSS_LOG_WARN("Unable to get supported tunnel peer modes. Defaulting to P2P");
    is_dip_tunnel_supported = true;  // P2P モードへ fallback
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

- SAI クエリ失敗時（未対応ドライバ等）: `is_dip_tunnel_supported = true`（P2P モード）に自動 fallback。
- `SAI_TUNNEL_PEER_MODE_P2P` が列挙されれば DIP トンネルサポートあり。
- P2MP のみが返された場合: `is_dip_tunnel_supported = false` → P2MP モードで動作。

## 2. VXLAN_TUNNEL_MAP addOperation() でのプラットフォーム分岐

初回 MAP エントリ追加（`!tunnel_obj->isActive()`）時に ASIC の P2P サポート有無で SAI ポートオブジェクトの生成が分岐する (vxlanorch.cpp:2075-2086):

### P2P サポートなし (isDipTunnelsSupported() == false = P2MP モード)

初回 MAP 追加時に SIP トンネルポートとブリッジポートをこの時点で即時生成する:

```cpp
if (!tunnel_orch->isDipTunnelsSupported())
{
    Port tunPort;
    auto src_vtep = tunnel_obj->getSrcIP().to_string();
    if (!tunnel_orch->getTunnelPort(src_vtep, tunPort, true))
    {
        auto port_tunnel_name = tunnel_orch->getTunnelPortName(src_vtep, true);
        gPortsOrch->addTunnel(port_tunnel_name, tunnel_obj->getTunnelId(), false);
        gPortsOrch->getPort(port_tunnel_name,tunPort);
        gPortsOrch->addBridgePort(tunPort);
    }
}
```

- P2MP ASIC では MAP 追加が SIP ブリッジポートの実体化トリガになる。
- P2P ASIC ではこの処理はスキップ（EVPN DIP トンネルが別途ブリッジポートを管理）。

### P2P サポートあり (isDipTunnelsSupported() == true)

`addOperation()` では上記ブランチを通らない。EVPN `addTunnelUser()` が後から DIP トンネルごとにブリッジポートを生成する。

## 3. VXLAN_TUNNEL_MAP delOperation() でのプラットフォーム分岐

最後の MAP エントリ削除時（`vlan_vrf_vni_count == 0`）に SIP トンネル HW 削除パスが分岐する (vxlanorch.cpp:2191-2226):

### P2MP モード (isDipTunnelsSupported() == false)

`!isTunnelReferenced()` を確認し、参照がなければブリッジポートとトンネルポートを即時削除する:

```cpp
if (!tunnel_orch->isDipTunnelsSupported())
{
    ret = gPortsOrch->getPort(port_tunnel_name, tunnelPort);
    ...
    ret = gPortsOrch->removeBridgePort(tunnelPort);
    ...
    gPortsOrch->removeTunnel(tunnelPort);
}
tunnel_obj->deleteTunnelHw(mapper_list, TUNNEL_MAP_USE_DEDICATED_ENCAP_DECAP);
```

### P2P モード (isDipTunnelsSupported() == true)

ブリッジポート即時削除はスキップ。DIP トンネルが残存していれば `del_tnl_hw_pending = true` を設定して遅延削除する:

```cpp
if (tunnel_orch->isDipTunnelsSupported())
{
    SWSS_LOG_WARN("Postponing the SIP Tunnel HW deletion DIP Tunnel count = %d", ...);
}
```

## 4. SmartSwitch / DPU 差異

`vxlanorch.cpp` に SmartSwitch DPU 固有の分岐コードは存在しない。DPU 側の VXLAN 処理は別のオーバーレイスタックが担当する可能性があるが、現在の orchagent 実装では NPU 通常モードのみが対象。

## まとめ表

| 差異ポイント | P2P モード (DIP サポートあり) | P2MP モード (DIP サポートなし) |
|---|---|---|
| SAI クエリ失敗時 | fallback で P2P | — |
| MAP 初回追加時ブリッジポート生成 | スキップ（EVPN が後で管理） | addOperation() で即時生成 |
| MAP 最終削除時ブリッジポート削除 | 遅延（DIP カウント待ち） | 参照なければ即時削除 |
| `del_tnl_hw_pending` 設定タイミング | DIP トンネル残存時 | リモート参照残存時 |
| SmartSwitch DPU | コード分岐なし | 同左 |
