# APPL_DB SRV6 テーブル — Phase C テーブル間クロスリファレンス スキャンノート

対象テーブル: `SRV6_MY_SID_TABLE` / `SRV6_SID_LIST_TABLE` (APPL_DB)
Consumer: `Srv6Orch` (`sonic-swss/orchagent/srv6orch.cpp`)
スキャン範囲: `createUpdateMysidEntry()` L1431-1649, `deleteMysidEntry()` L1651-1700, `createUpdateSidList()` L1020-1117, コンストラクタ L98-115 全行精読

---

## 検出したクロスリファレンス

### 1. SRV6_MY_SID_TABLE.vrf → VRF (CONFIG_DB) via VrfOrch

`createUpdateMysidEntry()` (`srv6orch.cpp:1480-1506`) は `mySidVrfRequired(end_behavior)` が true の行動
(`end.dt4`, `end.dt6`, `end.dt46`, `udt4`, `udt6`, `udt46`) の場合、`vrf` フィールドを VrfOrch で解決する。

- `vrf == "default"` の場合: `gVirtualRouterId` (グローバル仮想ルータ ID) を直接使用
- 非デフォルト VRF の場合: `m_vrfOrch->isVRFexists(dt_vrf)` で存在確認し `getVRFid()` で OID 取得

VRF が CONFIG_DB に存在しない場合は `SWSS_LOG_ERROR("VRF %s doesn't exist in DB")` を出力して `return false`。MySID エントリは SAI に登録されない。

**参照関係**: `APPL_DB SRV6_MY_SID_TABLE.vrf` → `CONFIG_DB VRF.name` (VrfOrch 経由 OID 解決、必須)

evidence: `srv6orch.cpp:1480-1502`

### 2. SRV6_MY_SID_TABLE.adj → Neighbor テーブル (STATE_DB) via NeighOrch

`createUpdateMysidEntry()` (`srv6orch.cpp:1511-1543`) は `mySidNextHopRequired(end_behavior)` が true の行動
(`end.x`, `end.dx4`, `end.dx6`, `ua`, `udx4`, `udx6` 等) の場合、`adj` フィールドで指定した IP アドレスを NeighOrch で解決する。

- `m_neighOrch->hasNextHop(nexthop)` で Neighbor の存在を確認
- `m_neighOrch->getNextHopId(nexthop)` で SAI next hop OID を取得

Neighbor が未確立の場合は `m_pendingSRv6MySIDEntries[nexthop]` に保留し、Neighbor ADD 通知で自動再処理。成功後 `m_neighOrch->increaseNextHopRefCount()` で参照カウントを増加する (`srv6orch.cpp:1644`)。MySID DEL 時は `decreaseNextHopRefCount()` で解放する (`srv6orch.cpp:1689`)。

**参照関係**: `APPL_DB SRV6_MY_SID_TABLE.adj` → Neighbor テーブル (NeighOrch) (OID 解決、adj 依存行動のみ)

evidence: `srv6orch.cpp:1511-1547`, `srv6orch.cpp:1644`, `srv6orch.cpp:1689`

### 3. SRV6_MY_SID_TABLE key → SRV6_MY_LOCATORS (CONFIG_DB) via m_locatorCfgTable

`Srv6Orch` コンストラクタ (`srv6orch.cpp:107`) は `m_locatorCfgTable(cfgDb, CFG_SRV6_MY_LOCATOR_TABLE_NAME)` で CONFIG_DB の `SRV6_MY_LOCATORS` テーブルへの直接 Table 参照を保持する。

`getLocatorCfgFromDb()` (`srv6orch.cpp:331-350`) は MySID エントリ処理時に locator 名で `SRV6_MY_LOCATORS` を HGET し、ビット長 (`block_len`, `node_len`, `func_len`, `arg_len`) を取得する。

ロケータが CONFIG_DB に存在しない場合は `SWSS_LOG_ERROR` を出力して `false` を返す。Orch 側に retry 機構はない。

**参照関係**: `APPL_DB SRV6_MY_SID_TABLE` key パラメータ → `CONFIG_DB SRV6_MY_LOCATORS` (HGET 直接参照、ビット長取得)

evidence: `srv6orch.cpp:107`, `srv6orch.cpp:331-350`

### 4. SRV6_SID_LIST_TABLE → SRv6 Nexthop テーブル (orch 内 sid_table_)

`createUpdateSidList()` (`srv6orch.cpp:1020-1117`) は SID リストを SAI `sai_srv6_sidlist_t` として作成し、`sid_table_[sid_name]` に格納する。`createSrv6Nexthop()` (`srv6orch.cpp:840-886`) が nexthop 作成時に `sid_table_[srv6_segment].nexthops.insert(nh)` で SID リストへの参照を登録する。

`deleteSidList()` (`srv6orch.cpp:1119-1144`) は `sid_table_[sid_name].nexthops.size() > 0` の場合 `task_need_retry` を返し、nexthop が参照中の SID リストを削除できない。nexthop を先に削除してから SID リストを削除する必要がある。

**参照関係**: SRv6 nexthop → `APPL_DB SRV6_SID_LIST_TABLE` (orch 内部 sid_table_ 経由の参照カウント、DEL 時に順序依存)

evidence: `srv6orch.cpp:875`, `srv6orch.cpp:1129-1133`

---

## クロスリファレンスサマリ

| 参照元 | 参照先 | 種別 | 必須条件 |
|--------|--------|------|----------|
| `SRV6_MY_SID_TABLE.vrf` | `CONFIG_DB VRF.name` (VrfOrch) | OID 解決 | VRF が先に CONFIG_DB に存在すること。`end.dt*`/`udt*` 行動のみ必須 |
| `SRV6_MY_SID_TABLE.adj` | Neighbor (NeighOrch) | OID 解決 | Neighbor 未解決は自動 pending。`end.x`/`ua` 等の行動のみ必須 |
| `SRV6_MY_SID_TABLE` key | `CONFIG_DB SRV6_MY_LOCATORS` | 直接 HGET (ビット長取得) | ロケータが CONFIG_DB に存在すること |
| SRv6 nexthop | `SRV6_SID_LIST_TABLE` | orch 内部参照カウント | SID リスト DEL 前に参照 nexthop を DEL すること |
