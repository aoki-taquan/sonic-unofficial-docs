# ROUTE_TABLE (APPL_DB) — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/app-route.md` Phase C 追加分。
`ROUTE_TABLE` (APPL_DB) は YANG 未定義テーブル（APPL_DB 側はそもそも YANG 管理対象外）のため
すべての参照が「実装レベルの暗黙参照」となる。
`sonic-swss/orchagent/routeorch.cpp` を精読し、`doRouteTask()` から呼ばれる外部 Orch / 外部テーブル依存を網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/routeorch.cpp` | `RouteOrch::doRouteTask()` / `addRoutePost()` / `addNextHopGroup()` |
| `sonic-swss/orchagent/routeorch.h` | メンバー宣言（m_neighOrch, m_intfsOrch, m_vrfOrch, m_fgNhgOrch, m_srv6Orch） |
| `sonic-swss/fpmsyncd/routesync.cpp` | APPL_DB へ書き込む側（参考） |

## YANG leafref

APPL_DB の `ROUTE_TABLE` は YANG モデルを持たない（APPL_DB は ProducerStateTable で書かれる軽量経路で、CONFIG_DB ではないため）。
すべての参照は orchagent C++ 実装に閉じている。

## 暗黙参照 (実装レベル)

### 1. VRF テーブル (key の `<vrf-name>` 部分)

- **参照先**: `VRF_TABLE` (CONFIG_DB) → `VRFOrch` 内部の VRF レジストリ
- **参照方向**: 存在確認 + OID 解決
- **条件**: key が `Vrf*:<prefix>` 形式（非デフォルト VRF）のとき
- **参照元**: `routeorch.cpp` L706–717 (`m_vrfOrch->isVRFexists(vrf_name)` / `m_vrfOrch->getVRFid(vrf_name)`)
- **意味**: VRF 名が VRFOrch に未登録なら `it++`（再試行で待機）。VRFOrch が VRF を作成すると次回の `doRouteTask()` で進む。デフォルト VRF（プレフィクス先頭が `Vrf` でない）は `gVirtualRouterId` を使用。
- **refcount**: ルート install 成功時に `m_vrfOrch->increaseVrfRefCount(vrf_id)` (`routeorch.cpp` L2013)、削除時に `decreaseVrfRefCount(vrf_id)` (L2773, L2993)。

### 2. NEIGH テーブル (NeighOrch 経由)

- **参照先**: `NEIGH_TABLE` (APPL_DB) → `NeighOrch` が管理する next-hop OID
- **参照方向**: 存在確認 + OID 取得 + refcount 管理 + 解決トリガ
- **条件**: `nexthop` フィールド非空、かつ各 nexthop が IP next-hop（intf-only でない）のとき
- **参照元**:
  - `routeorch.cpp` L1499–1510 (`hasNextHop()` / `getNextHopId()` / `addNextHop()` in `addNextHopGroup()`)
  - L2094–2119 (single NH パスでの解決)
  - L2197–2219 (ECMP メンバー追加時)
  - L1364, L1386, L1663, L1770, L1813 (refcount inc/dec)
- **意味**:
  - `hasNextHop()` が true → `getNextHopId()` で SAI OID 取得。
  - 未解決 → `m_neighOrch->resolveNeighbor(nexthop)` で ARP/ND 要求を発行して `return false`（次回再試行）。
  - MPLS NH は IP neighbor が解決済みなら `addNextHop()` で MPLS NH を自動追加。
  - Tunnel/Overlay NH は `addTunnelNextHop()` で別途生成。
- **refcount**: ルート install 成功時に `increaseNextHopRefCount()`、削除時に `decreaseNextHopRefCount()` を対称に呼ぶ。refcount=0 になった MPLS / Tunnel NH は `removeMplsNextHop()` / `removeTunnelNextHop()` で除去。
- **フラグ依存**: `NHFLAGS_IFDOWN` が立った NH はスキップして ECMP メンバーから除外 (`routeorch.cpp` L1532, L1705, L1970)。

### 3. INTF テーブル (IntfsOrch 経由 — ifname / intf-only NH)

- **参照先**: `INTF_TABLE` (APPL_DB) → `IntfsOrch` 内部の RIF 管理
- **参照方向**: OID 解決 + refcount 管理 + サブネット判定
- **条件**: `ifname` フィールド指定時、または nexthop が intf-only NH（IP 部分が無くインタフェース直接指定）の場合
- **参照元**:
  - `routeorch.cpp` L968 (`gIntfsOrch->getRouterIntfsAlias()` でエイリアス検証 — ただしコメント L911 で「常に信頼はできない」と注記あり)
  - L1045 (`m_intfsOrch->isPrefixSubnet()` でコネクテッドルート判定)
  - L2083 (`m_intfsOrch->getRouterIntfsId()` で intf-only NH 解決)
  - L2429 (`addRoutePost()` 内での RIF OID 再確認)
  - L1362, L1384 (refcount inc/dec)
- **意味**:
  - intf-only NH（`nexthop.isIntfNextHop()`）の場合は RIF OID を直接使用。RIF が未作成（`SAI_NULL_OBJECT_ID`）なら `return false`（再試行）。
  - `isPrefixSubnet()` でフルマスク経路が直接接続サブネットと一致する場合の特殊扱い。
- **refcount**: NH の alias 単位で `increaseRouterIntfsRefCount()` / `decreaseRouterIntfsRefCount()`。

### 4. PORT テーブル (PortsOrch — Inband + allPortsReady)

- **参照先**: `PORT_TABLE` (APPL_DB) → `PortsOrch`
- **参照方向**: 起動ブロック + Inband 判定 + CPU port 取得
- **条件**: 常時 (`doTask()` 入口) + intf-only NH が inband port の場合
- **参照元**:
  - `routeorch.cpp` L609 (`gPortsOrch->allPortsReady()` — false 中は全 ROUTE_TABLE 処理ブロック)
  - L243 (`gPortsOrch->getCpuPort()` — link-local 用に CPU port を取得)
  - L2074 (`gPortsOrch->isInbandPort(nexthop.alias)` — inband 宛 static route はスキップ)
- **意味**:
  - PortsOrch の初期化完了が先行必須。これが false の間 `routeorch` は何もしない。
  - inband port 宛の static route は ASIC に書かない（neighbor 作成側で自動的に host route が入るため）。

### 5. NhgOrch / CbfNhgOrch テーブル (nexthop_group フィールド)

- **参照先**: `NEXTHOP_GROUP_TABLE` / `CLASS_BASED_NEXT_HOP_GROUP_TABLE` (CONFIG_DB) → `NhgOrch` / `CbfNhgOrch`
- **参照方向**: 存在確認 + 内部オブジェクト取得 + refcount 管理
- **条件**: `nexthop_group` フィールドが非空のとき
- **参照元**:
  - `routeorch.cpp` L810–814 (`nexthop_group` と `nexthop`/`ifname` の排他チェック — 同時指定はエラー erase)
  - L838–839, L1006–1012 (`getNhg(nhg_index)` で NhgBase 取得、不在は ERROR)
  - L1096, L1424, L1478 (`NhgOrch::getSyncedNhgCount()` で global NHG 上限チェック)
  - L2042–2057 (`addNextHopGroup` ハンドリング)
  - L2411 (`gNhgOrch->hasNhg(ctx.nhg_index) && gCbfNhgOrch->hasNhg(ctx.nhg_index)` の OR チェック)
  - L2546 (`incNhgRefCount()` / 削除時 `decNhgRefCount()`)
- **意味**:
  - `nhg_index` 指定時は NhgOrch 管理の NHG を再利用（RouteOrch が NHG を作らない）。
  - NhgOrch にも CbfNhgOrch にも index が無い → INFO ログを出して `return false`（NHG 後から作成されると次回 install）。

### 6. FgNhgOrch テーブル (Fine-Grained NHG)

- **参照先**: FG_NHG / FG_NHG_PREFIX (CONFIG_DB) → `FgNhgOrch`
- **参照方向**: 適用判定 + 専用 NHG 生成
- **条件**: `isRouteFineGrained(vrf_id, ipPrefix, nextHops)` が true（プレフィクスが FG_NHG 設定にマッチ）のとき
- **参照元**:
  - `routeorch.cpp` L529, L597 (`validNextHopInNextHopGroup()` / `invalidNextHopInNextHopGroup()`)
  - L2028–2037 (`isRouteFineGrained()` + `setFgNhg()`)
  - L2403, L2475 (`addRoutePost` での FG ルート判定、削除時 `removeFgNhg()`)
- **意味**: Fine-Grained NHG は通常の NHG 管理を完全にバイパスし、FgNhgOrch が独自に SAI NHG をハッシュベースで構築する。

### 7. Srv6Orch テーブル (SRv6 SID-list / VPN SID)

- **参照先**: `SRV6_SID_LIST_TABLE` / `SRV6_MY_SID_TABLE` → `Srv6Orch`
- **参照方向**: 存在確認 + nexthop 生成 + Agg ID 取得
- **条件**: `segment` または `seg_src` フィールド非空（`srv6_nh = true`）のとき
- **参照元**:
  - `routeorch.cpp` L1250 (`removeSrv6Nexthops` バルク削除)
  - L2055 (`contextIdExists(context_index)` — VPN SID list 存在確認)
  - L2100, L2143, L2169 (`srv6Nexthops()` で SRv6 nexthop OID 生成)
  - L2295, L2352 (`getAggId(nextHops)` で SRv6 集約 ID 取得)
- **意味**: SRv6 経路は通常の NHG ではなく Srv6Orch が管理する集約オブジェクトを SAI route entry に紐付ける。

### 8. VxLAN Tunnel (overlay NH / remote VTEP)

- **参照先**: `VXLAN_TUNNEL` / VNET 経由の remote VTEP
- **参照方向**: VTEP 作成 + tunnel next-hop 取得
- **条件**: `vni_label` フィールド非空（`overlay_nh = true`）かつ SRv6 でない場合
- **参照元**:
  - `routeorch.cpp` L872 (`m_vrfOrch->isL3VniVlan(vni)` で L3 VNI 検証)
  - L2127 (`createRemoteVtep(vrf_id, nexthop)` で remote VTEP 作成)
  - L2133, L2208 (`m_neighOrch->addTunnelNextHop(nexthop)` で tunnel NH 生成)
  - L1781–1789 (`removeTunnelNextHop()` / `removeOverlayNextHop()`)
- **意味**: EVPN remote VTEP 宛のルートは VxlanTunnelOrch / NeighOrch が連携して tunnel NH を作成。

### 9. FlowCounterRouteOrch (フローカウンタ連携)

- **参照先**: `FlowCounterRouteOrch` (route flow counter)
- **参照方向**: 通知のみ（refcount/OID は無関係）
- **条件**: 常時（ROUTE add/remove イベントごと）
- **参照元**:
  - `routeorch.cpp` L259 (`onAddMiscRouteEntry()` — link-local prefix 用)
  - L282 (`onRemoveMiscRouteEntry()`)
  - L2708 (`handleRouteAdd()` で flow counter 候補に追加)
- **意味**: route flow counter が enable されている場合、ROUTE_TABLE 各エントリの追加/削除を通知して計測対象を更新。

## 参照関係サマリ

```
ROUTE_TABLE (APPL_DB)
  ├─ [暗黙] VRF_TABLE (VRFOrch)            (key の <vrf-name> — 存在確認+OID+refcount、L706–717, L2013)
  ├─ [暗黙] NEIGH_TABLE (NeighOrch)        (nexthop — OID+refcount+resolve トリガ、L1499–1510, L2094–2119)
  ├─ [暗黙] INTF_TABLE (IntfsOrch)         (ifname / intf-only NH — RIF OID+refcount、L2083, L2429, L1362)
  ├─ [暗黙] PORT_TABLE (PortsOrch)         (allPortsReady ブロック + isInbandPort スキップ、L609, L2074)
  ├─ [暗黙] NhgOrch / CbfNhgOrch           (nexthop_group — index 解決+refcount、L838, L1096, L2411, L2546)
  ├─ [暗黙] FgNhgOrch (FG_NHG / FG_NHG_PREFIX) (Fine-Grained NHG — 専用 NHG 構築、L2028–2037, L2403)
  ├─ [暗黙] Srv6Orch (SRV6_SID_LIST)       (segment/seg_src — SRv6 NH+Agg ID、L2055, L2100, L2295)
  ├─ [暗黙] VxlanTunnel / remote VTEP      (vni_label — overlay NH+tunnel NH、L2127, L2133)
  └─ [通知のみ] FlowCounterRouteOrch       (route flow counter、L259, L282, L2708)
```

## 排他関係

- `nexthop_group` と `nexthop`/`ifname` の同時指定はエラー（L810–814 — erase で完全に弾く）。
- `segment` / `seg_src` (SRv6) と `vni_label` (VxLAN overlay) は同時指定不可（実装上 `srv6_nh` と `overlay_nh` が排他的に分岐）。

## evidence

- `routeorch.cpp`:
  - L25–30, L46–51 (extern / メンバー初期化)
  - L243, L259, L282 (CPU port / flow counter)
  - L529, L597 (FgNhg メンバー検証)
  - L609 (`allPortsReady()` ガード)
  - L674, L706–717, L872, L2013, L2773, L2993 (VRFOrch)
  - L733, L772, L810–814, L838–839, L1006–1012, L1075, L1096, L1424, L1478, L2042–2057, L2411, L2546 (NhgOrch / CbfNhgOrch / nexthop_group)
  - L968, L1045, L1362, L1384, L2083, L2429 (IntfsOrch)
  - L1364, L1386, L1499–1510, L1532, L1663, L1705, L1770, L1781–1789, L1801–1813, L1901, L1963, L1970, L2094–2119, L2197–2219, L2440, L2630, L2942, L2956 (NeighOrch)
  - L2028–2037, L2403, L2475 (FgNhgOrch)
  - L1250, L2055, L2100, L2143, L2169, L2295, L2352 (Srv6Orch)
  - L2074 (PortsOrch isInbandPort)
  - L2127, L2133, L2208 (VxLAN overlay / tunnel NH)
  - L2708 (FlowCounterRouteOrch handleRouteAdd)
