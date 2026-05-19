# VXLAN_FDB_TABLE — プラットフォーム差 (Phase H) 解析メモ

対象: `APP_DB` の `VXLAN_FDB_TABLE` テーブル。
ソース: `sonic-swss/orchagent/fdborch.cpp`、`sonic-swss/orchagent/vxlanorch.cpp`。

## 1. DIP トンネルサポート有無による分岐

`VXLAN_FDB_TABLE` エントリの SAI プログラム方法は ASIC の VTEP トンネルモデルによって分岐する。`VxlanTunnelOrch::isDipTunnelsSupported()` がこの ASIC capability を保持する。

```cpp
// fdborch.cpp:836-854
if (tunnel_orch->isDipTunnelsSupported())
{
    // DIP モード: リモート VTEP ごとの個別トンネルポートを解決
    port = tunnel_orch->getTunnelPortName(remote_ip);
}
else
{
    // SIP モード: EVPN NVO の共有 source VTEP トンネルポートを使用
    VxlanTunnel* sip_tunnel = evpn_nvo_orch->getEVPNVtep();
    port = tunnel_orch->getTunnelPortName(sip_tunnel->getSrcIP().to_string(), true);
}
```

| 項目 | DIP トンネル対応 ASIC (P2P モード) | SIP トンネル ASIC (P2MP モード) |
|------|-----------------------------------|---------------------------------|
| トンネルポート | リモート VTEP IP ごとに個別ポート (`getTunnelPortName(remote_ip)`) | EVPN NVO の単一共有 SIP トンネルポート |
| `remote_vtep` 空時 | 即破棄 (`erase(it)`) | `VXLAN_EVPN_NVO` 未設定なら破棄 |
| VLAN メンバー判定 | `isVlanMember(vlan, port, "")` — port のみで判定 | `isVlanMember(vlan, port, remote_ip)` — port + end_point_ip で判定 |

## 2. SAI FDB エントリ属性の VXLAN 固有セット

VXLAN 由来エントリ (`FDB_ORIGIN_VXLAN_ADVERTIZED`) には、通常の PROVISIONED / LEARN MAC と異なる SAI 属性が設定される。

```cpp
// fdborch.cpp:1424-1428 — VXLAN は常に STATIC
if (fdbData.origin == FDB_ORIGIN_VXLAN_ADVERTIZED)
    attr.value.s32 = SAI_FDB_ENTRY_TYPE_STATIC;

// fdborch.cpp:1441-1445 — dynamic VXLAN は ALLOW_MAC_MOVE=true
if ((fdbData.origin == FDB_ORIGIN_VXLAN_ADVERTIZED) && (fdbData.type == "dynamic"))
    attr.id = SAI_FDB_ENTRY_ATTR_ALLOW_MAC_MOVE; attr.value.booldata = true;

// fdborch.cpp:1453-1470 — VXLAN は ENDPOINT_IP を必ず設定
if (fdbData.origin == FDB_ORIGIN_VXLAN_ADVERTIZED)
    attr.id = SAI_FDB_ENTRY_ATTR_ENDPOINT_IP;
    attr.value.ipaddr = remote_ip; // IPv4 または IPv6
```

| SAI 属性 | VXLAN (ADVERTIZED) | PROVISIONED (static) | PROVISIONED (dynamic) |
|----------|-------------------|----------------------|-----------------------|
| `SAI_FDB_ENTRY_ATTR_TYPE` | `STATIC` (常に) | `STATIC` / `DYNAMIC` (type 依存) | `DYNAMIC` |
| `SAI_FDB_ENTRY_ATTR_ALLOW_MAC_MOVE` | `true` (type=dynamic 時のみ) | 設定なし | 設定なし |
| `SAI_FDB_ENTRY_ATTR_ENDPOINT_IP` | 設定 (remote_vtep IP) | 設定なし | 設定なし |

`SAI_FDB_ENTRY_ATTR_ENDPOINT_IP` は ASIC が SIP/DIP トンネルどちらのモードでも設定される。これは VXLAN FDB エントリのリモート VTEP IP を SAI レベルで記録するためであり、ASIC ベンダー側で転送判断に利用される。

## 3. VLAN メンバー判定の end_point_ip 差

SIP トンネルモード (`isDipTunnelsSupported() == false`) では `addFdbEntry()` 内で `end_point_ip` に `remote_ip` をセットし、`isVlanMember(vlan, port, end_point_ip)` でポート+IPの組み合わせで VLAN メンバーシップを判定する (`fdborch.cpp:1308-1313`)。

```cpp
// fdborch.cpp:1308-1313
if (!tunnel_orch->isDipTunnelsSupported())
{
    end_point_ip = fdbData.remote_ip;
}
if (!m_portsOrch->isVlanMember(vlan, port, end_point_ip))
```

DIP トンネルモードでは `end_point_ip = ""` のまま、ポートのみで判定する。

## 4. 参考行番号

- `sonic-swss/orchagent/fdborch.cpp:836-854`: DIP / SIP トンネルモード分岐
- `sonic-swss/orchagent/fdborch.cpp:1308-1313`: `end_point_ip` SIP モード設定
- `sonic-swss/orchagent/fdborch.cpp:1424-1495`: VXLAN FDB SAI 属性設定 (TYPE / ALLOW_MAC_MOVE / ENDPOINT_IP)
- `sonic-swss/orchagent/vxlanorch.cpp:1256-1274`: `isDipTunnelsSupported()` — SAI query で P2P/P2MP ケーパビリティを判定
