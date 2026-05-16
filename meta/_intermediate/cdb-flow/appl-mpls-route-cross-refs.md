# LABEL_ROUTE_TABLE (APPL_DB) — Phase C 暗黙参照調査メモ

調査日: 2026-05-15
対象ページ: `docs/reference/config-db/appl-mpls-route.md`
証拠ソース:
- `sonic-net/sonic-swss/orchagent/mplsrouteorch.cpp`（全行精読）
- `sonic-net/sonic-swss/orchagent/nhgorch.cpp`（MPLS NH 分岐 `isLabeled()` 関連箇所を全件精読）
- `sonic-net/sonic-swss/orchagent/routeorch.cpp`（MPLS 経路の入口 `doTask` / `doLabelTask` 連携部）

---

## 発見した暗黙参照一覧

`APPL_DB:LABEL_ROUTE_TABLE` の各 `<vrf-name>:<incoming-label>` エントリは、YANG leafref を持たない (APPL_DB に YANG なし) が、`routeorch::doLabelTask` および `NhgOrch` 経由で以下のオブジェクト/テーブルを実行時に暗黙参照する。

### 1. NEXTHOP — NeighOrch が管理する IP/MPLS NH

**参照先**: NeighOrch 内部の `NextHopKey` → SAI `next_hop`
**方向**: 実行時参照（NeighOrch API 経由）
**条件**: `addLabelRoute()` で単一 NH / ECMP NHG を SAI に登録する直前
**証拠**:
- `mplsrouteorch.cpp:514-516`: `m_neighOrch->hasNextHop(nexthop)` / `getNextHopId(nexthop)` で既存 IP NH の SAI OID を取得
- `mplsrouteorch.cpp:519-527`: MPLS NH (`isMplsNextHop()`) の場合、IP neighbor が解決済みなら `m_neighOrch->addNextHop(ctx)` で MPLS NH を新規生成
- `mplsrouteorch.cpp:534-540`: 未解決時は `m_neighOrch->resolveNeighbor(nexthop)` を発火し `return false`（retry）
- `nhgorch.cpp:544-546, 563-570, 681`: NHG メンバ作成・破棄でも同 API を経由

**影響**: NeighOrch に該当 NextHop が登録されていない、あるいは MPLS NH の生成に失敗すると inseg エントリは生成されず、retry ループに入る。

### 2. NEIGH (NEIGH_TABLE)

**参照先**: `APPL_DB:NEIGH_TABLE|<ifname>:<ip>` / kernel ARP/NDP テーブル
**方向**: 実行時参照（NeighOrch 経由、ARP/NDP 解決前提）
**条件**: 非 intf NH (`nexthop.isIntfNextHop() == false`) のすべての MPLS ルート
**証拠**:
- `mplsrouteorch.cpp:520`: `m_neighOrch->isNeighborResolved(nexthop)` でカーネル ARP/NDP 解決済みか確認
- `mplsrouteorch.cpp:538, 559`: 未解決時 `resolveNeighbor()` で ARP/NDP 解決をトリガ
- `nhgorch.cpp:583-585, 838, 947`: NHG 内部も同等の解決チェック・`NHFLAGS_IFDOWN` 確認

**影響**: NEIGH (ARP/NDP) が未解決の MPLS ルートは即座には ASIC に書かれず、neighbor 解決後の retry サイクルで成立する。

### 3. INTF (INTF_TABLE / Router Interface)

**参照先**: `IntfsOrch` 内部の RIF オブジェクト → SAI `router_interface`
**方向**: 実行時参照
**条件**: `nexthop.isIntfNextHop() == true`（directly connected な NH） — `addLabelRoute()` / Post 双方
**証拠**:
- `mplsrouteorch.cpp:503, 707`: `m_intfsOrch->getRouterIntfsId(nexthop.alias)` で RIF OID を取得。`SAI_NULL_OBJECT_ID` のときは LOG_INFO+retry
- `nhgorch.cpp:542, 757, 885`: NHG メンバの intf NH について `gIntfsOrch->getRouterIntfsId()` および ref-count 増減

**影響**: RIF 未作成の状態では directly connected な MPLS NH を持つ inseg エントリが ASIC に反映されない。

### 4. NHG (NEXT_HOP_GROUP_TABLE) — NhgOrch / CbfNhgOrch

**参照先**: `APPL_DB:NEXT_HOP_GROUP_TABLE|<index>`（NhgOrch 管理）および CBF NHG
**方向**: 実行時参照
**条件**: APPL_DB エントリが `nexthop_group=<index>` を指定したとき
**証拠**:
- `mplsrouteorch.cpp:157-170`: `nexthop_group` と `nexthop`/`ifname` の同時指定は LOG_ERROR で erase
- `mplsrouteorch.cpp:256-267`: `getNhg(nhg_index)` 失敗時 LOG_ERROR + retry（`gNhgOrch->hasNhg()` / `gCbfNhgOrch->hasNhg()` で双方をチェック）
- `mplsrouteorch.cpp:483-490`: `addLabelRoute()` 内で `out_of_range` を `catch` し NHG 消失検出
- `mplsrouteorch.cpp:686-689`: Post でも NHG 所有確認

**影響**: NhgOrch に該当 NHG が登録される前に inseg を投入すると、retry されながら NHG 出現待ちになる。両方指定するとエントリは即座に drop。

### 5. VRF (VRF_TABLE)

**参照先**: `CONFIG_DB:VRF|<name>` → VrfOrch 内部の `sai_object_id_t` VRF
**方向**: 実行時参照（キー `<vrf-name>:<label>` の prefix から）
**条件**: APPL_DB キーが `Vrf<name>:` プレフィックスを持つとき
**証拠**:
- `mplsrouteorch.cpp:107-118`: キー先頭が `VRF_PREFIX` (`"Vrf"`) の場合、`m_vrfOrch->isVRFexists(vrf_name)` 確認後 `getVRFid()` で SAI VRF OID を取得。未存在なら `it++` で retry
- `mplsrouteorch.cpp:75`: 出力経路でも `getVRFname()` を逆引き利用
- `mplsrouteorch.cpp:474, 957`: VRF ref-count 増減（route 確定後）

**実装上の特記**: 現状 `fpmsyncd::onLabelRouteMsg()` は非デフォルト VRF の MPLS ルートをスキップ (`routesync.cpp:2674-2681`)。よって本暗黙参照は手動 APPL_DB 書込・サードパーティ FPM クライアント経由でのみ顕在化する。

**影響**: 指定 VRF が VrfOrch に未存在だと、エントリは消費されず retry ループのまま留まる。

---

## SAI 参照

- SAI `inseg_entry` (`SAI_OBJECT_TYPE_INSEG_ENTRY`): label / num_of_pop / packet_action / next_hop_id を設定 (`mplsrouteorch.cpp:777-840`)
- SAI `next_hop` (`SAI_OBJECT_TYPE_NEXT_HOP`): IP NH および MPLS NH 双方を NeighOrch 経由で確保
- SAI `next_hop_group` (`SAI_OBJECT_TYPE_NEXT_HOP_GROUP`): NhgOrch 経由（CBF NHG も含む）
- SAI `router_interface`: directly connected NH の解決に間接利用

## YANG leafref

APPL_DB スキーマには YANG モデル定義が無く、leafref は **存在しない**。ここで列挙した参照はすべて C++ 実装レイヤの **暗黙依存**である。

## 排他制約

- `nexthop_group` と `nexthop`/`ifname` の同時指定: 即 drop (`mplsrouteorch.cpp:165-170`)
- 非デフォルト VRF: 現状 fpmsyncd 側で生成されない（プラットフォーム非依存の制限）
