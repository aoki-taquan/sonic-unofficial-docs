# appl-vrf — Phase H プラットフォーム差異 詳細根拠

調査日: 2026-05-15
対象ページ: `docs/reference/config-db/appl-vrf.md`
ソース:

- `sonic-net/sonic-swss` `orchagent/vrforch.cpp` @ `4305596156d70e9797e8a881b3d19b46de0bce0d`
- `sonic-net/sonic-swss` `orchagent/vrforch.h` @ 同上
- `sonic-net/sonic-sairedis` `vslib/vpp/SwitchVpp.cpp` / `SwitchVpp.h` / `SwitchVppRif.cpp`

## 1. VRF/VNET capability 差異（SAI Virtual Router 属性）

APPL_DB `VRF_TABLE` のスキーマ自体はプラットフォーム共通だが、SAI Virtual Router に渡される 4 つの拡張属性は ASIC SAI 実装の capability に依存する。`VRFOrch::addOperation` (`vrforch.cpp:23-95`) は CONFIG_DB / VNET から来たフィールドを下表の SAI 属性へそのまま変換し、capability チェックなしで `create_virtual_router` / `set_virtual_router_attribute` を呼ぶ。

| APPL_DB フィールド | SAI 属性 | ASIC 依存性 |
|--------------------|---------|-------------|
| `src_mac` | `SAI_VIRTUAL_ROUTER_ATTR_SRC_MAC_ADDRESS` | 主要 ASIC は必須属性として実装。VS / VPP もダミー受理 |
| `ttl_action` | `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_TTL1_PACKET_ACTION` | SAI 任意属性。Broadcom / Mellanox は `TRAP/DROP/FORWARD` を受理。古い SAI / VPP は `NOT_SUPPORTED` の可能性 |
| `ip_opt_action` | `SAI_VIRTUAL_ROUTER_ATTR_VIOLATION_IP_OPTIONS_PACKET_ACTION` | 同上 |
| `l3_mc_action` | `SAI_VIRTUAL_ROUTER_ATTR_UNKNOWN_L3_MULTICAST_PACKET_ACTION` | L3 マルチキャスト未対応 ASIC / VS / VPP では `NOT_SUPPORTED` の可能性 |

vrforch は capability 失敗時のフォールバックを持たず、SAI が `NOT_SUPPORTED` を返した場合は `task_failed` 相当となり、APPL_DB の該当 entry は再試行キューに残る。YANG `sonic-vrf.yang` には 4 属性のいずれも定義がない (`vni` / `fallback` / `description` のみ)。`VNET` 経由で `vnetorch` が APPL_DB `VRF_TABLE` に直書きする非標準経路でのみ capability 差が顕在化する。

## 2. VS / VPP 差異

### VS (`libsaivs`)

`SAI_OBJECT_TYPE_VIRTUAL_ROUTER` の create/remove は内部 map 操作のみ。4 属性すべて SUCCESS で受理し、packet action / src_mac は no-op。

### VPP (`libsaivpp` = sonic-sairedis vslib/vpp)

`SwitchVpp.cpp:1183-1187` で VRF remove は `removeVrf()` (`SwitchVppRif.cpp:1940-1955`) に分岐し、`m_switchConfig->m_useTapDevice == true` のとき `vpp_del_ip_vrf()` を呼んで VPP データプレーン側の VRF も削除する。`vpp_add_ip_vrf()` (`SwitchVppRif.cpp:1387-1419`) は `ip_vrf_add(vrf_id, "vrf_<n>", false)` で VPP VRF を作成し、`vpp_ip_flow_hash_set()` で 5-tuple ハッシュを固定設定する。VPP では 4 capability 属性はすべて no-op、ハッシュマスクは APPL_DB から制御不可。

## 3. EVPN VTEP 依存

`vni != 0` を指定して L3 VNI を VRF にマップする場合、`VRFOrch::updateVrfVNIMap` (`vrforch.cpp:225-230`) は `EvpnNvoOrch::getEVPNVtep()` で **EVPN_NVO 経由で作成済みの VTEP** を取得することを必須とする。未設定なら `return false` で APPL_DB エントリは task キューに残ったまま `STATE_VRF_OBJECT_TABLE` の `state=ok` が書かれない。EVPN VXLAN 未対応 ASIC では `vni > 0` の VRF entry は永久に成立しない。

## 4. プラットフォーム別まとめ表

| 観点 | Broadcom DNX/XGS | Mellanox | Cisco silicon-one | VS | VPP |
|------|------------------|----------|--------------------|----|-----|
| `src_mac` SAI 属性 | OK | OK | OK | OK (no-op) | OK (no-op) |
| `ttl_action` / `ip_opt_action` | OK | OK | OK | OK (no-op) | OK (no-op) |
| `l3_mc_action` | OK (一部 SKU) | OK | OK | OK (no-op) | OK (no-op) |
| `vni` (L3 VNI) ASIC 転送 | DNX OK / XGS 一部 | OK | OK | dummy | dummy |
| EVPN VTEP 必須 | あり | あり | あり | あり (受理のみ) | あり (受理のみ) |
| VRF 削除時 VPP 同期 | 不要 | 不要 | 不要 | 不要 | `m_useTapDevice=true` のみ |
