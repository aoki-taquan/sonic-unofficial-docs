# EVPN DIP Tunnel (VXLAN_TUNNEL の EVPN 動的生成) — Phase A: Implicit Defaults & Code-derived Behaviors

## 対象オブジェクト

CONFIG_DB に `VXLAN_EVPN_TUNNEL` テーブルは存在しない。本ページで扱う「EVPN DIP トンネル」は
`orchagent` の `VxlanTunnel::createDynamicDIPTunnel()` が BGP EVPN でリモート VTEP を学習した際に
**ランタイムで動的生成**する per-remote-VTEP P2P トンネルである。

- トンネル名: `EVPN_<remote_vtep_ip>` (prefix `EVPN_TUNNEL_NAME_PREFIX`)
- トンネルポート名: `Port_EVPN_<remote_vtep_ip>` (prefix `EVPN_TUNNEL_PORT_PREFIX`)
- 生成元: `vxlanorch.cpp:1160` — `new VxlanTunnel(tunnel_name, src_ip_, dipaddr, TNL_CREATION_SRC_EVPN)`

これは CONFIG_DB 由来 (`TNL_CREATION_SRC_CLI`) の VXLAN_TUNNEL エントリとは別物。

---

## コード由来の暗黙デフォルト

### 1. `decap_ttl_mode` — `VxlanTunnelTTLMode::NOT_SET`

**根拠**: `vxlanorch.h:152`
```cpp
VxlanTunnel(string name, IpAddress srcIp, IpAddress dstIp, tunnel_creation_src_t src,
            VxlanTunnelTTLMode ttl_mode = VxlanTunnelTTLMode::NOT_SET);
```

EVPN DIP トンネル生成時 (`vxlanorch.cpp:1160`) は `ttl_mode` 引数を渡さないため、デフォルト値
`VxlanTunnelTTLMode::NOT_SET` が使用される。

**根拠**: `vxlanorch.cpp:372-383` (`create_tunnel()`)
```cpp
if (decap_ttl_mode == VxlanTunnelTTLMode::PIPE) { ... }
else if (decap_ttl_mode == VxlanTunnelTTLMode::UNIFORM) { ... }
// NOT_SET の場合は SAI_TUNNEL_ATTR_DECAP_TTL_MODE を設定しない
```

**結論**: EVPN DIP トンネルは `SAI_TUNNEL_ATTR_DECAP_TTL_MODE` を SAI に渡さない。
プラットフォーム SAI 実装依存のデフォルト TTL モードが適用される。(**プラットフォーム依存 silent default**)

---

### 2. `peer_mode` — `SAI_TUNNEL_PEER_MODE_P2P` (ハードコード)

**根拠**: `vxlanorch.cpp:903`
```cpp
p2p = (src_creation_ == TNL_CREATION_SRC_EVPN)? true:false;
```

**根拠**: `vxlanorch.cpp:356-363`
```cpp
if ((dst_ip != nullptr) && p2p) {
    attr.id = SAI_TUNNEL_ATTR_PEER_MODE;
    attr.value.s32 = SAI_TUNNEL_PEER_MODE_P2P;
    attr.id = SAI_TUNNEL_ATTR_ENCAP_DST_IP;
    attr.value.ipaddr = *dst_ip;
}
```

**結論**: `TNL_CREATION_SRC_EVPN` の場合、`dst_ip` が指定されていれば常に
`SAI_TUNNEL_PEER_MODE_P2P` が設定される。EVPN DIP トンネルは per-remote-VTEP P2P 動作をする。
(**ハードコード**)

---

### 3. `mapper_list` — VLAN + VRF (TUNNEL_MAP_USE_COMMON_ENCAP_DECAP)

**根拠**: `vxlanorch.cpp:1167-1169`
```cpp
TUNNELMAP_SET_VLAN(mapper_list);
TUNNELMAP_SET_VRF(mapper_list);
dip_tunnel->createTunnelHw(mapper_list, TUNNEL_MAP_USE_COMMON_ENCAP_DECAP, false);
```

**結論**: EVPN DIP トンネル作成時は VLAN + VRF の両マッパーを有効化する。BRIDGE マッパーは
含まれない。`TUNNEL_MAP_USE_COMMON_ENCAP_DECAP` は共通 encap/decap マッパーを使用する。
(**ハードコード**)

---

### 4. `with_term` — `false` (tunnel termination なし)

**根拠**: `vxlanorch.cpp:1169`
```cpp
dip_tunnel->createTunnelHw(mapper_list, TUNNEL_MAP_USE_COMMON_ENCAP_DECAP, false);
```

`createTunnelHw()` の第 3 引数 `with_term=false` により、EVPN DIP トンネルは SAI tunnel
termination (`create_tunnel_termination()`) を生成しない。Decap は VTEP (P2MP トンネル) 側で
処理される。(**ハードコード**)

---

### 5. `tagging_mode` — `"untagged"` (VLAN flood domain 参加時)

**根拠**: `vxlanorch.cpp:2525-2527` (EvpnRemoteVnip2pOrch::addOperation)
```cpp
// NOTE: does 'untagged' make the most sense here?
string tagging_mode = "untagged";
gPortsOrch->addVlanMember(vlanPort, tunnelPort, tagging_mode);
```

**根拠**: `vxlanorch.cpp:2685-2687`
```cpp
// NOTE: does 'untagged' make the most sense here?
string tagging_mode = "untagged";
gPortsOrch->addVlanMember(vlanPort, tunnelPort, tagging_mode, end_point_ip);
```

**結論**: EVPN DIP トンネルポートを VLAN flood domain に追加する際、常に `"untagged"` で
メンバー追加される。コード内のコメント ("does 'untagged' make the most sense here?") は
設計の迷いを示しているが、実装はハードコード。(**ハードコード**)

---

### 6. `tnl_src` (STATE_DB) — `"EVPN"` ハードコード

**根拠**: `vxlanorch.cpp:1938-1939`
```cpp
else {
    fvVector.emplace_back("tnl_src", "EVPN");
}
```

`addRemoveStateTableEntry()` が STATE_DB の VXLAN_TUNNEL エントリに書き込む `tnl_src` フィールドは
CLI 生成 (`"CLI"`) か EVPN 生成 (`"EVPN"`) かを識別する。EVPN DIP トンネルは常に `"EVPN"` が入る。
(**ハードコード**)

---

### 7. `operstatus` 初期値 — `"down"`

**根拠**: `vxlanorch.cpp:1942`
```cpp
fvVector.emplace_back("operstatus", "down");
```

STATE_DB への初期登録時は常に `"operstatus"="down"`。Up への遷移は
`updateDbTunnelOperStatus()` から `SAI_PORT_OPER_STATUS_UP` イベント受信時。
(**ハードコード初期値**)

---

### 8. EVPN VTEP 不在時の動作 — サイレントドロップ

**根拠**: `vxlanorch.cpp:1685-1692`
```cpp
auto vtep_ptr = evpn_orch->getEVPNVtep();
if (!vtep_ptr) {
    SWSS_LOG_WARN("Unable to find EVPN VTEP. user=%d remote_vtep=%s", ...);
    return false;
}
```

`VXLAN_EVPN_NVO` が設定されておらず EVPN VTEP が取得できない場合、DIP トンネル生成は
`false` を返してサイレントに失敗する。キューへの残留なし。(**dead-consumer / silent drop 経路**)

---

## 要約テーブル

| 属性 / 挙動 | デフォルト / 実挙動 | 分類 |
|------------|-------------------|------|
| `decap_ttl_mode` | `NOT_SET` → SAI 属性省略 → プラットフォーム依存 | プラットフォーム依存 silent default |
| `peer_mode` | `SAI_TUNNEL_PEER_MODE_P2P` (EVPN src 時ハードコード) | ハードコード |
| `mapper_list` | VLAN + VRF のみ (BRIDGE なし) + COMMON ENCAP/DECAP | ハードコード |
| `with_term` | `false` (tunnel termination 生成なし) | ハードコード |
| `tagging_mode` | `"untagged"` (VLAN flood domain 参加時) | ハードコード |
| `tnl_src` (STATE_DB) | `"EVPN"` 固定 | ハードコード |
| `operstatus` 初期値 | `"down"` | ハードコード初期値 |
| EVPN VTEP 不在 | `addTunnelUser()` が `false` を返してサイレント失敗 | dead-consumer / silent drop |

---

## 参照コード

- `sonic-swss/orchagent/vxlanorch.cpp`: `createDynamicDIPTunnel()` (l.1147), `createTunnelHw()` (l.883), `addTunnelUser()` (l.1674), `EvpnRemoteVnip2pOrch::addOperation()` (l.2449), `addRemoveStateTableEntry()` (l.1913)
- `sonic-swss/orchagent/vxlanorch.h`: `VxlanTunnel` constructor (l.152), `EVPN_TUNNEL_NAME_PREFIX` (l.43), `EVPN_TUNNEL_PORT_PREFIX` (l.42), `TNL_CREATION_SRC_EVPN` (l.54)
