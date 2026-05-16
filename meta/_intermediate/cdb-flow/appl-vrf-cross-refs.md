# appl-vrf — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/appl-vrf.md` Phase C 追加分。
本ページの主題は **APPL_DB `VRF_TABLE`**（`vrfmgrd` が書き手 / `VRFOrch` が読み手）。
ここでの「暗黙参照」とは、`VRF_TABLE` エントリの生成・SAI Virtual Router 生成・L3 VNI マッピング・ref_count 管理が依存する、他テーブル / 他 Orch / プラットフォーム前提を指す。`sonic-swss/orchagent/vrforch.cpp` を中心に精読し、CONFIG_DB / APPL_DB / STATE_DB / SAI 各方向の暗黙依存を網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/vrforch.cpp` | `VRFOrch::addOperation()` (L26–162)、`delOperation()` (L165–197)、`updateVrfVNIMap()` (L200–247)、`delVrfVNIMap()` (L249–276)、`updateL3VniVlan()` (L278–)、`getEVPNVtep()` / `getVlanMappedToVni()` 呼び出し |
| `sonic-swss/orchagent/vrforch.h` | `VRFOrch::increaseVrfRefCount()` / `decreaseVrfRefCount()` 公開 API、`vrf_table_` ref_count 管理 |
| `sonic-swss/cfgmgr/vrfmgr.cpp` | CONFIG_DB `VRF` → APPL_DB `VRF_TABLE` への pass-through (L303) |
| `sonic-swss-common/common/schema.h` | `APP_VRF_TABLE_NAME = "VRF_TABLE"`、`STATE_VRF_OBJECT_TABLE_NAME` |
| `sonic-swss/orchagent/routeorch.cpp` / `intfsorch.cpp` / `fgnhgorch.cpp` / `mplsrouteorch.cpp` / `srv6orch.cpp` / `twamporch.cpp` / `p4orch/*` | `m_vrfOrch->increaseVrfRefCount(vrf_id)` 呼び出し（参照元側） |

## YANG leafref

`sonic-vrf.yang` は CONFIG_DB `VRF` のみを規定し、APPL_DB `VRF_TABLE` は YANG 未モデル化（オペレーショナル）。leafref は存在せず、全依存は実装レベルの暗黙参照。`VNET` 経由パスは `sonic-vnet.yang` で `Vrf-name` の `pattern "Vnet[a-zA-Z0-9_-]+"` を持つが、`VRF_TABLE` キーに転写される際の整合性チェックは orchagent 側で行われない。

## 暗黙参照 (実装レベル)

### 1. CONFIG_DB `VRF` (上流ソース)

- **参照先**: `CONFIG_DB VRF`
- **参照方向**: `vrfmgrd` が subscribe → APPL_DB `VRF_TABLE` に pass-through
- **条件**: 常時。`vrfmgr.cpp:303` で `m_appVrfTableProducer.set(vrfName, kfvFieldsValues(t))`
- **意味**: APPL_DB `VRF_TABLE|<vrfName>` の存在および全フィールドは CONFIG_DB `VRF|<vrfName>` の SET/DEL に直接連動する。YANG `sonic-vrf.yang` の `vni` / `fallback` / `description` のみが標準経路で書き込まれる。
- **evidence**: `cfgmgr/vrfmgr.cpp:303`、`schema.h` の `APP_VRF_TABLE_NAME`

### 2. CONFIG_DB `VNET` / APPL_DB `VNET_TABLE` (非標準入力経路)

- **参照先**: `CONFIG_DB VNET`, `APPL_DB VNET_TABLE`
- **参照方向**: `VNetOrch` が APPL_DB `VRF_TABLE` を **直接書き込む**（YANG 未定義 4 属性 `v4` / `v6` / `src_mac` / `ttl_action` / `ip_opt_action` / `l3_mc_action` を含む）
- **条件**: `VNET_TUNNEL_ROUTES` 系の機能を有効にしたとき
- **意味**: `vrforch.cpp:48–67` の if/else チェーンで処理される拡張属性は通常 `config vrf add` 経由では現れず、`VnetOrch` 経由の直書きでのみ実体化する。`VRFOrch` 側は書き手を区別せず一律に SAI Virtual Router 属性へ変換する。
- **evidence**: `vrforch.cpp:48–67`（属性変換）、本ページ "Phase H プラットフォーム差異" 参照

### 3. CONFIG_DB `VXLAN_EVPN_NVO` + APPL_DB `EVPN_NVO_TABLE` (L3 VNI 前提)

- **参照先**: `CONFIG_DB VXLAN_EVPN_NVO`, `APPL_DB EVPN_NVO_TABLE`、`EvpnNvoOrch`
- **参照方向**: `VRFOrch::updateVrfVNIMap()` が `gDirectory.get<EvpnNvoOrch*>()->getEVPNVtep()` を呼ぶ
- **条件**: `vni != 0` で L3 VNI を VRF にマップするときのみ
- **意味**: VTEP（source VTEP オブジェクト）が `EvpnNvoOrch` 配下に存在しなければ `updateVrfVNIMap` は `SWSS_LOG_NOTICE("updateVrfVNIMap unable to find EVPN VTEP")` を出して `return false`。結果として `vrf_vni_map_table_[vrf_name]` は更新されず、L3 VNI マッピングは半設定状態のまま `task_failed` 復路で再試行キューに残る。`STATE_VRF_OBJECT_TABLE|<vrfName>` の `state=ok` も書き込まれない。
- **evidence**: `vrforch.cpp:205, 225–230`

### 4. CONFIG_DB `VXLAN_TUNNEL` + APPL_DB `VXLAN_TUNNEL_TABLE` (VTEP 実体・VLAN-VNI map)

- **参照先**: `CONFIG_DB VXLAN_TUNNEL`, `APPL_DB VXLAN_TUNNEL_TABLE`, `VxlanTunnelOrch`
- **参照方向**: `VRFOrch::updateVrfVNIMap()` が `gDirectory.get<VxlanTunnelOrch*>()->getVlanMappedToVni(vni)` を呼ぶ
- **条件**: `vni != 0` のとき
- **意味**: `getVlanMappedToVni(vni)` が `0` を返す（= `VXLAN_TUNNEL_MAP` 経由の VLAN-VNI map 未投入）と `l3vni_table_[vni].vlan_id = 0` のまま `updateL3VniStatus()` が呼ばれず、L3 VNI は VLAN 紐付け待ちの半設定状態となる。後続で `VXLAN_TUNNEL_MAP` が投入されると `updateL3VniVlan()` (`vrforch.cpp:278`) 経路で VE UP まで進む。
- **evidence**: `vrforch.cpp:206, 233–240, 278`

### 5. CONFIG_DB `INTERFACE` / `VLAN_INTERFACE` / `PORTCHANNEL_INTERFACE` / `LOOPBACK_INTERFACE` (ref_count 入力)

- **参照先**: 各種 `*_INTERFACE` テーブル（`IntfsOrch` 経由）
- **参照方向**: `IntfsOrch::addIntfsToVrf()` 等で `m_vrfOrch->increaseVrfRefCount(vrf_id)` を呼ぶ
- **条件**: インタフェースの `vrf_name` 属性が当該 VRF を指すとき（`intfsorch.cpp:504, 848, 855`）
- **意味**: `vrf_table_[vrf_name].ref_count` が増加し、`VRFOrch::delOperation()` の `if (vrf_table_[vrf_name].ref_count)` (`vrforch.cpp:169–170`) で削除がブロックされる。`SWSS_LOG_NOTICE` を出して `return task_need_retry` し、VRF エントリは APPL_DB に残ったままインタフェース削除完了を待つ。
- **evidence**: `intfsorch.cpp:504, 848, 855`、`vrforch.cpp:169–170`

### 6. APPL_DB `ROUTE_TABLE` / `LABEL_ROUTE_TABLE` / `FG_NHG` / SRv6 (ref_count 入力 - ルート系)

- **参照先**: `APPL_DB ROUTE_TABLE`（`RouteOrch`）、`LABEL_ROUTE_TABLE`（`MplsRouteOrch`）、`FG_NHG_TABLE`（`FgNhgOrch`）、SRv6 関連、TWAMP セッション
- **参照方向**: 各 Orch が `m_vrfOrch->increaseVrfRefCount(vrf_id)` を呼ぶ
- **条件**: ルート / FG NHG / SRv6 DT VRF / TWAMP セッションが当該 VRF を参照するとき
- **意味**: ref_count 増減を通じて VRF 削除を防御する。ルート単独で参照中の VRF を `config vrf del` しても VRFOrch 側で task_need_retry し、消費者が消えるまで保留される。
- **evidence**: `routeorch.cpp:2013`, `mplsrouteorch.cpp:474`, `fgnhgorch.cpp:1326`, `srv6orch.cpp:1639`, `twamporch.cpp:429`

### 7. BGP / FRR (CONFIG_DB `BGP_*` 経由の間接参照)

- **参照先**: `CONFIG_DB BGP_NEIGHBOR` / `BGP_GLOBALS` / `BGP_GLOBALS_AF` 等（`bgpcfgd` 経由 FRR `vrf <name>` 設定）
- **参照方向**: 直接の DB 参照は無いが、BGP セッションが VRF コンテキストで学習したルートが Kernel → `fpmsyncd` → APPL_DB `ROUTE_TABLE` → `RouteOrch` 経由で `increaseVrfRefCount()` を呼ぶ
- **条件**: 当該 VRF に対して BGP セッションが UP しルートを学習しているとき
- **意味**: BGP 学習ルートも (6) と同じ ref_count 経路に集約される。BGP セッション自体の存在は ref_count に直接影響しないが、学習ルート 1 本でも残っていれば VRF 削除はブロックされる。EVPN タイプ 5 経由の L3 VNI 学習ルートも同様。
- **evidence**: 直接の cpp 参照は `routeorch.cpp:2013` 経路に集約。BGP→APPL_DB 経路は `sonic-frr` / `fpmsyncd` 側

### 8. P4Orch (`router_interface_manager` / `route_manager` / `acl_rule_manager` / `ip_multicast_manager`)

- **参照先**: P4RT テーブル経由のルータインタフェース / ルート / ACL `SET_VRF` アクション / IP マルチキャスト
- **参照方向**: `gDirectory.get<VRFOrch*>()->increaseVrfRefCount(...)` を直接呼ぶ
- **条件**: P4RT 経由で VRF を参照するエントリが投入されたとき
- **意味**: P4 経路でも ref_count を介して VRF 削除を防御する。標準 CONFIG_DB 経路と独立に動作。
- **evidence**: `p4orch/router_interface_manager.cpp:355`, `p4orch/route_manager.cpp:700`, `p4orch/acl_rule_manager.cpp:1851, 2067`, `p4orch/ip_multicast_manager.cpp:775`

### 9. STATE_DB `VRF_OBJECT_TABLE` (書き戻し / 削除タイミング制御)

- **参照先**: `STATE_DB VRF_OBJECT_TABLE`
- **参照方向**: `VRFOrch` が書き手、`vrfmgrd::isVrfObjExist()` が読み手
- **条件**: VRF 作成・更新成功時 (`vrforch.cpp:120, 150`) / 削除時 (`vrforch.cpp:193`)
- **意味**: `vrfmgrd` は CONFIG_DB `VRF` 削除を受け取っても、`STATE_VRF_OBJECT_TABLE|<vrfName>` のエントリが消えるまで Linux VRF デバイス削除を待つ。Phase A "STATE_DB 書き戻し" で既述。
- **evidence**: `vrforch.cpp:120, 150, 193`

### 10. FlowCounterRouteOrch (router_id ライフサイクル通知)

- **参照先**: `FlowCounterRouteOrch`（`gFlowCounterRouteOrch`）
- **参照方向**: `VRFOrch::addOperation()` が `onAddVR(router_id)` (`vrforch.cpp:110`)、`delOperation()` が `onRemoveVR(router_id)` (`vrforch.cpp:184`) を呼ぶ
- **条件**: 常時。SAI Virtual Router 生成・削除のたび
- **意味**: ルートカウンタ機能が VRF (router_id) ごとのカウンタコンテキストを準備する。APPL_DB 書き込みは伴わないが、`FLOW_COUNTER_ROUTE_PATTERN_TABLE` (CONFIG_DB) のパターンマッチに影響する。
- **evidence**: `vrforch.cpp:25, 110, 184`

### 11. SAI Switch (`gVirtualRouterId` / capability)

- **参照先**: SAI スイッチデフォルト VR (`gVirtualRouterId`)、SAI 任意属性 capability
- **参照方向**: `VRFOrch::addOperation()` が `sai_virtual_router_api->create_virtual_router()` を呼ぶ
- **条件**: 常時 (作成)。任意属性 4 種は capability に依存（Phase H 参照）
- **意味**: `default` VRF は `VRFOrch` を経由せず orchagent 起動時に `gVirtualRouterId` として確保される（APPL_DB `VRF_TABLE|default` は通常存在しない）。`config vrf add VrfRed` のみが `VRFOrch` 経路を通る。
- **evidence**: `vrforch.cpp` 全体、Phase H 既述

## 要約マッピング

| カテゴリ | 暗黙参照先 | 影響 |
|---------|-----------|------|
| VRF/VNET | CONFIG_DB `VRF`、CONFIG_DB / APPL_DB `VNET` 系 | エントリ生成・拡張 4 属性の入力経路 |
| VXLAN / EVPN VTEP | `VXLAN_EVPN_NVO`、`VXLAN_TUNNEL`、`VXLAN_TUNNEL_MAP` | `vni != 0` の L3 VNI 成立条件 |
| INTF | `*_INTERFACE` 各種 | ref_count による VRF 削除防御 |
| BGP / FRR | `BGP_*`（間接的に `ROUTE_TABLE` 経由） | 学習ルート存在による削除ブロック |
| ルート / P4 / TWAMP | `ROUTE_TABLE`, `LABEL_ROUTE_TABLE`, `FG_NHG`, SRv6, `TWAMP_SESSION`, `P4RT_TABLE` | ref_count 増減 |
| STATE_DB | `VRF_OBJECT_TABLE` | vrfmgrd の削除タイミング制御 |
| 内部 Orch | `FlowCounterRouteOrch`, `gVirtualRouterId` | router_id 通知 / default VRF 分離 |

## ドキュメント反映方針

- 上記を簡潔なテーブルにまとめて Phase C ブロック `<!-- cross-refs -->` を `<!-- /platform -->` の直後・`## 関連ページ` の直前に挿入。
- 注記で「VXLAN_EVPN_NVO 未設定で `vni != 0` を書くと L3 VNI が半設定状態」「ref_count > 0 で `config vrf del` がブロックされる」の 2 点を強調。
- 既存の Phase A "defaults" / Phase H "platform" ブロックには手を加えない。
