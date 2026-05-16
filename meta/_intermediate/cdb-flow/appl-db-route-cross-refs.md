# APPL_DB ROUTE_TABLE — 暗黙参照 (cross-refs) 調査メモ (Task F Phase C)

## 調査対象

`docs/reference/config-db/appl-db-route.md` Phase C 追加分。
APPL_DB `ROUTE_TABLE` は YANG 未定義テーブル（APPL_DB 側はそもそも YANG 管理対象外）のため、
すべての参照は orchagent C++ 実装に閉じた「暗黙参照」となる。
`sonic-swss/orchagent/routeorch.cpp` および `nhgorch.cpp` を精読し、`RouteOrch::doTask()` /
`addRoute()` / `addNextHopGroup()` から呼ばれる外部 Orch / 外部テーブル依存を網羅した。

## ソースファイル

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/routeorch.cpp` | `RouteOrch::doTask()` / `addRoute()` / `addRoutePost()` / `addNextHopGroup()` |
| `sonic-swss/orchagent/routeorch.h` | メンバ宣言（`m_neighOrch` / `m_intfsOrch` / `m_vrfOrch` / `m_fgNhgOrch` / `m_srv6Orch`） |
| `sonic-swss/orchagent/nhgorch.cpp` | `NhgOrch::doTask()` / `Nhg::sync()` — `nexthop_group` 解決の本体 |
| `sonic-swss/orchagent/nhgbase.cpp` | `NhgBase` の SAI NHG / member 作成・破棄 |

## YANG leafref

APPL_DB の `ROUTE_TABLE` は YANG モデルを持たない（APPL_DB は ProducerStateTable / FPM 由来の
軽量経路テーブルで CONFIG_DB ではない）。よって leafref は 0 件で、参照解決はすべて
orchagent C++ 側の存在確認 + refcount + OID 解決で実装される。

## 暗黙参照（実装レベル）

### 1. VRF テーブル（VRFOrch 経由 — key の `Vrf<name>:` プレフィクス）

- **参照先**: `VRF_TABLE` (CONFIG_DB) → `VRFOrch` 内部の VRF レジストリ（SAI virtual_router OID）
- **参照方向**: 存在確認 + OID 解決 + refcount
- **条件**: key が `Vrf<name>:<prefix>` 形式（非デフォルト VRF）のとき
- **参照元**:
  - `routeorch.cpp` L706–717 (`m_vrfOrch->isVRFexists(vrf_name)` / `m_vrfOrch->getVRFid(vrf_name)`)
  - L893–897 (L3 VNI 紐付け確認 `isL3VniVlan(vni)`)
  - L2013 (`m_vrfOrch->increaseVrfRefCount(vrf_id)`)
  - L2773 / L2993 (`decreaseVrfRefCount(vrf_id)`)
- **意味**: VRF 名が VRFOrch に未登録なら `it++`（再試行で待機）。VRFOrch が VRF を作成すると
  次回の `doTask()` で進む。デフォルト VRF（先頭が `Vrf` でない）は `gVirtualRouterId` を使用。

### 2. NEIGH テーブル（NeighOrch 経由 — `nexthop` フィールド）

- **参照先**: `NEIGH_TABLE` (APPL_DB) → `NeighOrch` が管理する next-hop OID
- **参照方向**: 存在確認 + OID 取得 + refcount + 解決トリガ（ARP/ND probe）
- **条件**: `nexthop` フィールド非空、かつ各 nexthop が IP next-hop（intf-only でない）
- **参照元**:
  - `routeorch.cpp` L1499–1510 (`hasNextHop()` / `getNextHopId()` / `addNextHop()` in `addNextHopGroup`)
  - L2094–2119（single NH パスの解決）
  - L2106–2109 (`NHFLAGS_IFDOWN` チェック)
  - L2151–2155 (`m_neighOrch->resolveNeighbor(nexthop)` で ARP/ND probe をキック)
  - L2197–2219（ECMP メンバ追加時）
  - L1364 / L1386 / L1663 / L1770 / L1813（refcount inc/dec）
- **意味**:
  - `hasNextHop()` が true → `getNextHopId()` で SAI OID 取得。
  - 未解決 → `resolveNeighbor()` 呼出で ARP/ND を発行し `return false`（次回 doTask で retry）。
  - MPLS NH は IP neighbor が解決済みなら `addNextHop()` で MPLS NH を自動生成。
- **refcount**: install 成功時に `increaseNextHopRefCount()`、削除時に `decreaseNextHopRefCount()`。
  refcount=0 になった MPLS / Tunnel NH は `removeMplsNextHop()` / `removeTunnelNextHop()` で除去。
- **フラグ依存**: `NHFLAGS_IFDOWN` が立った NH は ECMP メンバから除外（L1532 / L1705 / L1970）。

### 3. INTF テーブル（IntfsOrch 経由 — `ifname` / intf-only NH）

- **参照先**: `INTF_TABLE` (APPL_DB) → `IntfsOrch` 内部の RIF 管理（SAI router_interface OID）
- **参照方向**: OID 解決 + refcount + サブネット判定
- **条件**: `ifname` 指定、または nexthop が intf-only NH（IP 部分が無く interface 直接指定）
- **参照元**:
  - `routeorch.cpp` L968 (`gIntfsOrch->getRouterIntfsAlias()` でエイリアス検証、コメント L911 で「常に信頼はできない」と注記)
  - L1045 (`m_intfsOrch->isPrefixSubnet()` でコネクテッドルート判定)
  - L2083 / L2086–2090 (`m_intfsOrch->getRouterIntfsId()` で intf-only NH 解決、`SAI_NULL_OBJECT_ID` なら retry)
  - L2429 (`addRoutePost()` での RIF OID 再確認)
  - L1362 / L1384（refcount inc/dec）
- **意味**: intf-only NH は RIF OID を直接使用。RIF 未作成なら `return false` で retry。
  フルマスク経路がコネクテッドサブネットと一致する場合は `isPrefixSubnet()` で特殊扱い。

### 4. PORT テーブル（PortsOrch 経由 — allPortsReady + Inband + CPU port）

- **参照先**: `PORT_TABLE` (APPL_DB) → `PortsOrch`
- **参照方向**: 起動ブロック + Inband 判定 + CPU port 取得
- **条件**: 常時（`doTask()` 入口）+ intf-only NH が inband port の場合
- **参照元**:
  - `routeorch.cpp` L609 (`gPortsOrch->allPortsReady()` — false の間は ROUTE_TABLE 全処理が早期 return)
  - L243 (`gPortsOrch->getCpuPort()` — link-local 用 CPU port)
  - L2074 (`gPortsOrch->isInbandPort(nexthop.alias)` — inband 宛 static route はスキップ)
  - L915–926（`eth0` / `docker0` / `usb0` / `lo` / `Loopback*` 宛は `removeRoute(ctx)` を実行）
- **意味**: PortsOrch の初期化完了が先行必須。これが false の間 `routeorch` は何もしない。
  inband port 宛 static route は ASIC に書かない（neighbor 側で host route が入るため）。

### 5. NhgOrch / CbfNhgOrch（`nexthop_group` フィールド）

- **参照先**: `NEXTHOP_GROUP_TABLE` / `CLASS_BASED_NEXT_HOP_GROUP_TABLE` (APPL_DB) → `NhgOrch` / `CbfNhgOrch`
- **参照方向**: 存在確認 + 内部オブジェクト取得 + refcount + SAI OID 共有
- **条件**: `nexthop_group` フィールドが非空のとき（`nexthop`/`ifname` とは排他）
- **参照元**:
  - `routeorch.cpp` L807–812（`nhg_index` と `nexthop`/`ifname` の同時指定はエラー erase）
  - L838–839 / L996–1003 / L1006–1012 (`gNhgOrch->getNhg(nhg_index)` で `NhgBase` 取得、`out_of_range` で retry)
  - L1096 / L1424 / L1478 (`NhgOrch::getSyncedNhgCount()` で global NHG 上限チェック)
  - L2042–2057 (`addNextHopGroup` ハンドリング)
  - L2411 (`gNhgOrch->hasNhg(ctx.nhg_index) || gCbfNhgOrch->hasNhg(ctx.nhg_index)`)
  - L2546 (`incNhgRefCount()` / 削除時 `decNhgRefCount()`)
  - `nhgorch.cpp` L319–362（NHG の temp 保持 / promotion — `m_maxNextHopGroupCount` リソース満員時）
  - `nhgorch.cpp` L771–772 (`SAI_NEXT_HOP_GROUP_TYPE_ECMP` 共通 API)
- **意味**: `nhg_index` 指定時は NhgOrch 管理の NHG を再利用（RouteOrch は NHG を作らない）。
  index が NhgOrch / CbfNhgOrch のどちらにも無ければ `return false` → NHG 作成後に再試行で install。
  NHG リソース満員時 `nhgorch.cpp` 側は temp NHG を保持して promotion 待ちとする。

### 6. FgNhgOrch（Fine-Grained NHG — FG_NHG / FG_NHG_PREFIX）

- **参照先**: `FG_NHG` / `FG_NHG_PREFIX` (CONFIG_DB) → `FgNhgOrch`
- **参照方向**: 適用判定 + 専用 NHG 生成 + ロールバック
- **条件**: `isRouteFineGrained(vrf_id, ipPrefix, nextHops)` が true（プレフィクスが FG_NHG にマッチ）
- **参照元**:
  - `routeorch.cpp` L529 / L597 (`validNextHopInNextHopGroup()` / `invalidNextHopInNextHopGroup()`)
  - L1424–1431 (`createFineGrainedNextHopGroup()` 上限ガード)
  - L2028–2037 (`isRouteFineGrained()` + `setFgNhg()`)
  - L2403 / L2470–2477（`addRoutePost` の FG ルート判定、失敗時 `m_fgNhgOrch->removeFgNhg(vrf_id, ipPrefix)` でロールバック）
  - L2475（削除時 `removeFgNhg()`）
- **意味**: 通常の NHG 管理を完全バイパスし、FgNhgOrch が独自に SAI NHG をハッシュベースで構築。
  途中失敗時は即座に `removeFgNhg()` で解体してから `return false`。

### 7. Srv6Orch（SRv6 SID-list / VPN SID — `segment` / `seg_src`）

- **参照先**: `SRV6_SID_LIST_TABLE` / `SRV6_MY_SID_TABLE` (APPL_DB) → `Srv6Orch`
- **参照方向**: 存在確認 + nexthop 生成 + Agg ID 取得 + バルク削除
- **条件**: `segment` または `seg_src` 非空（`srv6_nh = true`）のとき
- **参照元**:
  - `routeorch.cpp` L736–795 (`vni_label` / `segment` / `seg_src` から `overlay_nh` / `srv6_nh` のフラグ立て)
  - L1250 (`removeSrv6Nexthops` バルク削除)
  - L2055 (`contextIdExists(context_index)` — VPN SID list 存在確認)
  - L2100 / L2143 / L2169 (`m_srv6Orch->srv6Nexthops()` で SRv6 NH OID 生成)
  - L2142–2149（SRv6 NH 作成失敗 → `ERROR` + `return false` で retry）
  - L2188–2200（SRv6 NHG は temp route を作らず即 `return false`）
  - L2295 / L2352 (`getAggId(nextHops)` で SRv6 集約 ID 取得)
- **意味**: SRv6 経路は通常の NHG ではなく Srv6Orch が管理する集約オブジェクトを SAI route entry に紐付ける。
  ASIC が `SAI_OBJECT_TYPE_MY_SID_ENTRY` 等未対応の場合は `SAI_STATUS_NOT_SUPPORTED` で失敗。

### 8. VxLAN Tunnel / VxlanTunnelOrch（overlay NH / remote VTEP — `vni_label` + `router_mac`）

- **参照先**: `VXLAN_TUNNEL` (CONFIG_DB) / VNET 経由の remote VTEP → `VxlanTunnelOrch` + `NeighOrch::addTunnelNextHop`
- **参照方向**: VTEP 作成 + tunnel next-hop 取得 + L3 VNI 検証
- **条件**: `vni_label` 非空（`overlay_nh = true`）かつ SRv6 でない場合
- **参照元**:
  - `routeorch.cpp` L872 / L893–897 (`m_vrfOrch->isL3VniVlan(vni)` で L3 VNI 検証 — false なら retry)
  - L2127 (`createRemoteVtep(vrf_id, nexthop)` で remote VTEP 作成)
  - L2128–2141 (overlay 作成失敗 → `ERROR` + `return false`)
  - L2133 / L2208 (`m_neighOrch->addTunnelNextHop(nexthop)` で tunnel NH 生成)
  - L1781–1789 (`removeTunnelNextHop()` / `removeOverlayNextHop()`)
- **意味**: EVPN remote VTEP 宛のルートは VxlanTunnelOrch / NeighOrch が連携して tunnel NH を作成。
  EVPN IP Prefix 経路では `nexthop`/`vni_label`/`router_mac`/`ifname` が揃わないと fpmsyncd 側で書き込みをスキップする。

### 9. FlowCounterRouteOrch（フローカウンタ連携 — 通知のみ）

- **参照先**: `FlowCounterRouteOrch`
- **参照方向**: 通知のみ（refcount / OID は無関係）
- **条件**: 常時（ROUTE add/remove ごと）+ link-local prefix の add/remove
- **参照元**:
  - `routeorch.cpp` L259 (`onAddMiscRouteEntry()` — link-local prefix 用)
  - L282 (`onRemoveMiscRouteEntry()`)
  - L2708 (`handleRouteAdd()` で flow counter 候補に追加)
- **意味**: route flow counter が enable のとき、ROUTE_TABLE エントリの add/remove を通知して計測対象を更新。

### 10. CrmOrch（CRM カウンタ — side ref）

- **参照先**: `CRM_IPV4_ROUTE` / `CRM_IPV6_ROUTE` / `CRM_NEXTHOP_GROUP` / `CRM_NEXTHOP_GROUP_MEMBER`
- **参照方向**: 更新通知のみ（経路投入はブロックしない）
- **条件**: 経路 / NHG / member の create / remove ごと
- **参照元**: `routeorch.cpp` 各所の `gCrmOrch->incCrmResUsedCounter()` / `decCrmResUsedCounter()`
- **意味**: 閾値超過は観測通知のみで、実際の枯渇は SAI 戻り値（`SAI_STATUS_INSUFFICIENT_RESOURCES` 等）が
  `handleSaiCreateStatus` 経由で `task_failed` / `task_need_retry` に分岐する。

## 参照関係サマリ

```
ROUTE_TABLE (APPL_DB)
  ├─ [暗黙] VRF_TABLE (VRFOrch)          (key の Vrf<name>: — 存在+OID+refcount; L706–717, L2013, L2773)
  ├─ [暗黙] NEIGH_TABLE (NeighOrch)      (nexthop — OID+refcount+resolve; L1499–1510, L2094–2119, L2151–2155)
  ├─ [暗黙] INTF_TABLE (IntfsOrch)       (ifname / intf-only — RIF OID+refcount; L968, L1045, L2083, L2429)
  ├─ [暗黙] PORT_TABLE (PortsOrch)       (allPortsReady + isInbandPort + cpu port; L609, L243, L2074, L915–926)
  ├─ [暗黙] NhgOrch / CbfNhgOrch         (nexthop_group — index 解決+refcount+上限; L838, L1096, L2411, L2546; nhgorch.cpp L319–362)
  ├─ [暗黙] FgNhgOrch (FG_NHG)           (Fine-Grained NHG — 専用 NHG; L2028–2037, L2403, L2470–2477)
  ├─ [暗黙] Srv6Orch (SRV6_SID_LIST)     (segment/seg_src — SRv6 NH+Agg ID; L2055, L2100, L2295, L2352)
  ├─ [暗黙] VxlanTunnel / remote VTEP    (vni_label — overlay NH + L3 VNI 検証; L872, L2127, L2133)
  ├─ [通知] FlowCounterRouteOrch         (route flow counter; L259, L282, L2708)
  └─ [side] CrmOrch                      (CRM 残量更新 — ブロックなし)
```

## 排他関係

- `nexthop_group` と `nexthop`/`ifname` の同時指定はエラー (`routeorch.cpp` L807–812 — erase で打ち切り)。
- `segment` / `seg_src` (SRv6) と `vni_label` (VxLAN overlay) は実装上 `srv6_nh` と `overlay_nh` が排他的に分岐。
- `blackhole = "true"` のときは `nexthop` / `ifname` の指定不要かつ無視される。

## evidence

- `routeorch.cpp`:
  - L25–30 / L46–51（extern / メンバ初期化）
  - L243 / L259 / L282（CPU port / FlowCounter）
  - L529 / L597（FgNhg メンバ検証）
  - L609（`allPortsReady()` ガード）
  - L706–717 / L872 / L893–897 / L2013 / L2773 / L2993（VRFOrch）
  - L807–812 / L838–839 / L996–1012 / L1075 / L1096 / L1424 / L1478 / L2042–2057 / L2411 / L2546（NhgOrch / CbfNhgOrch）
  - L968 / L1045 / L1362 / L1384 / L2083 / L2086–2090 / L2429（IntfsOrch）
  - L1364 / L1386 / L1499–1510 / L1532 / L1663 / L1705 / L1770 / L1781–1789 / L1801–1813 / L1901 / L1963 / L1970 / L2094–2119 / L2106–2109 / L2151–2155 / L2197–2219 / L2440 / L2630 / L2942 / L2956（NeighOrch）
  - L2028–2037 / L2403 / L2470–2477（FgNhgOrch）
  - L1250 / L2055 / L2100 / L2143 / L2169 / L2295 / L2352（Srv6Orch）
  - L2074 / L915–926（PortsOrch inband / management iface）
  - L2127 / L2128–2141 / L2133 / L2208（VxLAN overlay / tunnel NH）
  - L2708（FlowCounterRouteOrch）
- `nhgorch.cpp`:
  - L319–362（NHG リソース満員時の temp 保持と promotion）
  - L771–772（`SAI_NEXT_HOP_GROUP_TYPE_ECMP` 発行）
- `nhgbase.cpp`: SAI NHG / member の create/remove 共通実装（platform 分岐なし）。
