# NEIGH テーブル Phase F — 副次 DB 書込みスキャンノート

調査日: 2026-05-18
対象テーブル: CONFIG_DB `NEIGH`
主要ソース:
- `sonic-swss/cfgmgr/nbrmgr.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)
- `sonic-swss/orchagent/neighorch.cpp` (SHA: 4305596156d70e9797e8a881b3d19b46de0bce0d)

---

## 調査対象の 2 経路

CONFIG_DB `NEIGH` テーブルに関わる処理は 2 つの独立した経路がある。

1. **CONFIG_DB NEIGH → `nbrmgrd` → Linux kernel (Netlink)**: スタティック neighbor の設定経路
2. **APPL_DB NEIGH_TABLE → `NeighOrch` → SAI → ASIC**: 動的 neighbor の ASIC プログラミング経路（neighsyncd 経由）

---

## 経路 1: CONFIG_DB NEIGH → nbrmgrd

### DB 書込み

`nbrmgrd` (`NbrMgr::doSetNeighTask`, `setNeighbor`) は以下の DB に書込みを行わない:

- **APPL_DB**: `reconcileNeighResolveTable()` は `NEIGH_RESOLVE_TABLE` を **読むだけ** (getKeys/hget のみ)。書込みなし。
- **STATE_DB**: `isIntfStateOk()` / `isNeighRestoreDone()` は読み取りのみ。`nbrmgrd` は STATE_DB への書込みを行わない。
- **COUNTERS_DB / ASIC_DB / FLEX_COUNTER_DB**: 参照なし。

### 副作用

nbrmgrd の副作用は **Linux カーネルの neighbor テーブル変更のみ**:
- `RTM_NEWNEIGH` (Netlink): `NUD_PERMANENT` または `NUD_DELAY+NTF_USE` でカーネル neighbor テーブルに書込み
- カーネル ARP/NDP 解決トリガー: `NTF_USE` フラグ付き `RTM_NEWNEIGH` によりカーネルが ARP/NDP 解決を開始し、ネットワークへ ARP/NS パケットが送出される

---

## 経路 2: APPL_DB NEIGH_TABLE → NeighOrch

（CONFIG_DB NEIGH は直接この経路を通らないが、下流 ASIC プログラミングに関わるため記載）

### DB 書込み一覧

| 副次 DB | テーブル | 操作 | 条件 | evidence |
|---|---|---|---|---|
| APPL_DB | `NEIGH_RESOLVE_TABLE` (`APP_NEIGH_RESOLVE_TABLE_NAME`) | SET（解決要求） | MAC がゼロ（未解決）の neighbor が SET 操作で来たとき | `neighorch.cpp:121` (`resolveNeighborEntry`) |
| APPL_DB | `NEIGH_RESOLVE_TABLE` | DEL（解決完了後削除） | MAC 確定後の neighbor 追加成功時 | `neighorch.cpp:140` (`clearResolvedNeighborEntry`) |
| STATE_DB | `STATE_SYSTEM_NEIGH_TABLE_NAME` | SET / DEL | **VoQ 環境のみ** (`switch_type == "voq"`)。リモート system neighbor のステータス反映 | `neighorch.cpp:2223, 2173, 2260` |
| CHASSIS_APP_DB | `CHASSIS_APP_SYSTEM_NEIGH_TABLE_NAME` | SET / DEL | **VoQ 環境のみ**。シャーシレベルの system neighbor テーブルへの書込み | `neighorch.cpp:2654, 2688` |

### CRM カウンタ更新（COUNTERS_DB 間接更新）

`gCrmOrch->incCrmResUsedCounter` / `decCrmResUsedCounter` を通じて `COUNTERS_DB` の CRM カウンタが更新される:

| CRM リソース | inc 条件 | dec 条件 |
|---|---|---|
| `CRM_IPV4_NEIGHBOR` | IPv4 neighbor SAI 作成成功 | neighbor SAI 削除成功 |
| `CRM_IPV6_NEIGHBOR` | IPv6 neighbor SAI 作成成功 | neighbor SAI 削除成功 |
| `CRM_IPV4_NEXTHOP` | IPv4 next hop SAI 作成成功 | next hop SAI 削除成功 |
| `CRM_IPV6_NEXTHOP` | IPv6 next hop SAI 作成成功 | next hop SAI 削除成功 |
| `CRM_IPV4_ROUTE` | prefix route 追加成功（`addPrefixRouteForNeighbor`） | prefix route 削除成功 |
| `CRM_IPV6_ROUTE` | prefix route 追加成功（`addPrefixRouteForNeighbor`） | prefix route 削除成功 |

---

## まとめ

| 経路 | 副次 DB 書込み | カーネル副作用 |
|---|---|---|
| CONFIG_DB NEIGH → nbrmgrd | なし | カーネル neighbor テーブル変更（RTM_NEWNEIGH）、ARP/NDP トリガー |
| APPL_DB NEIGH_TABLE → NeighOrch | APPL_DB NEIGH_RESOLVE_TABLE, STATE_DB STATE_SYSTEM_NEIGH (VoQ), CHASSIS_APP_DB SYSTEM_NEIGH (VoQ), COUNTERS_DB CRM カウンタ | ASIC SAI プログラミング |
