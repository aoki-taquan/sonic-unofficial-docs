# nhg-orch cross-refs 調査ログ (Phase C)

**調査日**: 2026-05-16
**調査者**: Claude (batch agent)
**調査対象**: `sonic-swss/orchagent/nhgorch.cpp`, `orchagent/cbf/cbfnhgorch.cpp`, `orchagent/cbf/nhgmaporch.cpp`

## 調査方針

`NhgOrch` / `CbfNhgOrch` / `NhgMapOrch` が YANG leafref に現れない他テーブル・他
オーケストレータを暗黙的に参照する箇所を全行調査。

## 発見した暗黙参照

### 1. NeighOrch (APPL_DB:NEIGH_TABLE) — nexthop 解決

```cpp
// nhgorch.cpp:13
extern NeighOrch *gNeighOrch;

// nhgorch.cpp:544 — hasNextHop(): nexthop が NeighOrch に登録済みか確認
else if (gNeighOrch->hasNextHop(m_key))
    nh_id = gNeighOrch->getNextHopId(m_key);

// nhgorch.cpp:563-568 — MPLS ラベル付き nexthop: NeighOrch 経由で追加
else if (isLabeled() && gNeighOrch->isNeighborResolved(m_key))
    if (gNeighOrch->addNextHop(ctx))
        nh_id = gNeighOrch->getNextHopId(m_key);

// nhgorch.cpp:585 — nexthop 解決待ちをトリガー
gNeighOrch->resolveNeighbor(m_key);

// nhgorch.cpp:633, 648 — refcount 管理
gNeighOrch->increaseNextHopRefCount(m_key);
gNeighOrch->decreaseNextHopRefCount(m_key);

// nhgorch.cpp:678-681 — MPLS NH の unreferenced 時は NeighOrch から削除
gNeighOrch->removeMplsNextHop(m_key);

// nhgorch.cpp:838 — Temp NHG 作成時も NeighOrch で解決済み nexthop のみ採用
if (gNeighOrch->isNeighborResolved(nh_key))

// nhgorch.cpp:947 — インタフェース down フラグ確認
if (gNeighOrch->isNextHopFlagSet(nh_key, NHFLAGS_IFDOWN))
```

各 nexthop が NeighOrch に未登録の場合は SAI ID が `SAI_NULL_OBJECT_ID` となり、
そのメンバーはスキップされる（`syncMembers()` が `success=false` を返し再試行）。

**影響**: NeighOrch での nexthop 解決が完了するまで NHG は `sync=false` のまま。
NEXTHOP_GROUP_TABLE を書く前に対応 NEIGH_TABLE エントリが存在していること。

### 2. RouteOrch — NHG 数上限チェック・参照カウント

```cpp
// nhgorch.cpp:14
extern RouteOrch *gRouteOrch;

// nhgorch.cpp:252 — SET 時: 既存 NHG 数の確認
if (gRouteOrch->getNhgCount() + NextHopGroup::getSyncedCount() >= gRouteOrch->getMaxNhgCount())

// nhgorch.cpp:320 — temp NHG 昇格時も同様に確認
(gRouteOrch->getNhgCount() + NextHopGroup::getSyncedCount() >= gRouteOrch->getMaxNhgCount())

// routeorch.cpp:3147-3176 — RouteOrch 側から gNhgOrch->incNhgRefCount / decNhgRefCount を呼ぶ
gNhgOrch->incNhgRefCount(nhg_index);
gNhgOrch->decNhgRefCount(nhg_index);
```

RouteOrch が `ROUTE_TABLE` の `nhg_index` フィールドで NhgOrch / CbfNhgOrch のどちらが
所有するか判定し、ref_count を管理する。NHG が RouteOrch 管理の NHG 上限
（`m_maxNextHopGroupCount`）を圧迫しているとき、新規 NHG の作成が拒否される。

**影響**: ROUTE_TABLE の `nhg_index` フィールドが NhgOrch へのポインタとして機能する。
NEXTHOP_GROUP_TABLE 側の NHG が RouteOrch に参照されている間は DEL できない（ref_count > 0 の NHG は削除ガード）。

### 3. NeighOrch による validateNextHop / invalidateNextHop コールバック

```cpp
// neighorch.cpp:498 — リンクダウン/neighbor 削除時
rc &= gNhgOrch->invalidateNextHop(nexthop);

// neighorch.cpp:530 — リンクアップ/neighbor 復旧時
rc &= gNhgOrch->validateNextHop(nexthop);
```

NeighOrch が PORT oper-state 変化などを契機に `invalidateNextHop` / `validateNextHop` を
コールバックし、NhgOrch は全 NHG を走査して該当メンバーを SAI から除去/再追加する。
YANG / CONFIG_DB には現れないが、NhgOrch のメンバー active/inactive 制御の核心。

**影響**: NeighOrch との連携が断ち切られると、リンクダウン時に down-NH を引き続き
使用した ECMP が発生する可能性がある。

### 4. CbfNhgOrch — NhgOrch 所有 NHG へのメンバー参照

```cpp
// cbfnhgorch.cpp:11
extern NhgOrch *gNhgOrch;

// cbfnhgorch.cpp:644, 651 — CBF NHG のメンバーが NhgOrch 側に存在するか確認
if (!gNhgOrch->hasNhg(key))
    return false; // 再試行
const auto &nhg = gNhgOrch->getNhg(key);

// cbfnhgorch.cpp:690 — メンバー NHG の sync 済み SAI ID を取得
const auto &nhg = gNhgOrch->getNhg(member.first);

// cbfnhgorch.cpp:758, 808 — NhgOrch 側の refcount を増減
gNhgOrch->incNhgRefCount(m_key);
gNhgOrch->decNhgRefCount(m_key);
```

CLASS_BASED_NEXT_HOP_GROUP_TABLE の `members` に指定する NHG インデックスは
NhgOrch の `m_syncdNextHopGroups` に存在し `sync=true` でなければならない。
CBF NHG は NhgOrch NHG の参照カウントを保持し、ライフサイクルを結びつける。

**影響**: `NEXTHOP_GROUP_TABLE` エントリが未 sync の場合、対応 CBF NHG は
`sync=false` のまま (`return false` で再試行ループ)。

### 5. RouteOrch — CBF NHG 参照

```cpp
// routeorch.cpp:28-29
extern NhgOrch *gNhgOrch;
extern CbfNhgOrch *gCbfNhgOrch;

// routeorch.cpp:2411 — ROUTE_TABLE DEL 時: どちらが所有するか確認
if (!gNhgOrch->hasNhg(ctx.nhg_index) && !gCbfNhgOrch->hasNhg(ctx.nhg_index))

// routeorch.cpp:3151-3157 — NhgOrch / CbfNhgOrch の ref_count を統一 API で増減
if (gNhgOrch->hasNhg(nhg_index))
    gNhgOrch->incNhgRefCount(nhg_index);
else
    gCbfNhgOrch->incNhgRefCount(nhg_index);
```

RouteOrch が `ROUTE_TABLE` の `nhg_index` フィールドを見て NhgOrch / CbfNhgOrch の
どちらを使うか自動選択する。CBF NHG と通常 NHG は同一 nhg_index 空間で区別される。

## 暗黙依存まとめ

| 依存対象 | 参照種別 | 方向 | 未解決時の挙動 |
|---------|---------|------|--------------|
| NeighOrch (NEIGH_TABLE) | nexthop 解決・refcount | NhgOrch → NeighOrch | 未解決 nexthop はスキップ、NHG が sync されない |
| NeighOrch callback | validate/invalidate | NeighOrch → NhgOrch | リンクダウン時の自動メンバー除外が機能しない |
| RouteOrch (ROUTE_TABLE) | NHG 数上限・refcount | NhgOrch ↔ RouteOrch | 上限到達時は新規 NHG 作成拒否。ref_count > 0 は DEL ガード |
| NhgOrch (NEXTHOP_GROUP_TABLE) | メンバー sync 確認・refcount | CbfNhgOrch → NhgOrch | メンバー NHG 未 sync の場合 CBF NHG 作成が再試行ループ |
| RouteOrch (ROUTE_TABLE:nhg_index) | NhgOrch/CbfNhgOrch 選択 | RouteOrch → 両者 | nhg_index が両者に存在しない場合ルート DEL 失敗 |

## 結論

YANG leafref は NEXTHOP_GROUP / CBF_NHG 間のメンバー依存のみ定義。
実装上は NeighOrch による nexthop 解決とコールバック、RouteOrch による NHG 数上限管理と
refcount が不可欠な暗黙依存関係。これらは CONFIG_DB や YANG では一切表現されていない。
