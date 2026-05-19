# tunnel-port Phase H — プラットフォーム差異スキャンノート

## 調査対象

- `orchagent/vxlanorch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `orchagent/vxlanorch.h` (同 ref)
- `orchagent/orchdaemon.cpp` (同 ref)

## isDipTunnelsSupported() の決定ロジック

`VxlanTunnelOrch::VxlanTunnelOrch()` (vxlanorch.cpp:1245–1275) が起動時に
`sai_query_attribute_enum_values_capability(gSwitchId, SAI_OBJECT_TYPE_TUNNEL,
SAI_TUNNEL_ATTR_PEER_MODE, &values)` を呼ぶ。

- 戻り値 != SAI_STATUS_SUCCESS → `is_dip_tunnel_supported = true` (デフォルト P2P 扱い) [vxlanorch.cpp:1261]
- 成功かつ `SAI_TUNNEL_PEER_MODE_P2P` が values に含まれる → `true` [vxlanorch.cpp:1268–1270]
- 成功かつ P2P が含まれない → `false` [vxlanorch.cpp:1265]

## モード別の処理分岐一覧

| 箇所 | DIP true | DIP false |
|------|----------|-----------|
| `addTunnelUser()` vxlanorch.cpp:1701 | 処理継続 | `return false` 即時 |
| `delTunnelUser()` vxlanorch.cpp:1747 | 処理継続 | Local SRC VTEP ポートを削除対象とする |
| `deleteTunnelPort()` vxlanorch.cpp:1808 | DIP ポートを削除 | Local VTEP ポートを削除 |
| `VxlanTunnelMapOrch::addOperation()` vxlanorch.cpp:2075 | getTunnelPort スキップ | Port_SRC_VTEP_* 生成 |
| orchdaemon Orch 登録 orchdaemon.cpp:577–584 | EvpnRemoteVnip2pOrch | EvpnRemoteVnip2mpOrch |

## orchdaemon での Orch 分岐

```cpp
if (vxlan_tunnel_orch->isDipTunnelsSupported())
{
    EvpnRemoteVnip2pOrch* evpn_remote_vni_orch = new EvpnRemoteVnip2pOrch(...);
    ...
}
else
{
    EvpnRemoteVnip2mpOrch* evpn_remote_vni_orch = new EvpnRemoteVnip2mpOrch(...);
    ...
}
```
(orchdaemon.cpp:577–587)

## 結論

プラットフォームの SAI 実装が `SAI_TUNNEL_PEER_MODE_P2P` を提供するかどうかが、
トンネルポートの生成モデル (P2P DIP / P2MP SRC VTEP 共用) を完全に決定する。
この差異は CONFIG_DB から制御不可能であり、SAI ドライバのケイパビリティに依存する。
