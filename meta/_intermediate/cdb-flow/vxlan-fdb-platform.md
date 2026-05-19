# vxlan-fdb — Phase H Platform Differences

Source: `sonic-swss/orchagent/fdborch.cpp`, `sonic-swss/orchagent/vxlanorch.cpp`

## 1. ASIC 差: P2P (DIP) vs P2MP トンネルモード

`VXLAN_FDB_TABLE` エントリを処理する `FdbOrch::doTask()` および `FdbOrch::addFdbEntry()` の挙動は、ASIC が SAI_TUNNEL_PEER_MODE_P2P をサポートするかどうかで 2 パスに分岐する。

### 判定ロジック (VxlanTunnelOrch コンストラクタ, vxlanorch.cpp:1256-1274)

判定は `VxlanTunnelOrch` の起動時に一度だけ行われ、`is_dip_tunnel_supported` として保持される。

```cpp
status = sai_query_attribute_enum_values_capability(gSwitchId, SAI_OBJECT_TYPE_TUNNEL,
                                                    SAI_TUNNEL_ATTR_PEER_MODE, &values);
if (status != SAI_STATUS_SUCCESS)
{
    is_dip_tunnel_supported = true;  // P2P に fallback
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

- SAI クエリ失敗時: `is_dip_tunnel_supported = true` (P2P/DIP モード) に自動 fallback。
- `SAI_TUNNEL_PEER_MODE_P2P` が列挙値に含まれれば DIP tunnel サポートあり。
- P2MP のみが返された場合: `is_dip_tunnel_supported = false` → P2MP モードで動作。

## 2. VXLAN_FDB_TABLE 処理への影響 (fdborch.cpp:836-854)

```cpp
if (tunnel_orch->isDipTunnelsSupported())
{
    // P2P (DIP) モード: remote_vtep からリモート VTEP 専用トンネルポート名を解決
    if (!remote_ip.length())
    {
        it = consumer.m_toSync.erase(it);  // remote_vtep 空 → 即破棄
        continue;
    }
    port = tunnel_orch->getTunnelPortName(remote_ip);
}
else
{
    // P2MP モード: source VTEP (EVPN NVO) の共有トンネルポートを使用
    EvpnNvoOrch* evpn_nvo_orch = gDirectory.get<EvpnNvoOrch*>();
    VxlanTunnel* sip_tunnel = evpn_nvo_orch->getEVPNVtep();
    if (sip_tunnel == NULL)
    {
        it = consumer.m_toSync.erase(it);  // EVPN NVO 未設定 → 即破棄
        continue;
    }
    port = tunnel_orch->getTunnelPortName(sip_tunnel->getSrcIP().to_string(), true);
}
```

| 条件 | P2P (DIP サポートあり) | P2MP (DIP サポートなし) |
|------|----------------------|------------------------|
| 使用するトンネルポート | `remote_vtep` ごとの動的 DIP トンネルポート | SIP (source VTEP) 共有トンネルポート |
| 解決失敗時の挙動 | `remote_vtep` 空 → `m_toSync.erase` 即破棄 | EVPN NVO source VTEP = NULL → `m_toSync.erase` 即破棄 |
| 先行条件 | VXLAN_TUNNEL エントリ + VxlanTunnelOrch のトンネルポート作成済み | VXLAN_EVPN_NVO エントリ + EvpnNvoOrch の source VTEP 登録済み |

## 3. addFdbEntry での VLAN メンバーシップ確認差 (fdborch.cpp:1308-1313)

```cpp
/* Assign end point IP only in SIP tunnel scenario since Port + IP address
   needed to uniquely identify Vlan member */
if (!tunnel_orch->isDipTunnelsSupported())
{
    end_point_ip = fdbData.remote_ip;
}
/* Retry until port is member of vlan*/
if (!m_portsOrch->isVlanMember(vlan, port, end_point_ip))
{
    saved_fdb_entries[port_name].push_back({...});
    return true;
}
```

- **P2P (DIP) モード**: `end_point_ip` は空。VLAN メンバーシップの確認はポート名のみで行う。
- **P2MP モード**: `end_point_ip = fdbData.remote_ip` を渡す。ポート + remote IP の組み合わせで VLAN メンバーシップを確認する（同じ P2MP ポートに複数リモート IP が収容されるため、IP で区別が必要）。

## 4. まとめ表

| 差異ポイント | P2P (DIP サポートあり) | P2MP (DIP サポートなし) |
|---|---|---|
| SAI クエリ失敗時の動作 | P2P に自動 fallback | - |
| トンネルポート解決 | `remote_vtep` ごとの DIP トンネルポート | source VTEP の共有 P2MP ポート |
| 失敗時の先行依存 | `VXLAN_TUNNEL` + トンネルポート作成 | `VXLAN_EVPN_NVO` + source VTEP 登録 |
| VLAN メンバー確認引数 | ポート名のみ | ポート名 + remote IP |
| エントリ破棄条件 | `remote_vtep` 空 | EVPN NVO source VTEP = NULL |

## 5. SmartSwitch / DPU 差異

`fdborch.cpp` に SmartSwitch DPU 固有の VXLAN_FDB_TABLE 処理分岐はない。P2P / P2MP の分岐のみがプラットフォーム差として存在する。
