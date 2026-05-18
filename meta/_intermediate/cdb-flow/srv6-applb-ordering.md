# APPL_DB SRV6 テーブル — Phase B 書込み順依存スキャンノート

対象テーブル: `SRV6_MY_SID_TABLE` / `SRV6_SID_LIST_TABLE` (APPL_DB)
Consumer: `Srv6Orch` (`sonic-swss/orchagent/srv6orch.cpp`)
スキャン範囲: `createUpdateMysidEntry()`, `updateNeighbor()`, `doTaskSidTable()`, `createUpdateSidList()`, `sidListExists()` 全行精読

---

## 検出した順序依存・タイミング依存

### 1. SRV6_MY_SID_TABLE の adj フィールド — 隣接 (Neighbor) 先行必須

`createUpdateMysidEntry()` (`srv6orch.cpp:1511-1543`) は `mySidNextHopRequired(end_behavior)` が true の行動
(`end.x`, `ua`, `udx4`, `udx6` 等) の場合に `adj` フィールドで指定した IP アドレスを Neighbor として解決しようとする。

`m_neighOrch->hasNextHop(nexthop)` が false、または `getNextHopId()` が `SAI_NULL_OBJECT_ID` を返す場合:
- エントリを `m_pendingSRv6MySIDEntries[nexthop]` に追加して `return false`
- SAI への MySID 登録は保留される

`updateNeighbor()` (`srv6orch.cpp:1212-1341`) が隣接 ADD 通知を受け取ると:
- `m_pendingSRv6MySIDEntries` を走査し、対応する nexthop の全 pending エントリを `createUpdateMysidEntry()` で再処理
- 成功した場合のみ pending リストから削除

**順序依存**: `adj` を持つ MySID エントリを APPL_DB に書く前に、対応するネイバーが確立されていることが推奨される。逆順でも最終的には Neighbor ADD イベントで自動解決されるが、ネイバー確立まで SAI への MySID 登録は保留される。

evidence: `srv6orch.cpp:1511-1543`, `srv6orch.cpp:1224-1259`

### 2. Neighbor DEL 時の MySID ロールバック → pending 再登録

`updateNeighbor()` DEL パス (`srv6orch.cpp:1266-1341`) は隣接 DELETE 通知を受け取ると:
- ASIC に登録済みで対応 adj を持つ全 MySID エントリを `deleteMysidEntry()` で SAI から削除
- 削除したエントリを `m_pendingSRv6MySIDEntries` に再登録（隣接が再確立されれば自動再 install）

**順序依存 (DEL 時)**: Neighbor が削除されると、そのネイバーを adj として参照する全 MySID が SAI から自動削除される。意図しない MySID 削除を防ぐには、MySID エントリを先に DEL してからネイバーを削除する順序を推奨する。

evidence: `srv6orch.cpp:1266-1341`

### 3. SRV6_SID_LIST_TABLE は SRV6_MY_SID_TABLE と独立

`doTaskSidTable()` (`srv6orch.cpp:1146-1186`) は `SRV6_SID_LIST_TABLE` を処理し、
`doTaskMySidTable()` は `SRV6_MY_SID_TABLE` を処理する。両者は Consumer が別 (`m_sidTable` / `m_mysidTable`)
であり、`SRV6_SID_LIST_TABLE` が `SRV6_MY_SID_TABLE` の前に存在する必要はない（MySID の行動は SID リストを直接参照しないため）。

**順序依存なし**: `SRV6_SID_LIST_TABLE` と `SRV6_MY_SID_TABLE` の書き込み順序は任意。

evidence: `srv6orch.cpp:1146-1186`, `srv6orch.cpp:2362-2384`

---

## 順序依存サマリ

| # | 依存関係 | 方向 | 緩和策 |
|---|----------|------|--------|
| 1 | `adj` 依存行動の MySID — Neighbor 先行推奨 | 先行推奨（逆順は pending 自動解決） | `updateNeighbor()` ADD 通知で自動再処理 |
| 2 | Neighbor DEL 時、MySID が自動 SAI 削除 → pending 再登録 | 自動 (意図しない削除に注意) | MySID DEL → Neighbor DEL の順序を推奨 |
| 3 | `SRV6_SID_LIST_TABLE` vs `SRV6_MY_SID_TABLE` | 順序依存なし | — |
