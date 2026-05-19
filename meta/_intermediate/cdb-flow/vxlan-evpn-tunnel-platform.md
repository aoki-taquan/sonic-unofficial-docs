# vxlan-evpn-tunnel — Phase H: プラットフォーム差異

## 調査対象ソース

- `sonic-net/sonic-swss` (master)
- `orchagent/vxlanorch.cpp` — `VxlanTunnelOrch::isDipTunnelsSupported()` (L1244-1274)、`addTunnelUser()` (L1679-1747)、`createDynamicDIPTunnel()` (L1151-1184)、`createTunnelHw()` (L297-420)
- `orchagent/vxlanorch.h` — `VxlanTunnelTTLMode` enum、`EVPN_TUNNEL_NAME_PREFIX`、`DEFAULT_TUNNEL_ENCAP_TTL` 等
- `orchagent/orchdaemon.cpp` — `isDipTunnelsSupported()` による Orch 分岐 (L577-587)

## 主要判定: isDipTunnelsSupported()

`vxlanorch.cpp:1244-1274` の `VxlanTunnelOrch::isDipTunnelsSupported()`:

```
sai_query_attribute_enum_values_capability(
    gSwitchId,
    SAI_OBJECT_TYPE_TUNNEL,
    SAI_TUNNEL_ATTR_PEER_MODE,
    &values
)
```

- SAI クエリ失敗 → `is_dip_tunnel_supported = true`（warn + fallback）
- P2P が列挙値に含まれる → `true`
- P2P が列挙値に含まれない → `false`

## Orch 分岐 (orchdaemon.cpp:577-587)

| `isDipTunnelsSupported()` | 起動 Orch |
|--------------------------|----------|
| `true` | `EvpnRemoteVnip2pOrch` |
| `false` | `EvpnRemoteVnip2mpOrch` |

## P2P モード動作 (主要プラットフォーム)

- `createDynamicDIPTunnel()` でリモート VTEP ごとに SAI P2P トンネル生成
- SAI: `SAI_TUNNEL_PEER_MODE_P2P` + `SAI_TUNNEL_ATTR_ENCAP_DST_IP`
- per-VTEP トンネルポート (`Port_EVPN_<remote_vtep_ip>`) を VLAN flood domain に参加
- `del_tnl_hw_pending` による SIP 遅延削除あり

## P2MP 縮退モード動作

- `addTunnelUser()` は DIP トンネル作成をスキップ (`vxlanorch.cpp:1701-1704`)
- リモート VTEP の IP 参照カウントのみ更新して `return true`
- SIP トンネルに P2MP ブリッジポートを使用 (`addBridgePort()`)
- DIP カウントが常に 0 のため SIP 即時削除可能

## TTL プラットフォーム依存

EVPN DIP トンネル生成時は `ttl_mode = VxlanTunnelTTLMode::NOT_SET` (コンストラクタのデフォルト引数)。
`createTunnelHw()` 内で `NOT_SET` の場合 `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` を属性リストに追加しない (`vxlanorch.cpp:372-383`)。
→ ASIC ベンダー SAI のデフォルト TTL モード（通常 PIPE）が適用される。

## WarmBoot

WarmBoot 後の orchagent 再起動時に SAI 照会が再実行される。P2P/P2MP モードは再判定される。
STATE_DB への重複書込みは `vxlanorch.cpp:1925-1948` のガードでスキップ。
