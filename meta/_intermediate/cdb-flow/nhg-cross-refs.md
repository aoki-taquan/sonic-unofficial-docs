# NEXTHOP_GROUP_TABLE — 暗黙参照 (cross-table refs) 調査メモ

## 調査対象

`docs/reference/config-db/nhg.md` Phase C 追加分。
`NEXTHOP_GROUP_TABLE` は APPL\_DB テーブルのため YANG leafref は存在しない。
`sonic-swss/orchagent/nhgorch.cpp` を全行精読し、外部テーブル・外部 Orch への依存を網羅した。

## ソースファイル精読

| ファイル | 役割 |
|---------|------|
| `sonic-swss/orchagent/nhgorch.cpp` | `NhgOrch::doTask()` / `NextHopGroupMember::getNhId()` / `NextHopGroupMember::sync()` / `remove()` / `~NextHopGroupMember()` / `NextHopGroup::sync()` / `NextHopGroup::remove()` / `NhgOrch::createTempNhg()` |
| `sonic-swss/orchagent/nhgorch.h` | `NhgOrch` / `NextHopGroup` / `NextHopGroupMember` クラス定義 |
| `sonic-swss/orchagent/neighorch.h` | `NeighOrch` API（`hasNextHop`, `getNextHopId`, `isNeighborResolved`, `resolveNeighbor`, `addNextHop`, `removeMplsNextHop`, `increaseNextHopRefCount`, `decreaseNextHopRefCount` 等） |
| `sonic-swss/orchagent/routeorch.h` | `RouteOrch::getNhgCount()`, `getMaxNhgCount()` — NHG 数上限管理 |

## YANG leafref

`NEXTHOP_GROUP_TABLE` は APPL\_DB テーブルのため YANG 未定義。全参照が実装レベルの暗黙参照。

## 暗黙参照 (実装レベル)

### 1. NEIGH（NeighOrch — NH の存在確認と OID 解決）

- **参照先**: `NeighOrch` が管理する nexthop エントリ（NEIGH テーブル相当）
- **参照方向**: 読み取り（OID 解決）
- **条件**: 各 NHG メンバーの nexthop を SAI NH ID に変換するとき
- **参照元**: `nhgorch.cpp` L544–546 (`getNhId()` — `gNeighOrch->hasNextHop()` / `getNextHopId()`), L563 (`isNeighborResolved()` — labeled NH), L568 (`addNextHop()` — labeled NH 作成), L585 (`resolveNeighbor()` — 隣接未解決時のトリガー)
- **意味**:
  - `gNeighOrch->hasNextHop(m_key)` が true → `getNextHopId()` で SAI OID 取得
  - labeled NH かつ `isNeighborResolved()` → `addNextHop()` で SAI labeled NH を生成して OID 取得
  - いずれも該当しない (SRv6 以外) → `resolveNeighbor()` を呼んで ARP/ND 解決をトリガー、NHG は pending (`m_toSync` 残留)
  - SRv6 nexthop は `gSrv6Orch->createSrv6NexthopWithoutVpn()` 経由で作成

### 2. NEIGH（NeighOrch — refcount 管理）

- **参照先**: `NeighOrch` が管理する nexthop refcount
- **参照方向**: refcount 増減
- **条件**: NHG メンバーが SAI に sync されるとき・削除されるとき
- **参照元**: `nhgorch.cpp` L633 (`NextHopGroupMember::sync()` — `increaseNextHopRefCount()`), L648 (`NextHopGroupMember::remove()` — `decreaseNextHopRefCount()`), L759 (`NextHopGroup::sync()` 単一 NH 直接参照パス — `increaseNextHopRefCount()`), L887 (`NextHopGroup::remove()` — `decreaseNextHopRefCount()`)
- **意味**: 単一メンバー NHG の場合、NHG の SAI ID = NH の SAI OID をそのまま借用するため、refcount 管理は特に重要。NH の refcount が 0 でないと NH を削除できない。

### 3. NEIGH（NeighOrch — labeled / SRv6 NH の生存管理）

- **参照先**: `NeighOrch` が保持する MPLS labeled NH / SRv6 NH
- **参照方向**: 追加・削除（生存管理）
- **条件**: `~NextHopGroupMember()` 実行時（NHG メンバー削除）
- **参照元**: `nhgorch.cpp` L662–663 (SRv6 NH refcount=0 → `removeSrv6NexthopWithoutVpn()`), L677–681 (labeled NH refcount=0 → `removeMplsNextHop()`)
- **意味**: `NhgOrch` と `RouteOrch` が MPLS labeled NH の生存を協調管理する。`getNextHopRefCount() == 0` を確認してから `removeMplsNextHop()` を呼ぶ。どちらの Orch が先に NHG メンバーを削除しても同一チェックで安全に処理される。

### 4. NEIGH（NeighOrch — 隣接解決確認、createTempNhg）

- **参照先**: `NeighOrch` が管理する nexthop の解決状態
- **参照方向**: 存在確認（読み取り）
- **条件**: `createTempNhg()` で NHG 数上限到達時に temporary NHG を生成するとき
- **参照元**: `nhgorch.cpp` L838 (`gNeighOrch->isNeighborResolved(nh_key)`)
- **意味**: NHG の全メンバーから「解決済み」の NH だけを抽出し、その中からランダムに代表 1 NH を選んで temporary group を作成する。未解決メンバーは temporary group に含めない。

### 5. ROUTE_TABLE（RouteOrch — NHG 数上限チェック）

- **参照先**: `RouteOrch::getNhgCount()`, `getMaxNhgCount()`
- **参照方向**: NHG カウント参照（読み取り）
- **条件**: `doTask()` の SET 処理で新規 NHG を SAI に作成する直前
- **参照元**: `nhgorch.cpp` L252 (`gRouteOrch->getNhgCount() + NextHopGroup::getSyncedCount() >= gRouteOrch->getMaxNhgCount()`), L320 (UPDATE パスでも同様チェック)
- **意味**: `getNhgCount()` は `RouteOrch` が管理する NHG 数、`getSyncedCount()` は `NhgOrch` 管理分。両者の合計が SAI の max NHG 数に達すると、非 SRv6 NHG は `createTempNhg()` で temporary group に降格（1 NH で暫定解決）。SRv6 NHG は skip → `m_toSync` 残留して再試行待ち。

### 6. ROUTE_TABLE（RouteOrch — labeled NH 生存の協調管理）

- **参照先**: `RouteOrch` が監視する labeled NH の refcount
- **参照方向**: 協調管理（コメントによる設計合意）
- **条件**: labeled NH の削除判断時
- **参照元**: `nhgorch.cpp` L671–673 (コメント: "NhgOrch and RouteOrch are the ones controlling it's lifetime"), L677–681 (`removeMplsNextHop()` の refcount=0 ガード)
- **意味**: MPLS labeled NH の生存は `NhgOrch` と `RouteOrch` が協調管理する。どちらが先に `removeMplsNextHop()` を呼んでも安全なよう、`getNextHopRefCount() == 0` をガードとして設けている。

## 被参照関係（ROUTE_TABLE から本テーブルへの参照）

`ROUTE_TABLE` (APPL\_DB) は `nexthop_group` フィールドで `NEXTHOP_GROUP_TABLE` のキーを参照する。これは本テーブルが「被参照元」であることを意味し、`RouteOrch` が NHG を参照している間は DEL_COMMAND で NHG を削除できない（`getRefCount() > 0` でブロック）。

## 参照関係サマリ

```
NEXTHOP_GROUP_TABLE
  ├─ [暗黙] NEIGH (NeighOrch)
  │     ├─ hasNextHop() / getNextHopId()          (NH OID 解決 — 各メンバー sync 時)
  │     ├─ isNeighborResolved() / resolveNeighbor() (隣接解決トリガー — NH 未解決時)
  │     ├─ addNextHop() / removeMplsNextHop()      (labeled NH 生存管理)
  │     ├─ increaseNextHopRefCount()               (sync 時 refcount 増加)
  │     └─ decreaseNextHopRefCount()               (remove 時 refcount 減少)
  ├─ [暗黙] ROUTE_TABLE (RouteOrch)
  │     ├─ getNhgCount() / getMaxNhgCount()         (NHG 数上限チェック)
  │     └─ labeled NH 生存の協調管理               (MPLS NH の生存期間を共同管理)
  └─ [被参照] ROUTE_TABLE → NEXTHOP_GROUP_TABLE
              (nexthop_group フィールドで NHG キーを参照。参照中は DEL 不可)
```

VRF / VrfOrch への直接参照は nhgorch.cpp に存在しない。VRF 対応は `NextHopKey.vrf_id` を通じて `RouteOrch` / `NeighOrch` 側が処理する。

## evidence

- `nhgorch.cpp`: L1–21 (include / extern 宣言), L37–435 (`NhgOrch::doTask()` — SET/DEL 全処理), L524–590 (`NextHopGroupMember::getNhId()`), L628–683 (`sync()`/`remove()`/`~NextHopGroupMember()`), L720–812 (`NextHopGroup::sync()`), L824–860 (`NhgOrch::createTempNhg()`), L870–894 (`NextHopGroup::remove()`), L947 (`isNextHopFlagSet()`)
- `nhgorch.cpp` L252, L320: `gRouteOrch->getNhgCount() + NextHopGroup::getSyncedCount() >= gRouteOrch->getMaxNhgCount()`
- `nhgorch.cpp` L671–681: labeled NH 生存管理コメント + `removeMplsNextHop()` 実装
