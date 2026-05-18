# srv6-applb — Phase F 副作用調査メモ

調査日: 2026-05-18  
対象: `APPL_DB.SRV6_MY_SID_TABLE` / `APPL_DB.SRV6_SID_LIST_TABLE`  
根拠: `sonic-swss/orchagent/srv6orch.cpp` (ref: 4305596156d70e9797e8a881b3d19b46de0bce0d) 全行精読

---

## SRV6_MY_SID_TABLE SET 時の副作用

### 1. COUNTERS_DB への書き込み（条件付き）

`createUpdateMysidEntry()` L1592-1603 — 新規エントリかつ SAI カウンタ対応
(`getMySidCountersSupported() && getMySidCountersEnabled()`) の場合:

```cpp
auto ok = addMySidCounter(my_sid_entry, counter_oid);  // L1595
```

`addMySidCounter()` (L184-210) の処理:
- `FlowCounterHandler::createGenericCounter(counter_oid)` で SAI カウンタオブジェクト作成
- `m_mysid_counters_table->set("", fvs)` で `COUNTERS_DB.COUNTERS_SRV6_NAME_MAP` に `{key → oid}` を書き込む
- `m_pending_counters[counter_oid] = key` に pending 登録、1 秒タイマーで FlexCounter に OID を登録

### 2. CRM カウンタ更新

`gCrmOrch->incCrmResUsedCounter(CrmResourceType::CRM_SRV6_MY_SID_ENTRY)` (L1612)  
SAI `create_my_sid_entry()` 成功後に CRM の MySID エントリ使用数をインクリメント。

### 3. VRF 参照カウント増加（dt* 行動のみ）

`m_vrfOrch->increaseVrfRefCount(dt_vrf)` (L1639)  
`end.dt4` / `end.dt6` / `end.dt46` / `udt4` / `udt6` / `udt46` 行動で VRF OID 解決成功後に実行。
VRF が先に DEL されることを防ぐ（VrfOrch 側の参照カウントガード）。

### 4. NeighOrch 参照カウント増加（adj 依存行動のみ）

`m_neighOrch->increaseNextHopRefCount(nexthop, 1)` (L1644)  
`end.x` / `end.dx4` / `end.dx6` / `ua` / `udx4` / `udx6` 行動で Neighbor OID 解決成功後に実行。
Neighbor が先に DEL されることを防ぐ（NeighOrch 側の参照カウントガード）。

### 5. IP-in-IP トンネル + TermEntry 作成（DSCP モード行動のみ）

`mySidTunnelRequired()` が true の行動（DSCP モード設定が必要な SID）では:
- `createMySidIpInIpTunnel(dscp_mode, tunnel_oid)` (L1554) で SAI トンネルオブジェクトを作成
- `createMySidIpInIpTunnelTermEntry(tunnel_oid, sid_ip, term_entry_oid)` (L1561) でトンネル終端エントリを作成

---

## SRV6_MY_SID_TABLE DEL 時の副作用

`deleteMysidEntry()` (L1656-1710) の処理:

- `removeMySidCounter()` (L1677): `COUNTERS_DB.COUNTERS_SRV6_NAME_MAP` からエントリを削除、FlexCounter から OID 登録解除、SAI カウンタオブジェクト削除
- `gCrmOrch->decCrmResUsedCounter(CRM_SRV6_MY_SID_ENTRY)` (L1675): CRM カウンタをデクリメント
- `m_vrfOrch->decreaseVrfRefCount(vrf)` (L1683): VRF 参照カウントをデクリメント（dt* 行動のみ）
- `m_neighOrch->decreaseNextHopRefCount(nexthop, 1)` (L1689): Neighbor 参照カウントをデクリメント（adj 依存行動のみ）
- `removeMySidIpInIpTunnelTermEntry()` + `removeMySidIpInIpTunnel()` (L1698, L1704): トンネル削除（DSCP モードのみ）

---

## SRV6_SID_LIST_TABLE SET/DEL 時の副作用

**SET**: SAI `create_srv6_sidlist()` または `set_srv6_sidlist_attribute()` のみ。COUNTERS_DB / CRM への副作用なし。

**DEL**: `deleteSidList()` は `sid_table_[sid_name].nexthops.size()` が 0 のときのみ SAI `remove_srv6_sidlist()` を実行。nexthop 参照が残存する場合は `task_need_retry` を返す（副作用は発生しない）。  
SRv6 nexthop 登録時に `sid_table_[seg].nexthops.insert(nh)` (L875) が実行され、解放時に `nexthops.erase(nh)` が実行される。

---

## 副作用マトリクス（サマリ）

| 操作 | COUNTERS_DB 書き込み | CRM 更新 | VRF refcount | Neighbor refcount | IP-in-IP トンネル |
|------|---------------------|----------|-------------|-------------------|-----------------|
| MY_SID_TABLE SET（新規） | あり（SAI 対応時のみ） | +1 | +1（dt* のみ） | +1（adj 依存のみ） | 作成（DSCP 必要時） |
| MY_SID_TABLE UPDATE | なし | なし | 条件付き変化 | 条件付き変化 | なし |
| MY_SID_TABLE DEL | あり（削除） | -1 | -1（dt* のみ） | -1（adj 依存のみ） | 削除（DSCP あり時） |
| SID_LIST_TABLE SET | なし | なし | なし | なし | なし |
| SID_LIST_TABLE DEL | なし | なし | なし | なし | なし |
