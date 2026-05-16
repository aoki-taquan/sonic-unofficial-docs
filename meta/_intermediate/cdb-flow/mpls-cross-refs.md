# MPLS — Phase C 暗黙参照 調査メモ (Task F)

調査日: 2026-05-16
対象ページ: `docs/reference/config-db/appl-mpls-route.md`
ソース: `sonic-net/sonic-swss/orchagent/mplsrouteorch.cpp`

---

## 概要

`docs/reference/config-db/mpls.md` は存在しない (skip)。
最近傍スラッグ `appl-mpls-route.md` に Phase C `<!-- cross-refs -->` ブロックを適用済み。
詳細証跡は `meta/_intermediate/cdb-flow/appl-mpls-route-cross-refs.md` を参照。

---

## 暗黙参照サマリ (mplsrouteorch.cpp 精読結果)

`APPL_DB:LABEL_ROUTE_TABLE` は YANG leafref を持たないが、`mplsrouteorch.cpp` が以下テーブル/オブジェクトを実行時に暗黙参照する。

| 参照先 | DB / Orch | 参照方向 | 必須度 | 証拠 |
|---|---|---|---|---|
| NextHop (IP / MPLS) | NeighOrch → SAI `next_hop` | 実行時参照 | 必須 | mplsrouteorch.cpp:514-540 |
| NEIGH (ARP/NDP) | `APPL_DB:NEIGH_TABLE` / kernel | 解決前提・未解決時 retry | 必須 (非 intf NH) | mplsrouteorch.cpp:520, 538, 559 |
| INTF (Router Interface) | IntfsOrch → SAI `router_interface` | 実行時参照 | 必須 (intf NH) | mplsrouteorch.cpp:503, 707 |
| NEXTHOP_GROUP | `APPL_DB:NEXT_HOP_GROUP_TABLE` (NhgOrch / CbfNhgOrch) | 実行時参照 (`nexthop_group` 指定時) | 条件付き必須 | mplsrouteorch.cpp:157-170, 256-267, 483-490 |
| VRF | `CONFIG_DB:VRF` (VrfOrch) | 実行時参照 (`Vrf<name>:` キー時) | 条件付き必須 | mplsrouteorch.cpp:107-118, 474, 957 |

## 適用ステータス

- `docs/reference/config-db/appl-mpls-route.md` L238-279: `<!-- cross-refs -->` ブロック適用済み (2026-05-15)
- `meta/_intermediate/cdb-flow/appl-mpls-route-cross-refs.md`: 詳細証跡ファイル存在
- `docs/reference/config-db/mpls.md`: 存在しないため skip
